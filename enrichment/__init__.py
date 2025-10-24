"""Enrichment module for data enrichment using Task MCP (Parallel API)."""

from .config import get_enrichment_settings, EnrichmentSettings
from .client import TaskMCPClient
from .manager import TaskManager
from .models import (
    EnrichmentItem,
    TaskGroupRequest,
    DeepResearchRequest,
    TaskResult,
)
from .storage import EnrichmentResultsStorage
from .webhooks import WebhookHandler, WebhookPayload
from .fastapi_integration import setup_enrichment_routes, setup_webhook_callbacks

__all__ = [
    "EnrichmentSettings",
    "get_enrichment_settings",
    "TaskMCPClient",
    "TaskManager",
    "EnrichmentItem",
    "TaskGroupRequest",
    "DeepResearchRequest",
    "TaskResult",
    "EnrichmentResultsStorage",
    "WebhookHandler",
    "WebhookPayload",
    "setup_enrichment_routes",
    "setup_webhook_callbacks",
]
