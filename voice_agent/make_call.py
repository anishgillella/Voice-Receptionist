#!/usr/bin/env python
"""Simple script to make an outbound call with customer context."""

import asyncio
import sys
import os
from pathlib import Path
from uuid import UUID

sys.path.insert(0, str(Path(__file__).parent))

from app.vapi_client import initiate_outbound_call
from app.config import settings, INSURANCE_PROSPECT_SYSTEM_PROMPT
from app.db import get_db, get_customer_by_id, get_table_name
from app.context_manager import ContextManager


async def main():
    """Make an outbound call with customer context."""
    
    # Get phone number from environment or use default
    phone_number = os.getenv("CALL_PHONE_NUMBER") or "+14698674545"
    
    print("=" * 70)
    print("📞 Making Outbound Call with Customer Context")
    print("=" * 70)
    print(f"Phone: {phone_number}")
    
    # Get customer and context
    db = get_db()
    customer = db.execute(
        f"SELECT id FROM {get_table_name('customers')} WHERE phone_number = %s LIMIT 1",
        (phone_number,)
    )
    
    enhanced_prompt = INSURANCE_PROSPECT_SYSTEM_PROMPT
    
    if customer:
        customer_id = UUID(customer[0]['id'])
        customer_obj = get_customer_by_id(customer_id)
        
        print(f"\n👤 Customer Context:")
        print(f"   Name: {customer_obj.company_name}")
        print(f"   Industry: {customer_obj.industry}")
        print(f"   Location: {customer_obj.location}")
        
        # Get relevant past conversations
        ctx_manager = ContextManager()
        agent_context = ctx_manager.build_agent_context(
            customer_obj,
            current_topic="Insurance consultation",
            include_conversations=True
        )
        
        # Build enhanced prompt with customer context
        enhanced_prompt = ctx_manager.inject_context_to_system_prompt(
            INSURANCE_PROSPECT_SYSTEM_PROMPT,
            agent_context
        )
        
        print(f"\n✅ Context loaded and injected into system prompt")
    
    prospect_info = {
        "prospect_name": "Customer",
        "company_name": customer_obj.company_name if customer else "Business",
        "call_type": "outbound",
    }
    
    try:
        print(f"\n📞 Dialing...")
        response = await initiate_outbound_call(
            phone_number,
            prospect_info=prospect_info,
            call_type="outbound",
            system_prompt=enhanced_prompt,
        )
        
        call_id = response.get("id")
        print(f"\n✅ Call initiated successfully!")
        print(f"   Call ID: {call_id}")
        print(f"\n💡 To process this call after it completes, run:")
        print(f"   python process_call.py {call_id}")
        
        return call_id
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    call_id = asyncio.run(main())
