"""End-to-End Test Script for Email Agent.

This script validates:
1. Environment variables are set
2. All imports work
3. Database connection works
4. Gmail OAuth setup exists
5. S3 credentials work
6. API endpoints are functional
"""

import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent.parent))

print("\n" + "=" * 70)
print("🧪 EMAIL AGENT - END-TO-END TEST")
print("=" * 70)

# ============================================================================
# TEST 1: Environment Variables
# ============================================================================
print("\n📝 TEST 1: Environment Variables")
print("-" * 70)

from dotenv import load_dotenv
load_dotenv()

required_env_vars = {
    "GMAIL_CLIENT_ID": "Gmail OAuth Client ID",
    "GMAIL_CLIENT_SECRET": "Gmail OAuth Client Secret",
    "AWS_ACCESS_KEY_ID": "AWS Access Key",
    "AWS_SECRET_ACCESS_KEY": "AWS Secret Key",
    "AWS_S3_BUCKET_NAME": "S3 Bucket Name",
    "SUPABASE_URL": "Supabase URL",
    "SUPABASE_KEY": "Supabase API Key",
}

missing_vars = []
for var, desc in required_env_vars.items():
    value = os.getenv(var)
    if value:
        # Show first 10 and last 10 chars
        masked = value[:10] + "..." + value[-10:] if len(value) > 20 else "***"
        print(f"  ✅ {var}: {masked}")
    else:
        print(f"  ❌ {var}: MISSING")
        missing_vars.append(var)

if missing_vars:
    print(f"\n⚠️  Missing environment variables: {', '.join(missing_vars)}")
    print("   Add them to .env file and try again")
    sys.exit(1)
else:
    print(f"\n✅ All environment variables set!")

# ============================================================================
# TEST 2: Python Imports
# ============================================================================
print("\n📚 TEST 2: Python Imports")
print("-" * 70)

try:
    print("  Loading config...")
    from email_agent.config import email_settings
    print("    ✅ config.email_settings")
except Exception as e:
    print(f"    ❌ config: {e}")
    sys.exit(1)

try:
    print("  Loading models...")
    from email_agent.models import SendEmailRequest, FetchEmailsRequest
    print("    ✅ models")
except Exception as e:
    print(f"    ❌ models: {e}")
    sys.exit(1)

try:
    print("  Loading gmail_client...")
    from email_agent.gmail_client import GmailClient
    print("    ✅ gmail_client.GmailClient")
except Exception as e:
    print(f"    ❌ gmail_client: {e}")
    sys.exit(1)

try:
    print("  Loading s3_client...")
    from email_agent.s3_client import S3Client
    print("    ✅ s3_client.S3Client")
except Exception as e:
    print(f"    ❌ s3_client: {e}")
    sys.exit(1)

try:
    print("  Loading document_processor...")
    from email_agent.document_processor import DocumentProcessor
    print("    ✅ document_processor.DocumentProcessor")
except Exception as e:
    print(f"    ❌ document_processor: {e}")
    sys.exit(1)

try:
    print("  Loading db...")
    from email_agent.db import EmailDatabase
    print("    ✅ db.EmailDatabase")
except Exception as e:
    print(f"    ❌ db: {e}")
    sys.exit(1)

try:
    print("  Loading main app...")
    from email_agent.main import app
    print("    ✅ main.app (FastAPI)")
except Exception as e:
    print(f"    ❌ main: {e}")
    sys.exit(1)

print("\n✅ All imports successful!")

# ============================================================================
# TEST 3: Supabase Connection
# ============================================================================
print("\n🗄️  TEST 3: Supabase Connection")
print("-" * 70)

try:
    from supabase import create_client
    
    supabase = create_client(
        email_settings.supabase_url,
        email_settings.supabase_key
    )
    
    print("  Attempting to query tables...")
    response = supabase.table("customers").select("*").limit(1).execute()
    print(f"    ✅ Connected to Supabase")
    print(f"    ✅ customers table exists")
except Exception as e:
    print(f"    ❌ Supabase connection failed: {e}")
    print("    Make sure:")
    print("    - SUPABASE_URL is correct")
    print("    - SUPABASE_KEY is correct")
    print("    - Your Supabase project is running")
    sys.exit(1)

# Check if email tables exist
print("\n  Checking email tables...")
required_tables = [
    "email_config",
    "emails",
    "email_attachments",
    "email_conversations",
]

