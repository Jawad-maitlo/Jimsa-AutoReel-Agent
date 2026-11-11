from functools import lru_cache
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    app_name: str = "Jimsa Autoreel Agent"
    environment: str = "development"
    host: str = "127.0.0.1"
    port: int = 8000
    frontend_origin: str = "http://localhost:5173"
    database_url: str = f"sqlite:///{(ROOT_DIR / 'storage' / 'jimsa.db').as_posix()}"
    storage_dir: Path = ROOT_DIR / "storage"
    max_upload_mb: int = 4096
    whisper_model: str = "base"
    whisper_device: str = "cpu"
    whisper_compute_type: str = "int8"
    ollama_endpoint: str = "http://127.0.0.1:11434"
    ollama_model: str = "qwen2.5:7b"
    request_timeout_seconds: int = 120
    token_encryption_key: str = ""
    app_base_url: str = "http://127.0.0.1:8000"
    public_media_base_url: str = ""
    google_client_id: str = ""
    google_client_secret: str = ""
    meta_app_id: str = ""
    meta_app_secret: str = ""
    meta_graph_version: str = "v23.0"
    model_config = SettingsConfigDict(env_file=ROOT_DIR / ".env", extra="ignore")

    @property
    def videos_dir(self) -> Path:
        return self.storage_dir / "videos"

    @property
    def reels_dir(self) -> Path:
        return self.storage_dir / "reels"

    @property
    def thumbnails_dir(self) -> Path:
        return self.storage_dir / "thumbnails"

    @property
    def temp_dir(self) -> Path:
        return self.storage_dir / "temp"

    @property
    def models_dir(self) -> Path:
        return self.storage_dir / "models"

    def ensure_directories(self) -> None:
        for path in (self.storage_dir, self.videos_dir, self.reels_dir,
                     self.thumbnails_dir, self.temp_dir, self.models_dir):
            path.mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.ensure_directories()
    return settings
