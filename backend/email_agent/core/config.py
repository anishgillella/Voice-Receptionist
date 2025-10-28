"""Email Agent Configuration and Environment Variables."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


# Get the directory where this config file is located
config_dir = Path(__file__).parent.parent


class EmailAgentSettings(BaseSettings):
    """Centralised email agent settings loaded from the environment."""

    model_config = SettingsConfigDict(
        env_file=config_dir / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Gmail OAuth Configuration
    gmail_client_id: str = Field(..., alias="GMAIL_CLIENT_ID")
    gmail_client_secret: str = Field(..., alias="GMAIL_CLIENT_SECRET")
    gmail_redirect_uri: str = Field(
        default="http://localhost:8000/auth/gmail/callback",
        alias="GMAIL_REDIRECT_URI"
    )

    # AWS S3 Configuration
    aws_access_key_id: str = Field(..., alias="AWS_ACCESS_KEY_ID")
    aws_secret_access_key: str = Field(..., alias="AWS_SECRET_ACCESS_KEY")
    aws_region: str = Field(default="us-east-1", alias="AWS_REGION")
    aws_s3_bucket_name: str = Field(..., alias="AWS_S3_BUCKET_NAME")

    # Supabase Configuration
    supabase_url: str = Field(..., alias="SUPABASE_URL")
    supabase_key: str = Field(..., alias="SUPABASE_KEY")
    supabase_schema: str = Field(default="public", alias="SUPABASE_SCHEMA")

    # Backend Configuration
    backend_base_url: str = Field(
        default="http://localhost:8000",
        alias="BACKEND_BASE_URL"
    )

    # Email Agent Configuration
    max_attachment_size_mb: int = Field(default=25, alias="MAX_ATTACHMENT_SIZE_MB")

    # Environment
    environment: str = Field(default="development", alias="ENVIRONMENT")
    debug: bool = Field(default=True, alias="DEBUG")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    @property
    def supported_document_types(self) -> list[str]:
        """Get supported document types."""
        return ["pdf", "docx", "doc"]


@lru_cache(maxsize=1)
def get_email_settings() -> EmailAgentSettings:
    """Return a cached EmailAgentSettings instance."""
    return EmailAgentSettings()  # type: ignore[call-arg]


email_settings = get_email_settings()
