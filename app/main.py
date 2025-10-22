"""FastAPI application for initiating Vapi calls and handling webhooks."""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from .config import Settings, get_settings
from .vapi_client import initiate_outbound_call


logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


app = FastAPI(title="Voice Agent", version="0.1.0")


class CallRequest(BaseModel):
    """Payload for making an outbound call."""

    phone_number: str = Field(..., description="E.164 formatted phone number, e.g. +15551234567")
    metadata: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Optional metadata to attach to the Vapi call",
    )


class InsuranceProspectCallRequest(BaseModel):
    """Payload for making an outbound call to an insurance prospect."""
    
    phone_number: str = Field(..., description="E.164 formatted phone number, e.g. +15551234567")
    prospect_name: str = Field(..., description="Prospect's full name")
    company_name: str = Field(..., description="Company/business name")
    industry: Optional[str] = Field(default=None, description="Industry/business type")
    lead_id: Optional[str] = Field(default=None, description="Internal lead ID")
    estimated_employees: Optional[int] = Field(default=None, description="Estimated number of employees")
    location: Optional[str] = Field(default=None, description="Business location/state")


@app.get("/health")
async def healthcheck() -> Dict[str, str]:
    """Basic readiness probe."""

    return {"status": "ok"}


@app.post("/call")
async def trigger_call(
    payload: CallRequest,
    settings: Settings = Depends(get_settings),
) -> JSONResponse:
    """Trigger an outbound Vapi call to the provided number."""

    # Trigger call via the Vapi API
    try:
        response = await initiate_outbound_call(
            payload.phone_number,
            metadata=payload.metadata,
        )
    except Exception as exc:  # pragma: no cover - propagated to caller
        logger.exception("Failed to initiate Vapi call")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc

    logger.info("Queued call via Vapi", extra={"response": response})

    return JSONResponse(content=response, status_code=status.HTTP_202_ACCEPTED)


@app.post("/call/insurance-prospect")
async def trigger_insurance_prospect_call(
    payload: InsuranceProspectCallRequest,
    settings: Settings = Depends(get_settings),
) -> JSONResponse:
    """Trigger an outbound call to an insurance prospect.
    
    This endpoint initiates a call with insurance prospect information that the
    agent will use to personalize the conversation.
    """
    
    # Build prospect metadata
    prospect_info = {
        "prospect_name": payload.prospect_name,
        "company_name": payload.company_name,
        "call_type": "insurance_prospect",
    }
    
    if payload.industry:
        prospect_info["industry"] = payload.industry
    if payload.lead_id:
        prospect_info["lead_id"] = payload.lead_id
    if payload.estimated_employees:
        prospect_info["estimated_employees"] = payload.estimated_employees
    if payload.location:
        prospect_info["location"] = payload.location
    
    # Trigger call via the Vapi API
    try:
        response = await initiate_outbound_call(
            payload.phone_number,
            prospect_info=prospect_info,
        )
    except Exception as exc:  # pragma: no cover - propagated to caller
        logger.exception("Failed to initiate insurance prospect call")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc
    
    logger.info(
        "Queued insurance prospect call",
        extra={
            "prospect": payload.prospect_name,
            "company": payload.company_name,
            "phone": payload.phone_number,
            "response": response,
        },
    )
    
    return JSONResponse(content=response, status_code=status.HTTP_202_ACCEPTED)


async def _handle_end_of_call_report(message: Dict[str, Any], settings: Settings) -> None:
    """Process an ``end-of-call-report`` payload."""

    artifact = message.get("artifact", {})
    transcript = artifact.get("transcript")
    recording = artifact.get("recording")
    messages = artifact.get("messages")
    ended_reason = message.get("endedReason")
    call_data = message.get("call", {})
    call_id = call_data.get("id") or message.get("id") or message.get("callId")

    logger.info("Call ended", extra={"ended_reason": ended_reason})
    if transcript:
        logger.info("Full transcript:\n%s", transcript)
        await _persist_transcript(
            transcript,
            settings=settings,
            call_id=call_id,
            ended_reason=ended_reason,
            recording=recording,
            messages=messages,
            raw_message=message,
        )
    if recording:
        logger.info("Recording info", extra={"recording": recording})


async def _handle_status_update(message: Dict[str, Any]) -> None:
    """Process a status-update webhook message."""

    status_value = message.get("status")
    if status_value == "ended":
        logger.info("Call status ended", extra={"call": message.get("call")})


@app.post("/webhook")
async def webhook(request: Request) -> Dict[str, str]:
    """Receive webhook callbacks from Vapi."""

    try:
        payload = await request.json()
    except json.JSONDecodeError as exc:  # pragma: no cover - FastAPI handles silently
        logger.warning("Invalid JSON payload received from Vapi", exc_info=exc)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid JSON")

    message = payload.get("message")
    if not isinstance(message, dict):
        logger.warning("Webhook payload missing message field: %s", payload)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing message field")

    message_type = message.get("type")
    logger.debug("Received webhook message", extra={"message_type": message_type})

    settings = get_settings()

    if message_type == "end-of-call-report":
        asyncio.create_task(_handle_end_of_call_report(message, settings))
    elif message_type == "status-update":
        asyncio.create_task(_handle_status_update(message))
    else:
        logger.info("Ignored webhook message type", extra={"type": message_type, "call_id": message.get("call", {}).get("id")})

    return {"status": "received"}


async def _persist_transcript(
    transcript: str,
    *,
    settings: Settings,
    call_id: Optional[str],
    ended_reason: Optional[str],
    recording: Optional[Dict[str, Any]],
    messages: Optional[Any],
    raw_message: Dict[str, Any],
) -> None:
    """Persist call transcript and metadata to disk."""

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    safe_call_id = call_id or "unknown"

    target_dir = Path(settings.transcript_dir).expanduser()
    target_dir.mkdir(parents=True, exist_ok=True)

    file_path = target_dir / f"{timestamp}_{safe_call_id}.json"

    payload = {
        "call_id": call_id,
        "ended_reason": ended_reason,
        "recording": recording,
        "messages": messages,
        "transcript": transcript,
        "raw_message": raw_message,
        "written_at": datetime.now(timezone.utc).isoformat(),
    }

    def _write() -> None:
        file_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    await asyncio.to_thread(_write)
    logger.info("Stored transcript", extra={"path": str(file_path)})

