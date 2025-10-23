"""FastAPI application for email agent."""

from __future__ import annotations

import logging
from uuid import UUID

from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.responses import JSONResponse

from .config import email_settings
from .db import EmailDatabase
from .document_processor import DocumentProcessor
from .gmail_client import GmailClient
from .models import (
    SendEmailRequest,
    FetchEmailsRequest,
)
from .s3_client import S3Client

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

app = FastAPI(
    title="Email Agent",
    description="AI-powered email agent for Gmail integration and document extraction",
    version="0.1.0",
)

# Initialize clients
db = EmailDatabase()
gmail_client = GmailClient()
s3_client = S3Client()


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "email-agent",
        "email_account": "aianishgillella@gmail.com"
    }


# Email Operations Endpoints
@app.post("/emails/fetch")
async def fetch_emails(request: FetchEmailsRequest):
    """Fetch emails from Gmail inbox."""
    try:
        logger.info(f"Fetching emails (max_results={request.max_results})")
        
        # Fetch emails using default account
        emails = await gmail_client.get_emails(
            max_results=request.max_results,
            query=request.query,
        )
        
        logger.info(f"Fetched {len(emails)} emails from Gmail")
        return {
            "success": True,
            "emails_fetched": len(emails),
            "emails": emails,
        }
    except Exception as error:
        logger.error(f"Error fetching emails: {error}")
        raise HTTPException(status_code=500, detail="Failed to fetch emails")


@app.post("/emails/send")
async def send_email(request: SendEmailRequest):
    """Send an email via Gmail from aianishgillella@gmail.com."""
    try:
        logger.info(f"Sending email to {request.to_email}")
        
        # Send email using default account
        message_id = gmail_client.send_email(
            to_email=request.to_email,
            subject=request.subject,
            body_html=request.body_html,
            body_text=request.body_text,
        )
        
        if message_id:
            logger.info(f"Email sent successfully: {message_id}")
            return {
                "success": True,
                "message": "Email sent successfully",
                "message_id": message_id,
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to send email")
    except HTTPException:
        raise
    except Exception as error:
        logger.error(f"Error sending email: {error}")
        raise HTTPException(status_code=500, detail="Failed to send email")


# Document Operations Endpoints
@app.post("/documents/extract")
async def extract_document(
    customer_id: str,
    file: UploadFile = File(...),
):
    """Extract text from an uploaded document."""
    try:
        customer_uuid = UUID(customer_id)
        
        logger.info(f"Extracting text from: {file.filename}")
        
        # Read file content
        file_content = await file.read()
        
        # Check file size
        file_size_mb = len(file_content) / (1024 * 1024)
        if file_size_mb > email_settings.max_attachment_size_mb:
            raise HTTPException(
                status_code=413,
                detail=f"File too large. Max size: {email_settings.max_attachment_size_mb}MB",
            )
        
        # Extract text
        extracted_text = DocumentProcessor.extract_text(file.filename, file_content)
        
        if not extracted_text:
            raise HTTPException(
                status_code=415,
                detail="Unsupported file format or extraction failed",
            )
        
        logger.info(f"Successfully extracted {len(extracted_text)} characters")
        return {
            "success": True,
            "filename": file.filename,
            "extracted_text": extracted_text,
            "text_length": len(extracted_text),
        }
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid customer ID format")
    except HTTPException:
        raise
    except Exception as error:
        logger.error(f"Error extracting document: {error}")
        raise HTTPException(status_code=500, detail="Failed to extract document")


@app.get("/documents/list")
async def list_customer_documents(customer_id: str):
    """List all documents for a customer."""
    try:
        customer_uuid = UUID(customer_id)
        
        logger.info(f"Listing documents for customer: {customer_id}")
        
        # Get customer info
        customer = await db.get_customer_info(customer_uuid)
        if not customer:
            raise HTTPException(status_code=404, detail="Customer not found")
        
        # List documents
        documents = await s3_client.list_customer_documents(
            first_name=customer.get("first_name", "unknown"),
            last_name=customer.get("last_name", "unknown"),
        )
        
        logger.info(f"Found {len(documents)} documents")
        return {
            "success": True,
            "customer_id": str(customer_uuid),
            "document_count": len(documents),
            "documents": documents,
        }
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid customer ID format")
    except HTTPException:
        raise
    except Exception as error:
        logger.error(f"Error listing documents: {error}")
        raise HTTPException(status_code=500, detail="Failed to list documents")


# Email Details Endpoint
@app.get("/emails/{email_id}")
async def get_email_details(email_id: str):
    """Get detailed information about a specific email with attachments."""
    try:
        email_uuid = UUID(email_id)
        
        # Get email with attachments
        email = await db.get_email_with_attachments(email_uuid)
        
        if not email:
            raise HTTPException(status_code=404, detail="Email not found")
        
        return {
            "success": True,
            "email": email,
        }
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid email ID format")
    except HTTPException:
        raise
    except Exception as error:
        logger.error(f"Error getting email details: {error}")
        raise HTTPException(status_code=500, detail="Failed to retrieve email")


# Thread Management Endpoints
@app.get("/threads/customer/{customer_id}")
async def get_customer_threads(customer_id: str):
    """Get all email threads for a customer."""
    try:
        customer_uuid = UUID(customer_id)
        
        logger.info(f"Fetching all threads for customer {customer_id}")
        
        threads = await db.get_customer_all_threads(customer_uuid)
        
        return {
            "success": True,
            "customer_id": str(customer_uuid),
            "thread_count": len(threads),
            "threads": threads,
        }
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid customer ID format")
    except Exception as error:
        logger.error(f"Error fetching customer threads: {error}")
        raise HTTPException(status_code=500, detail="Failed to fetch threads")


@app.get("/threads/{thread_id}")
async def get_thread_complete(thread_id: str, customer_id: str = None):
    """Get complete thread with all messages and attachments."""
    try:
        logger.info(f"Fetching complete thread: {thread_id}")
        
        # Get conversation thread JSONB with all messages
        thread_jsonb = await db.get_conversation_thread_jsonb(thread_id)
        
        if not thread_jsonb:
            raise HTTPException(status_code=404, detail="Thread not found")
        
        # Get documents in thread
        documents = await db.get_thread_documents(thread_id)
        
        return {
            "success": True,
            "thread_id": thread_id,
            "conversation": thread_jsonb,
            "documents": documents,
            "document_count": len(documents),
        }
    except HTTPException:
        raise
    except Exception as error:
        logger.error(f"Error fetching thread: {error}")
        raise HTTPException(status_code=500, detail="Failed to fetch thread")


@app.get("/threads/{thread_id}/documents")
async def get_thread_docs(thread_id: str):
    """Get all documents in a thread."""
    try:
        logger.info(f"Fetching documents for thread: {thread_id}")
        
        documents = await db.get_thread_documents(thread_id)
        
        return {
            "success": True,
            "thread_id": thread_id,
            "document_count": len(documents),
            "documents": documents,
        }
    except Exception as error:
        logger.error(f"Error fetching thread documents: {error}")
        raise HTTPException(status_code=500, detail="Failed to fetch documents")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
    )
