"""Email Agent Services - Business logic and vector search."""

from .embeddings_vectorstore import EmbeddingsManager, VectorStore, get_vector_store
from .voice_agent_context import VoiceAgentContextManager, get_voice_agent_context_manager

__all__ = [
    "EmbeddingsManager",
    "VectorStore",
    "get_vector_store",
    "VoiceAgentContextManager",
    "get_voice_agent_context_manager",
]
