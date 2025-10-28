"""Document extraction and chunking pipeline for emails."""

import logging
import asyncio
from typing import Optional, List, Dict, Any
from uuid import UUID
import os

from .ocr_extractor import MistralOCRExtractor
from ..core.config import email_settings

logger = logging.getLogger(__name__)


class DocumentChunker:
    """Split documents into chunks for embedding."""
    
    def __init__(self, chunk_size: int = 500, overlap: int = 100):
        self.chunk_size = chunk_size
        self.overlap = overlap
    
    def chunk_text(self, text: str, metadata: Dict[str, Any] = None) -> List[Dict]:
        """Split text into overlapping chunks."""
        chunks = []
        words = text.split()
        
        for i in range(0, len(words), self.chunk_size - self.overlap):
            chunk_words = words[i:i + self.chunk_size]
            chunk_text = " ".join(chunk_words)
            
            chunk = {
                "text": chunk_text,
                "tokens": len(chunk_text.split()),
                "metadata": metadata or {}
            }
            chunks.append(chunk)
        
        return chunks
    
    def chunk_by_pages(self, pages: List[Dict], metadata: Dict = None) -> List[Dict]:
        """Keep pages as natural chunk boundaries."""
        chunks = []
        
        for page_num, page_content in enumerate(pages, 1):
            chunk = {
                "text": page_content.get("text", ""),
                "page": page_num,
                "tokens": len(page_content.get("text", "").split()),
                "metadata": {
                    **(metadata or {}),
                    "page": page_num
                }
            }
            chunks.append(chunk)
        
        return chunks


class DocumentExtractor:
    """Extract text and create chunks from email attachments."""
    
    def __init__(self):
        self.ocr = MistralOCRExtractor(
            api_key=os.getenv("MISTRAL_API_KEY")
        )
        self.chunker = DocumentChunker()
    
    async def extract_from_bytes(
        self,
        file_bytes: bytes,
        filename: str,
        email_id: UUID,
        document_id: UUID = None
    ) -> Dict[str, Any]:
        """Extract text from document bytes."""
        try:
            file_ext = filename.split('.')[-1].lower()
            
            if file_ext == 'pdf':
                return await self._extract_pdf_ocr(
                    file_bytes, filename, email_id, document_id
                )
            elif file_ext in ['docx', 'doc']:
                return await self._extract_docx(
                    file_bytes, filename, email_id, document_id
                )
            else:
                logger.warning(f"Unsupported file type: {file_ext}")
                return {
                    "success": False,
                    "error": f"Unsupported file type: {file_ext}"
                }
        
        except Exception as e:
            logger.error(f"Error extracting document {filename}: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _extract_pdf_ocr(
        self,
        file_bytes: bytes,
        filename: str,
        email_id: UUID,
        document_id: UUID = None
    ) -> Dict[str, Any]:
        """Extract PDF using Mistral OCR."""
        
        logger.info(f"Extracting PDF with Mistral OCR: {filename}")
        
        loop = asyncio.get_event_loop()
        ocr_result = await loop.run_in_executor(
            None,
            lambda: self.ocr.extract(
                file_bytes=file_bytes,
                file_name=filename
            )
        )
        
        # OCR extractor now returns a dict with 'chunks' key
        if not ocr_result.get('success'):
            logger.error(f"OCR failed: {ocr_result.get('error')}")
            raise Exception(ocr_result.get('error', 'OCR extraction failed'))
        
        ocr_chunks = ocr_result.get('chunks', [])
        full_text = ocr_result.get('full_text', '')
        
        # Convert OCR chunks to our chunking format
        pages = []
        for chunk_idx, ocr_chunk in enumerate(ocr_chunks, 1):
            pages.append({
                "page": chunk_idx,
                "text": ocr_chunk.get('text', ''),
                "tokens": ocr_chunk.get('tokens', 0)
            })
        
        # Use the chunker to format pages
        chunks = self.chunker.chunk_by_pages(
            pages,
            metadata={
                "email_id": str(email_id),
                "document_id": str(document_id) if document_id else None,
                "filename": filename,
                "extraction_method": "mistral_ocr"
            }
        )
        
        logger.info(
            f"✅ Extracted PDF: {filename} "
            f"({len(pages)} pages, {len(full_text)} chars)"
        )
        
        return {
            "success": True,
            "full_text": full_text,
            "chunks": chunks,
            "metadata": {
                "filename": filename,
                "email_id": str(email_id),
                "document_id": str(document_id) if document_id else None,
                "page_count": len(pages),
                "extraction_method": "mistral_ocr",
                "char_count": len(full_text),
                "token_estimate": len(full_text.split())
            }
        }
    
    async def _extract_docx(
        self,
        file_bytes: bytes,
        filename: str,
        email_id: UUID,
        document_id: UUID = None
    ) -> Dict[str, Any]:
        """Extract DOCX using python-docx."""
        
        logger.info(f"Extracting DOCX: {filename}")
        
        try:
            from io import BytesIO
            from docx import Document
            
            doc = Document(BytesIO(file_bytes))
            full_text = "\n".join([para.text for para in doc.paragraphs if para.text.strip()])
            
            chunks = self.chunker.chunk_text(
                full_text,
                metadata={
                    "email_id": str(email_id),
                    "document_id": str(document_id) if document_id else None,
                    "filename": filename,
                    "extraction_method": "docx_native"
                }
            )
            
            logger.info(f"✅ Extracted DOCX: {filename} ({len(full_text)} chars)")
            
            return {
                "success": True,
                "full_text": full_text,
                "chunks": chunks,
                "metadata": {
                    "filename": filename,
                    "email_id": str(email_id),
                    "document_id": str(document_id) if document_id else None,
                    "extraction_method": "docx_native",
                    "char_count": len(full_text),
                    "token_estimate": len(full_text.split())
                }
            }
        
        except Exception as e:
            logger.error(f"Error extracting DOCX {filename}: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }


_extractor = None

def get_extractor() -> DocumentExtractor:
    """Get or create document extractor instance."""
    global _extractor
    if _extractor is None:
        _extractor = DocumentExtractor()
    return _extractor
