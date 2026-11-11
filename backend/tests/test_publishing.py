from datetime import datetime, timedelta, timezone
from uuid import uuid4
import pytest
from app.config import get_settings
from app.database import SessionLocal
from app.models import Project, PublishJob, Reel, SocialAccount, Video
from app.services.publishing import execute_publish
from app.services.publishers import PublishError


def make_exported_reel():
    output = get_settings().reels_dir / "publish-test.mp4"
    output.write_bytes(b"test-video-content")
    with SessionLocal() as db:
        project = Project(name="Publishing")
        db.add(project); db.flush()
        video = Video(project_id=project.id, original_name="source.mp4", file_path=f"source-{uuid4().hex}.mp4", file_size=100, duration=20)
        db.add(video); db.flush()
        reel = Reel(video_id=video.id, title="Publish me", start=0, end=10, status="exported", output_path=str(output))
        db.add(reel); db.flush()
        account = SocialAccount(platform="youtube", platform_account_id=f"channel-{uuid4().hex}", display_name="Test channel", access_token_encrypted="")
        db.add(account); db.commit()
        return reel.id, account.id


def test_duplicate_scheduling_and_cancel(client, monkeypatch):
    import app.routers.social as social_router
    monkeypatch.setattr(social_router, "dispatch_due_jobs", lambda: 0)
    reel_id, account_id = make_exported_reel()
    future = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
    response = client.post(f"/api/social/reels/{reel_id}/publish", json={"account_id": account_id, "scheduled_at": future})
    assert response.status_code == 201, response.text
    job = response.json()
    assert job["status"] == "queued"
    duplicate = client.post(f"/api/social/reels/{reel_id}/publish", json={"account_id": account_id, "scheduled_at": future})
    assert duplicate.status_code == 409
    cancelled = client.post(f"/api/social/publish-jobs/{job['id']}/cancel")
    assert cancelled.status_code == 200 and cancelled.json()["status"] == "cancelled"


def test_instagram_schedule_rejected_before_submission(client):
    reel_id, _ = make_exported_reel()
    with SessionLocal() as db:
        account = SocialAccount(platform="instagram", platform_account_id="ig-1", display_name="IG")
        db.add(account); db.commit(); account_id = account.id
    future = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
    response = client.post(f"/api/social/reels/{reel_id}/publish", json={"account_id": account_id, "scheduled_at": future})
    assert response.status_code == 422
    assert "not supported" in response.json()["detail"]


def test_failed_publish_never_marks_published(monkeypatch):
    reel_id, account_id = make_exported_reel()
    with SessionLocal() as db:
        job = PublishJob(reel_id=reel_id, account_id=account_id, platform="youtube", idempotency_key=f"test-{reel_id}-{account_id}")
        db.add(job); db.commit(); job_id = job.id
    def fail(*_args):
        raise PublishError("Simulated platform rejection")
    import app.services.publishing as service
    monkeypatch.setitem(service.PUBLISHERS, "youtube", fail)
    with pytest.raises(PublishError):
        execute_publish(job_id)
    with SessionLocal() as db:
        job = db.get(PublishJob, job_id)
        assert job.status == "failed"
        assert job.published_at is None
        assert "Simulated" in job.error
        assert job.attempts == 1


def test_confirmed_response_controls_status(monkeypatch):
    reel_id, account_id = make_exported_reel()
    with SessionLocal() as db:
        job = PublishJob(reel_id=reel_id, account_id=account_id, platform="youtube", idempotency_key=f"confirm-{reel_id}-{account_id}")
        db.add(job); db.commit(); job_id = job.id
    import app.services.publishing as service
    monkeypatch.setitem(service.PUBLISHERS, "youtube", lambda *_args: ("video-123", "https://youtube.test/v/123", "published"))
    execute_publish(job_id)
    with SessionLocal() as db:
        job = db.get(PublishJob, job_id)
        assert job.status == "published"
        assert job.platform_post_id == "video-123"
        assert job.published_at is not None
