"""Request and response models for Vapi webhook integration."""

from typing import Optional

from pydantic import BaseModel, Field


class CallerInfo(BaseModel):
    phone_number: Optional[str] = Field(None, description="Caller ID or phone number.")
    name: Optional[str] = Field(None, description="Caller display name if available.")


class VapiWebhookPayload(BaseModel):
    session_id: str = Field(..., description="Unique identifier for the call session.")
    text: str = Field("", description="Latest transcription from the caller.")
    call_id: Optional[str] = Field(None, description="Unique call identifier from Vapi.")
    caller: Optional[CallerInfo] = Field(None, description="Optional caller metadata.")


class VapiWebhookResponse(BaseModel):
    response: str = Field(..., description="Text to synthesize back to the caller.")


