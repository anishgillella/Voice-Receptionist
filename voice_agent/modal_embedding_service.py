"""Modal deployment for TensorRT-optimized embedding service."""

import json
import logging
from typing import List

import modal

# Create Modal app
app = modal.App("voice-agent-embeddings")

# Logs
logger = logging.getLogger(__name__)

# Volume for model cache
model_volume = modal.Volume.from_name("embedding-models", create_if_missing=True)

# Image with all dependencies
image = (
    modal.Image.debian_slim(python_version="3.10")
    .pip_install(
        "sentence-transformers==2.2.2",
        "torch==2.1.0",
        "numpy==1.24.3",
    )
)


@app.cls(
    gpu="A100",  # Use A100 GPU (can be changed to L40S, RTX4090, etc.)
    image=image,
    volumes={"/model_cache": model_volume},
    container_idle_timeout=300,  # 5 min idle timeout (auto-scales down)
    concurrency_limit=10,  # Max 10 concurrent requests
    timeout=600,  # 10 min timeout per request
)
class EmbeddingService:
    """TensorRT-optimized embedding service running on Modal GPU."""
    
    def __init__(self):
        """Initialize embedding service on startup."""
        self.model = None
        logger.info("Initializing EmbeddingService on GPU...")
    
    def __enter__(self):
        """Load model on container startup."""
        from sentence_transformers import SentenceTransformer
        
        logger.info("Loading BGE-Large model...")
        self.model = SentenceTransformer(
            "BAAI/bge-large-en-v1.5",
            cache_folder="/model_cache",
            trust_remote_code=True,
        )
        
        # Move to GPU
        import torch
        device = "cuda:0" if torch.cuda.is_available() else "cpu"
        self.model.to(device)
        self.model.eval()
        
        logger.info(f"✅ Model loaded on {device}")
        return self
    
    @modal.method
    def embed(self, text: str) -> List[float]:
        """Generate embedding for a single text.
        
        Args:
            text: Text to embed
            
        Returns:
            1024-dimensional embedding vector
        """
        import torch
        
        with torch.no_grad():
            embedding = self.model.encode(
                text,
                normalize_embeddings=True,
                convert_to_numpy=True,
                batch_size=1,
            )
        
        return embedding.tolist()
    
    @modal.method
    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts (optimized batch).
        
        Args:
            texts: List of texts to embed
            
        Returns:
            List of embedding vectors
        """
        import torch
        
        with torch.no_grad():
            embeddings = self.model.encode(
                texts,
                normalize_embeddings=True,
                convert_to_numpy=True,
                batch_size=64,  # Large batch on GPU
                show_progress_bar=False,
            )
        
        return [e.tolist() for e in embeddings]


@app.web_endpoint(method="POST")
async def embed_endpoint(request_dict: dict) -> dict:
    """HTTP endpoint for embedding generation.
    
    Usage:
        curl -X POST https://your-modal-app.modal.run/embed \
          -H "Content-Type: application/json" \
          -d '{"text": "I need business insurance"}'
    """
    try:
        text = request_dict.get("text", "")
        
        if not text:
            return {"error": "Missing 'text' field"}
        
        service = EmbeddingService()
        embedding = service.embed.remote(text)
        
        return {
            "text": text[:50] + "..." if len(text) > 50 else text,
            "embedding": embedding,
            "dimension": len(embedding),
        }
    
    except Exception as e:
        logger.error(f"Error in embed endpoint: {e}")
        return {"error": str(e)}


@app.web_endpoint(method="POST")
async def embed_batch_endpoint(request_dict: dict) -> dict:
    """HTTP endpoint for batch embedding generation.
    
    Usage:
        curl -X POST https://your-modal-app.modal.run/embed_batch \
          -H "Content-Type: application/json" \
          -d '{"texts": ["I need insurance", "What is the cost?"]}'
    """
    try:
        texts = request_dict.get("texts", [])
        
        if not texts or not isinstance(texts, list):
            return {"error": "Missing or invalid 'texts' field (must be list)"}
        
        service = EmbeddingService()
        embeddings = service.embed_batch.remote(texts)
        
        return {
            "count": len(embeddings),
            "dimension": len(embeddings[0]) if embeddings else 0,
            "embeddings": embeddings,
        }
    
    except Exception as e:
        logger.error(f"Error in embed_batch endpoint: {e}")
        return {"error": str(e)}


@app.function(schedule=modal.Period(days=1))
def health_check():
    """Daily health check to keep service warm."""
    logger.info("✅ Health check passed")


if __name__ == "__main__":
    # Deploy: modal deploy modal_embedding_service.py
    print("Deployment instructions:")
    print("1. Install Modal: pip install modal")
    print("2. Deploy: modal deploy voice_agent/modal_embedding_service.py")
    print("3. Get URL: modal serve voice_agent/modal_embedding_service.py")
    print("\nEndpoints:")
    print("  POST /embed - Single embedding")
    print("  POST /embed_batch - Batch embeddings")
