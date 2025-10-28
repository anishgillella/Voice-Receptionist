"""Pydantic models for email agent entities."""

from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


# Gmail Account Models
class GmailAccountBase(BaseModel):
    """Base Gmail account model."""

    customer_id: UUID
    email_address: EmailStr
    access_token: str
    refresh_token: str
    token_expiry: Optional[datetime] = None
    scopes: list[str] = Field(
        default=["https://www.googleapis.com/auth/gmail.modify"]
    )


class GmailAccountCreate(GmailAccountBase):
    """Gmail account creation model."""

    pass


class GmailAccount(GmailAccountBase):
    """Gmail account with database fields."""

    id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# Email Models
class EmailBase(BaseModel):
    """Base email model."""

    customer_id: UUID
    gmail_account_id: UUID
    gmail_message_id: str
    gmail_thread_id: Optional[str] = None
    sender_email: str
    sender_name: Optional[str] = None
    recipient_email: str
    recipient_name: Optional[str] = None
    subject: Optional[str] = None
    body_text: Optional[str] = None
    body_html: Optional[str] = None
    email_type: str = Field(default="received")  # 'received', 'sent', 'draft'
    received_at: Optional[datetime] = None
    sent_at: Optional[datetime] = None
    is_read: bool = False
    has_attachments: bool = False
    attachment_count: int = 0
    labels: list[str] = Field(default=[])
    metadata: Optional[dict] = None


class EmailCreate(EmailBase):
    """Email creation model."""

    pass


class Email(EmailBase):
    """Email with database fields."""

    id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# Email Attachment Models
class EmailAttachmentBase(BaseModel):
    """Base email attachment model."""

    email_id: UUID
    customer_id: UUID
    filename: str
    mime_type: Optional[str] = None
    file_size_bytes: Optional[int] = None
    file_extension: str  # 'pdf', 'docx', 'doc'
    s3_key: str
    s3_url: str
    upload_status: str = "pending"  # 'pending', 'uploading', 'success', 'failed'
    upload_error: Optional[str] = None


class EmailAttachmentCreate(EmailAttachmentBase):
    """Email attachment creation model."""

    pass


class EmailAttachment(EmailAttachmentBase):
    """Email attachment with database fields."""

    id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# Email Conversation Models
class EmailConversationBase(BaseModel):
    """Base email conversation model."""

    customer_id: UUID
    gmail_account_id: UUID
    gmail_thread_id: str
    subject: Optional[str] = None
    participant_emails: list[str]
    message_count: int = 0
    last_message_at: Optional[datetime] = None
    is_archived: bool = False
    conversation_summary: Optional[str] = None


class EmailConversationCreate(EmailConversationBase):
    """Email conversation creation model."""

    pass


class EmailConversation(EmailConversationBase):
    """Email conversation with database fields."""

    id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# API Request/Response Models
class GmailAuthStartRequest(BaseModel):
    """Request to start Gmail authentication."""

    customer_id: UUID


class GmailAuthCallbackRequest(BaseModel):
    """Request for Gmail OAuth callback."""

    code: str
    state: Optional[str] = None


class SendEmailRequest(BaseModel):
    """Request to send an email."""

    to_email: EmailStr
    subject: str
    body_html: str
    body_text: Optional[str] = None


class FetchEmailsRequest(BaseModel):
    """Request to fetch emails from Gmail."""

    max_results: int = Field(default=10, le=100)
    query: Optional[str] = None  # Gmail search query


class EmailSummaryResponse(BaseModel):
    """Summary response for an email."""

    id: UUID
    subject: str
    sender_email: str
    sender_name: Optional[str]
    received_at: Optional[datetime]
    attachment_count: int
    preview: Optional[str]


class ConversationResponse(BaseModel):
    """Response for a conversation with emails."""

    id: UUID
    subject: Optional[str]
    participant_emails: list[str]
    message_count: int
    last_message_at: Optional[datetime]
    emails: list[Email]
    attachments: list[EmailAttachment]
