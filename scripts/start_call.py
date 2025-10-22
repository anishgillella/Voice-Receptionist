"""CLI helper to initiate an outbound Vapi call."""

from __future__ import annotations

import asyncio
import json
import sys
from typing import Any, Dict

from pydantic import BaseModel, ValidationError

sys.path.append("/Users/anishgillella/Desktop/Stuff/Projects/Voice Agent")

from app.config import get_settings  # noqa: E402
from app.vapi_client import initiate_outbound_call, create_or_update_insurance_agent  # noqa: E402


class CLIArgs(BaseModel):
    """Validated CLI arguments."""

    phone_number: str
    prospect_name: str | None = None
    company_name: str | None = None
    industry: str | None = None
    lead_id: str | None = None
    metadata_json: str | None = None


async def main(args: CLIArgs) -> None:
    metadata: Dict[str, Any] | None = None
    if args.metadata_json:
        metadata = json.loads(args.metadata_json)
    
    # Build prospect info if provided
    prospect_info: Dict[str, Any] | None = None
    if args.prospect_name and args.company_name:
        prospect_info = {
            "prospect_name": args.prospect_name,
            "company_name": args.company_name,
            "call_type": "insurance_prospect",
        }
        if args.industry:
            prospect_info["industry"] = args.industry
        if args.lead_id:
            prospect_info["lead_id"] = args.lead_id

    response = await initiate_outbound_call(
        args.phone_number,
        metadata=metadata,
        prospect_info=prospect_info,
    )
    print(json.dumps(response, indent=2))


async def create_agent() -> None:
    """Create an insurance prospect agent on Vapi."""
    print("Creating insurance prospect agent on Vapi...")
    response = await create_or_update_insurance_agent()
    print("Agent created successfully!")
    print(json.dumps(response, indent=2))
    print(f"\nAgent ID: {response.get('id')}")
    print("Update your .env file with: VAPI_AGENT_ID={response.get('id')}")


if __name__ == "__main__":
    try:
        # Check if this is a create agent command
        if len(sys.argv) > 1 and sys.argv[1] == "create-agent":
            get_settings()  # Ensure environment variables are validated early
            asyncio.run(create_agent())
        else:
            # Standard call initiation
            cli_args = CLIArgs(
                phone_number=sys.argv[1],
                prospect_name=sys.argv[2] if len(sys.argv) > 2 else None,
                company_name=sys.argv[3] if len(sys.argv) > 3 else None,
                industry=sys.argv[4] if len(sys.argv) > 4 else None,
                lead_id=sys.argv[5] if len(sys.argv) > 5 else None,
                metadata_json=sys.argv[6] if len(sys.argv) > 6 else None,
            )
            get_settings()  # Ensure environment variables are validated early
            asyncio.run(main(cli_args))
    except (IndexError, ValidationError) as exc:  # pragma: no cover - CLI guard
        print("Usage:")
        print("  python scripts/start_call.py <phone_number> [prospect_name] [company_name] [industry] [lead_id] [metadata_json]")
        print("  python scripts/start_call.py create-agent")
        print("\nExample:")
        print("  python scripts/start_call.py +15551234567 'John Doe' 'Acme Corp' 'Manufacturing' 'lead_123'")
        print("  python scripts/start_call.py +15551234567 'Jane Smith' 'Tech Startup' 'Software' 'lead_456' '{\"custom_field\": \"value\"}'")
        raise SystemExit(1) from exc

