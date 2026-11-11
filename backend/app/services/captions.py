import re
from dataclasses import dataclass
from ..models import Transcript, TranscriptSegment

TIME_PATTERN = r"(\d{2,}:\d{2}:\d{2}[,.]\d{3})"


def format_srt_time(seconds: float) -> str:
    millis = max(0, round(seconds * 1000))
    hours, millis = divmod(millis, 3_600_000)
    minutes, millis = divmod(millis, 60_000)
    secs, millis = divmod(millis, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def parse_srt_time(value: str) -> float:
    match = re.fullmatch(r"(\d{2,}):(\d{2}):(\d{2})[,.](\d{3})", value.strip())
    if not match:
        raise ValueError(f"Invalid caption timestamp: {value}")
    hours, minutes, seconds, millis = (int(part) for part in match.groups())
    if minutes >= 60 or seconds >= 60:
        raise ValueError(f"Invalid caption timestamp: {value}")
    return hours * 3600 + minutes * 60 + seconds + millis / 1000


def clip_segments(transcript: Transcript | None, start: float, end: float) -> list[TranscriptSegment]:
    if not transcript:
        return []
    return [s for s in transcript.segments if s.end > start and s.start < end]


def clip_text(transcript: Transcript | None, start: float, end: float) -> str:
    return " ".join(s.text.strip() for s in clip_segments(transcript, start, end)).strip()


def build_srt(segments: list[TranscriptSegment], start: float, end: float) -> str:
    blocks = []
    for segment in segments:
        seg_start = max(0, segment.start - start)
        seg_end = min(end - start, segment.end - start)
        if seg_end <= seg_start or not segment.text.strip():
            continue
        blocks.append(f"{len(blocks) + 1}\n{format_srt_time(seg_start)} --> {format_srt_time(seg_end)}\n{segment.text.strip()}")
    return "\n\n".join(blocks) + ("\n" if blocks else "")


def plain_captions(segments: list[TranscriptSegment]) -> str:
    """Legacy caption format retained for reels created before the SRT editor."""
    return "\n".join(f"[{format_srt_time(max(0, s.start))}] {s.text.strip()}" for s in segments)


@dataclass
class CaptionCue:
    start: float
    end: float
    text: str


def editable_srt(value: str, start: float, end: float) -> str:
    """Validate edited SRT (or legacy timestamp lines) and offset it to the reel trim.

    Stored cue times use the source-video timeline. This lets trim changes naturally
    exclude out-of-range cues without silently replacing edited text with a transcript.
    """
    text = value.replace("\r\n", "\n").replace("\r", "\n").strip()
    if not text:
        raise ValueError("Burned-in subtitles need timed captions. Add SRT cues or disable subtitles.")
    cues: list[CaptionCue] = []
    if "-->" in text:
        for block in re.split(r"\n\s*\n", text):
            lines = [line.strip() for line in block.split("\n") if line.strip()]
            if lines and lines[0].isdigit():
                lines = lines[1:]
            if len(lines) < 2 or "-->" not in lines[0]:
                raise ValueError("Invalid SRT captions. Each cue needs a timestamp line and caption text.")
            timing = re.fullmatch(rf"{TIME_PATTERN}\s*-->\s*{TIME_PATTERN}(?:\s+.*)?", lines[0])
            if not timing:
                raise ValueError("Invalid SRT timing. Use HH:MM:SS,mmm --> HH:MM:SS,mmm.")
            cue_start, cue_end = parse_srt_time(timing.group(1)), parse_srt_time(timing.group(2))
            if cue_end <= cue_start:
                raise ValueError("Each caption cue must end after it starts.")
            cues.append(CaptionCue(cue_start, cue_end, "\n".join(lines[1:])))
    else:
        legacy: list[tuple[float, str]] = []
        for line in text.split("\n"):
            match = re.fullmatch(rf"\[{TIME_PATTERN}\]\s*(.+)", line.strip())
            if not match:
                raise ValueError("Invalid captions. Use standard SRT cues with timestamps and text.")
            legacy.append((parse_srt_time(match.group(1)), match.group(2).strip()))
        for index, (cue_start, cue_text) in enumerate(legacy):
            cue_end = legacy[index + 1][0] if index + 1 < len(legacy) else end
            cues.append(CaptionCue(cue_start, cue_end, cue_text))
    blocks = []
    for cue in cues:
        cue_start, cue_end = max(0, cue.start - start), min(end - start, cue.end - start)
        if cue_end > cue_start and cue.text.strip():
            blocks.append(f"{len(blocks) + 1}\n{format_srt_time(cue_start)} --> {format_srt_time(cue_end)}\n{cue.text.strip()}")
    if not blocks:
        raise ValueError("No edited caption cues overlap this trim. Adjust the cue times or disable subtitles.")
    return "\n\n".join(blocks) + "\n"


def suggest_metadata(title: str, excerpt: str) -> dict[str, str | float]:
    words = re.findall(r"[A-Za-z0-9]+", excerpt.lower())
    stop = {"this", "that", "with", "from", "have", "about", "your", "youre", "there", "their", "what", "when", "where", "would", "could", "should", "because", "really", "just", "like", "know"}
    frequencies: dict[str, int] = {}
    for word in words:
        if len(word) > 3 and word not in stop:
            frequencies[word] = frequencies.get(word, 0) + 1
    tags = [word for word, _ in sorted(frequencies.items(), key=lambda item: (-item[1], item[0]))[:5]]
    hashtags = " ".join("#" + re.sub(r"[^a-zA-Z0-9]", "", tag) for tag in ["reels", "shorts", *tags])
    description = excerpt[:350] + ("…" if len(excerpt) > 350 else "")
    return {"title": title, "description": description, "hashtags": hashtags}
