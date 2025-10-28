"""Document processing module for email attachments.

Handles OCR extraction, text chunking, and document processing.
"""

from .document_processor import DocumentProcessor
from .document_extraction import DocumentExtractor, DocumentChunker, get_extractor
from .ocr_extractor import MistralOCRExtractor

__all__ = [
    'DocumentProcessor',
    'DocumentExtractor',
    'DocumentChunker',
    'MistralOCRExtractor',
    'get_extractor',
]
