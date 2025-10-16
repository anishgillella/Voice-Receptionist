"""CLI helper to initiate an outbound Vapi call."""

from __future__ import annotations

import asyncio
import json
import sys
from typing import Any, Dict

from pydantic import BaseModel, ValidationError

sys.path.append("/Users/anishgillella/Desktop/Stuff/Projects/Voice Agent")

from app.config import get_settings  # noqa: E402
from app.vapi_client import initiate_outbound_call  # noqa: E402


class CLIArgs(BaseModel):
    """Validated CLI arguments."""

    phone_number: str
    metadata_json: str | None = None


async def main(args: CLIArgs) -> None:
    metadata: Dict[str, Any] | None = None
    if args.metadata_json:
        metadata = json.loads(args.metadata_json)

    response = await initiate_outbound_call(args.phone_number, metadata=metadata)
    print(json.dumps(response, indent=2))


if __name__ == "__main__":
    try:
        cli_args = CLIArgs(
            phone_number=sys.argv[1],
            metadata_json=sys.argv[2] if len(sys.argv) > 2 else None,
        )
    except (IndexError, ValidationError) as exc:  # pragma: no cover - CLI guard
        print("Usage: python scripts/start_call.py <phone_number> [metadata_json]")
        raise SystemExit(1) from exc

    get_settings()  # Ensure environment variables are validated early
    asyncio.run(main(cli_args))

