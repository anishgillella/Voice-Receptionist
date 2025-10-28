"""Gmail API client for email operations."""

from __future__ import annotations

import base64
import json
import logging
from io import BytesIO
from pathlib import Path
from typing import Optional
import asyncio

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from ..core.config import email_settings

logger = logging.getLogger(__name__)

# Gmail API scopes
GMAIL_SCOPES = [
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/gmail.send",
]


class GmailClient:
    """Client for interacting with Gmail API."""

    def __init__(self):
        """Initialize Gmail client with OAuth configuration."""
        self.client_id = email_settings.gmail_client_id
        self.client_secret = email_settings.gmail_client_secret
        self.redirect_uri = email_settings.gmail_redirect_uri
        self._default_tokens = None

    def get_auth_flow(self) -> Flow:
        """Get OAuth flow for Gmail authentication."""
        flow = Flow.from_client_config(
            {
                "installed": {
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": [self.redirect_uri],
                }
            },
            scopes=GMAIL_SCOPES,
        )
        flow.redirect_uri = self.redirect_uri
        return flow

    def get_auth_url(self) -> str:
        """Get the authorization URL for user to authenticate."""
        flow = self.get_auth_flow()
        auth_url, _ = flow.authorization_url(prompt="consent")
        return auth_url

    def exchange_code_for_token(self, code: str) -> dict:
        """Exchange authorization code for access token."""
        flow = self.get_auth_flow()
        flow.fetch_token(code=code)
        credentials = flow.credentials

        return {
            "access_token": credentials.token,
            "refresh_token": credentials.refresh_token,
            "token_expiry": credentials.expiry,
            "scopes": credentials.scopes,
        }

    def load_default_tokens_from_file(self) -> Optional[dict]:
        """Load default tokens from local file."""
        token_file = Path(__file__).parent / "gmail_tokens.json"
        
        if not token_file.exists():
            logger.warning(f"Token file not found: {token_file}")
            return None
        
        try:
            with open(token_file, "r") as f:
                tokens = json.load(f)
            logger.info("✅ Loaded tokens from local file")
            return tokens
        except Exception as error:
            logger.error(f"Error loading tokens from file: {error}")
            return None

    async def load_default_tokens_from_supabase(self, db) -> Optional[dict]:
        """Load default tokens from Supabase."""
        try:
            from supabase import create_client
            
            supabase = create_client(
                email_settings.supabase_url,
                email_settings.supabase_key
            )
            
            response = (
                supabase.table("email_config")
                .select("*")
                .eq("config_key", "default_gmail_account")
                .execute()
            )
            
            if response.data and len(response.data) > 0:
                tokens = response.data[0]
                logger.info("✅ Loaded tokens from Supabase")
                return {
                    "access_token": tokens.get("access_token"),
                    "refresh_token": tokens.get("refresh_token"),
                    "token_expiry": tokens.get("token_expiry"),
                }
            else:
                logger.warning("No tokens found in Supabase email_config table")
                return None
        except Exception as error:
            logger.error(f"Error loading tokens from Supabase: {error}")
            return None

    async def get_default_tokens(self, db=None) -> Optional[dict]:
        """Get default account tokens (from Supabase or local file)."""
        if self._default_tokens:
            return self._default_tokens
        
        # Try Supabase first
        if db:
            tokens = await self.load_default_tokens_from_supabase(db)
            if tokens:
                self._default_tokens = tokens
                return tokens
        
        # Fall back to local file
        tokens = self.load_default_tokens_from_file()
        if tokens:
            self._default_tokens = tokens
            return tokens
        
        logger.error("No tokens found. Run: python oauth_setup.py")
        return None

    def get_service(self, access_token: str, refresh_token: Optional[str] = None):
        """Build Gmail service with credentials."""
        credentials = Credentials(
            token=access_token,
            refresh_token=refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=self.client_id,
            client_secret=self.client_secret,
            scopes=GMAIL_SCOPES,
        )
        return build("gmail", "v1", credentials=credentials)

    async def get_emails(
        self,
        service=None,
        access_token: Optional[str] = None,
        refresh_token: Optional[str] = None,
        max_results: int = 10,
        query: Optional[str] = None,
        db=None,
    ) -> list[dict]:
        """Fetch emails from Gmail inbox."""
        try:
            # If no service provided, get default tokens and create service
            if not service:
                if not access_token:
                    tokens = await self.get_default_tokens(db)
                    if not tokens:
                        logger.error("No Gmail tokens available")
                        return []
                    access_token = tokens.get("access_token")
                    refresh_token = tokens.get("refresh_token")
                
                service = self.get_service(access_token, refresh_token)
            
            results = (
                service.users()
                .messages()
                .list(userId="me", maxResults=max_results, q=query)
                .execute()
            )

            messages = results.get("messages", [])
            emails = []

            for message in messages:
                email_data = self.get_message_details(service, message["id"])
                if email_data:
                    emails.append(email_data)

            return emails
        except HttpError as error:
            logger.error(f"An error occurred: {error}")
            return []

    def get_message_details(self, service, message_id: str) -> Optional[dict]:
        """Get detailed information about a specific message."""
        try:
            message = service.users().messages().get(userId="me", id=message_id, format="full").execute()

            headers = message["payload"]["headers"]
            sender = next((h["value"] for h in headers if h["name"] == "From"), None)
            recipient = next(
                (h["value"] for h in headers if h["name"] == "To"),
                None,
            )
            subject = next(
                (h["value"] for h in headers if h["name"] == "Subject"),
                None,
            )
            date = next((h["value"] for h in headers if h["name"] == "Date"), None)

            body_text = ""
            body_html = ""
            attachments = []

            if "parts" in message["payload"]:
                for part in message["payload"]["parts"]:
                    if part["mimeType"] == "text/plain":
                        if "data" in part["body"]:
                            body_text = base64.urlsafe_b64decode(
                                part["body"]["data"]
                            ).decode("utf-8")
                    elif part["mimeType"] == "text/html":
                        if "data" in part["body"]:
                            body_html = base64.urlsafe_b64decode(
                                part["body"]["data"]
                            ).decode("utf-8")
                    elif "filename" in part and part["filename"]:
                        attachments.append(
                            {
                                "filename": part["filename"],
                                "mimeType": part["mimeType"],
                                "partId": part["partId"],
                                "fileId": message_id,
                            }
                        )
            elif "body" in message["payload"] and "data" in message["payload"]["body"]:
                body_text = base64.urlsafe_b64decode(
                    message["payload"]["body"]["data"]
                ).decode("utf-8")

            return {
                "message_id": message_id,
                "thread_id": message["threadId"],
                "sender": sender,
                "recipient": recipient,
                "subject": subject,
                "date": date,
                "body_text": body_text,
                "body_html": body_html,
                "attachments": attachments,
                "labels": message.get("labelIds", []),
            }
        except HttpError as error:
            logger.error(f"An error occurred: {error}")
            return None

    def download_attachment(self, service, message_id: str, part_id: str) -> Optional[bytes]:
        """Download attachment from a message."""
        try:
            attachment = (
                service.users()
                .messages()
                .attachments()
                .get(userId="me", messageId=message_id, id=part_id)
                .execute()
            )

            file_data = base64.urlsafe_b64decode(attachment["data"])
            return file_data
        except HttpError as error:
            logger.error(f"An error occurred: {error}")
            return None

    def download_attachment_from_raw_email(self, service, message_id: str, filename: str) -> Optional[bytes]:
        """Download attachment by parsing raw email format - works when attachment token expires."""
        try:
            import email
            from email import policy
            
            # Get raw email
            message = service.users().messages().get(
                userId="me",
                id=message_id,
                format="raw"
            ).execute()
            
            if 'raw' not in message:
                logger.error("No raw email data available")
                return None
            
            raw_email = base64.urlsafe_b64decode(message['raw'])
            msg = email.message_from_bytes(raw_email, policy=policy.default)
            
            # Find attachment by filename
            for part in msg.iter_parts():
                if part.get_content_disposition() == 'attachment':
                    if part.get_filename() == filename:
                        return part.get_payload(decode=True)
            
            logger.warning(f"Attachment '{filename}' not found in email")
            return None
            
        except Exception as error:
            logger.error(f"Error downloading from raw email: {error}")
            return None

    async def download_attachment_async(
        self,
        message_id: str,
        part_id: str,
        filename: str,
        service=None,
        access_token: Optional[str] = None,
        refresh_token: Optional[str] = None,
        db=None,
    ) -> Optional[bytes]:
        """Async download attachment from a message."""
        try:
            # If no service provided, get default tokens and create service
            if not service:
                if not access_token:
                    tokens = await self.get_default_tokens(db)
                    if not tokens:
                        logger.error("No Gmail tokens available")
                        return None
                    access_token = tokens.get("access_token")
                    refresh_token = tokens.get("refresh_token")
                
                service = self.get_service(access_token, refresh_token)
            
            loop = asyncio.get_event_loop()
            
            # Try attachment API first
            file_data = await loop.run_in_executor(
                None,
                lambda: self.download_attachment(service, message_id, part_id)
            )
            
            if file_data:
                return file_data
            
            # Fall back to raw email parsing
            logger.info("Attachment API failed, falling back to raw email parsing...")
            file_data = await loop.run_in_executor(
                None,
                lambda: self.download_attachment_from_raw_email(service, message_id, filename)
            )
            return file_data
            
        except Exception as error:
            logger.error(f"Error downloading attachment: {error}")
            return None

    def send_email(
        self,
        service=None,
        to_email: Optional[str] = None,
        subject: Optional[str] = None,
        body_html: Optional[str] = None,
        body_text: Optional[str] = None,
        access_token: Optional[str] = None,
        refresh_token: Optional[str] = None,
    ) -> Optional[str]:
        """Send an email through Gmail."""
        try:
            from email.mime.multipart import MIMEMultipart
            from email.mime.text import MIMEText

            # If no service provided, create one with default tokens
            if not service:
                if not access_token:
                    # Load default tokens
                    tokens = self.load_default_tokens_from_file()
                    if not tokens:
                        logger.error("No Gmail tokens available")
                        return None
                    access_token = tokens.get("access_token")
                    refresh_token = tokens.get("refresh_token")
                
                service = self.get_service(access_token, refresh_token)

            message = MIMEMultipart("alternative")
            message["to"] = to_email
            message["subject"] = subject

            if body_text:
                message.attach(MIMEText(body_text, "plain"))
            message.attach(MIMEText(body_html, "html"))

            raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()

            result = (
                service.users()
                .messages()
                .send(userId="me", body={"raw": raw_message})
                .execute()
            )

            return result.get("id")
        except HttpError as error:
            logger.error(f"An error occurred: {error}")
            return None

    def mark_as_read(self, service, message_id: str) -> bool:
        """Mark a message as read."""
        try:
            service.users().messages().modify(
                userId="me",
                id=message_id,
                body={"removeLabelIds": ["UNREAD"]},
            ).execute()
            return True
        except HttpError as error:
            logger.error(f"An error occurred: {error}")
            return False
