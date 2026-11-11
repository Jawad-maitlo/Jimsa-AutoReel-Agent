import json
import shutil
import subprocess
from fractions import Fraction
from pathlib import Path
from fastapi import HTTPException

ALLOWED_EXTENSIONS = {".mp4", ".mov", ".mkv", ".webm", ".m4v"}


def require_ffmpeg() -> None:
    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        raise HTTPException(503, "FFmpeg and FFprobe are required. See docs/SETUP.md for Windows installation.")


def run_command(args: list[str], timeout: int = 120) -> subprocess.CompletedProcess:
    try:
        result = subprocess.run(args, capture_output=True, text=True, timeout=timeout, check=False)
    except FileNotFoundError as exc:
        raise HTTPException(503, f"Executable not found: {args[0]}") from exc
    except subprocess.TimeoutExpired as exc:
        raise HTTPException(504, f"Media command timed out after {timeout} seconds") from exc
    if result.returncode != 0:
        message = (result.stderr or result.stdout or "Unknown media error")[-3000:]
        raise HTTPException(422, f"Media processing failed: {message}")
    return result


def probe_video(path: Path) -> dict:
    require_ffmpeg()
    result = run_command([
        "ffprobe", "-v", "error", "-show_entries",
        "format=duration:stream=index,codec_type,codec_name,width,height,avg_frame_rate,sample_rate,channels",
        "-of", "json", str(path)
    ])
    try:
        data = json.loads(result.stdout)
        streams = data.get("streams", [])
        video = next(s for s in streams if s.get("codec_type") == "video")
        audio = next((s for s in streams if s.get("codec_type") == "audio"), None)
        duration = float(data.get("format", {}).get("duration", 0))
        if duration <= 0:
            raise ValueError("Invalid duration")
        rate = video.get("avg_frame_rate", "0/1")
        fps = float(Fraction(rate)) if rate and rate != "0/0" else 0.0
        return {
            "duration": duration,
            "width": int(video.get("width") or 0),
            "height": int(video.get("height") or 0),
            "frame_rate": round(fps, 3),
            "has_audio": audio is not None,
            "audio_codec": audio.get("codec_name") if audio else None,
        }
    except (ValueError, KeyError, StopIteration, json.JSONDecodeError) as exc:
        raise HTTPException(422, "The file is corrupted or does not contain a readable video stream") from exc


def create_thumbnail(video_path: Path, thumbnail_path: Path) -> None:
    require_ffmpeg()
    thumbnail_path.parent.mkdir(parents=True, exist_ok=True)
    run_command([
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-ss", "1",
        "-i", str(video_path), "-frames:v", "1", "-vf", "scale='min(640,iw)':-2",
        str(thumbnail_path)
    ], timeout=60)
