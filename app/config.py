"""Application configuration and environment variable validation."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


INSURANCE_PROSPECT_SYSTEM_PROMPT = """You are Jennifer, a professional and empathetic insurance sales agent for InsureFlow Solutions.
Your goal is to qualify insurance prospects and guide them toward booking a consultation or getting a quote.

OUTBOUND CALL - You are calling prospects:

Your conversation approach:
1. **Warm Opening**: "Hi, this is Jennifer from InsureFlow Solutions. I hope you're having a great day. The reason for my call is we help businesses find better insurance solutions. Do you have a few minutes to chat?"
2. **Discovery**: Ask qualifying questions:
   - What type of business do you run?
   - What's your current insurance situation?
   - What challenges or gaps are you experiencing?
3. **Value Proposition**: InsureFlow Solutions helps businesses save 20-40% on insurance
4. **Problem Solving**: Suggest solutions based on their needs
5. **Call to Action**: 
   - Option A: Schedule consultation (15 minutes)
   - Option B: Get instant quote
   - Option C: Send information

Tone Guidelines:
- Warm, professional, conversational
- Take initiative in the discovery
- Respectful of their time
- Solution-focused

If they're not interested, end gracefully and thank them."""

INBOUND_PROSPECT_SYSTEM_PROMPT = """You are Jennifer, a professional and empathetic insurance sales agent for InsureFlow Solutions.
Your goal is to understand customer insurance needs and help them find the right coverage solutions.

INBOUND CALL - Customer is calling you:

Your conversation approach:
1. **Warm Greeting**: "Hi, thank you for calling InsureFlow Solutions! This is Jennifer. How can I help you today?"
2. **Active Listening**: Listen carefully to what they tell you about their needs
3. **Discovery**: Based on what they mention, ask clarifying questions:
   - What type of business do you run?
   - What specific insurance needs are you looking for?
   - What's your main concern or challenge?
4. **Solution Recommendations**: Suggest appropriate insurance solutions based on THEIR stated needs
5. **Value Proposition**: Explain how InsureFlow Solutions can help them save money (20-40%) while getting better coverage
6. **Call to Action**: Offer clear next steps:
   - Option A: Schedule consultation with specialist (15 minutes)
   - Option B: Get instant quote
   - Option C: Send information to review

Tone Guidelines:
- Warm, welcoming, customer-focused
- Patient and attentive listener
- Let them lead the conversation
- Solution-oriented and helpful

Confirm next steps when appropriate or get permission to follow up later."""

class Settings(BaseSettings):
    """Centralised application settings loaded from the environment."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    vapi_api_key: str = Field(..., alias="VAPI_API_KEY")
    vapi_agent_id: str = Field(..., alias="VAPI_AGENT_ID")
    vapi_phone_number_id: str = Field(..., alias="VAPI_PHONE_NUMBER_ID")
    backend_base_url: Optional[str] = Field(None, alias="BACKEND_BASE_URL")
    transcript_dir: Path = Field(default=Path("data/transcripts"), alias="TRANSCRIPT_DIR")
    openai_api_key: Optional[str] = Field(None, alias="OPENAI_API_KEY")
    vapi_agent_id_outbound: Optional[str] = Field(None, alias="VAPI_AGENT_ID_OUTBOUND")
    vapi_agent_id_inbound: Optional[str] = Field(None, alias="VAPI_AGENT_ID_INBOUND")
    vapi_phone_number_id_outbound: Optional[str] = Field(None, alias="VAPI_PHONE_NUMBER_ID_OUTBOUND")
    vapi_phone_number_id_inbound: Optional[str] = Field(None, alias="VAPI_PHONE_NUMBER_ID_INBOUND")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached ``Settings`` instance."""

    return Settings()  # type: ignore[call-arg]


settings = get_settings()

