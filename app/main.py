"""FastAPI entry point for the voice scheduling MVP."""

import json
from typing import Any

from fastapi import FastAPI, HTTPException

from pydantic import BaseModel

from .calendar import create_event, delete_event, list_upcoming_events
from .config import get_settings
from .db import (
    ensure_tables_exist,
    fetch_transcript,
    insert_calendar_action,
    insert_transcript,
    upsert_session,
)
from .llm import APPOINTMENT_TOOLS, run_conversation
from .sessions import session_store
from .vapi_client import vapi_client
from .vapi_models import VapiWebhookPayload, VapiWebhookResponse


app = FastAPI(title="Voice Scheduler MVP")


SYSTEM_PROMPT = "You are a friendly salon scheduling assistant."


@app.get("/health", tags=["system"])
def health_check() -> dict[str, str]:
    """Simple health probe."""

    settings = get_settings()
    return {"status": "ok", "calendar": settings.google_calendar_id}


@app.on_event("startup")
async def on_startup() -> None:
    await ensure_tables_exist()


@app.post("/vapi-webhook", response_model=VapiWebhookResponse, tags=["vapi"])
async def vapi_webhook(payload: VapiWebhookPayload) -> VapiWebhookResponse:
    """Handle Vapi webhook events by delegating to OpenAI."""

    if payload.transcript and payload.transcript.transcript_type != "final":
        return VapiWebhookResponse(response="")

    if not payload.text:
        payload_text = payload.transcript.transcript if payload.transcript else ""
    else:
        payload_text = payload.text

    if not payload_text:
        raise HTTPException(status_code=400, detail="Empty transcript received.")

    session_history = session_store.get(payload.session_id)
    await upsert_session(
        payload.session_id,
        {
            "call_id": payload.call_id,
            "caller": payload.caller.dict() if payload.caller else None,
            "metadata": payload.metadata,
        },
    )

    messages = [
        *session_history,
        {"role": "user", "content": payload_text},
    ]

    session_store.append(payload.session_id, "user", payload_text)
    await insert_transcript(
        payload.session_id,
        "user",
        payload_text,
        {
            "call_id": payload.call_id,
            "metadata": payload.metadata,
            "transcript": payload.transcript.dict() if payload.transcript else None,
        },
    )

    response = run_conversation(messages, tools=APPOINTMENT_TOOLS)
    choice = response.choices[0]
    assistant_message: dict[str, Any] = choice.message

    if assistant_message.get("tool_calls"):
        tool = assistant_message["tool_calls"][0]
        name = tool["function"]["name"]
        arguments = json.loads(tool["function"]["arguments"])
        reply_text, calendar_metadata = await handle_tool_call(
            payload.session_id, name, arguments
        )
    else:
        reply_text = assistant_message.get("content", "I'm here to help.")
        calendar_metadata = None

    session_store.append(
        payload.session_id,
        "assistant",
        reply_text,
        metadata=calendar_metadata,
    )
    await insert_transcript(
        payload.session_id,
        "assistant",
        reply_text,
        {"tool": calendar_metadata} if calendar_metadata else {},
    )

    return VapiWebhookResponse(response=reply_text)


async def handle_tool_call(
    session_id: str, name: str, arguments: dict[str, Any]
) -> tuple[str, dict[str, Any] | None]:
    action = arguments.get("action")

    if name != "schedule_action" or not action:
        return "I'm sorry, I couldn't process that request. Could you rephrase?", None

    if action == "list_events":
        max_results = int(arguments.get("max_results", 5))
        events = list_upcoming_events(max_results=max_results)
        if not events:
            return "I don't see any upcoming appointments on the calendar.", None
        lines = []
        for event in events:
            start = event.get("start", {}).get("dateTime") or event.get("start", {}).get("date")
            summary = event.get("summary", "(no title)")
            lines.append(f"• {summary} at {start}")
        return "Here are the next appointments:\n" + "\n".join(lines), None

    if action == "create_event":
        summary = arguments.get("summary")
        start_iso = arguments.get("start_iso")
        end_iso = arguments.get("end_iso")
        notes = arguments.get("notes")

        if not all([summary, start_iso, end_iso]):
            return "I need the service, start time, and end time to book an appointment.", None

        description = notes or ""
        event = create_event(summary=summary, start_iso=start_iso, end_iso=end_iso, description=description)
        await insert_calendar_action(
            session_id=session_id,
            action="create",
            event_id=event.get("id"),
            summary=summary,
            start_time=event["start"].get("dateTime"),
            end_time=event["end"].get("dateTime"),
            stylist=arguments.get("stylist"),
            service=arguments.get("service"),
        )
        metadata = {
            "action": "create",
            "event_id": event.get("id"),
            "start": event["start"].get("dateTime"),
            "end": event["end"].get("dateTime"),
        }
        return f"All set! I booked {summary} starting at {event['start']['dateTime']}", metadata

    if action == "cancel_event":
        event_id = arguments.get("event_id")
        if not event_id:
            return "Please provide the appointment ID to cancel.", None
        delete_event(event_id)
        await insert_calendar_action(
            session_id=session_id,
            action="delete",
            event_id=event_id,
            summary=None,
            start_time=None,
            end_time=None,
            stylist=None,
            service=None,
        )
        metadata = {"action": "cancel", "event_id": event_id}
        return "The appointment has been cancelled.", metadata

    return "I couldn't complete that request.", None


class OutboundCallRequest(BaseModel):
    to_number: str
    phone_number_id: str | None = None
    agent_id: str | None = None


class UpdateAssistantRequest(BaseModel):
    refresh_prompts: bool = True


@app.post("/outbound-call", tags=["vapi"])
def outbound_call(request: OutboundCallRequest) -> dict[str, Any]:
    """Initiate an outbound Vapi call to the specified phone number."""

    result = vapi_client.start_call(
        to_number=request.to_number,
        phone_number_id=request.phone_number_id,
        agent_id=request.agent_id,
    )
    return result


@app.post("/assistant/update-prompts", tags=["vapi"])
def update_prompts(_: UpdateAssistantRequest) -> dict[str, Any]:
    """Push the latest salon prompt and messages to the Vapi assistant."""

    result = vapi_client.update_assistant_prompts()
    return result


@app.get("/call/latest", tags=["vapi"])
def get_latest_call() -> dict[str, Any]:
    """Retrieve the latest call metadata from Vapi."""

    call = vapi_client.fetch_latest_call()
    if not call:
        raise HTTPException(status_code=404, detail="No calls found")
    return call


@app.get("/call/{call_id}", tags=["vapi"])
def get_call(call_id: str) -> dict[str, Any]:
    """Fetch a call transcript and details by ID."""

    call = vapi_client.fetch_call_by_id(call_id)
    if not call:
        raise HTTPException(status_code=404, detail="Call not found")
    return call


@app.get("/transcript/{session_id}", tags=["transcripts"])
async def get_transcript(session_id: str) -> list[dict[str, Any]]:
    rows = await fetch_transcript(session_id)
    return [
        {
            "role": row["role"],
            "message": row["message"],
            "metadata": row["metadata"],
            "timestamp": row["created_at"].isoformat() if row["created_at"] else None,
        }
        for row in rows
    ]




