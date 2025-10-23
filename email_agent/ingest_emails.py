"""Script to ingest emails from Gmail into Supabase."""

import asyncio
import logging
from uuid import UUID

from email_agent.config import email_settings
from email_agent.db import EmailDatabase
from email_agent.gmail_client import GmailClient
from email_agent.s3_client import S3Client
from email_agent.document_processor import DocumentProcessor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def ingest_emails():
    """Fetch emails from Gmail and store in database."""
    db = EmailDatabase()
    gmail_client = GmailClient()
    s3_client = S3Client()
    
    # Fetch emails from Gmail
    logger.info("Fetching emails from Gmail...")
    emails = await gmail_client.get_emails(max_results=5, query="from:anish.gillella@gmail.com")
    logger.info(f"Fetched {len(emails)} emails")
    
    for email_data in emails:
        logger.info(f"\nProcessing email: {email_data.get('subject')}")
        
        # Get or create customer
        customer_info = await db.get_or_create_customer_from_email(email_data)
        if not customer_info:
            logger.error(f"Failed to create customer for {email_data.get('sender')}")
            continue
        
        customer_id = UUID(customer_info['id'])
        logger.info(f"Customer: {customer_info.get('email_address')} ({customer_id})")
        
        # Parse sender
        sender = email_data.get('sender', '')
        if '<' in sender:
            sender_email = sender.split('<')[-1].rstrip('>')
            sender_name = sender.split('<')[0].strip()
        else:
            sender_email = sender
            sender_name = None
        
        # Store email
        stored_email = await db.store_email(
            customer_id=customer_id,
            gmail_message_id=email_data.get('message_id'),
            gmail_thread_id=email_data.get('thread_id'),
            sender_email=sender_email,
            sender_name=sender_name,
            recipient_email=email_data.get('recipient', ''),
            subject=email_data.get('subject'),
            body_text=email_data.get('body_text', ''),
            body_html=email_data.get('body_html', ''),
            email_type='received',
            received_at=email_data.get('date'),
            has_attachments=len(email_data.get('attachments', [])) > 0,
            attachment_count=len(email_data.get('attachments', [])),
            labels=email_data.get('labels', []),
        )
        
        if not stored_email:
            logger.error(f"Failed to store email {email_data.get('message_id')}")
            continue
        
        email_id = UUID(stored_email['id'])
        logger.info(f"✅ Stored email: {email_id}")
        
        # Process attachments
        if email_data.get('attachments'):
            logger.info(f"Processing {len(email_data['attachments'])} attachments...")
            for attachment in email_data['attachments']:
                logger.info(f"  - {attachment.get('filename')}")
                
                # For now, just create dummy S3 entry (we'll need to implement real download)
                filename = attachment.get('filename')
                file_ext = filename.split('.')[-1].lower() if '.' in filename else ''
                
                s3_key = s3_client.build_s3_key(
                    first_name=customer_info.get('first_name', 'unknown'),
                    last_name=customer_info.get('last_name', 'unknown'),
                    email_id=str(email_id),
                    filename=filename,
                )
                
                s3_url = s3_client.get_s3_url(s3_key)
                
                # Store attachment metadata
                att = await db.store_email_attachment(
                    email_id=email_id,
                    customer_id=customer_id,
                    filename=filename,
                    mime_type=attachment.get('mimeType', 'application/octet-stream'),
                    file_size_bytes=0,  # Unknown size
                    file_extension=file_ext,
                    s3_key=s3_key,
                    s3_url=s3_url,
                    upload_status='pending',
                )
                
                if att:
                    logger.info(f"    ✅ Attachment metadata stored")
    
    logger.info("\n✅ Ingestion complete!")


if __name__ == "__main__":
    asyncio.run(ingest_emails())
