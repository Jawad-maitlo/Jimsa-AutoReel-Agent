import logging
import os
import subprocess
from pathlib import Path
from sqlalchemy.orm import Session
from ..config import get_settings
from ..models import Reel, Video
from .captions import editable_srt
from .media import require_ffmpeg
from .tasks import CancelledError, TaskContext, manager

logger = logging.getLogger(__name__)

PRESETS = {
    "youtube": {"width": 1080, "height": 1920, "max_duration": 180},
    "instagram": {"width": 1080, "height": 1920, "max_duration": 90},
    "facebook": {"width": 1080, "height": 1920, "max_duration": 90},
}
CRF = {"draft": "28", "medium": "23", "high": "18"}


def subtitle_filter_path(path: Path) -> str:
    # FFmpeg filter escaping, including Windows drive separators.
    value = str(path.resolve()).replace("\\", "/").replace(":", "\\:")
    return value.replace("'", "\\'").replace("[", "\\[").replace("]", "\\]").replace(",", "\\,")


def render_reel(db: Session, reel: Reel, context: TaskContext) -> None:
    require_ffmpeg()
    video = db.get(Video, reel.video_id)
    if not video or not Path(video.file_path).is_file():
        raise ValueError("Source video is missing")
    if reel.end <= reel.start or reel.start >= video.duration:
        raise ValueError("Reel trim range is outside the source video")
    end = min(reel.end, video.duration)
    duration = end - reel.start
    preset = PRESETS.get(reel.preset, PRESETS["youtube"])
    if duration > preset["max_duration"]:
        raise ValueError(f"{reel.preset.title()} preset supports at most {preset['max_duration']} seconds")
    settings = get_settings()
    output = settings.reels_dir / f"reel_{reel.id}.mp4"
    temp_output = settings.temp_dir / f"reel_{reel.id}_rendering.mp4"
    subtitle_path = settings.temp_dir / f"reel_{reel.id}.srt"
    reel.status = "processing"
    reel.error = None
    db.commit()
    try:
        scale = f"scale={reel.width}:{reel.height}:force_original_aspect_ratio="
        if reel.fit_mode == "crop":
            vf = scale + "increase,crop=" + f"{reel.width}:{reel.height},setsar=1"
        else:
            vf = scale + "decrease,pad=" + f"{reel.width}:{reel.height}:(ow-iw)/2:(oh-ih)/2:color=0x040404,setsar=1"
        if reel.burn_subtitles:
            subtitle_path.write_text(editable_srt(reel.subtitles_text, reel.start, end), encoding="utf-8")
            vf += f",subtitles='{subtitle_filter_path(subtitle_path)}'"
        args = ["ffmpeg", "-hide_banner", "-y", "-ss", f"{reel.start:.3f}", "-t", f"{duration:.3f}",
                "-i", str(Path(video.file_path).resolve()), "-vf", vf,
                "-c:v", "libx264", "-preset", "veryfast", "-crf", CRF[reel.quality],
                "-c:a", "aac", "-b:a", "160k", "-ar", "48000", "-movflags", "+faststart",
                "-progress", "pipe:1", "-nostats", str(temp_output)]
        context.update(8, "Rendering vertical video")
        stderr_log = settings.temp_dir / f"reel_{reel.id}_ffmpeg.log"
        stderr_fh = open(stderr_log, "w", encoding="utf-8", errors="replace")
        try:
            process = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=stderr_fh, text=True,
                                       creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0)
            manager.register_process(context.job_id, process)
            assert process.stdout is not None
            for line in process.stdout:
                context.check_cancelled()
                if line.startswith("out_time_ms="):
                    try:
                        seconds = int(line.split("=", 1)[1]) / 1_000_000
                        context.update(min(94, 8 + seconds / max(duration, 0.1) * 86), "Rendering vertical video")
                    except ValueError:
                        pass
            return_code = process.wait()
        finally:
            stderr_fh.close()
        if return_code != 0:
            stderr = ""
            try:
                stderr = stderr_log.read_text(encoding="utf-8", errors="replace")
            except OSError:
                pass
            logger.error("FFmpeg render failed (exit %d) for reel %d:\n%s", return_code, reel.id, stderr[-3000:])
            raise RuntimeError(f"FFmpeg export failed (exit code {return_code}): {stderr[-2500:]}")
        context.check_cancelled()
        if not temp_output.exists() or temp_output.stat().st_size < 100:
            raise RuntimeError("FFmpeg did not produce a valid output file")
        temp_output.replace(output)
        reel.output_path = str(output)
        reel.status = "exported"
        reel.error = None
        db.commit()
        context.update(98, "Export saved")
    except CancelledError:
        reel.status = "draft"
        reel.error = "Rendering cancelled by user"
        db.commit()
        raise
    except Exception as exc:
        reel.status = "failed"
        reel.error = str(exc)[-3000:]
        db.commit()
        raise
    finally:
        manager.unregister_process(context.job_id)
        if temp_output.exists():
            temp_output.unlink(missing_ok=True)
        subtitle_path.unlink(missing_ok=True)
        stderr_log.unlink(missing_ok=True)
