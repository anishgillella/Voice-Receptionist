"""Application configuration and environment variable validation."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Centralised application settings loaded from the environment."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    vapi_api_key: str = Field(..., alias="VAPI_API_KEY")
    vapi_agent_id: str = Field(..., alias="VAPI_AGENT_ID")
    vapi_phone_number_id: str = Field(..., alias="VAPI_PHONE_NUMBER_ID")
    backend_base_url: Optional[str] = Field(None, alias="BACKEND_BASE_URL")
    transcript_dir: Path = Field(default=Path("data/transcripts"), alias="TRANSCRIPT_DIR")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached ``Settings`` instance."""

    return Settings()  # type: ignore[call-arg]


settings = get_settings()

