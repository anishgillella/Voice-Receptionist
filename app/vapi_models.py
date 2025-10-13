"""Request and response models for Vapi webhook integration."""

from typing import Optional

from pydantic import BaseModel, Field


class CallerInfo(BaseModel):
    phone_number: Optional[str] = Field(None, description="Caller ID or phone number.")
    name: Optional[str] = Field(None, description="Caller display name if available.")


class TranscriptPayload(BaseModel):
    session_id: str = Field(..., description="Call session identifier.")
    call_id: str | None = Field(None, description="Unique call identifier.")
    role: str = Field(..., description="Role associated with the transcript snippet (user/assistant).")
    transcript: str = Field(..., description="Recognized transcript text.")
    transcript_type: str = Field(..., description="Partial or final indicator.")
    metadata: dict | None = Field(None, description="Additional transcript metadata if provided.")


class VapiWebhookPayload(BaseModel):
    session_id: str = Field(..., description="Unique identifier for the call session.")
    text: str = Field("", description="Latest transcription from the caller.")
    call_id: str | None = Field(None, description="Unique call identifier from Vapi.")
    message_type: str | None = Field(
        None, description="Type of webhook message (transcript, function-call, etc.)."
    )
    caller: Optional[CallerInfo] = Field(None, description="Optional caller metadata.")
    transcript: Optional[TranscriptPayload] = Field(
        None, description="Optional transcript event data from Vapi."
    )
    metadata: dict | None = Field(
        None, description="Raw event metadata supplied by Vapi."
    )


class VapiWebhookResponse(BaseModel):
    response: str = Field(..., description="Text to synthesize back to the caller.")


