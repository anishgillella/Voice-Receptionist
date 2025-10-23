#!/usr/bin/env python
"""Run SQL migrations directly."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from app.db import get_db


def run_migration():
    """Run the migration to add customer fields."""
    
    db = get_db()
    
    print("=" * 70)
    print("🔄 Running Migration: Add Customer Fields")
    print("=" * 70)
    
    migrations = [
        ("first_name", "Add first_name column"),
        ("last_name", "Add last_name column"),
        ("email", "Add email column"),
    ]
    
    for column_name, description in migrations:
        try:
            print(f"\n⏳ {description}...")
            query = f"ALTER TABLE brokerage.customers ADD COLUMN IF NOT EXISTS {column_name} TEXT"
            db.execute(query)
            print(f"   ✅ Done")
        except Exception as e:
            print(f"   ❌ Error: {e}")
            # Continue anyway
    
    # Verify columns exist
    print(f"\n✅ Verifying columns...")
    result = db.execute("""
        SELECT column_name, data_type
        FROM information_schema.columns
        WHERE table_name = 'customers' AND table_schema = 'brokerage'
        ORDER BY ordinal_position
    """)
    
    print(f"\n📋 Customers table columns:")
    for row in result:
        print(f"   • {row['column_name']}: {row['data_type']}")
    
    print(f"\n✅ Migration complete!")


if __name__ == "__main__":
    run_migration()
