#!/usr/bin/env python
"""Process a specific call: fetch transcript, generate summary, store embeddings."""

import asyncio
import sys
from pathlib import Path
from uuid import UUID

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from backend.voice_agent.core.config import settings
from backend.voice_agent.api.main import _process_call_transcript
from backend.voice_agent.core.db import get_db, get_customer_by_id, get_table_name
from backend.voice_agent.services.context_manager import ContextManager


async def main():
    """Process a specific call."""
    
    if len(sys.argv) < 2:
        print("❌ Usage: python process_call.py <call_id>")
        print("\nExample:")
        print("   python process_call.py 019a0e6d-f431-7ff1-a62f-f032c0e69744")
        sys.exit(1)
    
    call_id = sys.argv[1]
    customer_phone = "+14698674545"  # Default customer
    
    print("=" * 70)
    print("🔄 Processing Call")
    print("=" * 70)
    print(f"Call ID: {call_id}")
    print(f"Customer Phone: {customer_phone}")
    
    try:
        # Get customer
        db = get_db()
        customer = db.execute(
            f"SELECT id FROM {get_table_name('customers')} WHERE phone_number = %s LIMIT 1",
            (customer_phone,)
        )
        
        if customer:
            customer_id = UUID(customer[0]['id'])
            customer_obj = get_customer_by_id(customer_id)
            
            # Build and display context
            print(f"\n👤 Customer Context:")
            print(f"   Name: {customer_obj.company_name}")
            print(f"   Phone: {customer_obj.phone_number}")
            print(f"   Industry: {customer_obj.industry}")
            print(f"   Location: {customer_obj.location}")
            
            # Get relevant past conversations
            ctx_manager = ContextManager()
            past_conversations = ctx_manager.get_relevant_past_conversations(
                customer_id,
                "insurance consultation",
                top_k=3
            )
            
            if past_conversations:
                print(f"\n📜 Past Conversations: {len(past_conversations)}")
                for i, conv in enumerate(past_conversations, 1):
                    summary = conv.get('summary') or conv.get('transcript', '')[:100]
                    print(f"   {i}. {summary}...")
            else:
                print(f"\n📜 Past Conversations: None")
        
        # Process the call
        print(f"\n🔄 Processing transcript, summary, and embeddings...")
        await _process_call_transcript(call_id, customer_phone, settings)
        
        print("\n✅ Call processed successfully!")
        print(f"\n📊 Data stored in brokerage schema:")
        print(f"   • Transcript")
        print(f"   • Summary (AI-generated)")
        print(f"   • Transcript Embedding")
        print(f"   • Summary Embedding")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
