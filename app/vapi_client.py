"""Helper utilities for interacting with the Vapi REST API."""

from __future__ import annotations

from typing import Any, Dict, Optional

import httpx

from .config import settings

VAPI_BASE_URL = "https://api.vapi.ai"


async def initiate_outbound_call(
    customer_number: str,
    *,
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Trigger an outbound call via Vapi.

    Args:
        customer_number: E.164-formatted phone number for the customer.
        metadata: Optional metadata dict to include with the call.

    Returns:
        Parsed JSON response from Vapi.
    """

    payload: Dict[str, Any] = {
        "assistantId": settings.vapi_agent_id,
        "phoneNumberId": settings.vapi_phone_number_id,
        "customer": {"number": customer_number},
    }

    if metadata:
        payload["metadata"] = metadata

    headers = {
        "Authorization": f"Bearer {settings.vapi_api_key}",
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(base_url=VAPI_BASE_URL, timeout=30.0) as client:
        response = await client.post("/call", json=payload, headers=headers)
        response.raise_for_status()
        return response.json()

