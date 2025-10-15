"""Configuration utilities for the voice scheduling MVP."""

from functools import lru_cache
from pathlib import Path
from typing import Optional

import yaml
from pydantic import Field, HttpUrl
from pydantic_settings import BaseSettings


CONFIG_PATH = Path(__file__).resolve().parent.parent / "salon_config.yaml"


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    vapi_api_key: str = Field(..., env="VAPI_API_KEY")
    openai_api_key: str = Field(..., env="OPENAI_API_KEY")

    google_client_id: str = Field(..., env="GOOGLE_CLIENT_ID")
    google_client_secret: str = Field(..., env="GOOGLE_CLIENT_SECRET")
    google_refresh_token: str = Field(..., env="GOOGLE_REFRESH_TOKEN")
    google_calendar_id: str = Field("primary", env="GOOGLE_CALENDAR_ID")

    supabase_database_url: str = Field(..., env="SUPABASE_DATABASE_URL")

    default_timezone: str = Field("America/New_York", env="DEFAULT_TIMEZONE")
    backend_base_url: HttpUrl = Field(..., env="BACKEND_BASE_URL")

    vapi_agent_id: Optional[str] = Field(None, env="VAPI_AGENT_ID")
    transcript_debug: bool = Field(False, env="TRANSCRIPT_DEBUG")
    vapi_phone_number_id: Optional[str] = Field(None, env="VAPI_PHONE_NUMBER_ID")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

    @property
    def salon_profile(self) -> dict:
        with CONFIG_PATH.open("r", encoding="utf-8") as fh:
            return yaml.safe_load(fh)


@lru_cache()
def get_settings() -> Settings:
    """Return cached application settings."""

    return Settings()


