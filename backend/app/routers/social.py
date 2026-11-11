import asyncio
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import PublishJob, Reel, SocialAccount
from ..schemas import AccountOut, PublishCreate, PublishOut
from ..security import idempotency_digest
from ..services.oauth import complete_oauth, start_oauth
from ..services.publishing import dispatch_due_jobs

router = APIRouter(prefix="/social", tags=["social publishing"])
SUPPORTED = {"youtube", "instagram", "facebook"}


@router.get("/accounts", response_model=list[AccountOut])
def accounts(db: Session = Depends(get_db)):
    return db.query(SocialAccount).order_by(SocialAccount.platform, SocialAccount.display_name).all()


@router.get("/oauth/{platform}/start")
def oauth_start(platform: str):
    if platform not in SUPPORTED:
        raise HTTPException(404, "Unsupported platform")
    return {"authorization_url": start_oauth(platform)}


@router.get("/oauth/callback", response_class=HTMLResponse)
def oauth_callback(code: str = Query(...), state: str = Query(...), db: Session = Depends(get_db)):
    platform = complete_oauth(db, code, state)
    return f"""<!doctype html><html><head><title>Account connected</title></head><body style='font-family:Arial;background:#111;color:#eee;padding:40px'><h1>{platform.title()} connected</h1><p>You can close this window and return to Jimsa Autoreel Agent.</p><script>if(window.opener)window.opener.postMessage({{type:'jimsa-social-connected'}},'*');</script></body></html>"""


@router.delete("/accounts/{account_id}", status_code=204)
def disconnect(account_id: int, db: Session = Depends(get_db)):
    account = db.get(SocialAccount, account_id)
    if not account:
        raise HTTPException(404, "Account not found")
    active = db.query(PublishJob).filter(PublishJob.account_id == account_id, PublishJob.status.in_(["queued", "scheduled", "uploading"])).first()
    if active:
        raise HTTPException(409, "Cancel this account's active publishing jobs before disconnecting")
    db.delete(account)
    db.commit()


def serialize(job: PublishJob) -> PublishOut:
    data = PublishOut.model_validate(job)
    data.reel_title = job.reel.title
    data.account_name = job.account.display_name
    return data


@router.get("/publish-jobs", response_model=list[PublishOut])
def publish_jobs(db: Session = Depends(get_db)):
    dispatch_due_jobs()
    jobs = db.query(PublishJob).order_by(PublishJob.created_at.desc()).limit(200).all()
    return [serialize(job) for job in jobs]


@router.post("/reels/{reel_id}/publish", response_model=PublishOut, status_code=201)
def queue_publish(reel_id: int, payload: PublishCreate, db: Session = Depends(get_db)):
    reel = db.get(Reel, reel_id)
    if not reel or reel.status != "exported" or not reel.output_path:
        raise HTTPException(409, "Export the reel successfully before publishing")
    account = db.get(SocialAccount, payload.account_id)
    if not account or account.status != "connected":
        raise HTTPException(400, "Connect a valid social account first")
    scheduled = payload.scheduled_at
    if scheduled and scheduled.tzinfo is None:
        scheduled = scheduled.replace(tzinfo=timezone.utc)
    if scheduled and scheduled <= datetime.now(timezone.utc):
        raise HTTPException(422, "Scheduled time must be in the future")
    if scheduled and account.platform == "instagram":
        raise HTTPException(422, "Instagram scheduling is not supported by this integration")
    duplicate = db.query(PublishJob).filter(PublishJob.reel_id == reel_id, PublishJob.account_id == account.id,
                                            PublishJob.status.in_(["queued", "scheduled", "uploading", "published"])).first()
    if duplicate:
        raise HTTPException(409, f"This reel already has publishing job #{duplicate.id} for the selected account")
    key = idempotency_digest(reel_id, account.id, reel.updated_at.isoformat())
    job = PublishJob(reel_id=reel_id, account_id=account.id, platform=account.platform,
                     status="queued", scheduled_at=scheduled, idempotency_key=key)
    db.add(job)
    db.commit()
    db.refresh(job)
    dispatch_due_jobs()
    return serialize(job)


@router.post("/publish-jobs/{job_id}/retry", response_model=PublishOut)
def retry(job_id: int, db: Session = Depends(get_db)):
    job = db.get(PublishJob, job_id)
    if not job:
        raise HTTPException(404, "Publishing job not found")
    if job.status not in {"failed", "cancelled"}:
        raise HTTPException(409, "Only failed or cancelled jobs can be retried")
    job.status = "queued"
    job.error = None
    job.scheduled_at = None
    db.commit()
    dispatch_due_jobs()
    return serialize(job)


@router.post("/publish-jobs/{job_id}/cancel", response_model=PublishOut)
def cancel(job_id: int, db: Session = Depends(get_db)):
    job = db.get(PublishJob, job_id)
    if not job:
        raise HTTPException(404, "Publishing job not found")
    if job.status not in {"queued", "scheduled"}:
        raise HTTPException(409, "Only queued or scheduled jobs can be cancelled safely")
    job.status = "cancelled"
    db.commit()
    return serialize(job)
