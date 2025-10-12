"""FastAPI entry point for the voice scheduling MVP."""

import json
from typing import Any

from fastapi import FastAPI, HTTPException

from pydantic import BaseModel

from .config import get_settings
from .calendar import create_event, delete_event, list_upcoming_events
from .llm import APPOINTMENT_TOOLS, run_conversation
from .sessions import session_store
from .vapi_models import VapiWebhookPayload, VapiWebhookResponse
from .vapi_client import vapi_client


app = FastAPI(title="Voice Scheduler MVP")


SYSTEM_PROMPT = "You are a friendly salon scheduling assistant."


@app.get("/health", tags=["system"])
def health_check() -> dict[str, str]:
    """Simple health probe."""

    settings = get_settings()
    return {"status": "ok", "calendar": settings.google_calendar_id}


@app.post("/vapi-webhook", response_model=VapiWebhookResponse, tags=["vapi"])
async def vapi_webhook(payload: VapiWebhookPayload) -> VapiWebhookResponse:
    """Handle Vapi webhook events by delegating to OpenAI."""

    if not payload.text:
        raise HTTPException(status_code=400, detail="Empty transcript received.")

    session_history = session_store.get(payload.session_id)
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        *session_history,
        {"role": "user", "content": payload.text},
    ]

    response = run_conversation(messages, tools=APPOINTMENT_TOOLS)
    choice = response.choices[0]
    assistant_message: dict[str, Any] = choice.message

    if assistant_message.get("tool_calls"):
        tool = assistant_message["tool_calls"][0]
        name = tool["function"]["name"]
        arguments = json.loads(tool["function"]["arguments"])
        reply_text = handle_tool_call(name, arguments)
    else:
        reply_text = assistant_message.get("content", "I'm here to help.")

    session_store.append(payload.session_id, "user", payload.text)
    session_store.append(payload.session_id, "assistant", reply_text)

    return VapiWebhookResponse(response=reply_text)


def handle_tool_call(name: str, arguments: dict[str, Any]) -> str:
    action = arguments.get("action")

    if name != "schedule_action" or not action:
        return "I'm sorry, I couldn't process that request. Could you rephrase?"

    if action == "list_events":
        max_results = int(arguments.get("max_results", 5))
        events = list_upcoming_events(max_results=max_results)
        if not events:
            return "I don't see any upcoming appointments on the calendar."
        lines = []
        for event in events:
            start = event.get("start", {}).get("dateTime") or event.get("start", {}).get("date")
            summary = event.get("summary", "(no title)")
            lines.append(f"• {summary} at {start}")
        return "Here are the next appointments:\n" + "\n".join(lines)

    if action == "create_event":
        summary = arguments.get("summary")
        start_iso = arguments.get("start_iso")
        end_iso = arguments.get("end_iso")
        notes = arguments.get("notes")

        if not all([summary, start_iso, end_iso]):
            return "I need the service, start time, and end time to book an appointment."

        description = notes or ""
        event = create_event(summary=summary, start_iso=start_iso, end_iso=end_iso, description=description)
        return f"All set! I booked {summary} starting at {event['start']['dateTime']}"

    if action == "cancel_event":
        event_id = arguments.get("event_id")
        if not event_id:
            return "Please provide the appointment ID to cancel."
        delete_event(event_id)
        return "The appointment has been cancelled."

    return "I couldn't complete that request."


class OutboundCallRequest(BaseModel):
    to_number: str
    phone_number_id: str
    agent_id: str | None = None


@app.post("/outbound-call", tags=["vapi"])
def outbound_call(request: OutboundCallRequest) -> dict[str, Any]:
    """Initiate an outbound Vapi call to the specified phone number."""

    result = vapi_client.start_call(
        to_number=request.to_number,
        phone_number_id=request.phone_number_id,
        agent_id=request.agent_id,
    )
    return result




