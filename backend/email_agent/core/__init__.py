"""Email Agent Core - Configuration, Models, and Database."""

from .config import email_settings, EmailAgentSettings
from .models import (
    Email, EmailCreate, EmailBase,
    EmailAttachment, EmailAttachmentCreate,
    EmailConversation, EmailConversationCreate,
    SendEmailRequest, FetchEmailsRequest,
)
from .db import EmailDatabase

__all__ = [
    "email_settings",
    "EmailAgentSettings",
    "Email",
    "EmailCreate", 
    "EmailBase",
    "EmailAttachment",
    "EmailAttachmentCreate",
    "EmailConversation",
    "EmailConversationCreate",
    "SendEmailRequest",
    "FetchEmailsRequest",
    "EmailDatabase",
]
