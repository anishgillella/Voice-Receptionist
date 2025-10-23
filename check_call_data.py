#!/usr/bin/env python
"""Check the call data that was just stored."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from app.db import get_db

print("=" * 70)
print("📊 Checking Call Data in Brokerage Schema")
print("=" * 70)

db = get_db()

# 1. Check customers
print("\n👥 Customers:")
customers = db.execute("SELECT id, phone_number, company_name FROM brokerage.customers LIMIT 5")
if customers:
    for c in customers:
        print(f"   • {c['company_name']} ({c['phone_number']})")
else:
    print("   (No customers yet)")

# 2. Check conversations (transcripts)
print("\n💬 Recent Conversations:")
conversations = db.execute("""
    SELECT c.call_id, c.transcript, c.summary, cu.company_name, c.created_at
    FROM brokerage.conversations c
    JOIN brokerage.customers cu ON c.customer_id = cu.id
    ORDER BY c.created_at DESC
    LIMIT 5
""")

if conversations:
    for conv in conversations:
        print(f"\n   📞 Call: {conv['call_id']}")
        print(f"      Customer: {conv['company_name']}")
        print(f"      Transcript (first 100 chars): {conv['transcript'][:100]}...")
        print(f"      Summary: {conv['summary'] or '(Not generated yet)'}")
        print(f"      Created: {conv['created_at']}")
else:
    print("   (No conversations yet - wait for call to complete)")

# 3. Check embeddings
print("\n🔢 Embeddings:")
embeddings = db.execute("""
    SELECT call_id, embedding_type, created_at
    FROM brokerage.embeddings
    ORDER BY created_at DESC
    LIMIT 10
""")

if embeddings:
    for emb in embeddings:
        print(f"   • {emb['call_id'][:8]}... ({emb['embedding_type']})")
else:
    print("   (No embeddings yet)")

print("\n" + "=" * 70)
