import secrets
import time
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode
import httpx
from fastapi import HTTPException
from sqlalchemy.orm import Session
from ..config import get_settings
from ..models import SocialAccount
from ..security import decrypt_token, encrypt_token

STATES: dict[str, tuple[str, float]] = {}
SCOPES = {
    "youtube": "https://www.googleapis.com/auth/youtube.upload https://www.googleapis.com/auth/youtube.readonly",
    "instagram": "pages_show_list pages_manage_posts instagram_content_publish business_management",
    "facebook": "pages_show_list pages_manage_posts pages_read_engagement",
}


def start_oauth(platform: str) -> str:
    settings = get_settings()
    state = secrets.token_urlsafe(32)
    STATES[state] = (platform, time.time() + 600)
    redirect_uri = settings.app_base_url.rstrip("/") + "/api/social/oauth/callback"
    if platform == "youtube":
        if not settings.google_client_id or not settings.google_client_secret:
            raise HTTPException(400, "Google OAuth credentials are missing. Complete docs/SOCIAL_API.md and update .env.")
        params = {"client_id": settings.google_client_id, "redirect_uri": redirect_uri, "response_type": "code",
                  "scope": SCOPES[platform], "access_type": "offline", "prompt": "consent", "state": state}
        return "https://accounts.google.com/o/oauth2/v2/auth?" + urlencode(params)
    if platform in {"instagram", "facebook"}:
        if not settings.meta_app_id or not settings.meta_app_secret:
            raise HTTPException(400, "Meta app credentials are missing. Complete docs/SOCIAL_API.md and update .env.")
        params = {"client_id": settings.meta_app_id, "redirect_uri": redirect_uri, "response_type": "code",
                  "scope": SCOPES[platform], "state": state}
        return "https://www.facebook.com/" + getattr(settings, "meta_graph_version", "v23.0") + "/dialog/oauth?" + urlencode(params)
    raise HTTPException(404, "Unsupported platform")


def _upsert(db: Session, platform: str, account_id: str, name: str, token: str, refresh: str = "", expires: int | None = None, scopes: str = "") -> None:
    account = db.query(SocialAccount).filter(SocialAccount.platform == platform, SocialAccount.platform_account_id == account_id).first()
    if not account:
        account = SocialAccount(platform=platform, platform_account_id=account_id)
        db.add(account)
    account.display_name = name
    account.access_token_encrypted = encrypt_token(token)
    if refresh:
        account.refresh_token_encrypted = encrypt_token(refresh)
    account.token_expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires) if expires else None
    account.scopes = scopes
    account.status = "connected"


def ensure_fresh_token(db: Session, account: SocialAccount) -> None:
    expires = account.token_expires_at
    if expires and expires.tzinfo is None:
        expires = expires.replace(tzinfo=timezone.utc)
    if not expires or expires > datetime.now(timezone.utc) + timedelta(seconds=90):
        return
    if account.platform == "youtube" and account.refresh_token_encrypted:
        settings = get_settings()
        response = httpx.post("https://oauth2.googleapis.com/token", data={
            "client_id": settings.google_client_id, "client_secret": settings.google_client_secret,
            "refresh_token": decrypt_token(account.refresh_token_encrypted), "grant_type": "refresh_token"}, timeout=60)
        data = response.json()
        if response.is_error or not data.get("access_token"):
            account.status = "expired"
            db.commit()
            raise RuntimeError("YouTube token refresh failed; reconnect the account")
        account.access_token_encrypted = encrypt_token(data["access_token"])
        account.token_expires_at = datetime.now(timezone.utc) + timedelta(seconds=data.get("expires_in", 3600))
        account.status = "connected"
        db.commit()
        return
    account.status = "expired"
    db.commit()
    raise RuntimeError(f"{account.platform.title()} access token expired; reconnect the account")


def complete_oauth(db: Session, code: str, state: str) -> str:
    saved = STATES.pop(state, None)
    if not saved or saved[1] < time.time():
        raise HTTPException(400, "OAuth state is invalid or expired; restart account connection")
    platform = saved[0]
    settings = get_settings()
    redirect_uri = settings.app_base_url.rstrip("/") + "/api/social/oauth/callback"
    with httpx.Client(timeout=60) as client:
        if platform == "youtube":
            response = client.post("https://oauth2.googleapis.com/token", data={
                "code": code, "client_id": settings.google_client_id, "client_secret": settings.google_client_secret,
                "redirect_uri": redirect_uri, "grant_type": "authorization_code"})
            data = response.json()
            if response.is_error or not data.get("access_token"):
                raise HTTPException(400, "Google token exchange failed; verify credentials and redirect URI")
            channels = client.get("https://www.googleapis.com/youtube/v3/channels", params={"part": "snippet", "mine": "true"},
                                  headers={"Authorization": f"Bearer {data['access_token']}"}).json()
            items = channels.get("items", [])
            if not items:
                raise HTTPException(400, "The connected Google account has no YouTube channel")
            channel = items[0]
            _upsert(db, platform, channel["id"], channel.get("snippet", {}).get("title", "YouTube channel"),
                    data["access_token"], data.get("refresh_token", ""), data.get("expires_in"), SCOPES[platform])
        else:
            version = getattr(settings, "meta_graph_version", "v23.0")
            token_response = client.get(f"https://graph.facebook.com/{version}/oauth/access_token", params={
                "client_id": settings.meta_app_id, "client_secret": settings.meta_app_secret,
                "redirect_uri": redirect_uri, "code": code})
            token_data = token_response.json()
            if token_response.is_error or not token_data.get("access_token"):
                raise HTTPException(400, "Meta token exchange failed; verify app credentials and redirect URI")
            long_lived = client.get(f"https://graph.facebook.com/{version}/oauth/access_token", params={
                "grant_type": "fb_exchange_token", "client_id": settings.meta_app_id, "client_secret": settings.meta_app_secret,
                "fb_exchange_token": token_data["access_token"]}).json()
            token = long_lived.get("access_token", token_data["access_token"])
            expires = long_lived.get("expires_in", token_data.get("expires_in"))
            pages_response = client.get(f"https://graph.facebook.com/{version}/me/accounts", params={
                "fields": "id,name,access_token,instagram_business_account{id,username}", "access_token": token})
            pages = pages_response.json().get("data", [])
            added = 0
            for page in pages:
                page_token = page.get("access_token", token)
                if platform == "facebook":
                    _upsert(db, platform, page["id"], page.get("name", "Facebook Page"), page_token, expires=expires, scopes=SCOPES[platform])
                    added += 1
                elif page.get("instagram_business_account"):
                    ig = page["instagram_business_account"]
                    _upsert(db, platform, ig["id"], ig.get("username", "Instagram Business"), page_token, expires=expires, scopes=SCOPES[platform])
                    added += 1
            if not added:
                message = "No eligible Facebook Pages found" if platform == "facebook" else "No Instagram Business/Creator account linked to an authorized Facebook Page"
                raise HTTPException(400, message)
    db.commit()
    return platform
