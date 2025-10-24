"""Logfire integration for call evaluation and Pydantic model tracing."""

from __future__ import annotations

import logging
from functools import wraps
from typing import Any, Callable

try:
    import logfire
    LOGFIRE_AVAILABLE = True
except ImportError:
    LOGFIRE_AVAILABLE = False

from ..config import settings

logger = logging.getLogger(__name__)


def setup_logfire() -> None:
    """Initialize Logfire with API key from config."""
    if not LOGFIRE_AVAILABLE:
        logger.warning("Logfire not installed, skipping initialization")
        return

    if not settings.logfire_api_key:
        logger.warning("LOGFIRE_API_KEY not configured, skipping Logfire")
        return

    try:
        logfire.configure(token=settings.logfire_api_key)
        logger.info("✅ Logfire initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize Logfire: {e}")


def trace_model(model_name: str) -> Callable:
    """Decorator to trace Pydantic model creation and validation.
    
    Args:
        model_name: Name of the model being traced
        
    Returns:
        Decorator function
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            if not LOGFIRE_AVAILABLE:
                return func(*args, **kwargs)
            
            try:
                with logfire.span(f"pydantic_model_{model_name}", _level="debug") as span:
                    span.set_attribute("model_name", model_name)
                    span.set_attribute("kwargs_keys", list(kwargs.keys()))
                    
                    result = func(*args, **kwargs)
                    span.set_attribute("status", "success")
                    return result
            except Exception as e:
                if LOGFIRE_AVAILABLE:
                    logfire.error(f"Model validation failed for {model_name}: {str(e)}")
                raise
        
        return wrapper
    return decorator


def trace_llm_call(call_type: str) -> Callable:
    """Decorator to trace LLM API calls.
    
    Args:
        call_type: Type of LLM call (e.g., "judge", "extract")
        
    Returns:
        Decorator function
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            if not LOGFIRE_AVAILABLE:
                return await func(*args, **kwargs)
            
            with logfire.span(f"llm_{call_type}", _level="info") as span:
                span.set_attribute("llm_call_type", call_type)
                result = await func(*args, **kwargs)
                span.set_attribute("status", "success")
                return result
        
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            if not LOGFIRE_AVAILABLE:
                return func(*args, **kwargs)
            
            with logfire.span(f"llm_{call_type}", _level="info") as span:
                span.set_attribute("llm_call_type", call_type)
                result = func(*args, **kwargs)
                span.set_attribute("status", "success")
                return result
        
        # Return appropriate wrapper based on function type
        if hasattr(func, '__code__') and 'async' in str(func.__code__.co_flags):
            return async_wrapper
        return sync_wrapper
    
    return decorator


def log_call_metrics(call_id: str, metrics: dict[str, Any]) -> None:
    """Log call metrics to Logfire.
    
    Args:
        call_id: VAPI call ID
        metrics: Dictionary of metrics to log
    """
    if not LOGFIRE_AVAILABLE:
        return
    
    try:
        logfire.info(
            "call_metrics_extracted",
            call_id=call_id,
            **metrics
        )
    except Exception as e:
        logger.error(f"Failed to log metrics to Logfire: {e}")


def log_call_judgment(call_id: str, judgment: dict[str, Any]) -> None:
    """Log call judgment to Logfire.
    
    Args:
        call_id: VAPI call ID
        judgment: Dictionary of judgment data
    """
    if not LOGFIRE_AVAILABLE:
        return
    
    try:
        logfire.info(
            "call_judgment_completed",
            call_id=call_id,
            **judgment
        )
    except Exception as e:
        logger.error(f"Failed to log judgment to Logfire: {e}")
