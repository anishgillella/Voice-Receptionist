"""Configuration utilities for the voice scheduling MVP."""

from functools import lru_cache
from typing import Optional

from pydantic import BaseSettings, Field, HttpUrl


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    vapi_api_key: str = Field(..., env="VAPI_API_KEY")
    openai_api_key: str = Field(..., env="OPENAI_API_KEY")

    google_client_id: str = Field(..., env="GOOGLE_CLIENT_ID")
    google_client_secret: str = Field(..., env="GOOGLE_CLIENT_SECRET")
    google_refresh_token: str = Field(..., env="GOOGLE_REFRESH_TOKEN")
    google_calendar_id: str = Field("primary", env="GOOGLE_CALENDAR_ID")

    default_timezone: str = Field("America/New_York", env="DEFAULT_TIMEZONE")
    backend_base_url: HttpUrl = Field(..., env="BACKEND_BASE_URL")

    vapi_agent_id: Optional[str] = Field(None, env="VAPI_AGENT_ID")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    """Return cached application settings."""

    return Settings()


