"""Modal GPU service client for distributed embedding computation."""

from __future__ import annotations

import logging
from typing import List, Optional

import httpx

from ..core.config import settings

logger = logging.getLogger(__name__)


class ModalEmbeddingClient:
    """Client for Modal embedding service with fallback."""
    
    def __init__(self, modal_url: Optional[str] = None):
        """Initialize Modal client.
        
        Args:
            modal_url: Modal service URL (e.g., https://app-name.modal.run)
        """
        self.modal_url = modal_url or settings.modal_embedding_url
        self.available = bool(self.modal_url)
        self.http_client = httpx.AsyncClient(timeout=30.0)
        
        if self.available:
            logger.info(f"✅ Modal embedding service configured: {self.modal_url}")
        else:
            logger.info("Modal embedding service not configured, will use local embeddings")
    
    async def embed(self, text: str) -> Optional[List[float]]:
        """Get embedding from Modal service.
        
        Args:
            text: Text to embed
            
        Returns:
            Embedding vector or None if failed
        """
        if not self.available:
            return None
        
        try:
            logger.debug(f"Calling Modal embedding service for text: {text[:50]}...")
            
            response = await self.http_client.post(
                f"{self.modal_url}/embed",
                json={"text": text},
            )
            response.raise_for_status()
            
            result = response.json()
            embedding = result.get("embedding")
            
            if embedding:
                logger.debug(f"✅ Got embedding from Modal ({len(embedding)} dims)")
                return embedding
            else:
                logger.warning(f"Invalid response from Modal: {result}")
                return None
            
        except Exception as e:
            logger.warning(f"Failed to get embedding from Modal: {e}")
            return None
    
    async def embed_batch(self, texts: List[str]) -> Optional[List[List[float]]]:
        """Get embeddings from Modal service (batch).
        
        Args:
            texts: List of texts to embed
            
        Returns:
            List of embedding vectors or None if failed
        """
        if not self.available:
            return None
        
        try:
            logger.debug(f"Calling Modal embedding service for batch of {len(texts)} texts")
            
            response = await self.http_client.post(
                f"{self.modal_url}/embed_batch",
                json={"texts": texts},
            )
            response.raise_for_status()
            
            result = response.json()
            embeddings = result.get("embeddings")
            
            if embeddings:
                logger.debug(f"✅ Got {len(embeddings)} embeddings from Modal")
                return embeddings
            else:
                logger.warning(f"Invalid response from Modal: {result}")
                return None
            
        except Exception as e:
            logger.warning(f"Failed to get batch embeddings from Modal: {e}")
            return None
    
    async def close(self):
        """Close HTTP client."""
        await self.http_client.aclose()


# Global client instance
_modal_client: Optional[ModalEmbeddingClient] = None


def get_modal_client() -> ModalEmbeddingClient:
    """Get or create Modal embedding client."""
    global _modal_client
    
    if _modal_client is None:
        _modal_client = ModalEmbeddingClient()
    
    return _modal_client


async def close_modal_client():
    """Close Modal client."""
    global _modal_client
    if _modal_client:
        await _modal_client.close()
        _modal_client = None

