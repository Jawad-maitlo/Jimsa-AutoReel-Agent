import logging
from pathlib import Path
from fastapi import HTTPException
from sqlalchemy.orm import Session
from ..config import get_settings
from ..models import Transcript, TranscriptSegment, Video
from .media import require_ffmpeg
from .tasks import TaskContext

logger = logging.getLogger(__name__)


def transcribe_video(db: Session, video: Video, context: TaskContext, force: bool = False) -> Transcript:
    if video.transcript and not force:
        context.update(100, "Reusing existing transcript")
        return video.transcript
    if not video.has_audio:
        raise ValueError("This video has no audio stream. Add audio before transcription.")
    require_ffmpeg()
    settings = get_settings()
    context.update(5, f"Loading faster-whisper model '{settings.whisper_model}' (first run may download it)")
    try:
        from faster_whisper import WhisperModel
        model = WhisperModel(
            settings.whisper_model,
            device=settings.whisper_device,
            compute_type=settings.whisper_compute_type,
            download_root=str(settings.models_dir),
        )
        segments_iter, info = model.transcribe(str(Path(video.file_path)), vad_filter=True, word_timestamps=False)
        segments = []
        for index, segment in enumerate(segments_iter):
            context.check_cancelled()
            text = segment.text.strip()
            if text:
                segments.append((float(segment.start), float(segment.end), text))
            progress = min(92, 10 + (float(segment.end) / max(video.duration, 1)) * 82)
            context.update(progress, f"Transcribing · segment {index + 1}")
    except ImportError as exc:
        raise RuntimeError("faster-whisper is not installed. Run setup_windows.bat or pip install -r requirements.txt.") from exc
    except Exception as exc:
        if exc.__class__.__name__ == "CancelledError":
            raise
        raise RuntimeError(f"Transcription failed: {exc}") from exc
    if not segments:
        raise ValueError("No speech was detected in the audio track")
    if video.transcript:
        db.delete(video.transcript)
        db.flush()
    transcript = Transcript(video_id=video.id, language=info.language, model=settings.whisper_model,
                            text=" ".join(item[2] for item in segments))
    db.add(transcript)
    db.flush()
    for start, end, text in segments:
        db.add(TranscriptSegment(transcript_id=transcript.id, start=start, end=end, text=text))
    video.status = "transcribed"
    db.commit()
    db.refresh(transcript)
    context.update(96, "Transcript saved")
    return transcript
