from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    """Runtime settings from backend/.env (or the environment). Relative paths are resolved
    against the backend folder, so scripts and tests find the same files from anywhere."""

    model_config = SettingsConfigDict(env_file=BACKEND_ROOT / ".env", extra="ignore")

    database_path: Path = Path("yapit.db")
    config_dir: Path = Path("config")
    cors_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]
    max_upload_mb: float = 25

    @field_validator("database_path", "config_dir")
    @classmethod
    def _relative_to_backend(cls, path: Path) -> Path:
        return path if path.is_absolute() else BACKEND_ROOT / path

    @property
    def max_upload_bytes(self) -> int:
        return int(self.max_upload_mb * 1024 * 1024)


@lru_cache
def get_settings() -> Settings:
    return Settings()
