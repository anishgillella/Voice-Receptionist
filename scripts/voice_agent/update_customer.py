#!/usr/bin/env python
"""Update customer record in brokerage database."""

import asyncio
import sys
from pathlib import Path
from uuid import UUID

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from backend.voice_agent.core.config import settings
from backend.voice_agent.core.db import get_db, get_table_name


def update_customer():
    """Update customer information."""
    
    if len(sys.argv) < 2:
        print("Usage: python update_customer.py <phone_number> [first_name] [last_name] [email]")
        print("\nExample:")
        print('   python update_customer.py "+14698674545" "Anish" "Gillella" "anish@example.com"')
        sys.exit(1)
    
    phone_number = sys.argv[1]
    first_name = sys.argv[2] if len(sys.argv) > 2 else None
    last_name = sys.argv[3] if len(sys.argv) > 3 else None
    email = sys.argv[4] if len(sys.argv) > 4 else None
    
    print("=" * 70)
    print("📝 Updating Customer")
    print("=" * 70)
    print(f"Phone: {phone_number}")
    print(f"First Name: {first_name or '(no change)'}")
    print(f"Last Name: {last_name or '(no change)'}")
    print(f"Email: {email or '(no change)'}")
    
    db = get_db()
    
    # Build dynamic update query
    updates = []
    params = []
    
    if first_name:
        updates.append("first_name = %s")
        params.append(first_name)
    
    if last_name:
        updates.append("last_name = %s")
        params.append(last_name)
    
    if email:
        updates.append("email = %s")
        params.append(email)
    
    if not updates:
        print("❌ No fields to update!")
        sys.exit(1)
    
    params.append(phone_number)
    
    update_query = f"""
        UPDATE brokerage.customers
        SET {', '.join(updates)}
        WHERE phone_number = %s
    """
    
    try:
        rows = db.update(update_query, tuple(params))
        print(f"\n✅ Updated {rows} customer(s)")
        
        # Show updated customer
        result = db.execute(
            "SELECT id, first_name, last_name, email, company_name, phone_number FROM brokerage.customers WHERE phone_number = %s",
            (phone_number,)
        )
        
        if result:
            customer = result[0]
            print(f"\n📋 Updated Customer:")
            print(f"   First Name: {customer['first_name']}")
            print(f"   Last Name: {customer['last_name']}")
            print(f"   Email: {customer['email']}")
            print(f"   Company: {customer['company_name']}")
            print(f"   Phone: {customer['phone_number']}")
    
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    update_customer()
