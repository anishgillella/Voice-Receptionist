"""Post-call metrics calculation and analysis."""

from __future__ import annotations

import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


def calculate_call_duration(messages: list[Dict[str, Any]]) -> int:
    """Calculate approximate call duration from message timestamps.
    
    Args:
        messages: List of message objects from VAPI
        
    Returns:
        Duration in seconds
    """
    if not messages or len(messages) < 2:
        return 0
    
    try:
        # Try to extract timestamps and calculate duration
        # This is approximate based on message structure
        return len(messages) * 5  # Rough estimate: ~5 seconds per message exchange
    except Exception as e:
        logger.warning(f"Failed to calculate call duration: {e}")
        return 0


def analyze_transcript_length(transcript: str) -> Dict[str, int]:
    """Analyze transcript word and character count.
    
    Args:
        transcript: Full transcript text
        
    Returns:
        Dictionary with word_count and char_count
    """
    words = len(transcript.split())
    chars = len(transcript)
    
    return {
        "word_count": words,
        "char_count": chars,
        "estimated_duration_seconds": int(words * 0.5),  # ~2 words per second
    }


def extract_key_phrases(transcript: str) -> Dict[str, list[str]]:
    """Extract key phrases from transcript for analysis.
    
    Args:
        transcript: Full transcript text
        
    Returns:
        Dictionary with extracted phrases by category
    """
    transcript_lower = transcript.lower()
    
    # Define key phrase patterns (simple extraction)
    patterns = {
        "booking_indicators": [
            "book", "schedule", "appointment", "consultation", "call",
            "meeting", "time", "thursday", "wednesday", "monday", "tuesday",
        ],
        "quote_indicators": [
            "quote", "price", "cost", "rate", "premium", "estimate",
        ],
        "objection_indicators": [
            "but", "however", "concern", "problem", "issue", "expensive",
            "too much", "can't afford", "not sure", "maybe later",
        ],
        "positive_indicators": [
            "great", "perfect", "excellent", "love", "happy", "wonderful",
            "exactly what", "sounds good", "interested", "yes",
        ],
    }
    
    results = {}
    for category, phrases in patterns.items():
        found = [p for p in phrases if p in transcript_lower]
        results[category] = found
    
    return results

