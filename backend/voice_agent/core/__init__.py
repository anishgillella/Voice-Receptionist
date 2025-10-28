"""Voice Agent Core - Configuration, Models, and Database."""

from .config import Settings, get_settings, INSURANCE_PROSPECT_SYSTEM_PROMPT, INBOUND_PROSPECT_SYSTEM_PROMPT
from .models import Customer, CustomerCreate, CallJudgment, CallMetrics
from .db import (
    get_db, get_or_create_customer, store_conversation, store_embedding,
    store_customer_memory, close_db, update_conversation_summary,
    get_table_name, store_call_metrics, store_call_judgment,
)

__all__ = [
    "Settings",
    "get_settings",
    "INSURANCE_PROSPECT_SYSTEM_PROMPT",
    "INBOUND_PROSPECT_SYSTEM_PROMPT",
    "Customer",
    "CustomerCreate",
    "CallJudgment",
    "CallMetrics",
    "get_db",
    "get_or_create_customer",
    "store_conversation",
    "store_embedding",
    "store_customer_memory",
    "close_db",
    "update_conversation_summary",
    "get_table_name",
    "store_call_metrics",
    "store_call_judgment",
]
