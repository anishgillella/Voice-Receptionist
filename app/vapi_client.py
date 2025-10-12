"""Utility client for interacting with the Vapi REST API."""

from typing import Any, Dict, Optional

import httpx

from .config import get_settings


class VapiClient:
    def __init__(self) -> None:
        settings = get_settings()
        self._client = httpx.Client(
            base_url="https://api.vapi.ai",
            headers={
                "Authorization": f"Bearer {settings.vapi_api_key}",
                "Content-Type": "application/json",
            },
            timeout=30,
        )
        self._agent_id = settings.vapi_agent_id

    def start_call(self, to_number: str, phone_number_id: str, agent_id: Optional[str] = None) -> Dict[str, Any]:
        assistant_identifier = agent_id or self._agent_id
        if not assistant_identifier:
            raise ValueError("assistant_id is required; set VAPI_AGENT_ID or pass agent_id explicitly.")

        payload = {
            "assistantId": assistant_identifier,
            "phoneNumberId": phone_number_id,
            "customer": {"number": to_number},
        }

        response = self._client.post("/call", json=payload)
        response.raise_for_status()
        return response.json()


vapi_client = VapiClient()


