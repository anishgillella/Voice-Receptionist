"""Context retrieval for voice agent from email data."""

import logging
import redis
import json
from typing import Optional, Dict, Any
from uuid import UUID
import hashlib

from email_agent.embeddings_vectorstore import get_vector_store
from email_agent.db import EmailDatabase

logger = logging.getLogger(__name__)


class VoiceAgentContextManager:
    """
    Retrieve relevant email context for voice agent calls.
    Uses vector search + caching for fast, token-efficient context.
    """
    
    def __init__(self, redis_host: str = 'localhost', redis_port: int = 6379):
        """Initialize with Redis cache."""
        self.db = EmailDatabase()
        self.vector_store = get_vector_store(self.db)
        
        try:
            self.cache = redis.Redis(
                host=redis_host,
                port=redis_port,
                decode_responses=True
            )
            self.cache.ping()
            logger.info("✅ Connected to Redis cache")
            self.use_cache = True
        except:
            logger.warning("⚠️  Redis not available, will skip caching")
            self.use_cache = False
            self.cache = None
    
    def _get_cache_key(self, customer_id: UUID, query: str) -> str:
        """Generate cache key from customer and query."""
        query_hash = hashlib.md5(query.lower().encode()).hexdigest()
        return f"context:{customer_id}:{query_hash}"
    
    async def get_email_context(
        self,
        customer_id: UUID,
        query: str,
        top_k: int = 3,
        use_reranking: bool = False
    ) -> Dict[str, Any]:
        """
        Get relevant email context for voice agent.
        
        Args:
            customer_id: Customer UUID
            query: Voice query from customer
            top_k: Number of top chunks to return
            use_reranking: Use LLM re-ranking (slower but more accurate)
            
        Returns:
            Context dict with relevant email/document info
        """
        cache_key = self._get_cache_key(customer_id, query)
        
        # Check cache first
        if self.use_cache:
            cached = self.cache.get(cache_key)
            if cached:
                logger.info(f"✅ Cache HIT for query: {query}")
                return json.loads(cached)
        
        logger.info(f"🔍 Searching for: {query}")
        
        # Vector search
        chunks = await self.vector_store.search_similar_chunks(
            query=query,
            customer_id=customer_id,
            limit=10 if use_reranking else top_k,
            similarity_threshold=0.3
        )
        
        if not chunks:
            logger.info("No relevant context found")
            return {
                "status": "no_context",
                "message": "No relevant emails or documents found"
            }
        
        # Re-ranking (optional - uses LLM)
        if use_reranking and len(chunks) > top_k:
            chunks = await self._rerank_chunks(query, chunks, top_k)
        else:
            chunks = chunks[:top_k]
        
        # Build context string
        context_str = await self._build_context_string(chunks)
        
        # Build response
        response = {
            "status": "success",
            "query": query,
            "chunks_found": len(chunks),
            "context": context_str,
            "sources": [
                {
                    "filename": c.get('metadata', {}).get('filename'),
                    "page": c.get('metadata', {}).get('page'),
                    "email_id": c.get('email_id')
                }
                for c in chunks
            ]
        }
        
        # Cache for next time
        if self.use_cache:
            self.cache.setex(
                cache_key,
                3600,  # 1 hour TTL
                json.dumps(response)
            )
        
        return response
    
    async def _rerank_chunks(
        self,
        query: str,
        chunks: list,
        top_k: int
    ) -> list:
        """
        Re-rank chunks using LLM (optional, more accurate).
        
        For now, use similarity score as proxy.
        Can be enhanced with actual LLM re-ranking later.
        """
        try:
            import openai
            
            chunk_texts = "\n---\n".join([
                f"[{i}] {c['text'][:300]}... (score: {c.get('similarity', 0):.2f})"
                for i, c in enumerate(chunks[:10])
            ])
            
            response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=[{
                    "role": "user",
                    "content": f"""Given this voice query: "{query}"
                    
Which of these chunks are most relevant? Return top {top_k} indices.

{chunk_texts}

Return JSON: {{"top_indices": [0, 2, 5]}}"""
                }],
                max_tokens=100
            )
            
            import json
            result = json.loads(response.choices[0].message.content)
            top_indices = result.get('top_indices', [])
            
            return [chunks[i] for i in top_indices if i < len(chunks)]
        
        except Exception as e:
            logger.warning(f"Re-ranking failed, using similarity scores: {str(e)}")
            return chunks[:top_k]
    
    async def _build_context_string(self, chunks: list) -> str:
        """Build human-readable context string."""
        context_lines = ["📧 **Relevant Email Context:**\n"]
        
        for i, chunk in enumerate(chunks, 1):
            metadata = chunk.get('metadata', {})
            context_lines.append(f"{i}. **{metadata.get('filename')}** (page {metadata.get('page', 'N/A')})")
            context_lines.append(f"   {chunk['text'][:300]}...\n")
        
        return "\n".join(context_lines)
    
    async def get_customer_summary(self, customer_id: UUID) -> Dict[str, Any]:
        """Get brief summary of customer's emails for context."""
        try:
            threads = await self.db.get_customer_all_threads(customer_id)
            emails = await self.db.get_emails_for_customer(customer_id, limit=50)
            
            summary = f"""
📊 **Customer Email Summary:**
- Total threads: {len(threads)}
- Total emails: {len(emails)}
- Recent activity: {threads[0]['subject'] if threads else 'No emails yet'}
"""
            return {
                "status": "success",
                "summary": summary,
                "thread_count": len(threads),
                "email_count": len(emails)
            }
        
        except Exception as e:
            logger.error(f"Error getting customer summary: {str(e)}")
            return {"status": "error", "message": str(e)}


# Singleton
_context_manager = None

def get_voice_agent_context_manager() -> VoiceAgentContextManager:
    """Get or create context manager."""
    global _context_manager
    if _context_manager is None:
        _context_manager = VoiceAgentContextManager()
    return _context_manager
