"""Database operations for email agent."""

from __future__ import annotations

import logging
from typing import Optional
from uuid import UUID

from supabase import create_client

from .config import email_settings

logger = logging.getLogger(__name__)


class EmailDatabase:
    """Database operations for email management."""

    def __init__(self):
        """Initialize Supabase client."""
        self.supabase = create_client(email_settings.supabase_url, email_settings.supabase_key)

    async def store_gmail_account(
        self,
        customer_id: UUID,
        email_address: str,
        access_token: str,
        refresh_token: str,
        token_expiry: Optional[str] = None,
        scopes: Optional[list[str]] = None,
    ) -> Optional[dict]:
        """Store Gmail OAuth credentials for a customer."""
        try:
            data = {
                "customer_id": str(customer_id),
                "email_address": email_address,
                "access_token": access_token,
                "refresh_token": refresh_token,
                "token_expiry": token_expiry,
                "scopes": scopes or ["https://www.googleapis.com/auth/gmail.modify"],
            }

            response = (
                self.supabase.table("gmail_accounts")
                .upsert(data, on_conflict="customer_id,email_address")
                .execute()
            )

            logger.info(f"Stored Gmail account for customer {customer_id}")
            return response.data[0] if response.data else None
        except Exception as error:
            logger.error(f"Error storing Gmail account: {error}")
            return None

    async def get_gmail_account(self, customer_id: UUID) -> Optional[dict]:
        """Get Gmail OAuth credentials for a customer."""
        try:
            response = (
                self.supabase.table("gmail_accounts")
                .select("*")
                .eq("customer_id", str(customer_id))
                .execute()
            )

            if response.data:
                return response.data[0]
            return None
        except Exception as error:
            logger.error(f"Error retrieving Gmail account: {error}")
            return None

    async def store_email(
        self,
        customer_id: UUID,
        gmail_message_id: str,
        sender_email: str,
        recipient_email: str,
        subject: Optional[str] = None,
        body_text: Optional[str] = None,
        body_html: Optional[str] = None,
        email_type: str = "received",
        received_at: Optional[str] = None,
        sent_at: Optional[str] = None,
        has_attachments: bool = False,
        attachment_count: int = 0,
        labels: Optional[list[str]] = None,
        gmail_thread_id: Optional[str] = None,
        gmail_account_id: Optional[UUID] = None,
        metadata: Optional[dict] = None,
    ) -> Optional[dict]:
        """Store an email in the database."""
        try:
            data = {
                "customer_id": str(customer_id),
                "gmail_message_id": gmail_message_id,
                "gmail_thread_id": gmail_thread_id,
                "sender_email": sender_email,
                "recipient_email": recipient_email,
                "subject": subject,
                "body_text": body_text,
                "body_html": body_html,
                "email_type": email_type,
                "received_at": received_at,
                "sent_at": sent_at,
                "has_attachments": has_attachments,
                "attachment_count": attachment_count,
                "labels": labels or [],
                "metadata": metadata or {},
            }
            
            if gmail_account_id:
                data["gmail_account_id"] = str(gmail_account_id)

            response = (
                self.supabase.table("emails")
                .upsert(data, on_conflict="gmail_message_id")
                .execute()
            )

            logger.info(f"Stored email {gmail_message_id} for customer {customer_id}")
            return response.data[0] if response.data else None
        except Exception as error:
            logger.error(f"Error storing email: {error}")
            return None

    async def store_email_attachment(
        self,
        email_id: UUID,
        customer_id: UUID,
        filename: str,
        mime_type: str,
        file_size_bytes: int,
        file_extension: str,
        s3_key: str,
        s3_url: str,
        upload_status: str = "success",
        upload_error: Optional[str] = None,
    ) -> Optional[dict]:
        """Store an email attachment record in the database."""
        return await self.store_attachment(
            email_id=email_id,
            customer_id=customer_id,
            filename=filename,
            mime_type=mime_type,
            file_size_bytes=file_size_bytes,
            file_extension=file_extension,
            s3_key=s3_key,
            s3_url=s3_url,
            upload_status=upload_status,
            upload_error=upload_error,
        )

    async def store_attachment(
        self,
        email_id: UUID,
        customer_id: UUID,
        filename: str,
        mime_type: str,
        file_size_bytes: int,
        file_extension: str,
        s3_key: str,
        s3_url: str,
        upload_status: str = "success",
        upload_error: Optional[str] = None,
    ) -> Optional[dict]:
        """Store an email attachment record in the database."""
        try:
            data = {
                "email_id": str(email_id),
                "customer_id": str(customer_id),
                "filename": filename,
                "mime_type": mime_type,
                "file_size_bytes": file_size_bytes,
                "file_extension": file_extension,
                "s3_key": s3_key,
                "s3_url": s3_url,
                "upload_status": upload_status,
                "upload_error": upload_error,
            }

            response = self.supabase.table("email_attachments").insert(data).execute()

            logger.info(f"Stored attachment {filename} for email {email_id}")
            return response.data[0] if response.data else None
        except Exception as error:
            logger.error(f"Error storing attachment: {error}")
            return None

    async def get_emails_for_customer(
        self,
        customer_id: UUID,
        limit: int = 50,
    ) -> list[dict]:
        """Get all emails for a customer."""
        try:
            response = (
                self.supabase.table("emails")
                .select("*")
                .eq("customer_id", str(customer_id))
                .order("received_at", desc=True)
                .limit(limit)
                .execute()
            )

            return response.data or []
        except Exception as error:
            logger.error(f"Error retrieving emails: {error}")
            return []

    async def get_email_with_attachments(self, email_id: UUID) -> Optional[dict]:
        """Get a specific email with all its attachments."""
        try:
            response = (
                self.supabase.table("emails")
                .select("*, email_attachments(*)")
                .eq("id", str(email_id))
                .execute()
            )

            return response.data[0] if response.data else None
        except Exception as error:
            logger.error(f"Error retrieving email with attachments: {error}")
            return None

    async def store_conversation(
        self,
        customer_id: UUID,
        gmail_account_id: UUID,
        gmail_thread_id: str,
        subject: Optional[str] = None,
        participant_emails: Optional[list[str]] = None,
    ) -> Optional[dict]:
        """Store an email conversation/thread."""
        try:
            data = {
                "customer_id": str(customer_id),
                "gmail_account_id": str(gmail_account_id),
                "gmail_thread_id": gmail_thread_id,
                "subject": subject,
                "participant_emails": participant_emails or [],
                "message_count": 0,
            }

            response = (
                self.supabase.table("email_conversations")
                .upsert(data, on_conflict="gmail_account_id,gmail_thread_id")
                .execute()
            )

            logger.info(f"Stored conversation {gmail_thread_id} for customer {customer_id}")
            return response.data[0] if response.data else None
        except Exception as error:
            logger.error(f"Error storing conversation: {error}")
            return None

    async def get_attachments_for_email(self, email_id: UUID) -> list[dict]:
        """Get all attachments for a specific email."""
        try:
            response = (
                self.supabase.table("email_attachments")
                .select("*")
                .eq("email_id", str(email_id))
                .execute()
            )

            return response.data or []
        except Exception as error:
            logger.error(f"Error retrieving attachments: {error}")
            return []

    async def update_attachment_status(
        self,
        attachment_id: UUID,
        upload_status: str,
        upload_error: Optional[str] = None,
    ) -> bool:
        """Update the upload status of an attachment."""
        try:
            data = {
                "upload_status": upload_status,
                "upload_error": upload_error,
            }

            self.supabase.table("email_attachments").update(data).eq(
                "id",
                str(attachment_id),
            ).execute()

            logger.info(f"Updated attachment {attachment_id} status to {upload_status}")
            return True
        except Exception as error:
            logger.error(f"Error updating attachment status: {error}")
            return False

    async def get_customer_info(self, customer_id: UUID) -> Optional[dict]:
        """Get customer information."""
        try:
            response = (
                self.supabase.table("customers")
                .select("*")
                .eq("id", str(customer_id))
                .execute()
            )

            return response.data[0] if response.data else None
        except Exception as error:
            logger.error(f"Error retrieving customer info: {error}")
            return None

    async def get_or_create_customer_from_email(self, email_data: dict) -> Optional[dict]:
        """Get or create a customer based on email data (sender email)."""
        try:
            sender = email_data.get('sender', '')
            # Extract email address from "Name <email@example.com>" format
            if '<' in sender:
                sender_email = sender.split('<')[-1].rstrip('>')
            else:
                sender_email = sender
            
            # Try to find existing customer
            response = (
                self.supabase.table("customers")
                .select("*")
                .eq("email", sender_email)
                .execute()
            )

            if response.data and len(response.data) > 0:
                return response.data[0]

            # If customer not found, create a new one
            response = (
                self.supabase.table("customers")
                .insert({"email": sender_email})
                .execute()
            )
            return response.data[0] if response.data else None
        except Exception as error:
            logger.error(f"Error getting or creating customer from email: {error}")
            return None

    async def get_customer_thread(
        self,
        customer_id: UUID,
        thread_id: str,
    ) -> Optional[dict]:
        """Get complete thread with all messages and attachments for a customer."""
        try:
            response = (
                self.supabase.rpc("get_customer_thread", {
                    "p_customer_id": str(customer_id),
                    "p_thread_id": thread_id,
                })
                .execute()
            )

            if response.data and len(response.data) > 0:
                thread = response.data[0]
                logger.info(f"Retrieved thread {thread_id} for customer {customer_id}")
                return thread
            return None
        except Exception as error:
            logger.error(f"Error retrieving customer thread: {error}")
            return None

    async def get_customer_all_threads(self, customer_id: UUID) -> list[dict]:
        """Get all threads for a customer."""
        try:
            response = (
                self.supabase.rpc("get_customer_threads", {
                    "p_customer_id": str(customer_id),
                })
                .execute()
            )

            threads = response.data or []
            logger.info(f"Retrieved {len(threads)} threads for customer {customer_id}")
            return threads
        except Exception as error:
            logger.error(f"Error retrieving customer threads: {error}")
            return []

    async def get_thread_documents(self, thread_id: str) -> list[dict]:
        """Get all documents in a thread."""
        try:
            response = (
                self.supabase.rpc("get_thread_documents", {
                    "p_thread_id": thread_id,
                })
                .execute()
            )

            documents = response.data or []
            logger.info(f"Retrieved {len(documents)} documents from thread {thread_id}")
            return documents
        except Exception as error:
            logger.error(f"Error retrieving thread documents: {error}")
            return []

    async def get_conversation_thread_jsonb(self, thread_id: str) -> Optional[dict]:
        """Get complete conversation thread JSONB structure with all messages and attachments."""
        try:
            response = (
                self.supabase.table("email_conversations")
                .select("conversation_thread")
                .eq("gmail_thread_id", thread_id)
                .execute()
            )

            if response.data and len(response.data) > 0:
                thread_data = response.data[0]
                logger.info(f"Retrieved conversation thread JSONB for {thread_id}")
                return thread_data.get("conversation_thread")
            return None
        except Exception as error:
            logger.error(f"Error retrieving conversation thread JSONB: {error}")
            return None