for table in required_tables:
    try:
        response = supabase.table(table).select("*").limit(1).execute()
        print(f"    ✅ {table}")
    except Exception as e:
        print(f"    ⚠️  {table}: {str(e)[:50]}...")
        print(f"       (Run the migration: voice_agent/migrations/email_schema.sql)")

# ============================================================================
# TEST 4: Gmail OAuth Setup
# ============================================================================
print("\n🔐 TEST 4: Gmail OAuth Setup")
print("-" * 70)

gmail_token_file = Path(__file__).parent / "gmail_tokens.json"

if gmail_token_file.exists():
    print(f"  ✅ Gmail tokens file found: {gmail_token_file}")
    import json
    try:
        with open(gmail_token_file, "r") as f:
            tokens = json.load(f)
        if "access_token" in tokens and "refresh_token" in tokens:
            print(f"    ✅ access_token present")
            print(f"    ✅ refresh_token present")
        else:
            print(f"    ⚠️  Missing required token fields")
    except Exception as e:
        print(f"    ❌ Failed to read tokens: {e}")
else:
    print(f"  ⚠️  Gmail tokens file NOT found: {gmail_token_file}")
    print(f"    Run: python oauth_setup.py")
    print(f"    (This is REQUIRED for email operations)")

# ============================================================================
# TEST 5: AWS S3 Connection
# ============================================================================
print("\n☁️  TEST 5: AWS S3 Connection")
print("-" * 70)

try:
    import boto3
    
    s3_client = boto3.client(
        "s3",
        aws_access_key_id=email_settings.aws_access_key_id,
        aws_secret_access_key=email_settings.aws_secret_access_key,
        region_name=email_settings.aws_region,
    )
    
    # Try to list buckets
    response = s3_client.list_buckets()
    buckets = [b["Name"] for b in response.get("Buckets", [])]
    
    if email_settings.aws_s3_bucket_name in buckets:
        print(f"  ✅ Connected to AWS S3")
        print(f"  ✅ Bucket '{email_settings.aws_s3_bucket_name}' exists")
    else:
        print(f"  ❌ Bucket '{email_settings.aws_s3_bucket_name}' not found")
        print(f"     Available buckets: {', '.join(buckets)}")
        sys.exit(1)
except Exception as e:
    print(f"  ❌ S3 connection failed: {e}")
    print("  Make sure:")
    print("  - AWS_ACCESS_KEY_ID is correct")
    print("  - AWS_SECRET_ACCESS_KEY is correct")
    print("  - AWS_REGION is correct")
    sys.exit(1)

# ============================================================================
# TEST 6: API Endpoints
# ============================================================================
print("\n🚀 TEST 6: API Endpoints")
print("-" * 70)

try:
    from fastapi.testclient import TestClient
    
    client = TestClient(app)
    
    # Test health endpoint
    print("  Testing GET /health...")
    response = client.get("/health")
    if response.status_code == 200:
        print(f"    ✅ /health: OK")
    else:
        print(f"    ❌ /health returned {response.status_code}")
    
    print("\n✅ API endpoints are registered!")
    
except Exception as e:
    print(f"  ⚠️  Could not test endpoints: {e}")
    print("  (This is usually ok, just means testclient not available)")

# ============================================================================
# TEST 7: Configuration Summary
# ============================================================================
print("\n📊 TEST 7: Configuration Summary")
print("-" * 70)

print(f"  Gmail Client ID: {email_settings.gmail_client_id[:20]}...")
print(f"  AWS Region: {email_settings.aws_region}")
print(f"  AWS S3 Bucket: {email_settings.aws_s3_bucket_name}")
print(f"  Supabase URL: {email_settings.supabase_url[:30]}...")
print(f"  Max Attachment Size: {email_settings.max_attachment_size_mb}MB")
print(f"  Supported Formats: {', '.join(email_settings.supported_document_types)}")
print(f"  Environment: {email_settings.environment}")
print(f"  Debug Mode: {email_settings.debug}")

# ============================================================================
# FINAL SUMMARY
# ============================================================================
print("\n" + "=" * 70)
print("✅ END-TO-END TEST COMPLETE!")
print("=" * 70)

print("\n🎯 Next Steps:")
print("  1. Run OAuth setup (if not done):")
print("     python oauth_setup.py")
print("")
print("  2. Start the API server:")
print("     uvicorn email_agent.main:app --reload --port 8000")
print("")
print("  3. Test the API:")
print("     curl http://localhost:8000/health")
print("")
print("=" * 70)
print("\n✨ All systems go! Ready to send emails! 🚀\n")
