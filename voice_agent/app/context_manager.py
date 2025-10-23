"""Context manager for preparing agent prompt with customer history."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
from uuid import UUID

from .db import get_table_name, get_db
from .embeddings import generate_embedding
from .models import Customer

logger = logging.getLogger(__name__)

# Token estimation (rough, for budgeting)
TOKENS_PER_WORD = 0.75
MAX_CONTEXT_TOKENS = 3000  # Budget for past context


class ContextManager:
    """Manages customer context for agent prompts."""

    def __init__(self):
        """Initialize context manager."""
        self.db = get_db()

    def estimate_tokens(self, text: str) -> int:
        """Estimate token count for text.

        Args:
            text: Text to estimate

        Returns:
            Approximate token count
        """
        words = len(text.split())
        return int(words * TOKENS_PER_WORD)

    def build_customer_profile_context(self, customer: Customer) -> str:
        """Build customer profile context string.

        Args:
            customer: Customer object

        Returns:
            Formatted customer profile context
        """
        profile = f"""CUSTOMER PROFILE:
- First Name: {customer.first_name or 'N/A'}
- Last Name: {customer.last_name or 'N/A'}
- Company: {customer.company_name}
- Email: {customer.email or 'N/A'}
- Phone: {customer.phone_number}
- Industry: {customer.industry or 'N/A'}
- Location: {customer.location or 'N/A'}
"""
        return profile

    def get_relevant_past_conversations(
        self,
        customer_id: UUID,
        current_topic: str,
        top_k: int = 3,
    ) -> List[Dict[str, Any]]:
        """Get past conversations relevant to current topic using semantic search.

        Args:
            customer_id: Customer UUID
            current_topic: Current call topic/context
            top_k: Number of similar conversations to return

        Returns:
            List of relevant past conversation dictionaries
        """
        try:
            # Get all past conversations for this customer
            query = f"""
                SELECT id, call_id, transcript, summary, created_at
                FROM {get_table_name('conversations')}
                WHERE customer_id = %s
                ORDER BY created_at DESC
                LIMIT 20
            """
            results = self.db.execute(query, (str(customer_id),))

            if not results:
                logger.info(f"No past conversations found for customer {customer_id}")
                return []

            conversations = [dict(r) for r in results]

            # If only 1-2 conversations, return them all
            if len(conversations) <= top_k:
                return conversations

            # Generate embedding for current topic
            try:
                topic_embedding = generate_embedding(current_topic)
            except Exception as e:
                logger.warning(f"Failed to generate topic embedding: {e}")
                # Fallback: return most recent conversations
                return conversations[:top_k]

            # Get embeddings for each conversation (from database)
            embeddings_data = {}
            for conv in conversations:
                emb_query = f"""
                    SELECT embedding FROM {get_table_name('embeddings')}
                    WHERE call_id = %s AND embedding_type = 'full'
                    LIMIT 1
                """
                emb_result = self.db.execute(emb_query, (conv["call_id"],))
                if emb_result:
                    embeddings_data[conv["call_id"]] = emb_result[0]["embedding"]

            if not embeddings_data:
                # No embeddings yet, return most recent
                return conversations[:top_k]

            # Calculate similarity scores
            import numpy as np

            scores = []
            for conv in conversations:
                if conv["call_id"] in embeddings_data:
                    stored_embedding = embeddings_data[conv["call_id"]]
                    # Cosine similarity
                    similarity = np.dot(topic_embedding, stored_embedding) / (
                        np.linalg.norm(topic_embedding) * np.linalg.norm(stored_embedding)
                    )
                    scores.append((conv, similarity))
                else:
                    # No embedding, low score
                    scores.append((conv, 0.0))

            # Sort by similarity and return top_k
            scores.sort(key=lambda x: x[1], reverse=True)
            relevant = [conv for conv, score in scores[:top_k]]

            logger.info(
                f"Found {len(relevant)} relevant conversations for customer {customer_id}"
            )
            return relevant

        except Exception as e:
            logger.error(f"Error retrieving relevant conversations: {e}")
            return []

    def build_conversation_summary_context(
        self, conversations: List[Dict[str, Any]], max_tokens: int = 2000
    ) -> str:
        """Build context from past conversations with token optimization.

        Args:
            conversations: List of conversation dictionaries
            max_tokens: Maximum tokens to use for conversation context

        Returns:
            Formatted conversation context
        """
        if not conversations:
            return ""

        context = "PAST CONVERSATIONS:\n"
        tokens_used = 0

        for i, conv in enumerate(conversations, 1):
            # Use summary if available, otherwise use transcript excerpt
            content = conv.get("summary") or conv.get("transcript", "")[:500]

            # Estimate tokens for this content
            content_tokens = self.estimate_tokens(content)

            # Check if adding this would exceed budget
            if tokens_used + content_tokens > max_tokens:
                logger.info(f"Token budget reached, stopping at conversation {i-1}")
                break

            # Add conversation
            call_date = conv.get("created_at", "Unknown date")
            context += f"\n[Call on {call_date}]:\n{content}\n"
            tokens_used += content_tokens

        context += f"\n(Used ~{tokens_used} tokens for conversation history)"
        return context

    def build_agent_context(
        self,
        customer: Customer,
        current_topic: str = "Insurance inquiry",
        include_conversations: bool = True,
    ) -> Dict[str, Any]:
        """Build complete agent context with customer profile and history.

        Args:
            customer: Customer object
            current_topic: Current call topic for semantic search
            include_conversations: Whether to include past conversations

        Returns:
            Dictionary with:
            - profile_context: Customer profile string
            - conversation_context: Past conversations string
            - full_context: Combined context
            - token_estimate: Approximate token count
        """
        # Build profile context
        profile_context = self.build_customer_profile_context(customer)

        # Get relevant past conversations if enabled
        conversation_context = ""
        if include_conversations:
            relevant_convs = self.get_relevant_past_conversations(
                customer.id,
                current_topic,
                top_k=3,
            )
            conversation_context = self.build_conversation_summary_context(
                relevant_convs,
                max_tokens=MAX_CONTEXT_TOKENS,
            )

        # Combine
        full_context = profile_context
        if conversation_context:
            full_context += "\n" + conversation_context

        # Estimate total tokens
        token_estimate = self.estimate_tokens(full_context)

        result = {
            "profile_context": profile_context,
            "conversation_context": conversation_context,
            "full_context": full_context,
            "token_estimate": token_estimate,
        }

        logger.info(
            f"Built context for customer {customer.id}: ~{token_estimate} tokens"
        )

        return result

    def inject_context_to_system_prompt(
        self, base_prompt: str, context: Dict[str, Any]
    ) -> str:
        """Inject customer context into system prompt.

        Args:
            base_prompt: Base system prompt
            context: Context dictionary from build_agent_context

        Returns:
            Enhanced system prompt with context
        """
        enhanced_prompt = f"""{base_prompt}

---
{context['full_context']}
---

Use the above customer information and history to personalize your conversation.
Reference past interactions when relevant."""

        return enhanced_prompt
