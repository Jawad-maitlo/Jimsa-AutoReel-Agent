from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field, field_validator


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)


class ProjectOut(ORMModel):
    id: int
    name: str
    created_at: datetime
    updated_at: datetime
    video_count: int = 0


class VideoOut(ORMModel):
    id: int
    project_id: int
    original_name: str
    file_size: int
    duration: float
    width: int
    height: int
    frame_rate: float
    has_audio: bool
    audio_codec: str | None
    status: str
    error: str | None
    created_at: datetime
    thumbnail_url: str | None = None
    stream_url: str | None = None


class SegmentOut(ORMModel):
    id: int
    start: float
    end: float
    text: str


class TranscriptOut(ORMModel):
    id: int
    video_id: int
    language: str | None
    model: str
    text: str
    segments: list[SegmentOut] = []


class HighlightOut(ORMModel):
    id: int
    video_id: int
    start: float
    end: float
    title: str
    explanation: str
    confidence: float
    transcript_excerpt: str
    analysis_method: str
    selected: bool


class HighlightUpdate(BaseModel):
    start: float = Field(ge=0)
    end: float = Field(gt=0)
    title: str = Field(min_length=1, max_length=180)
    selected: bool = True

    @field_validator("end")
    @classmethod
    def valid_range(cls, value, info):
        if "start" in info.data and value <= info.data["start"]:
            raise ValueError("End must be after start")
        return value


class ReelCreate(BaseModel):
    highlight_id: int | None = None
    start: float = Field(ge=0)
    end: float = Field(gt=0)
    title: str = Field(min_length=1, max_length=180)
    preset: str = Field(default="youtube", pattern="^(youtube|instagram|facebook)$")
    width: int = Field(default=1080)
    height: int = Field(default=1920)
    quality: str = Field(default="medium", pattern="^(draft|medium|high)$")
    fit_mode: str = Field(default="crop", pattern="^(crop|pad)$")
    burn_subtitles: bool = True

    @field_validator("end")
    @classmethod
    def valid_range(cls, value, info):
        if "start" in info.data and value <= info.data["start"]:
            raise ValueError("End must be after start")
        return value


class BatchReelCreate(BaseModel):
    preset: str = Field(default="youtube", pattern="^(youtube|instagram|facebook)$")
    width: int = Field(default=1080)
    height: int = Field(default=1920)
    quality: str = Field(default="medium", pattern="^(draft|medium|high)$")
    fit_mode: str = Field(default="crop", pattern="^(crop|pad)$")
    burn_subtitles: bool = True
    render: bool = True


class ReelUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=180)
    description: str | None = None
    hashtags: str | None = None
    subtitles_text: str | None = None
    cover_timestamp: float | None = Field(default=None, ge=0)
    start: float | None = Field(default=None, ge=0)
    end: float | None = Field(default=None, gt=0)
    preset: str | None = Field(default=None, pattern="^(youtube|instagram|facebook)$")
    quality: str | None = Field(default=None, pattern="^(draft|medium|high)$")
    fit_mode: str | None = Field(default=None, pattern="^(crop|pad)$")
    burn_subtitles: bool | None = None


class ReelOut(ORMModel):
    id: int
    video_id: int
    highlight_id: int | None
    title: str
    description: str
    hashtags: str
    subtitles_text: str
    cover_timestamp: float
    start: float
    end: float
    preset: str
    width: int
    height: int
    quality: str
    fit_mode: str
    burn_subtitles: bool
    status: str
    error: str | None
    created_at: datetime
    updated_at: datetime
    output_url: str | None = None


class JobOut(ORMModel):
    id: str
    kind: str
    entity_id: int
    status: str
    progress: float
    stage: str
    error: str | None
    cancel_requested: bool
    created_at: datetime
    updated_at: datetime


class AccountOut(ORMModel):
    id: int
    platform: str
    platform_account_id: str
    display_name: str
    token_expires_at: datetime | None
    scopes: str
    status: str


class PublishCreate(BaseModel):
    account_id: int
    scheduled_at: datetime | None = None


class PublishOut(ORMModel):
    id: int
    reel_id: int
    account_id: int
    platform: str
    status: str
    scheduled_at: datetime | None
    platform_post_id: str | None
    platform_url: str | None
    error: str | None
    attempts: int
    created_at: datetime
    published_at: datetime | None
    reel_title: str = ""
    account_name: str = ""


class SettingsUpdate(BaseModel):
    whisper_model: str | None = None
    whisper_device: str | None = None
    whisper_compute_type: str | None = None
    ollama_endpoint: str | None = None
    ollama_model: str | None = None
    public_media_base_url: str | None = None
