"""
Script to create Anish Gillella customer record and prepare for personalized call.
"""

import asyncio
import httpx
from app.db import get_or_create_customer, get_customer_conversations
from app.config import settings

async def create_customer_and_call():
    """Create Anish Gillella customer record and trigger call."""
    
    print("=" * 70)
    print("🎯 Creating Customer: Anish Gillella")
    print("=" * 70)
    
    # 1. Create/get customer record
    print("\n📝 Creating customer record...")
    customer = get_or_create_customer("+14698674545")
    print(f"✅ Customer Created/Found:")
    print(f"   ID: {customer.id}")
    print(f"   Name: Anish Gillella")
    print(f"   Phone: {customer.phone_number}")
    print(f"   Company: {customer.company_name}")
    print(f"   Industry: {customer.industry}")
    print(f"   Location: {customer.location}")
    
    # 2. Get any previous calls for context
    print("\n📞 Checking previous call history...")
    conversations = get_customer_conversations(customer.id, limit=5)
    print(f"   Previous calls: {len(conversations)}")
    if conversations:
        for i, conv in enumerate(conversations, 1):
            print(f"   - Call {i}: {conv['created_at']}")
    
    # 3. Trigger outbound call with customer context
    print("\n🚀 Triggering outbound call with personalized context...")
    
    call_payload = {
        "phone_number": "+14698674545",
        "prospect_name": "Anish Gillella",
        "company_name": customer.company_name,
        "industry": customer.industry,
        "location": customer.location,
        "estimated_employees": 50,  # Made up
    }
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{settings.backend_base_url}/call/insurance-prospect",
                json=call_payload,
                timeout=30.0
            )
            
            if response.status_code == 202:
                result = response.json()
                call_id = result.get("id", "unknown")
                print(f"✅ Call triggered successfully!")
                print(f"   Call ID: {call_id}")
                print(f"   Status: {response.status_code}")
                print(f"\n📋 Call Details:")
                print(f"   Prospect: Anish Gillella")
                print(f"   Company: {customer.company_name}")
                print(f"   Industry: {customer.industry}")
                print(f"   Location: {customer.location}")
                print(f"\n💬 The agent will:")
                print(f"   - Address customer as 'Anish'")
                print(f"   - Reference: {customer.company_name}")
                print(f"   - Discuss insurance for {customer.industry} industry")
                print(f"   - Be aware of: {customer.location} location")
            else:
                print(f"❌ Failed to trigger call: {response.status_code}")
                print(f"   Response: {response.text}")
                
    except Exception as e:
        print(f"❌ Error triggering call: {e}")
        raise
    
    print("\n" + "=" * 70)
    print("✅ Anish Gillella customer created with personalized call queued!")
    print("=" * 70)

if __name__ == "__main__":
    asyncio.run(create_customer_and_call())
