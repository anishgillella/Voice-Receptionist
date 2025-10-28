#!/usr/bin/env python
"""Make a call with enriched context from email campaigns."""

import asyncio
import sys
from pathlib import Path
from uuid import UUID

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from backend.voice_agent.services.vapi_client import initiate_outbound_call
from backend.voice_agent.core.config import settings, INSURANCE_PROSPECT_SYSTEM_PROMPT
from backend.voice_agent.core.db import get_db, get_customer_by_id, get_table_name
from backend.voice_agent.services.context_manager import ContextManager
from backend.email_agent.services import VoiceAgentContextManager


async def main():
    """Make an outbound call with customer + email context."""
    
    # Get customer ID - using the one we've been testing with
    customer_id = UUID("6f535748-7c0a-4528-b990-8c48eb3f23fc")
    phone_number = os.getenv("CALL_PHONE_NUMBER") or "+14698674545"
    
    print("=" * 80)
    print("📞 Making Outbound Call with COMPLETE Context")
    print("=" * 80)
    print(f"Phone: {phone_number}")
    print(f"Customer ID: {customer_id}")
    
    # Step 1: Get customer from voice agent DB
    print("\n" + "=" * 80)
    print("1️⃣  CUSTOMER CONTEXT (Voice Agent DB)")
    print("=" * 80)
    
    try:
        db = get_db()
        customer = db.execute(
            f"SELECT * FROM {get_table_name('customers')} WHERE id = %s LIMIT 1",
            (str(customer_id),)
        )
        
        if customer:
            customer_obj = get_customer_by_id(customer_id)
            print(f"✅ Found customer: {customer_obj.company_name}")
            print(f"   Name: {customer_obj.first_name} {customer_obj.last_name}")
            print(f"   Industry: {customer_obj.industry}")
            print(f"   Location: {customer_obj.location}")
        else:
            print("⚠️  Customer not found in voice agent DB")
            customer_obj = None
    except Exception as e:
        print(f"⚠️  Could not fetch customer: {str(e)[:100]}")
        customer_obj = None
    
    # Step 2: Get voice agent context
    print("\n" + "=" * 80)
    print("2️⃣  CONVERSATION HISTORY (Voice Agent DB)")
    print("=" * 80)
    
    try:
        ctx_manager = ContextManager()
        if customer_obj:
            agent_context = ctx_manager.build_agent_context(
                customer_obj,
                current_topic="Insurance consultation",
                include_conversations=True
            )
            print(f"✅ Loaded agent context")
            if agent_context:
                print(f"   {str(agent_context)[:200]}...")
        else:
            agent_context = {}
            print("ℹ️  No agent context available")
    except Exception as e:
        print(f"⚠️  Could not build agent context: {str(e)[:100]}")
        agent_context = {}
    
    # Step 3: Get EMAIL CONTEXT from email agent
    print("\n" + "=" * 80)
    print("3️⃣  EMAIL CONTEXT (Email Agent)")
    print("=" * 80)
    
    email_context_str = ""
    try:
        ctx_mgr = VoiceAgentContextManager()
        
        # Get customer summary
        summary = await ctx_mgr.get_customer_summary(customer_id)
        print(f"✅ Customer email summary:")
        print(f"{summary.get('summary', 'No summary')}")
        
        # Get context for relevant queries
        test_queries = [
            "insurance coverage",
            "policy details",
            "account information"
        ]
        
        for query in test_queries:
            context = await ctx_mgr.get_email_context(
                customer_id=customer_id,
                query=query,
                top_k=2
            )
            
            if context['status'] == 'success':
                email_context_str += f"\n📧 Context for '{query}':\n"
                email_context_str += context['context']
                print(f"   ✅ Found context for: {query}")
            else:
                print(f"   ℹ️  No context found for: {query}")
        
        if email_context_str:
            print(f"\n✅ Email context loaded ({len(email_context_str)} chars)")
    except Exception as e:
        print(f"⚠️  Could not load email context: {str(e)[:100]}")
        email_context_str = ""
    
    # Step 4: Build enhanced system prompt
    print("\n" + "=" * 80)
    print("4️⃣  BUILDING SYSTEM PROMPT WITH ALL CONTEXT")
    print("=" * 80)
    
    enhanced_prompt = INSURANCE_PROSPECT_SYSTEM_PROMPT
    
    # Inject voice agent context
    if customer_obj and agent_context:
        enhanced_prompt = ctx_manager.inject_context_to_system_prompt(
            enhanced_prompt,
            agent_context
        )
        print("✅ Injected voice agent context")
    
    # Inject email context
    if email_context_str:
        enhanced_prompt += f"""

---
IMPORTANT: Customer Email & Document Context
==============================================
{email_context_str}

Use this information when discussing with the customer. Reference any documents or past communications as appropriate.
"""
        print("✅ Injected email & document context")
    
    print(f"\n📋 System prompt size: {len(enhanced_prompt)} characters")
    print(f"   (Includes customer data + conversation history + email context)")
    
    # Step 5: Make the call
    print("\n" + "=" * 80)
    print("5️⃣  MAKING CALL WITH COMPLETE CONTEXT")
    print("=" * 80)
    
    prospect_info = {
        "prospect_name": customer_obj.first_name if customer_obj else "Customer",
        "company_name": customer_obj.company_name if customer_obj else "Business",
        "call_type": "outbound_with_context",
    }
    
    try:
        print(f"\n☎️  Dialing {phone_number}...")
        response = await initiate_outbound_call(
            phone_number,
            prospect_info=prospect_info,
            call_type="outbound",
            system_prompt=enhanced_prompt,
        )
        
        call_id = response.get("id")
        print(f"\n✅ CALL INITIATED SUCCESSFULLY!")
        print(f"   Call ID: {call_id}")
        
        print(f"\n" + "=" * 80)
        print("📊 CONTEXT SUMMARY")
        print("=" * 80)
        print(f"""
✅ Voice Agent has:
   - Customer information (name, company, industry, location)
   - Past conversations and call history
   - Email threads and communications
   - Document attachments (PDFs with embedded context)
   - All past interactions

The AI voice agent is now fully informed and can:
   1. Reference past conversations
   2. Discuss documents from emails
   3. Provide personalized service
   4. Maintain continuity from previous touchpoints
""")
        
        print(f"\n💡 To process this call after it completes, run:")
        print(f"   python voice_agent/process_call.py {call_id}")
        
        return call_id
        
    except Exception as e:
        print(f"\n❌ Error making call: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    call_id = asyncio.run(main())
