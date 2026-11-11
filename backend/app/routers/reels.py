from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from ..database import SessionLocal, get_db
from ..models import Highlight, Reel, Video
from ..schemas import BatchReelCreate, ReelCreate, ReelOut, ReelUpdate
from ..services.captions import build_srt, clip_text, clip_segments, suggest_metadata
from ..services.reels import PRESETS, render_reel
from ..services.tasks import manager
from ..security import safe_storage_path
from ..config import get_settings

router = APIRouter(prefix="/reels", tags=["reels"])


def serialize(reel: Reel) -> ReelOut:
    data = ReelOut.model_validate(reel)
    data.output_url = f"/api/reels/{reel.id}/download" if reel.output_path and reel.status == "exported" else None
    return data


@router.get("", response_model=list[ReelOut])
def list_reels(video_id: int | None = None, db: Session = Depends(get_db)):
    query = db.query(Reel)
    if video_id:
        query = query.filter(Reel.video_id == video_id)
    return [serialize(r) for r in query.order_by(Reel.created_at.desc()).all()]


@router.post("/from-video/{video_id}", response_model=ReelOut, status_code=201)
def create_reel(video_id: int, payload: ReelCreate, db: Session = Depends(get_db)):
    video = db.get(Video, video_id)
    if not video:
        raise HTTPException(404, "Video not found")
    if payload.end > video.duration:
        raise HTTPException(422, "Reel end exceeds video duration")
    if payload.highlight_id and not db.query(Highlight).filter(Highlight.id == payload.highlight_id, Highlight.video_id == video_id).first():
        raise HTTPException(422, "Highlight does not belong to this video")
    if payload.width % 2 or payload.height % 2 or not 180 <= payload.width <= 2160 or not 320 <= payload.height <= 3840:
        raise HTTPException(422, "Dimensions must be even and within supported bounds")
    excerpt = clip_text(video.transcript, payload.start, payload.end)
    metadata = suggest_metadata(payload.title, excerpt)
    captions = build_srt(clip_segments(video.transcript, payload.start, payload.end), 0, payload.end)
    reel = Reel(video_id=video_id, **payload.model_dump(), description=metadata["description"],
                hashtags=metadata["hashtags"], subtitles_text=captions, cover_timestamp=payload.start)
    db.add(reel)
    db.commit()
    db.refresh(reel)
    return serialize(reel)


@router.post("/batch-from-video/{video_id}", response_model=list[ReelOut], status_code=201)
def batch_create_reels(video_id: int, payload: BatchReelCreate, db: Session = Depends(get_db)):
    """Create reels from all selected highlights of a video and optionally start rendering them."""
    video = db.get(Video, video_id)
    if not video:
        raise HTTPException(404, "Video not found")
    highlights = (db.query(Highlight)
                  .filter(Highlight.video_id == video_id, Highlight.selected == True)
                  .order_by(Highlight.start).all())
    if not highlights:
        raise HTTPException(409, "No selected highlights. Run highlight analysis first.")
    if payload.width % 2 or payload.height % 2 or not 180 <= payload.width <= 2160 or not 320 <= payload.height <= 3840:
        raise HTTPException(422, "Dimensions must be even and within supported bounds")
    preset_info = PRESETS.get(payload.preset, PRESETS["youtube"])
    created: list[Reel] = []
    for highlight in highlights:
        duration = highlight.end - highlight.start
        if duration > preset_info["max_duration"]:
            continue
        if highlight.end > video.duration:
            continue
        excerpt = clip_text(video.transcript, highlight.start, highlight.end)
        metadata = suggest_metadata(highlight.title, excerpt)
        captions = build_srt(clip_segments(video.transcript, highlight.start, highlight.end), 0, highlight.end)
        reel = Reel(
            video_id=video_id, highlight_id=highlight.id,
            start=highlight.start, end=highlight.end, title=highlight.title,
            preset=payload.preset, width=payload.width, height=payload.height,
            quality=payload.quality, fit_mode=payload.fit_mode,
            burn_subtitles=payload.burn_subtitles,
            description=metadata["description"], hashtags=metadata["hashtags"],
            subtitles_text=captions, cover_timestamp=highlight.start,
        )
        db.add(reel)
        created.append(reel)
    if not created:
        raise HTTPException(422, "No highlights fit the selected preset duration limit")
    db.commit()
    for reel in created:
        db.refresh(reel)
    if payload.render:
        for reel in created:
            def work(context, reel_id=reel.id):
                with SessionLocal() as task_db:
                    render_reel(task_db, task_db.get(Reel, reel_id), context)
            manager.submit("render", reel.id, work)
    return [serialize(r) for r in created]


@router.get("/{reel_id}", response_model=ReelOut)
def get_reel(reel_id: int, db: Session = Depends(get_db)):
    reel = db.get(Reel, reel_id)
    if not reel:
        raise HTTPException(404, "Reel not found")
    return serialize(reel)


@router.patch("/{reel_id}", response_model=ReelOut)
def update_reel(reel_id: int, payload: ReelUpdate, db: Session = Depends(get_db)):
    reel = db.get(Reel, reel_id)
    if not reel:
        raise HTTPException(404, "Reel not found")
    values = payload.model_dump(exclude_none=True)
    start = values.get("start", reel.start)
    end = values.get("end", reel.end)
    if end <= start or end > reel.video.duration:
        raise HTTPException(422, "Invalid trim range")
    if reel.status in {"processing", "uploading"}:
        raise HTTPException(409, "Cannot edit a reel while it is processing")
    for key, value in values.items():
        setattr(reel, key, value)
    if reel.status == "exported" and any(key in values for key in ["start", "end", "preset", "quality", "fit_mode", "burn_subtitles", "subtitles_text"]):
        reel.status = "draft"
        reel.output_path = None
    db.commit()
    db.refresh(reel)
    return serialize(reel)


@router.post("/{reel_id}/render", status_code=202)
def start_render(reel_id: int, db: Session = Depends(get_db)):
    reel = db.get(Reel, reel_id)
    if not reel:
        raise HTTPException(404, "Reel not found")
    def work(context):
        with SessionLocal() as task_db:
            render_reel(task_db, task_db.get(Reel, reel_id), context)
    job = manager.submit("render", reel_id, work)
    return {"job_id": job.id, "status": job.status}


@router.get("/{reel_id}/download")
def download_reel(reel_id: int, db: Session = Depends(get_db)):
    reel = db.get(Reel, reel_id)
    if not reel or not reel.output_path:
        raise HTTPException(404, "Rendered reel not available")
    path = safe_storage_path(reel.output_path, get_settings().reels_dir)
    if not path.is_file():
        raise HTTPException(404, "Output file is missing")
    filename = "".join(c if c.isalnum() or c in " -_" else "_" for c in reel.title)[:80] + ".mp4"
    return FileResponse(path, media_type="video/mp4", filename=filename)


@router.delete("/{reel_id}", status_code=204)
def delete_reel(reel_id: int, db: Session = Depends(get_db)):
    reel = db.get(Reel, reel_id)
    if not reel:
        raise HTTPException(404, "Reel not found")
    if reel.status == "processing":
        raise HTTPException(409, "Cancel processing before deleting this reel")
    if reel.output_path:
        safe_storage_path(reel.output_path, get_settings().reels_dir).unlink(missing_ok=True)
    db.delete(reel)
    db.commit()
