import json
import logging
import re
from dataclasses import dataclass
import httpx
from pydantic import BaseModel, Field, ValidationError, field_validator
from sqlalchemy.orm import Session
from ..config import get_settings
from ..models import Highlight, Transcript, TranscriptSegment, Video

logger = logging.getLogger(__name__)
HOOK_WORDS = {
    "secret", "mistake", "never", "always", "best", "worst", "why", "how", "actually",
    "important", "surprising", "learned", "truth", "problem", "tips", "story", "remember",
    "because", "finally", "nobody", "everyone", "stop", "start", "free", "proven",
}


@dataclass
class Candidate:
    start: float
    end: float
    title: str
    explanation: str
    confidence: float
    transcript_excerpt: str
    analysis_method: str


class LLMHighlight(BaseModel):
    start: float = Field(ge=0)
    end: float = Field(gt=0)
    title: str = Field(min_length=2, max_length=180)
    explanation: str = Field(min_length=2, max_length=1000)
    confidence: float = Field(ge=0, le=1)

    @field_validator("end")
    @classmethod
    def after_start(cls, value, info):
        if "start" in info.data and value <= info.data["start"]:
            raise ValueError("end must be after start")
        return value


def make_title(text: str) -> str:
    clean = re.sub(r"\s+", " ", text).strip()
    words = clean.split()
    title = " ".join(words[:9])
    if len(words) > 9:
        title += "…"
    return title[:1].upper() + title[1:] if title else "Untitled highlight"


def fallback_highlights(segments: list[TranscriptSegment], duration: float, count: int = 5,
                        min_length: float = 18, max_length: float = 58) -> list[Candidate]:
    """Deterministic, transcript-grounded selection; never invents transcript text."""
    if not segments:
        return []
    max_length = min(max_length, max(5, duration))
    min_length = min(min_length, max_length)
    scored = []
    for index, segment in enumerate(segments):
        words = set(re.findall(r"[a-zA-Z']+", segment.text.lower()))
        score = len(words & HOOK_WORDS) * 0.16
        score += 0.12 if "?" in segment.text else 0
        score += 0.08 if "!" in segment.text else 0
        score += 0.08 if 7 <= len(segment.text.split()) <= 28 else 0
        score += 0.06 if index < max(2, len(segments) // 8) else 0
        score += 0.04 if re.search(r"\b(I|we)\b", segment.text) else 0
        scored.append((score, index))
    candidates: list[Candidate] = []
    used: list[tuple[float, float]] = []
    for score, seed in sorted(scored, key=lambda item: (-item[0], item[1])):
        if len(candidates) >= count:
            break
        left = right = seed
        start, end = segments[seed].start, segments[seed].end
        while end - start < min_length and (left > 0 or right < len(segments) - 1):
            can_left = left > 0 and start - segments[left - 1].end < 4
            can_right = right < len(segments) - 1 and segments[right + 1].start - end < 4
            if can_right and (not can_left or end - start < min_length / 2):
                right += 1
                end = segments[right].end
            elif can_left:
                left -= 1
                start = segments[left].start
            else:
                break
        while end - start > max_length and (left < right):
            if segments[right].end - start > max_length:
                right -= 1
                end = segments[right].end
            else:
                left += 1
                start = segments[left].start
        start = max(0, start)
        end = min(duration, max(end, start + 1))
        if any(start < other_end + 1 and end > other_start - 1 for other_start, other_end in used):
            continue
        excerpt = " ".join(s.text.strip() for s in segments[left:right + 1]).strip()
        if not excerpt:
            continue
        confidence = round(min(0.88, 0.46 + score / 3), 2)
        candidates.append(Candidate(start, end, make_title(excerpt),
                                    "Selected by deterministic transcript cues: hooks, questions, emotional emphasis, and natural segment boundaries.",
                                    confidence, excerpt, "fallback"))
        used.append((start, end))
    return sorted(candidates, key=lambda item: item.start)


def _transcript_payload(segments: list[TranscriptSegment]) -> str:
    lines = [f"[{s.start:.2f} --> {s.end:.2f}] {s.text.strip()}" for s in segments]
    payload = "\n".join(lines)
    return payload[:48000]


def ollama_highlights(segments: list[TranscriptSegment], duration: float, count: int = 5) -> list[Candidate]:
    settings = get_settings()
    prompt = f"""You select short-form video highlights. Return ONLY a JSON array of up to {count} objects.
Each object needs numeric start/end seconds, title, explanation, confidence from 0 to 1.
Use only timestamps and ideas present in the transcript. Segments should be 15-60 seconds, begin and end at natural boundaries, and never exceed the source duration {duration:.2f}. Prefer strong hooks, useful information, emotion, stories, and complete thoughts.
TRANSCRIPT:\n{_transcript_payload(segments)}"""
    try:
        response = httpx.post(
            settings.ollama_endpoint.rstrip("/") + "/api/chat",
            json={"model": settings.ollama_model, "stream": False, "format": "json",
                  "messages": [{"role": "user", "content": prompt}],
                  "options": {"temperature": 0.2}},
            timeout=settings.request_timeout_seconds,
        )
        response.raise_for_status()
        content = response.json()["message"]["content"]
        raw = json.loads(content)
        if isinstance(raw, dict):
            raw = raw.get("highlights", [])
        validated = [LLMHighlight.model_validate(item) for item in raw]
    except (httpx.HTTPError, KeyError, ValueError, json.JSONDecodeError, ValidationError) as exc:
        raise RuntimeError(f"Ollama analysis unavailable or returned invalid data: {exc}") from exc
    results = []
    for item in validated[:count]:
        if item.end > duration + 0.5:
            continue
        excerpt = " ".join(s.text for s in segments if s.end >= item.start and s.start <= item.end)
        if not excerpt:
            continue
        results.append(Candidate(item.start, min(item.end, duration), item.title, item.explanation,
                                 item.confidence, excerpt, "ollama"))
    if not results:
        raise RuntimeError("Ollama returned no valid transcript-grounded highlights")
    return results


def analyze_transcript(db: Session, video: Video, transcript: Transcript, prefer_llm: bool = True,
                       count: int = 5) -> tuple[list[Highlight], str | None]:
    segments = list(transcript.segments)
    warning = None
    candidates = []
    if prefer_llm:
        try:
            candidates = ollama_highlights(segments, video.duration, count)
        except RuntimeError as exc:
            warning = str(exc)
            logger.warning("Using fallback highlight detection: %s", exc)
    if not candidates:
        candidates = fallback_highlights(segments, video.duration, count)
    if not candidates:
        raise ValueError("No usable highlights could be found in this transcript")
    db.query(Highlight).filter(Highlight.video_id == video.id).delete()
    for item in candidates:
        db.add(Highlight(video_id=video.id, **item.__dict__))
    video.status = "analyzed"
    db.commit()
    return list(db.query(Highlight).filter(Highlight.video_id == video.id).order_by(Highlight.start)), warning
