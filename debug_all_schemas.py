#!/usr/bin/env python
"""Check data in ALL schemas."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from app.db import get_db

print("=" * 70)
print("🔍 Checking Data in ALL Schemas")
print("=" * 70)

db = get_db()

# 1. Check what schemas exist
print("\n📊 Available Schemas:")
schemas = db.execute("SELECT schema_name FROM information_schema.schemata ORDER BY schema_name")
for schema in schemas:
    print(f"   • {schema['schema_name']}")

# 2. Check for conversations in public schema
print("\n💬 Conversations in PUBLIC schema:")
try:
    convs = db.execute("SELECT call_id, customer_id FROM public.conversations LIMIT 5")
    if convs:
        print(f"   Found {len(convs)} conversations in public schema!")
        for c in convs:
            print(f"      • {c['call_id']}")
    else:
        print("   (None)")
except Exception as e:
    print(f"   Error: {e}")

# 3. Check for conversations in brokerage schema
print("\n💬 Conversations in BROKERAGE schema:")
try:
    convs = db.execute("SELECT call_id, customer_id FROM brokerage.conversations LIMIT 5")
    if convs:
        print(f"   Found {len(convs)} conversations in brokerage schema!")
        for c in convs:
            print(f"      • {c['call_id']}")
    else:
        print("   (None)")
except Exception as e:
    print(f"   Error: {e}")

# 4. Check for customers in public schema
print("\n👥 Customers in PUBLIC schema:")
try:
    custs = db.execute("SELECT phone_number, company_name FROM public.customers LIMIT 5")
    if custs:
        print(f"   Found {len(custs)} customers!")
        for c in custs:
            print(f"      • {c['company_name']} ({c['phone_number']})")
    else:
        print("   (None)")
except Exception as e:
    print(f"   Error: {e}")

# 5. Check current search_path
print("\n🔍 Current search_path:")
result = db.execute("SHOW search_path")
if result:
    print(f"   {result[0]['search_path']}")

print("\n" + "=" * 70)
