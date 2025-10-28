#!/usr/bin/env python
"""Setup database schema by running migrations."""

import os
import sys
from pathlib import Path
import psycopg2

def load_env():
    """Load environment variables from .env file."""
    env_file = Path(__file__).parent.parent.parent / ".env"
    if not env_file.exists():
        print("❌ .env file not found")
        return None
    
    env_vars = {}
    with open(env_file) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                env_vars[key.strip()] = value.strip().strip("'\"")
    
    return env_vars

def run_migrations():
    """Apply database migrations."""
    env_vars = load_env()
    if not env_vars:
        sys.exit(1)
    
    # Get database URL
    db_url = env_vars.get("SUPABASE_URL") or env_vars.get("DATABASE_URL")
    if not db_url:
        print("❌ SUPABASE_URL or DATABASE_URL not found in .env")
        sys.exit(1)
    
    print("🗄️  DATABASE MIGRATION SETUP")
    print("=" * 70)
    print(f"📍 Connecting to Supabase...\n")
    
    try:
        conn = psycopg2.connect(db_url)
        cursor = conn.cursor()
        
        # Test connection
        cursor.execute("SELECT version();")
        version = cursor.fetchone()
        print(f"✅ Connected successfully\n")
        
        # Get migration files
        project_root = Path(__file__).parent.parent.parent
        migrations_dir = project_root / "migrations"
        
        # Apply migrations in order
        migrations = [
            "brokerage_schema.sql",
            "email_schema.sql", 
            "evaluation_schema.sql"
        ]
        
        print(f"📂 Migration Files:")
        for mig in migrations:
            mig_path = migrations_dir / mig
            if mig_path.exists():
                print(f"   ✓ {mig}")
            else:
                print(f"   ✗ {mig} (NOT FOUND)")
        
        print("\n" + "=" * 70)
        print("⏳ APPLYING MIGRATIONS\n")
        
        success_count = 0
        
        for mig_name in migrations:
            mig_path = migrations_dir / mig_name
            if not mig_path.exists():
                print(f"⚠️  {mig_name}: File not found, skipping")
                continue
            
            print(f"⏳ Applying {mig_name}...")
            
            try:
                with open(mig_path, "r") as f:
                    sql_content = f.read()
                
                # Execute the entire migration as one transaction
                cursor.execute(sql_content)
                conn.commit()
                
                print(f"   ✅ {mig_name} applied successfully\n")
                success_count += 1
                
            except psycopg2.Error as e:
                print(f"   ❌ Error: {e.pgerror if hasattr(e, 'pgerror') else str(e)}\n")
                conn.rollback()
            except Exception as e:
                print(f"   ❌ Error: {str(e)}\n")
                conn.rollback()
        
        # Verify schema
        print("=" * 70)
        print("🔍 VERIFYING SCHEMA\n")
        
        cursor.execute("""
            SELECT table_schema, COUNT(*) as table_count
            FROM information_schema.tables 
            WHERE table_schema IN ('public', 'brokerage')
            GROUP BY table_schema
            ORDER BY table_schema
        """)
        
        schemas = cursor.fetchall()
        for schema_name, count in schemas:
            print(f"   [{schema_name}] - {count} tables")
        
        # List key tables
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema IN ('public', 'brokerage')
            AND table_name IN ('customers', 'conversations', 'emails', 'email_attachments', 'call_metrics', 'call_judgments')
            ORDER BY table_name
        """)
        
        key_tables = [row[0] for row in cursor.fetchall()]
        
        print(f"\n   Key Tables Created:")
        for table in key_tables:
            print(f"      ✓ {table}")
        
        cursor.close()
        conn.close()
        
        print("\n" + "=" * 70)
        print(f"✅ Setup Complete! ({success_count} migrations applied)")
        print("=" * 70)
        print("\n🚀 Next Steps:")
        print("   1. python scripts/voice_agent/make_call.py")
        print("\n")
        
    except Exception as e:
        print(f"❌ Fatal Error: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    run_migrations()
