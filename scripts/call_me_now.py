#!/usr/bin/env python3
"""
Direct call script to call the user immediately with the insurance agent.

Usage:
    python scripts/call_me_now.py
"""

import asyncio
import json
import sys
from pathlib import Path
import os

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import get_settings
from app.vapi_client import initiate_outbound_call


async def main() -> None:
    """Make a direct call to the user."""
    
    settings = get_settings()
    
    # Your phone number in E.164 format (set via environment or command line)
    your_phone_number = os.getenv("TEST_PHONE_NUMBER")
    if not your_phone_number:
        print("❌ Error: TEST_PHONE_NUMBER environment variable not set")
        print("   Set it in your .env file or via: export TEST_PHONE_NUMBER='+1234567890'")
        sys.exit(1)
    
    # Determine call type from arguments (default: outbound)
    call_type = "outbound"
    if len(sys.argv) > 1:
        if sys.argv[1] in ["inbound", "outbound"]:
            call_type = sys.argv[1]
    
    print("\n" + "="*70)
    print("📞 Insurance Agent - Direct Call")
    print("="*70)
    print(f"Calling: {your_phone_number}")
    print(f"Call Type: {call_type.upper()}")
    if call_type == "inbound":
        print("(Using INBOUND agent - customer is calling in)")
    else:
        print("(Using OUTBOUND agent - Jennifer is calling)")
    print("Agent: Jennifer from InsureFlow Solutions")
    print("="*70 + "\n")
    
    # Build prospect info
    prospect_info = {
        "prospect_name": "User",
        "company_name": "Your Company",
        "call_type": call_type,
    }
    
    try:
        print("📞 Dialing... Please be ready to answer the call!")
        response = await initiate_outbound_call(
            your_phone_number,
            prospect_info=prospect_info,
            call_type=call_type,
        )
        
        call_id = response.get("id")
        print(f"\n✅ Call initiated successfully!")
        print(f"Call ID: {call_id}")
        print(f"\nResponse: {json.dumps(response, indent=2)}")
        print("\n💡 TIP: Your call transcript will be saved automatically when the call ends.")
        print(f"Check: data/transcripts/ for the transcript file")
        
    except Exception as e:
        print(f"\n❌ Error initiating call: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
