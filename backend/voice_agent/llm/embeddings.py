"""Embedding generation with caching and GPU optimization."""

from __future__ import annotations

import logging
from typing import Optional

from sentence_transformers import SentenceTransformer
from huggingface_hub import login

from ..core.config import settings
from ..services.embedding_cache import get_cached_embedding, cache_embedding, get_cache_stats

logger = logging.getLogger(__name__)

# Global model instance (loaded once)
_model_instance: Optional[SentenceTransformer] = None

# Try to import TensorRT
try:
    from .tensorrt_embeddings import get_tensorrt_embeddings
    TENSORRT_AVAILABLE = True
except ImportError:
    TENSORRT_AVAILABLE = False
    logger.warning("TensorRT not available, will use CPU embeddings")


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


def generate_embedding(text: str, use_cache: bool = True) -> list[float]:
    """Generate embedding vector for text using BGE-Large with caching.

    Args:
        text: Text to embed
        use_cache: Whether to use Redis cache

    Returns:
        1024-dimensional embedding vector
    """
    try:
        # Step 1: Try Redis cache first
        if use_cache:
            cached = get_cached_embedding(text)
            if cached:
                logger.debug(f"✅ Cache hit for embedding")
                return cached
        
        # Step 2: Try TensorRT (GPU optimized)
        if TENSORRT_AVAILABLE and settings.use_tensorrt:
            try:
                logger.debug(f"Generating embedding via TensorRT (GPU)")
                embeddings = get_tensorrt_embeddings()
                embedding = embeddings.encode(text, normalize_embeddings=True)
                
                # Cache the result
                if use_cache:
                    cache_embedding(text, embedding)
                
                return embedding
            except Exception as e:
                logger.warning(f"TensorRT generation failed, falling back to CPU: {e}")
        
        # Step 3: Fallback to CPU model
        logger.debug(f"Generating embedding via CPU")
        model = get_embedding_model()
        embedding = model.encode(text, normalize_embeddings=True)
        embedding_list = embedding.tolist()
        
        # Cache the result
        if use_cache:
            cache_embedding(text, embedding_list)
        
        return embedding_list
        
    except Exception as e:
        logger.error(f"Error generating embedding: {e}")
        raise


def generate_embeddings_batch(texts: list[str], use_cache: bool = True) -> list[list[float]]:
    """Generate embeddings for multiple texts with batching and caching.

    Args:
        texts: List of texts to embed
        use_cache: Whether to use Redis cache

    Returns:
        List of embedding vectors
    """
    try:
        # Check cache for each text
        embeddings = []
        texts_to_generate = []
        indices_to_generate = []
        
        if use_cache:
            for i, text in enumerate(texts):
                cached = get_cached_embedding(text)
                if cached:
                    embeddings.append(cached)
                    logger.debug(f"✅ Cache hit for batch item {i}")
                else:
                    embeddings.append(None)
                    texts_to_generate.append(text)
                    indices_to_generate.append(i)
        else:
            texts_to_generate = texts
            indices_to_generate = list(range(len(texts)))
            embeddings = [None] * len(texts)
        
        # Generate embeddings for cache misses
        if texts_to_generate:
            # Try TensorRT first
            if TENSORRT_AVAILABLE and settings.use_tensorrt:
                try:
                    logger.debug(f"Generating {len(texts_to_generate)} embeddings via TensorRT batch")
                    embeddings_gen = get_tensorrt_embeddings()
                    generated = embeddings_gen.encode_batch(texts_to_generate, normalize_embeddings=True)
                    
                    # Place generated embeddings in correct positions
                    for idx, text, embedding in zip(indices_to_generate, texts_to_generate, generated):
                        embeddings[idx] = embedding
                        if use_cache:
                            cache_embedding(text, embedding)
                    
                except Exception as e:
                    logger.warning(f"TensorRT batch generation failed, falling back to CPU: {e}")
                    # Fall through to CPU
                    embeddings = None
            
            # Fallback to CPU if needed
            if embeddings is None or any(e is None for e in embeddings):
                logger.debug(f"Generating {len(texts_to_generate)} embeddings via CPU batch")
                model = get_embedding_model()
                generated = model.encode(texts_to_generate, normalize_embeddings=True)
                
                embeddings = [None] * len(texts)
                for idx, text, embedding in zip(indices_to_generate, texts_to_generate, generated):
                    embedding_list = embedding.tolist()
                    embeddings[idx] = embedding_list
                    if use_cache:
                        cache_embedding(text, embedding_list)
        
        return embeddings
        
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
    
    # Clean up TensorRT resources if available
    if TENSORRT_AVAILABLE:
        try:
            from .tensorrt_embeddings import cleanup
            cleanup()
        except Exception as e:
            logger.warning(f"Error cleaning up TensorRT: {e}")

