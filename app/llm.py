"""OpenAI orchestration utilities."""

from typing import Any, Dict, List

from openai import OpenAI

from .config import get_settings


APPOINTMENT_TOOLS: List[Dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "schedule_action",
            "description": "Interact with Google Calendar to list, create, update, or cancel salon appointments.",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": [
                            "list_events",
                            "create_event",
                            "cancel_event",
                        ],
                    },
                    "summary": {
                        "type": "string",
                        "description": "Short description of the appointment (required for create).",
                    },
                    "start_iso": {
                        "type": "string",
                        "description": "ISO-8601 start datetime with timezone (e.g. 2025-10-12T14:00:00-04:00).",
                    },
                    "end_iso": {
                        "type": "string",
                        "description": "ISO-8601 end datetime with timezone (required for create).",
                    },
                    "event_id": {
                        "type": "string",
                        "description": "Calendar event ID (required for cancel).",
                    },
                    "max_results": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 10,
                        "description": "Number of upcoming events to list (for list_events).",
                    },
                    "notes": {
                        "type": "string",
                        "description": "Optional notes to include in appointment description.",
                    },
                },
                "required": ["action"],
            },
        },
    }
]


def get_client() -> OpenAI:
    settings = get_settings()
    return OpenAI(api_key=settings.openai_api_key)


def run_conversation(messages: List[Dict[str, Any]], tools: List[Dict[str, Any]] | None = None):
    client = get_client()
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        tools=tools or [],
    )
    return response



