"""Embeddings and vector search for email content."""

import logging
import os
from typing import List, Dict, Any, Optional
from uuid import UUID

try:
    from sentence_transformers import SentenceTransformer
    HAVE_LOCAL_EMBEDDINGS = True
except ImportError:
    HAVE_LOCAL_EMBEDDINGS = False

logger = logging.getLogger(__name__)


class EmbeddingsManager:
    """Handle embeddings for document chunks."""
    
    def __init__(self, use_local: bool = True):
        """
        Initialize embeddings manager.
        
        Args:
            use_local: Use local SentenceTransformer (fast, free) vs OpenAI API (accurate, costs money)
        """
        self.use_local = use_local and HAVE_LOCAL_EMBEDDINGS
        
        if self.use_local:
            logger.info("Using local SentenceTransformer embeddings (fast & free)")
            self.model = SentenceTransformer('all-MiniLM-L6-v2')  # 384 dimensions
            self.embedding_dim = 384
        else:
            logger.info("Using OpenAI embeddings (more accurate, costs money)")
            import openai
            self.client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
            self.embedding_dim = 1536  # text-embedding-3-small
    
    def embed_text(self, text: str) -> List[float]:
        """Embed a single text string."""
        if self.use_local:
            return self.model.encode(text, convert_to_numpy=True).tolist()
        else:
            response = self.client.embeddings.create(
                input=text,
                model="text-embedding-3-small"
            )
            return response.data[0].embedding
    
    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Embed multiple texts efficiently."""
        if self.use_local:
            return [
                embedding.tolist() 
                for embedding in self.model.encode(texts, show_progress_bar=True)
            ]
        else:
            response = self.client.embeddings.create(
                input=texts,
                model="text-embedding-3-small"
            )
            return [item.embedding for item in response.data]


class VectorStore:
    """Manage vector storage and similarity search in Supabase."""
    
    def __init__(self, db_client):
        """Initialize with database client."""
        self.db = db_client
        self.embeddings = EmbeddingsManager(use_local=True)
    
    async def store_chunk_embeddings(
        self,
        chunks: List[Dict[str, Any]],
        email_id: UUID,
        document_id: UUID,
        customer_id: UUID
    ) -> int:
        """
        Store document chunks with embeddings in database.
        
        Args:
            chunks: List of chunk dicts with 'text' and 'metadata'
            email_id: Email UUID
            document_id: Document UUID
            customer_id: Customer UUID
            
        Returns:
            Number of chunks stored
        """
        if not chunks:
            return 0
        
        logger.info(f"Storing {len(chunks)} chunks with embeddings...")
        
        # Embed all chunks
        texts = [chunk['text'] for chunk in chunks]
        embeddings = self.embeddings.embed_batch(texts)
        
        # Prepare data for storage
        data_to_insert = []
        for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
            data_to_insert.append({
                "email_id": str(email_id),
                "document_id": str(document_id),
                "customer_id": str(customer_id),
                "chunk_number": i + 1,
                "text": chunk['text'],
                "embedding": embedding,
                "tokens_count": chunk.get('tokens', len(chunk['text'].split())),
                "metadata": chunk.get('metadata', {})
            })
        
        # Store in batches
        batch_size = 100
        total_stored = 0
        
        for i in range(0, len(data_to_insert), batch_size):
            batch = data_to_insert[i:i + batch_size]
            try:
                response = self.db.supabase.table("email_chunks").insert(batch).execute()
                total_stored += len(batch)
                logger.info(f"  ✅ Stored batch {i//batch_size + 1} ({len(batch)} chunks)")
            except Exception as e:
                logger.error(f"Error storing chunks batch: {str(e)}")
        
        logger.info(f"✅ Successfully stored {total_stored} chunks with embeddings")
        return total_stored
    
    async def search_similar_chunks(
        self,
        query: str,
        customer_id: UUID,
        limit: int = 10,
        similarity_threshold: float = 0.5
    ) -> List[Dict[str, Any]]:
        """
        Search for chunks similar to query.
        
        Args:
            query: Search query
            customer_id: Limit to customer's documents
            limit: Max results
            similarity_threshold: Minimum similarity score (0-1)
            
        Returns:
            List of similar chunks with similarity scores
        """
        logger.info(f"Searching for: {query}")
        
        # Embed the query
        query_embedding = self.embeddings.embed_text(query)
        
        # Search using pgvector
        try:
            response = self.db.supabase.rpc(
                'similarity_search_email_chunks',
                {
                    'query_embedding': query_embedding,
                    'customer_id': str(customer_id),
                    'max_results': limit,
                    'similarity_threshold': similarity_threshold
                }
            ).execute()
            
            results = response.data or []
            logger.info(f"Found {len(results)} similar chunks")
            return results
        
        except Exception as e:
            logger.error(f"Error searching vectors: {str(e)}")
            return []


# Singleton instance
_vector_store = None

def get_vector_store(db_client) -> VectorStore:
    """Get or create vector store instance."""
    global _vector_store
    if _vector_store is None:
        _vector_store = VectorStore(db_client)
    return _vector_store
