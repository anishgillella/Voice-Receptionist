"""Email Agent Package."""

from .config import email_settings
from .db import EmailDatabase
from .gmail_client import GmailClient
from .models import (
    GmailAccount,
    Email,
    EmailAttachment,
    EmailConversation,
)
from .s3_client import S3Client
from .document_processor import DocumentProcessor

__all__ = [
    "email_settings",
    "EmailDatabase",
    "GmailClient",
    "S3Client",
    "DocumentProcessor",
    "GmailAccount",
    "Email",
    "EmailAttachment",
    "EmailConversation",
]
