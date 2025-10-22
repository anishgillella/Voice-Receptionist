#!/usr/bin/env python3
"""
Setup script to fully configure the insurance agents through code.

Creates/updates Vapi agents for both OUTBOUND and INBOUND calls.

Usage:
    python scripts/setup_insurance_agent.py --outbound [--update AGENT_ID]
    python scripts/setup_insurance_agent.py --inbound [--update AGENT_ID]
    
Examples:
    # Create new OUTBOUND agent
    python scripts/setup_insurance_agent.py --outbound
    
    # Create new INBOUND agent
    python scripts/setup_insurance_agent.py --inbound
    
    # Update existing OUTBOUND agent
    python scripts/setup_insurance_agent.py --outbound --update <AGENT_ID>
"""

import asyncio
import sys
from pathlib import Path

from cli_utils import setup_environment, print_section
from app.vapi_client import create_or_update_insurance_agent


async def setup_agent(agent_id: str | None = None, call_type: str = "outbound") -> None:
    """Setup or update an insurance agent."""
    
    settings = setup_environment()
    
    print_section("🔧 Insurance Agent Setup", 70)
    
    if agent_id:
        print(f"\nUpdating existing {call_type.upper()} agent: {agent_id}")
    else:
        print(f"\nCreating new {call_type.upper()} agent...")
    
    print(f"Call Type: {call_type.upper()}")
    print(f"Backend URL: {settings.backend_base_url}")
    print(f"API Key: {settings.vapi_api_key[:20]}...")
    
    response = await create_or_update_insurance_agent(agent_id=agent_id, call_type=call_type)
    
    if "error" in response:
        print(f"\n❌ Setup failed: {response.get('error')}")
        print(f"Status: {response.get('status_code')}")
        sys.exit(1)
    
    new_agent_id = response.get("id")
    
    # Update .env file if this is a new agent
    if not agent_id and new_agent_id:
        env_file = Path(".env")
        env_content = env_file.read_text()
        
        # Add or update the appropriate agent ID
        lines = env_content.split("\n")
        env_key = f"VAPI_AGENT_ID_{call_type.upper()}"
        found = False
        
        for i, line in enumerate(lines):
            if line.startswith(env_key + "="):
                lines[i] = f"{env_key}={new_agent_id}"
                found = True
                break
        
        if not found:
            lines.append(f"{env_key}={new_agent_id}")
        
        env_content = "\n".join(lines)
        env_file.write_text(env_content)
        print(f"\n✅ Updated .env file with new {call_type.upper()} agent ID")
    
    print_section("✅ Setup Complete!", 70)
    print(f"\nAgent ID: {new_agent_id}")
    print(f"Agent Name: {response.get('name')}")
    print(f"Call Type: {call_type.upper()}")
    print(f"Webhook URL: {settings.backend_base_url}/webhook")
    print(f"\nYour {call_type.upper()} agent is now configured!")


def main() -> None:
    """Main entry point."""
    
    agent_id = None
    call_type = "outbound"  # default
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "--outbound":
            call_type = "outbound"
        elif sys.argv[1] == "--inbound":
            call_type = "inbound"
        elif sys.argv[1] == "--help":
            print(__doc__)
            return
        
        # Check for --update flag
        if len(sys.argv) > 2:
            if sys.argv[2] == "--update" and len(sys.argv) > 3:
                agent_id = sys.argv[3]
    
    asyncio.run(setup_agent(agent_id=agent_id, call_type=call_type))


if __name__ == "__main__":
    main()
