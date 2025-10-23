"""Embedding generation using BGE-Large model from HuggingFace."""

from __future__ import annotations

import logging
from typing import Optional

from sentence_transformers import SentenceTransformer
from huggingface_hub import login

from .config import settings

logger = logging.getLogger(__name__)

# Global model instance (loaded once)
_model_instance: Optional[SentenceTransformer] = None


def get_embedding_model() -> SentenceTransformer:
    """Get or load the BGE-Large embedding model."""
    global _model_instance

    if _model_instance is None:
        logger.info(f"Loading embedding model: {settings.embedding_model}")
        try:
            # Login to HuggingFace if token is available
            if settings.hf_token:
                logger.info("Logging in to HuggingFace")
                login(token=settings.hf_token, add_to_git_credential=False)
            
            _model_instance = SentenceTransformer(settings.embedding_model)
            logger.info("Embedding model loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load embedding model: {e}")
            raise

    return _model_instance


def generate_embedding(text: str) -> list[float]:
    """Generate embedding vector for text using BGE-Large.

    Args:
        text: Text to embed

    Returns:
        1024-dimensional embedding vector
    """
    try:
        model = get_embedding_model()
        embedding = model.encode(text, normalize_embeddings=True)
        return embedding.tolist()
    except Exception as e:
        logger.error(f"Error generating embedding: {e}")
        raise


def generate_embeddings_batch(texts: list[str]) -> list[list[float]]:
    """Generate embeddings for multiple texts.

    Args:
        texts: List of texts to embed

    Returns:
        List of embedding vectors
    """
    try:
        model = get_embedding_model()
        embeddings = model.encode(texts, normalize_embeddings=True)
        return [e.tolist() for e in embeddings]
    except Exception as e:
        logger.error(f"Error generating batch embeddings: {e}")
        raise


def chunk_transcript(transcript: str, chunk_size: int = 500, overlap: int = 100) -> list[str]:
    """Split transcript into overlapping chunks.

    Args:
        transcript: Full transcript text
        chunk_size: Number of tokens per chunk (approximate)
        overlap: Number of tokens to overlap between chunks

    Returns:
        List of overlapping chunks
    """
    # Simple word-based chunking (approximate token count)
    words = transcript.split()
    chunks = []

    i = 0
    while i < len(words):
        chunk_words = words[i : i + chunk_size]
        chunk_text = " ".join(chunk_words)
        chunks.append(chunk_text)

        # Move forward with overlap
        i += chunk_size - overlap

    return chunks if chunks else [transcript]


def generate_summary_excerpt(transcript: str, max_words: int = 100) -> str:
    """Generate a short summary excerpt of the transcript.

    Args:
        transcript: Full transcript
        max_words: Maximum words in excerpt

    Returns:
        Summary excerpt
    """
    words = transcript.split()
    if len(words) <= max_words:
        return transcript

    # Take first max_words words as summary
    return " ".join(words[:max_words]) + "..."


def model_cleanup() -> None:
    """Clean up model resources."""
    global _model_instance
    if _model_instance is not None:
        logger.info("Cleaning up embedding model")
        _model_instance = None

