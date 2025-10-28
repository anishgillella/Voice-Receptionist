"""One-time OAuth setup script for Email Agent.

This script performs a one-time OAuth authentication with Gmail.
The refresh token is then stored and used for all future operations.

Usage:
    python oauth_setup.py
"""

import json
import logging
from pathlib import Path
from urllib.parse import urlencode

from google_auth_oauthlib.flow import Flow
from supabase import create_client
from ..core.config import email_settings

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Gmail API Scopes
GMAIL_SCOPES = [
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/gmail.send",
]


def get_oauth_url():
    """Generate Gmail OAuth authorization URL."""
    flow = Flow.from_client_config(
        {
            "installed": {
                "client_id": email_settings.gmail_client_id,
                "client_secret": email_settings.gmail_client_secret,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [email_settings.gmail_redirect_uri],
            }
        },
        scopes=GMAIL_SCOPES,
    )
    flow.redirect_uri = email_settings.gmail_redirect_uri
    
    auth_url, state = flow.authorization_url(prompt="consent")
    return auth_url, state, flow


def exchange_code_for_tokens(flow, code):
    """Exchange authorization code for access and refresh tokens."""
    try:
        flow.fetch_token(code=code)
        credentials = flow.credentials
        
        return {
            "access_token": credentials.token,
            "refresh_token": credentials.refresh_token,
            "token_expiry": str(credentials.expiry) if credentials.expiry else None,
        }
    except Exception as error:
        logger.error(f"Error exchanging code for tokens: {error}")
        return None


def store_tokens_to_file(tokens):
    """Store tokens to a local file for backup."""
    token_file = Path(__file__).parent / "gmail_tokens.json"
    
    with open(token_file, "w") as f:
        json.dump(tokens, f, indent=2)
    
    logger.info(f"✅ Tokens saved to: {token_file}")


def store_tokens_to_supabase(tokens, supabase_url, supabase_key):
    """Store tokens to Supabase for persistent access."""
    try:
        supabase = create_client(supabase_url, supabase_key)
        
        # Create or update email_config table
        data = {
            "config_key": "default_gmail_account",
            "email_address": "aianishgillella@gmail.com",
            "access_token": tokens["access_token"],
            "refresh_token": tokens["refresh_token"],
            "token_expiry": tokens.get("token_expiry"),
        }
        
        response = (
            supabase.table("email_config")
            .upsert(data, on_conflict="config_key")
            .execute()
        )
        
        logger.info(f"✅ Tokens stored to Supabase")
        return True
    except Exception as error:
        logger.error(f"Error storing tokens to Supabase: {error}")
        logger.info("⚠️ Tokens NOT stored in Supabase. Using local file instead.")
        return False


def main():
    """Main OAuth setup flow."""
    print("\n" + "=" * 70)
    print("🔐 Email Agent - One-Time OAuth Setup")
    print("=" * 70)
    
    print("\n📋 Steps:")
    print("1. A browser will open with Gmail login")
    print("2. Login as: aianishgillella@gmail.com")
    print("3. Approve permissions")
    print("4. Copy the authorization code from the redirect URL")
    print("5. Paste it below")
    
    print("\n🔗 OAuth URL:")
    print("-" * 70)
    
    auth_url, state, flow = get_oauth_url()
    print(auth_url)
    print("-" * 70)
    
    print("\n📌 Instructions:")
    print("1. Open the URL above in your browser")
    print("2. Login with aianishgillella@gmail.com")
    print("3. Click 'Allow' to grant permissions")
    print("4. You'll be redirected to: http://localhost:8000/auth/gmail/callback?code=XXXX&state=YYYY")
    print("5. Copy the 'code' value (the long string after 'code=')")
    print("6. Paste it below")
    
    auth_code = input("\n✉️  Paste the authorization code here: ").strip()
    
    if not auth_code:
        print("❌ No code provided. Exiting.")
        return
    
    print(f"\n⏳ Exchanging code for tokens...")
    tokens = exchange_code_for_tokens(flow, auth_code)
    
    if not tokens:
        print("❌ Failed to get tokens. Exiting.")
        return
    
    print("\n✅ Tokens received!")
    print(f"   - Access Token: {tokens['access_token'][:20]}...")
    print(f"   - Refresh Token: {tokens['refresh_token'][:20]}...")
    
    # Save to local file
    store_tokens_to_file(tokens)
    
    # Try to save to Supabase
    print("\n📚 Attempting to save to Supabase...")
    
    # Load Supabase credentials from environment
    import os
    from dotenv import load_dotenv
    
    load_dotenv()
    
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_KEY")
    
    if supabase_url and supabase_key:
        stored = store_tokens_to_supabase(tokens, supabase_url, supabase_key)
        if not stored:
            print("⚠️  Supabase storage failed, using local file.")
    else:
        print("⚠️  SUPABASE_URL or SUPABASE_KEY not set in .env")
        print("    Will use local file: gmail_tokens.json")
    
    print("\n" + "=" * 70)
    print("🎉 Setup Complete!")
    print("=" * 70)
    print("\n✨ Your email agent is now configured to use:")
    print("   Email: aianishgillella@gmail.com")
    print("\n📝 Next steps:")
    print("1. Start the server: uvicorn email_agent.main:app --reload")
    print("2. Test with: POST /emails/fetch")
    print("3. Enjoy! 🚀")
    print("\n" + "=" * 70)


if __name__ == "__main__":
    main()
