"""Simple Mistral OCR extractor - independent, no heavy dependencies."""

from typing import Optional, Dict, Any, List
import os
import asyncio
import logging
from pathlib import Path

from mistralai import Mistral
from mistralai.models import DocumentURLChunk

logger = logging.getLogger(__name__)


class MistralOCRExtractor:
    """Extract content from PDFs and documents using Mistral OCR service."""
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize Mistral OCR extractor.
        
        Args:
            api_key: Mistral API key. If not provided, uses MISTRAL_API_KEY env var.
        """
        self.api_key = api_key or os.getenv("MISTRAL_API_KEY")
        if not self.api_key:
            raise ValueError("Mistral API key required. Set MISTRAL_API_KEY environment variable.")
        
        self.client = Mistral(api_key=self.api_key)
    
    def extract(self, file_bytes: bytes, file_name: str) -> Dict[str, Any]:
        """Extract text from PDF using Mistral OCR.
        
        Args:
            file_bytes: The binary content of the file
            file_name: Original filename
            
        Returns:
            Dict with:
                - chunks: List of page chunks with extracted text
                - full_text: Complete extracted text
                - metadata: Extraction metadata
        """
        try:
            logger.info(f"Starting OCR extraction for: {file_name}")
            
            # Upload file to Mistral
            logger.info("Uploading file to Mistral OCR service...")
            upload_response = self.client.files.upload(
                file={
                    "file_name": file_name,
                    "content": file_bytes,
                },
                purpose="ocr"
            )
            
            file_id = upload_response.id
            logger.info(f"File uploaded successfully. File ID: {file_id}")
            
            # Get signed URL
            logger.info("Retrieving file URL...")
            url_response = self.client.files.get_signed_url(file_id=file_id)
            signed_url = url_response.url
            
            # Process with OCR using Document object
            logger.info("Processing with OCR...")
            ocr_response = self.client.ocr.process(
                model="mistral-ocr-latest",
                document=DocumentURLChunk(document_url=signed_url)
            )
            
            # Parse response
            chunks = []
            full_text_parts = []
            page_count = 0
            
            if hasattr(ocr_response, 'pages') and ocr_response.pages:
                page_count = len(ocr_response.pages)
                
                for page_idx, page in enumerate(ocr_response.pages, 1):
                    page_text = ""
                    
                    # Extract text from page - check different possible attributes
                    if hasattr(page, 'content') and page.content:
                        if isinstance(page.content, str):
                            page_text = page.content
                        elif isinstance(page.content, list):
                            page_text = "\n".join([
                                item.text if hasattr(item, 'text') else str(item)
                                for item in page.content
                            ])
                    elif hasattr(page, 'markdown'):
                        page_text = page.markdown
                    elif hasattr(page, 'text'):
                        page_text = page.text
                    
                    full_text_parts.append(page_text)
                    
                    chunks.append({
                        "page": page_idx,
                        "text": page_text.strip(),
                        "tokens": len(page_text.split())
                    })
                    
                    logger.info(f"Extracted page {page_idx}: {len(page_text)} chars")
            
            full_text = "\n".join(full_text_parts)
            
            logger.info(f"✅ OCR complete: {page_count} pages, {len(full_text)} characters")
            
            return {
                "success": True,
                "chunks": chunks,
                "full_text": full_text,
                "metadata": {
                    "filename": file_name,
                    "page_count": page_count,
                    "char_count": len(full_text),
                    "token_estimate": len(full_text.split()),
                    "extraction_method": "mistral_ocr"
                }
            }
        
        except Exception as e:
            logger.error(f"OCR extraction failed: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "chunks": [],
                "full_text": ""
            }