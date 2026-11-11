import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin
import httpx
from ..config import get_settings
from ..models import PublishJob, Reel, SocialAccount
from ..security import decrypt_token

YOUTUBE_UPLOAD = "https://www.googleapis.com/upload/youtube/v3/videos"


class PublishError(RuntimeError):
    pass


def _response(response: httpx.Response) -> dict:
    try:
        data = response.json()
    except ValueError:
        data = {}
    if response.is_error:
        detail = data.get("error", {})
        if isinstance(detail, dict):
            detail = detail.get("message", str(detail))
        raise PublishError(f"Platform API returned {response.status_code}: {detail or response.text[:500]}")
    return data


def _caption(reel: Reel) -> str:
    return "\n\n".join(part for part in [reel.description.strip(), reel.hashtags.strip()] if part)


def _public_url(reel: Reel) -> str:
    settings = get_settings()
    if not settings.public_media_base_url:
        raise PublishError("PUBLIC_MEDIA_BASE_URL is required for Instagram. Configure a public HTTPS host for storage/reels; see docs/SOCIAL_API.md.")
    return settings.public_media_base_url.rstrip("/") + "/" + Path(reel.output_path or "").name


def publish_youtube(job: PublishJob, reel: Reel, account: SocialAccount) -> tuple[str, str | None, str]:
    token = decrypt_token(account.access_token_encrypted)
    headers = {"Authorization": f"Bearer {token}"}
    status: dict = {"privacyStatus": "private", "selfDeclaredMadeForKids": False}
    if job.scheduled_at:
        status["publishAt"] = job.scheduled_at.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    metadata = {"snippet": {"title": reel.title[:100], "description": _caption(reel)[:5000], "categoryId": "22"}, "status": status}
    path = Path(reel.output_path or "")
    with httpx.Client(timeout=120) as client:
        start = client.post(YOUTUBE_UPLOAD, params={"uploadType": "resumable", "part": "snippet,status"},
                            headers={**headers, "X-Upload-Content-Type": "video/mp4", "X-Upload-Content-Length": str(path.stat().st_size)},
                            json=metadata)
        if start.is_error:
            _response(start)
        upload_url = start.headers.get("Location")
        if not upload_url:
            raise PublishError("YouTube did not return a resumable upload URL")
        with path.open("rb") as media:
            uploaded = client.put(upload_url, headers={**headers, "Content-Type": "video/mp4"}, content=media.read())
        data = _response(uploaded)
    video_id = data.get("id")
    if not video_id:
        raise PublishError("YouTube response did not confirm a video ID")
    return video_id, f"https://www.youtube.com/watch?v={video_id}", "scheduled" if job.scheduled_at else "published"


def publish_instagram(job: PublishJob, reel: Reel, account: SocialAccount) -> tuple[str, str | None, str]:
    if job.scheduled_at:
        raise PublishError("Instagram scheduling is not supported by this integration; publish now or use Meta Business Suite")
    settings = get_settings()
    token = decrypt_token(account.access_token_encrypted)
    api = f"https://graph.facebook.com/{getattr(settings, 'meta_graph_version', 'v23.0')}"
    ig_id = account.platform_account_id
    with httpx.Client(timeout=120) as client:
        created = _response(client.post(f"{api}/{ig_id}/media", data={
            "media_type": "REELS", "video_url": _public_url(reel), "caption": _caption(reel),
            "share_to_feed": "true", "access_token": token,
        }))
        container_id = created.get("id")
        if not container_id:
            raise PublishError("Instagram did not create a media container")
        for _ in range(30):
            state = _response(client.get(f"{api}/{container_id}", params={"fields": "status_code", "access_token": token}))
            status = state.get("status_code")
            if status == "FINISHED":
                break
            if status in {"ERROR", "EXPIRED"}:
                raise PublishError(f"Instagram media processing failed with status {status}")
            time.sleep(10)
        else:
            raise PublishError("Instagram media is still processing; retry later")
        published = _response(client.post(f"{api}/{ig_id}/media_publish", data={"creation_id": container_id, "access_token": token}))
    media_id = published.get("id")
    if not media_id:
        raise PublishError("Instagram did not confirm publication")
    return media_id, None, "published"


def publish_facebook(job: PublishJob, reel: Reel, account: SocialAccount) -> tuple[str, str | None, str]:
    token = decrypt_token(account.access_token_encrypted)
    settings = get_settings()
    api = f"https://graph.facebook.com/{getattr(settings, 'meta_graph_version', 'v23.0')}"
    page_id = account.platform_account_id
    path = Path(reel.output_path or "")
    with httpx.Client(timeout=180) as client:
        started = _response(client.post(f"{api}/{page_id}/video_reels", data={"upload_phase": "start", "access_token": token}))
        video_id, upload_url = started.get("video_id"), started.get("upload_url")
        if not video_id or not upload_url:
            raise PublishError("Facebook did not start a Reels upload")
        with path.open("rb") as media:
            uploaded = client.post(upload_url, headers={"Authorization": f"OAuth {token}", "offset": "0", "file_size": str(path.stat().st_size)}, content=media.read())
        _response(uploaded)
        finish_data = {"upload_phase": "finish", "video_id": video_id, "description": _caption(reel), "access_token": token,
                       "video_state": "SCHEDULED" if job.scheduled_at else "PUBLISHED"}
        if job.scheduled_at:
            finish_data["scheduled_publish_time"] = str(int(job.scheduled_at.timestamp()))
        finished = _response(client.post(f"{api}/{page_id}/video_reels", data=finish_data))
    if finished.get("success") is not True:
        raise PublishError("Facebook did not confirm the Reels publish request")
    return video_id, f"https://www.facebook.com/{video_id}", "scheduled" if job.scheduled_at else "published"


PUBLISHERS = {"youtube": publish_youtube, "instagram": publish_instagram, "facebook": publish_facebook}
