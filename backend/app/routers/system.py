import shutil
import subprocess
import httpx
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from .. import __version__
from ..config import get_settings
from ..database import get_db
from ..models import AppSetting, ProcessingJob
from ..schemas import JobOut, SettingsUpdate
from ..services.tasks import manager

router = APIRouter(tags=["system"])


def command_version(command: str) -> str | None:
    executable = shutil.which(command)
    if not executable:
        return None
    try:
        result = subprocess.run([executable, "-version"], capture_output=True, text=True, timeout=5)
        return result.stdout.splitlines()[0] if result.returncode == 0 else None
    except (OSError, subprocess.TimeoutExpired):
        return None


@router.get("/health")
def health():
    settings = get_settings()
    return {"status": "ok", "app": settings.app_name, "version": __version__, "database": "sqlite"}


@router.get("/system/status")
def system_status():
    settings = get_settings()
    ollama = {"available": False, "message": "Ollama is not reachable", "models": []}
    try:
        response = httpx.get(settings.ollama_endpoint.rstrip("/") + "/api/tags", timeout=2)
        response.raise_for_status()
        models = [model.get("name", "") for model in response.json().get("models", [])]
        ollama = {"available": True, "models": models,
                  "message": "Connected" if settings.ollama_model in models else f"Configured model '{settings.ollama_model}' is not installed"}
    except httpx.HTTPError:
        pass
    disk = shutil.disk_usage(settings.storage_dir)
    return {
        "ffmpeg": command_version("ffmpeg"), "ffprobe": command_version("ffprobe"),
        "ollama": ollama, "whisper": {"model": settings.whisper_model, "device": settings.whisper_device, "compute_type": settings.whisper_compute_type},
        "storage": {"path": str(settings.storage_dir), "free_gb": round(disk.free / 1024**3, 1)},
        "credentials": {"google": bool(settings.google_client_id and settings.google_client_secret),
                        "meta": bool(settings.meta_app_id and settings.meta_app_secret)},
    }


@router.get("/settings")
def read_settings():
    settings = get_settings()
    return {"whisper_model": settings.whisper_model, "whisper_device": settings.whisper_device,
            "whisper_compute_type": settings.whisper_compute_type, "ollama_endpoint": settings.ollama_endpoint,
            "ollama_model": settings.ollama_model, "public_media_base_url": settings.public_media_base_url,
            "max_upload_mb": settings.max_upload_mb}


@router.patch("/settings")
def update_settings(payload: SettingsUpdate, db: Session = Depends(get_db)):
    settings = get_settings()
    values = payload.model_dump(exclude_none=True)
    if "ollama_endpoint" in values and not values["ollama_endpoint"].startswith(("http://", "https://")):
        raise HTTPException(422, "Ollama endpoint must be an HTTP(S) URL")
    for key, value in values.items():
        clean_value = value.strip() if isinstance(value, str) else value
        setattr(settings, key, clean_value)
        setting = db.get(AppSetting, key)
        if not setting:
            setting = AppSetting(key=key)
            db.add(setting)
        setting.value = str(clean_value)
    db.commit()
    return read_settings()


@router.get("/jobs", response_model=list[JobOut])
def jobs(db: Session = Depends(get_db)):
    return db.query(ProcessingJob).order_by(ProcessingJob.created_at.desc()).limit(100).all()


@router.get("/jobs/{job_id}", response_model=JobOut)
def get_job(job_id: str, db: Session = Depends(get_db)):
    job = db.get(ProcessingJob, job_id)
    if not job:
        raise HTTPException(404, "Processing job not found")
    return job


@router.post("/jobs/{job_id}/cancel", response_model=JobOut)
def cancel_job(job_id: str, db: Session = Depends(get_db)):
    job = manager.cancel(db, job_id)
    if not job:
        raise HTTPException(404, "Processing job not found")
    return job
