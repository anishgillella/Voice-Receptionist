"""Conversation summarization using OpenRouter API with OpenAI client."""

from __future__ import annotations

import logging
from typing import Optional

from openai import OpenAI

from .config import settings

logger = logging.getLogger(__name__)


async def summarize_transcript(transcript: str) -> Optional[str]:
    """Generate a summary of a transcript using OpenRouter API (GPT-5-Nano).
    
    Args:
        transcript: Full conversation transcript
        
    Returns:
        Summary string or None if summarization fails
    """
    if not settings.openrouter_api_key:
        logger.warning("OPENROUTER_API_KEY not configured, skipping summarization")
        return None
    
    if not transcript or len(transcript.strip()) < 50:
        logger.warning("Transcript too short for summarization")
        return None
    
    try:
        # Create OpenAI-compatible client for OpenRouter
        client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=settings.openrouter_api_key
        )
        
        logger.info(f"Generating summary for transcript ({len(transcript)} chars) using {settings.summarization_model}")
        
        # Create chat completion
        response = client.chat.completions.create(
            model=settings.summarization_model,
            messages=[
                {
                    "role": "system",
                    "content": """You are a professional insurance sales analyst. 
Summarize the following call transcript in 2-3 sentences, focusing on:
1. Main topic/insurance need discussed
2. Key outcomes or next steps
3. Customer sentiment (interested/skeptical/not interested)

Be concise and factual."""
                },
                {
                    "role": "user",
                    "content": f"Summarize this call:\n\n{transcript}"
                }
            ],
            temperature=0.3,
            max_tokens=1000,
        )
        
        # Extract summary from response
        summary = response.choices[0].message.content.strip()
        logger.info(f"✅ Generated summary: {len(summary)} chars")
        
        return summary
            
    except Exception as e:
        logger.error(f"Error during summarization: {e}")
        return None
