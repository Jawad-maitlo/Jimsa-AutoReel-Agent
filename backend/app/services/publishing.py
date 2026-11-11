import logging
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from ..database import SessionLocal
from ..models import ProcessingJob, PublishJob, Reel
from .oauth import ensure_fresh_token
from .publishers import PUBLISHERS
from .tasks import TaskContext, manager

logger = logging.getLogger(__name__)


def execute_publish(job_id: int, context: TaskContext | None = None) -> None:
    with SessionLocal() as db:
        job = db.get(PublishJob, job_id)
        if not job or job.status in {"published", "cancelled"}:
            return
        reel = db.get(Reel, job.reel_id)
        if not reel or reel.status != "exported" or not reel.output_path:
            raise ValueError("Reel must be exported successfully before publishing")
        job.status = "uploading"
        job.attempts += 1
        job.error = None
        db.commit()
        account = job.account
        try:
            ensure_fresh_token(db, account)
            publisher = PUBLISHERS[job.platform]
            post_id, url, result_status = publisher(job, reel, account)
            job.platform_post_id = post_id
            job.platform_url = url
            job.status = result_status
            job.published_at = datetime.now(timezone.utc) if result_status == "published" else None
            db.commit()
        except Exception as exc:
            job.status = "failed"
            job.error = str(exc)[:3000]
            db.commit()
            logger.error("Publishing job %s failed: %s", job.id, exc)
            raise


def dispatch_due_jobs() -> int:
    now = datetime.now(timezone.utc)
    count = 0
    with SessionLocal() as db:
        jobs = db.query(PublishJob).filter(PublishJob.status.in_(["queued", "scheduled"])).all()
        for job in jobs:
            scheduled = job.scheduled_at
            if scheduled and scheduled.tzinfo is None:
                scheduled = scheduled.replace(tzinfo=timezone.utc)
            # YouTube and Facebook receive their future publish time immediately;
            # only a platform-confirmed response changes the job to scheduled.
            if scheduled and scheduled > now and job.platform not in {"youtube", "facebook"}:
                if job.status != "scheduled":
                    job.status = "scheduled"
                    db.commit()
                continue
            active = db.query(ProcessingJob).filter(ProcessingJob.kind == "publish", ProcessingJob.entity_id == job.id,
                                                     ProcessingJob.status.in_(["queued", "running"])).first()
            if not active:
                manager.submit("publish", job.id, lambda context, jid=job.id: execute_publish(jid, context))
                count += 1
    return count
