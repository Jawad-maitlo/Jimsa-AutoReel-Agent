import logging
import threading
import traceback
import uuid
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from ..database import SessionLocal
from ..models import ProcessingJob

logger = logging.getLogger(__name__)


class CancelledError(Exception):
    pass


class TaskContext:
    def __init__(self, job_id: str):
        self.job_id = job_id

    def update(self, progress: float, stage: str) -> None:
        with SessionLocal() as db:
            job = db.get(ProcessingJob, self.job_id)
            if job:
                if job.cancel_requested:
                    raise CancelledError("Processing cancelled by user")
                job.progress = max(0, min(100, progress))
                job.stage = stage[:180]
                job.status = "running"
                job.updated_at = datetime.now(timezone.utc)
                db.commit()

    def check_cancelled(self) -> None:
        with SessionLocal() as db:
            job = db.get(ProcessingJob, self.job_id)
            if job and job.cancel_requested:
                raise CancelledError("Processing cancelled by user")


class TaskManager:
    def __init__(self, workers: int = 4):
        self.executor = ThreadPoolExecutor(max_workers=workers, thread_name_prefix="jimsa")
        self._processes: dict[str, object] = {}
        self._lock = threading.Lock()

    def submit(self, kind: str, entity_id: int, work: Callable[[TaskContext], None]) -> ProcessingJob:
        job_id = str(uuid.uuid4())
        with SessionLocal() as db:
            active = db.query(ProcessingJob).filter(
                ProcessingJob.kind == kind,
                ProcessingJob.entity_id == entity_id,
                ProcessingJob.status.in_(["queued", "running"]),
            ).first()
            if active:
                return active
            job = ProcessingJob(id=job_id, kind=kind, entity_id=entity_id)
            db.add(job)
            db.commit()
            db.refresh(job)
        self.executor.submit(self._run, job_id, work)
        return job

    def _run(self, job_id: str, work: Callable[[TaskContext], None]) -> None:
        context = TaskContext(job_id)
        try:
            context.update(1, "Starting")
            work(context)
            with SessionLocal() as db:
                job = db.get(ProcessingJob, job_id)
                if job:
                    job.status = "completed"
                    job.progress = 100
                    job.stage = "Completed"
                    db.commit()
        except CancelledError as exc:
            self._finish(job_id, "cancelled", str(exc))
        except Exception as exc:
            logger.error("Background job %s failed: %s\n%s", job_id, exc, traceback.format_exc())
            self._finish(job_id, "failed", str(exc))

    @staticmethod
    def _finish(job_id: str, status: str, error: str) -> None:
        with SessionLocal() as db:
            job = db.get(ProcessingJob, job_id)
            if job:
                job.status = status
                job.stage = "Cancelled" if status == "cancelled" else "Failed"
                job.error = error[-3000:]
                job.updated_at = datetime.now(timezone.utc)
                db.commit()

    def cancel(self, db: Session, job_id: str) -> ProcessingJob | None:
        job = db.get(ProcessingJob, job_id)
        if not job:
            return None
        job.cancel_requested = True
        if job.status == "queued":
            job.status = "cancelled"
            job.stage = "Cancelled"
        db.commit()
        with self._lock:
            process = self._processes.get(job_id)
        if process:
            try:
                process.terminate()
            except OSError:
                pass
        return job

    def register_process(self, job_id: str, process: object) -> None:
        with self._lock:
            self._processes[job_id] = process

    def unregister_process(self, job_id: str) -> None:
        with self._lock:
            self._processes.pop(job_id, None)


manager = TaskManager()
