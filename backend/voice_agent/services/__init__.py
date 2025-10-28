"""Voice Agent Services - API clients and business logic."""

from .vapi_client import initiate_outbound_call
from .context_manager import ContextManager
from .modal_client import get_modal_client, close_modal_client
from .embedding_cache import get_cached_embedding, cache_embedding, get_cache_stats, get_redis_client, close_redis

__all__ = [
    "initiate_outbound_call",
    "ContextManager",
    "get_modal_client",
    "close_modal_client",
    "get_cached_embedding",
    "cache_embedding",
    "get_cache_stats",
    "get_redis_client",
    "close_redis",
]
