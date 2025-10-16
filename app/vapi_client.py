"""Utility client for interacting with the Vapi REST API."""

from typing import Any, Dict, Optional

import httpx

from .config import get_settings
from .models import build_end_call_message, build_first_message, build_system_prompt, build_voicemail_message


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
        self._phone_number_id = settings.vapi_phone_number_id
        self._profile = settings.salon_profile

    def update_assistant_prompts(self, *, base_url: Optional[str] = None) -> Dict[str, Any]:
        if not self._agent_id:
            raise ValueError("VAPI_AGENT_ID must be provided to update assistant prompts.")

        system_prompt = build_system_prompt(self._profile)
        first_message = build_first_message(self._profile)
        base_webhook_url = base_url or get_settings().backend_base_url.rstrip("/")

        payload = {
            "firstMessage": first_message,
            "model": {
                "provider": "openai",
                "model": "gpt-4o-mini",
                "messages": [
                    {
                        "role": "system",
                        "content": system_prompt,
                    }
                ],
            },
            "voicemailMessage": build_voicemail_message(self._profile),
            "endCallMessage": build_end_call_message(self._profile),
            "serverUrl": f"{base_webhook_url}/vapi-webhook",
            "serverMessages": [
                "transcript",
                "conversation-update",
                "end-of-call-report",
                "status-update",
            ],
        }

        response = self._client.patch(f"/assistant/{self._agent_id}", json=payload)
        response.raise_for_status()
        return response.json()

    def start_call(self, to_number: str, phone_number_id: Optional[str] = None, agent_id: Optional[str] = None) -> Dict[str, Any]:
        assistant_identifier = agent_id or self._agent_id
        if not assistant_identifier:
            raise ValueError("assistant_id is required; set VAPI_AGENT_ID or pass agent_id explicitly.")

        phone_id = phone_number_id or self._phone_number_id
        if not phone_id:
            raise ValueError("phone_number_id is required; set VAPI_PHONE_NUMBER_ID or pass phone_number_id explicitly.")

        payload = {
            "assistantId": assistant_identifier,
            "phoneNumberId": phone_id,
            "customer": {"number": to_number},
        }

        response = self._client.post("/call", json=payload)
        response.raise_for_status()
        return response.json()

    def fetch_latest_call(self) -> Dict[str, Any]:
        params = {"assistantId": self._agent_id, "limit": 1}
        response = self._client.get("/calls", params=params)
        response.raise_for_status()
        calls = response.json().get("items", [])
        if not calls:
            return {}
        return calls[0]

    def fetch_call_by_id(self, call_id: str) -> Dict[str, Any]:
        response = self._client.get(f"/call/{call_id}")
        response.raise_for_status()
        return response.json()


vapi_client = VapiClient()


