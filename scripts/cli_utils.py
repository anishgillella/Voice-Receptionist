"""Shared CLI utilities for Voice Agent scripts."""

import sys
from pathlib import Path
from typing import Optional

from app.config import get_settings, Settings


def setup_environment() -> Settings:
    """Setup and validate environment."""
    settings = get_settings()
    
    if not settings.vapi_api_key:
        print("❌ Error: VAPI_API_KEY not set in environment")
        print("   Set it in your .env file")
        sys.exit(1)
    
    if not settings.vapi_agent_id and not settings.vapi_agent_id_outbound:
        print("❌ Error: VAPI_AGENT_ID or VAPI_AGENT_ID_OUTBOUND not set")
        print("   Run: python scripts/setup_insurance_agent.py --outbound")
        sys.exit(1)
    
    return settings


def validate_phone_number(phone: str) -> bool:
    """Validate E.164 phone number format."""
    # Basic E.164 validation: +[1-9]\d{1,14}
    return bool(phone.startswith("+") and len(phone) >= 10 and phone[1:].isdigit())


def print_section(title: str, width: int = 70) -> None:
    """Print a formatted section header."""
    print(f"\n{'='*width}")
    print(f"{title}")
    print(f"{'='*width}")


def print_subsection(title: str, width: int = 70) -> None:
    """Print a formatted subsection header."""
    print(f"\n{f'─'*width}")
    print(f"{title}")
    print(f"{f'─'*width}")
