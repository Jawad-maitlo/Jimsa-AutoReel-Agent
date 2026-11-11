import uuid
from pathlib import Path
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from ..config import get_settings
from ..database import SessionLocal, get_db
from ..models import Highlight, Project, Transcript, Video
from ..schemas import HighlightOut, HighlightUpdate, TranscriptOut, VideoOut
from ..services.highlights import analyze_transcript
from ..services.media import ALLOWED_EXTENSIONS, create_thumbnail, probe_video
from ..services.tasks import manager
from ..services.transcription import transcribe_video
from ..security import safe_storage_path

router = APIRouter(prefix="/videos", tags=["videos"])


def serialize(video: Video) -> VideoOut:
    data = VideoOut.model_validate(video)
    data.thumbnail_url = f"/api/videos/{video.id}/thumbnail" if video.thumbnail_path else None
    data.stream_url = f"/api/videos/{video.id}/stream"
    return data


@router.get("", response_model=list[VideoOut])
def list_videos(project_id: int | None = None, db: Session = Depends(get_db)):
    query = db.query(Video)
    if project_id:
        query = query.filter(Video.project_id == project_id)
    return [serialize(v) for v in query.order_by(Video.created_at.desc()).all()]


@router.post("/import", response_model=VideoOut, status_code=201)
def import_video(project_id: int = Form(...), file: UploadFile = File(...), db: Session = Depends(get_db)):
    if not db.get(Project, project_id):
        raise HTTPException(404, "Project not found")
    original_name = Path(file.filename or "video.mp4").name
    suffix = Path(original_name).suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(415, f"Unsupported format '{suffix}'. Choose MP4, MOV, MKV, WebM, or M4V.")
    settings = get_settings()
    max_bytes = settings.max_upload_mb * 1024 * 1024
    destination = settings.videos_dir / f"{uuid.uuid4().hex}{suffix}"
    size = 0
    try:
        with destination.open("wb") as output:
            while chunk := file.file.read(1024 * 1024):
                size += len(chunk)
                if size > max_bytes:
                    raise HTTPException(413, f"File exceeds the {settings.max_upload_mb} MB limit")
                output.write(chunk)
        if size < 100:
            raise HTTPException(422, "The uploaded file is empty")
        metadata = probe_video(destination)
        thumbnail = settings.thumbnails_dir / f"{destination.stem}.jpg"
        try:
            create_thumbnail(destination, thumbnail)
        except HTTPException:
            thumbnail = None
        video = Video(project_id=project_id, original_name=original_name, file_path=str(destination),
                      thumbnail_path=str(thumbnail) if thumbnail else None, file_size=size, **metadata)
        db.add(video)
        db.commit()
        db.refresh(video)
        return serialize(video)
    except Exception:
        destination.unlink(missing_ok=True)
        raise
    finally:
        file.file.close()


@router.get("/{video_id}", response_model=VideoOut)
def get_video(video_id: int, db: Session = Depends(get_db)):
    video = db.get(Video, video_id)
    if not video:
        raise HTTPException(404, "Video not found")
    return serialize(video)


@router.get("/{video_id}/stream")
def stream_video(video_id: int, db: Session = Depends(get_db)):
    video = db.get(Video, video_id)
    if not video:
        raise HTTPException(404, "Video not found")
    path = safe_storage_path(video.file_path, get_settings().videos_dir)
    if not path.is_file():
        raise HTTPException(404, "Source file is missing from disk")
    return FileResponse(path, filename=video.original_name)


@router.get("/{video_id}/thumbnail")
def thumbnail(video_id: int, db: Session = Depends(get_db)):
    video = db.get(Video, video_id)
    if not video or not video.thumbnail_path:
        raise HTTPException(404, "Thumbnail not available")
    path = safe_storage_path(video.thumbnail_path, get_settings().thumbnails_dir)
    if not path.is_file():
        raise HTTPException(404, "Thumbnail file is missing")
    return FileResponse(path, media_type="image/jpeg")


@router.delete("/{video_id}", status_code=204)
def delete_video(video_id: int, delete_file: bool = False, db: Session = Depends(get_db)):
    video = db.get(Video, video_id)
    if not video:
        raise HTTPException(404, "Video not found")
    if delete_file:
        safe_storage_path(video.file_path, get_settings().videos_dir).unlink(missing_ok=True)
        if video.thumbnail_path:
            safe_storage_path(video.thumbnail_path, get_settings().thumbnails_dir).unlink(missing_ok=True)
    db.delete(video)
    db.commit()


@router.post("/{video_id}/transcribe", status_code=202)
def start_transcription(video_id: int, force: bool = False, db: Session = Depends(get_db)):
    video = db.get(Video, video_id)
    if not video:
        raise HTTPException(404, "Video not found")
    if video.transcript and not force:
        return {"status": "completed", "message": "Existing transcript reused", "job": None}
    if not video.has_audio:
        raise HTTPException(422, "This video has no audio stream")
    def work(context):
        with SessionLocal() as task_db:
            transcribe_video(task_db, task_db.get(Video, video_id), context, force)
    job = manager.submit("transcription", video_id, work)
    return {"status": job.status, "job_id": job.id}


@router.get("/{video_id}/transcript", response_model=TranscriptOut | None)
def get_transcript(video_id: int, db: Session = Depends(get_db)):
    video = db.get(Video, video_id)
    if not video:
        raise HTTPException(404, "Video not found")
    return video.transcript


@router.post("/{video_id}/highlights", response_model=list[HighlightOut])
def generate_highlights(video_id: int, prefer_llm: bool = True, count: int = 5, db: Session = Depends(get_db)):
    video = db.get(Video, video_id)
    if not video:
        raise HTTPException(404, "Video not found")
    if not video.transcript:
        raise HTTPException(409, "Transcribe this video before highlight analysis")
    if not 1 <= count <= 10:
        raise HTTPException(422, "Highlight count must be between 1 and 10")
    highlights, warning = analyze_transcript(db, video, video.transcript, prefer_llm, count)
    return [HighlightOut.model_validate(h) for h in highlights]


@router.get("/{video_id}/highlights", response_model=list[HighlightOut])
def list_highlights(video_id: int, db: Session = Depends(get_db)):
    return db.query(Highlight).filter(Highlight.video_id == video_id).order_by(Highlight.start).all()


@router.patch("/highlights/{highlight_id}", response_model=HighlightOut)
def update_highlight(highlight_id: int, payload: HighlightUpdate, db: Session = Depends(get_db)):
    highlight = db.get(Highlight, highlight_id)
    if not highlight:
        raise HTTPException(404, "Highlight not found")
    if payload.end > highlight.video.duration:
        raise HTTPException(422, "Highlight end exceeds video duration")
    for key, value in payload.model_dump().items():
        setattr(highlight, key, value)
    db.commit()
    db.refresh(highlight)
    return highlight
