from apollo_agents.file_handlers.base import BaseExtractor
from apollo_agents.file_handlers.models import (
    Content, Chunk, Text, ImageContent, FileMetadata
)
from typing import List, Optional, Dict, Any
import os
import asyncio
import base64
import json
import logging
import hashlib
import tempfile
from pathlib import Path

from mistralai import Mistral
from mistralai import DocumentURLChunk, ImageURLChunk, TextChunk

# Configure logger
logger = logging.getLogger(__name__)


def _extract_b64_payload(possible_data_url: str) -> str:
    """
    Accept either a raw base64 string or a data URL string and return the raw base64 payload.
    Also fixes missing base64 padding and strips whitespace.
    """
    s = possible_data_url.strip()
    if s.startswith("data:"):
        # Split at the first comma and take the tail
        parts = s.split(",", 1)
        s = parts[1] if len(parts) > 1 else ""
    # Remove whitespace/newlines
    s = "".join(s.split())
    # Fix padding if needed
    pad_len = (-len(s)) % 4
    if pad_len:
        s = s + ("=" * pad_len)
    return s


# Note: We intentionally avoid decoding images here. The OCR returns base64 strings.
# We just clean/pad the base64 and pass it downstream with a conservative MIME.

class MistralOCRExtractor(BaseExtractor):
    """Extract content from PDFs using Mistral OCR service.
    
    This extractor processes PDF files using Mistral's OCR service, extracting both
    text content and images as embedded in the markdown format returned by the API.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        include_images: bool = True
    ):
        # Use provided API key or fallback to environment variable
        self.api_key = api_key or os.getenv("MISTRAL_API_KEY")
        if not self.api_key:
            raise ValueError("Mistral API key is required. Provide it directly or set MISTRAL_API_KEY environment variable.")
        
        self.client = Mistral(api_key=self.api_key)
        self.include_images = include_images
        # Create temp directory for consistent file storage
        self.temp_dir = os.path.join(tempfile.gettempdir(), "apollo_mistral_ocr_cache")
        os.makedirs(self.temp_dir, exist_ok=True)

    @property
    def supported_types(self) -> List[str]:
        """List of supported file extensions."""
        return ['.pdf']
    
    def _get_hashed_filename(self, file_bytes: bytes, original_name: str) -> str:
        """
        Generate a consistent hashed filename based on file content and name.
        
        Args:
            file_bytes: The file content
            original_name: The original file name
            
        Returns:
            A hashed filename with original extension preserved
        """
        # Create hash from both content and original name for uniqueness
        hasher = hashlib.sha256()
        hasher.update(file_bytes)
        hasher.update(original_name.encode('utf-8'))
        file_hash = hasher.hexdigest()[:16]  # Use first 16 chars of hash
        
        # Preserve original extension
        _, ext = os.path.splitext(original_name)
        hashed_name = f"mistral_ocr_{file_hash}{ext}"
        
        return hashed_name

    async def extract(self, file_bytes: bytes, **kwargs) -> Content:
        """
        Extract text and image content from PDF file using Mistral OCR.
        
        Args:
            file_bytes (bytes): The binary content of the file.
            kwargs: Optional keyword arguments.
        
        Returns:
            Content: A Content object with document chunks (by page) containing text and images.
            
        Raises:
            ValueError: If the Mistral API returns an error.
        """
        try:
            # Create a temporary file for uploading
            loop = asyncio.get_event_loop()
            
            # Generate consistent hashed filename
            original_name = kwargs.get("file_name", "document.pdf")
            hashed_filename = self._get_hashed_filename(file_bytes, original_name)
            temp_file_path = os.path.join(self.temp_dir, hashed_filename)
            
            # Log the hashed filename for debugging
            logger.info(f"Using hashed filename: {hashed_filename} for original: {original_name}")
            
            # Write to temp file for potential caching/debugging
            # This also ensures consistency across runs
            if not os.path.exists(temp_file_path):
                with open(temp_file_path, 'wb') as f:
                    f.write(file_bytes)
                logger.debug(f"Created temp file: {temp_file_path}")
            else:
                logger.debug(f"Temp file already exists: {temp_file_path}")
            
            # Upload file to Mistral's OCR service with hashed name
            upload_response = await loop.run_in_executor(
                None,
                lambda: self.client.files.upload(
                    file={
                        "file_name": hashed_filename,
                        "content": file_bytes,
                    },
                    purpose="ocr"
                )
            )
            
            # Get signed URL for the uploaded file
            signed_url_response = await loop.run_in_executor(
                None,
                lambda: self.client.files.get_signed_url(
                    file_id=upload_response.id, 
                    expiry=1
                )
            )
            
            # Process PDF with OCR, including embedded images
            ocr_response = await loop.run_in_executor(
                None,
                lambda: self.client.ocr.process(
                    document=DocumentURLChunk(document_url=signed_url_response.url),
                    model="mistral-ocr-latest",
                    include_image_base64=self.include_images
                )
            )

            # Convert response to chunks organized by page
            chunks = []
            
            # Log available attributes for debugging
            if ocr_response.pages:
                first_page = ocr_response.pages[0]
            
            for idx, page in enumerate(ocr_response.pages):
                # Try to get page number with fallbacks for API structure changes
                try:
                    # First try direct attribute
                    page_num = page.page_number
                except AttributeError:
                    # Try alternative attribute names that might exist
                    if hasattr(page, 'page_index'):
                        page_num = page.page_index + 1  # Convert 0-based index to 1-based page number
                    elif hasattr(page, 'index'):
                        page_num = page.index + 1
                    else:
                        # Fallback to using the position in the list (1-based)
                        page_num = idx + 1
                        print(f"Warning: Using fallback page numbering for page {idx+1}. OCR API may have changed.")
                
                chunk_contents = []
                
                # Extract text content from markdown
                try:
                    text_content = page.markdown
                except AttributeError:
                    # Fallback if markdown attribute is missing
                    logger.warning("Missing 'markdown' attribute in OCRPageObject")
                    if hasattr(page, 'text'):
                        text_content = page.text
                    elif hasattr(page, 'content'):
                        text_content = page.content
                    else:
                        text_content = ""
                        logger.error(f"Could not find text content for page {page_num}")
                
                # If images are included, replace image placeholders with actual images
                try:
                    has_images = self.include_images and hasattr(page, 'images') and page.images
                except Exception as e:
                    logger.warning(f"Error checking for images: {str(e)}")
                    has_images = False
                
                if has_images:
                    for img in page.images:
                        try:
                            if not getattr(img, 'image_base64', None):
                                continue
                            b64_str = _extract_b64_payload(img.image_base64)
                            if not b64_str:
                                continue

                            image_id = getattr(img, 'id', f"img_{id(img)}")
                            image_width = getattr(img, 'width', 800)
                            image_height = getattr(img, 'height', 600)

                            image_obj = ImageContent(
                                content=b64_str,
                                width=image_width,
                                height=image_height,
                                mime_type="image/png",
                                metadata={"id": image_id, "page": page_num}
                            )
                            chunk_contents.append(image_obj)

                            text_content = text_content.replace(
                                f"![{image_id}]({image_id})", 
                                f"[Image: {image_id}]"
                            )
                        except Exception as e:
                            logger.warning(f"Error processing image: {str(e)}")
                
                # Add text content
                if text_content:
                    chunk_contents.append(
                        Text(
                            content=text_content,
                            metadata={"page": page_num, "type": "text"}
                        )
                    )
                
                # Add the chunk if it has contents
                if chunk_contents:
                    chunks.append(
                        Chunk(
                            contents=chunk_contents,
                            metadata={"page": page_num}
                        )
                    )
            
            return Content(chunks=chunks)
            
        except Exception as e:
            # Log error details
            logger.error(f"Mistral OCR error: {str(e)}")
            
            # Try to get more information about the OCR response structure
            try:
                if 'ocr_response' in locals():
                    logger.error(f"OCR response type: {type(ocr_response)}")
                    
                    if hasattr(ocr_response, 'pages') and ocr_response.pages:
                        logger.error(f"First page type: {type(ocr_response.pages[0])}")
                        logger.error(f"First page attributes: {dir(ocr_response.pages[0])}")
                    elif hasattr(ocr_response, 'pages'):
                        logger.error("OCR response has 'pages' attribute but it's empty")
                    else:
                        logger.error(f"OCR response attributes: {dir(ocr_response)}")
            except Exception as debug_err:
                logger.error(f"Error while debugging OCR response: {str(debug_err)}")
                
            # Re-raise with original error
            raise ValueError(f"Mistral OCR error: {str(e)}")

    @staticmethod
    def replace_images_in_markdown(markdown_str: str, images_dict: dict) -> str:
        """
        Replace image placeholders in markdown with references to base64-encoded images.
        
        Args:
            markdown_str: Markdown text containing image placeholders
            images_dict: Dictionary mapping image IDs to base64 strings
            
        Returns:
            Markdown text with image references
        """
        for img_name, base64_str in images_dict.items():
            markdown_str = markdown_str.replace(
                f"![{img_name}]({img_name})", 
                f"[Image: {img_name}]"
            )
        return markdown_str