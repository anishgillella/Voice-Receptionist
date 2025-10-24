"""Configuration for Task MCP (Parallel API) enrichment module."""

from __future__ import annotations

from functools import lru_cache
from typing import Optional
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class EnrichmentSettings(BaseSettings):
    """Enrichment module settings for Task MCP integration."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Parallel API (Task MCP) Configuration
    parallel_api_key: str = Field(..., alias="PARALLEL_API_KEY")
    parallel_api_base_url: str = Field(
        default="https://api.parallel.com",
        alias="PARALLEL_API_BASE_URL"
    )

    # Task Configuration
    task_timeout_seconds: int = Field(default=300, alias="TASK_TIMEOUT_SECONDS")
    max_parallel_tasks: int = Field(default=10, alias="MAX_PARALLEL_TASKS")
    task_poll_interval_seconds: int = Field(default=5, alias="TASK_POLL_INTERVAL_SECONDS")

    # Enrichment Data Configuration
    max_batch_size: int = Field(default=50, alias="MAX_BATCH_SIZE")
    retry_attempts: int = Field(default=3, alias="RETRY_ATTEMPTS")
    retry_delay_seconds: int = Field(default=2, alias="RETRY_DELAY_SECONDS")

    # Database Configuration (for storing enrichment results)
    supabase_url: Optional[str] = Field(None, alias="SUPABASE_URL")
    supabase_key: Optional[str] = Field(None, alias="SUPABASE_KEY")

    # Environment
    environment: str = Field(default="development", alias="ENVIRONMENT")
    debug: bool = Field(default=False, alias="DEBUG")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")


@lru_cache(maxsize=1)
def get_enrichment_settings() -> EnrichmentSettings:
    """Return a cached EnrichmentSettings instance."""
    return EnrichmentSettings()  # type: ignore[call-arg]


enrichment_settings = get_enrichment_settings()
