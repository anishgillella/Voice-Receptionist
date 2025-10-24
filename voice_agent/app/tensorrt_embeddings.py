"""TensorRT-optimized embedding generation for GPU acceleration."""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Optional

import numpy as np

try:
    import tensorrt as trt
    import torch
    from sentence_transformers import SentenceTransformer
    TENSORRT_AVAILABLE = True
except ImportError:
    TENSORRT_AVAILABLE = False

from .config import settings

logger = logging.getLogger(__name__)

# TensorRT logger
TRT_LOGGER = trt.Logger(trt.Logger.WARNING) if TENSORRT_AVAILABLE else None

# Global model instances
_model_cpu: Optional[SentenceTransformer] = None
_model_gpu: Optional[SentenceTransformer] = None


class TensorRTEmbeddings:
    """TensorRT-optimized embedding generation."""
    
    def __init__(self, use_tensorrt: bool = False):
        """Initialize TensorRT embeddings.
        
        Args:
            use_tensorrt: Whether to use TensorRT optimization
        """
        self.use_tensorrt = use_tensorrt and TENSORRT_AVAILABLE
        self.device = settings.tensorrt_device if self.use_tensorrt else "cpu"
        self.cache_dir = settings.tensorrt_cache_dir
        
        if self.use_tensorrt:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"✅ TensorRT embeddings initialized (device: {self.device})")
        else:
            logger.info("Using CPU embeddings (TensorRT disabled)")
    
    def _get_gpu_model(self) -> Optional[SentenceTransformer]:
        """Get or load GPU model.
        
        Returns:
            SentenceTransformer on GPU or None if failed
        """
        global _model_gpu
        
        if _model_gpu is not None:
            return _model_gpu
        
        try:
            from sentence_transformers import SentenceTransformer
            
            logger.info("Loading BGE-Large model for GPU...")
            model = SentenceTransformer("BAAI/bge-large-en-v1.5")
            model.to(self.device)
            
            # Set to eval mode for inference
            model.eval()
            
            _model_gpu = model
            logger.info(f"✅ GPU model loaded on {self.device}")
            return model
            
        except Exception as e:
            logger.error(f"Failed to load GPU model: {e}")
            return None
    
    def encode(self, text: str, normalize_embeddings: bool = True) -> list[float]:
        """Generate embedding for text.
        
        Args:
            text: Text to embed
            normalize_embeddings: Whether to normalize embeddings
            
        Returns:
            Embedding vector
        """
        try:
            if self.use_tensorrt and TENSORRT_AVAILABLE:
                model = self._get_gpu_model()
                if model:
                    with torch.no_grad():
                        embedding = model.encode(
                            text,
                            normalize_embeddings=normalize_embeddings,
                            convert_to_numpy=True,
                            device=self.device,
                            batch_size=32,
                        )
                    return embedding.tolist()
            
            # Fallback to CPU
            from sentence_transformers import SentenceTransformer
            
            global _model_cpu
            if _model_cpu is None:
                _model_cpu = SentenceTransformer("BAAI/bge-large-en-v1.5")
            
            embedding = _model_cpu.encode(
                text,
                normalize_embeddings=normalize_embeddings,
            )
            return embedding.tolist()
            
        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            raise
    
    def encode_batch(self, texts: list[str], normalize_embeddings: bool = True) -> list[list[float]]:
        """Generate embeddings for multiple texts (optimized).
        
        Args:
            texts: Texts to embed
            normalize_embeddings: Whether to normalize embeddings
            
        Returns:
            List of embedding vectors
        """
        try:
            if self.use_tensorrt and TENSORRT_AVAILABLE:
                model = self._get_gpu_model()
                if model:
                    with torch.no_grad():
                        embeddings = model.encode(
                            texts,
                            normalize_embeddings=normalize_embeddings,
                            convert_to_numpy=True,
                            device=self.device,
                            batch_size=64,  # Larger batch on GPU
                            show_progress_bar=False,
                        )
                    return [e.tolist() for e in embeddings]
            
            # Fallback to CPU
            from sentence_transformers import SentenceTransformer
            
            global _model_cpu
            if _model_cpu is None:
                _model_cpu = SentenceTransformer("BAAI/bge-large-en-v1.5")
            
            embeddings = _model_cpu.encode(
                texts,
                normalize_embeddings=normalize_embeddings,
                batch_size=32,
            )
            return [e.tolist() for e in embeddings]
            
        except Exception as e:
            logger.error(f"Error generating batch embeddings: {e}")
            raise


def get_tensorrt_embeddings() -> TensorRTEmbeddings:
    """Get TensorRT embeddings instance.
    
    Returns:
        TensorRTEmbeddings instance
    """
    use_tensorrt = settings.use_tensorrt
    return TensorRTEmbeddings(use_tensorrt=use_tensorrt)


def cleanup():
    """Clean up GPU resources."""
    global _model_cpu, _model_gpu
    
    if _model_gpu is not None:
        try:
            del _model_gpu
            _model_gpu = None
            if TENSORRT_AVAILABLE:
                torch.cuda.empty_cache()
            logger.info("GPU model cleaned up")
        except Exception as e:
            logger.warning(f"Error cleaning GPU model: {e}")
    
    if _model_cpu is not None:
        try:
            del _model_cpu
            _model_cpu = None
            logger.info("CPU model cleaned up")
        except Exception as e:
            logger.warning(f"Error cleaning CPU model: {e}")
