"""Post-call actions based on detected intents from transcript."""

from __future__ import annotations

import logging
import re
from typing import Dict, List, Optional
from enum import Enum

logger = logging.getLogger(__name__)


class CallIntent(str, Enum):
    """Detected intents from call transcript."""
    EMAIL_REQUEST = "email_request"
    MEETING_REQUEST = "meeting_request"
    CALLBACK_REQUEST = "callback_request"
    INFO_REQUEST = "info_request"
    NOT_INTERESTED = "not_interested"
    FOLLOW_UP = "follow_up"


class CallActionDetector:
    """Detect and plan actions based on call transcript."""
    
    # Keywords for each intent
    INTENT_KEYWORDS = {
        CallIntent.EMAIL_REQUEST: [
            r"send\s+(?:me\s+)?(?:an?\s+)?email",
            r"email\s+(?:me|it)",
            r"(?:send|mail)\s+.*\s+email",
            r"information\s+(?:by|via)\s+email",
            r"through\s+email",
            r"via\s+email",
        ],
        CallIntent.MEETING_REQUEST: [
            r"schedule\s+(?:a\s+)?meeting",
            r"set\s+up\s+(?:a\s+)?meeting",
            r"book\s+(?:a\s+)?(?:call|meeting)",
            r"(?:let'?s\s+)?meet",
            r"calendar\s+invite",
        ],
        CallIntent.CALLBACK_REQUEST: [
            r"call\s+(?:me|back)",
            r"callback",
            r"call\s+me\s+(?:back|later)",
            r"(?:i'?ll\s+)?wait\s+for\s+(?:your\s+)?call",
        ],
        CallIntent.NOT_INTERESTED: [
            r"not\s+interested",
            r"not\s+right\s+now",
            r"not\s+interested\s+right\s+now",
            r"(?:i'm|i\s+am)\s+not\s+interested",
            r"don't\s+(?:call|contact)\s+(?:me|again)",
        ],
    }
    
    def __init__(self):
        """Initialize action detector."""
        self.detected_intents: List[CallIntent] = []
        self.confidence_scores: Dict[CallIntent, float] = {}
    
    def detect_intents(self, transcript: str, parsed_messages: List[Dict]) -> List[CallIntent]:
        """Detect intents from transcript.
        
        Args:
            transcript: Raw transcript string
            parsed_messages: Parsed conversation messages
            
        Returns:
            List of detected intents ordered by confidence
        """
        self.detected_intents = []
        self.confidence_scores = {}
        
        # Convert to lowercase for matching
        transcript_lower = transcript.lower()
        
        # Look through customer messages
        customer_messages = [m for m in parsed_messages if m["role"] == "customer"]
        customer_text = " ".join([m["message"].lower() for m in customer_messages])
        
        # Check for each intent
        for intent, keywords in self.INTENT_KEYWORDS.items():
            matches = 0
            for pattern in keywords:
                if re.search(pattern, customer_text, re.IGNORECASE):
                    matches += 1
            
            if matches > 0:
                # Calculate confidence based on number of matches
                confidence = min(matches / len(keywords), 1.0)
                self.confidence_scores[intent] = confidence
                self.detected_intents.append(intent)
                logger.info(f"Detected intent: {intent.value} (confidence: {confidence:.2f})")
        
        # Sort by confidence
        self.detected_intents.sort(key=lambda x: self.confidence_scores[x], reverse=True)
        
        return self.detected_intents
    
    def get_recommended_actions(self, intents: List[CallIntent]) -> Dict[str, any]:
        """Get recommended actions based on detected intents.
        
        Args:
            intents: List of detected intents
            
        Returns:
            Dict with recommended actions
        """
        actions = {
            "send_email": False,
            "schedule_meeting": False,
            "schedule_callback": False,
            "add_to_followup": False,
            "add_to_dnc": False,  # Do Not Call list
            "reason": ""
        }
        
        if CallIntent.EMAIL_REQUEST in intents:
            actions["send_email"] = True
            actions["reason"] = "Customer requested email with information"
        
        if CallIntent.MEETING_REQUEST in intents:
            actions["schedule_meeting"] = True
            actions["reason"] = "Customer requested meeting scheduling"
        
        if CallIntent.CALLBACK_REQUEST in intents:
            actions["schedule_callback"] = True
            actions["reason"] = "Customer requested callback"
        
        if CallIntent.NOT_INTERESTED in intents and len(intents) == 1:
            actions["add_to_dnc"] = True
            actions["reason"] = "Customer explicitly not interested"
        elif any(i in intents for i in [CallIntent.EMAIL_REQUEST, CallIntent.FOLLOW_UP]):
            actions["add_to_followup"] = True
            actions["reason"] = "Customer willing to receive follow-up"
        
        return actions


def extract_email_addresses(transcript: str, parsed_messages: List[Dict]) -> Optional[str]:
    """Extract email address mentioned in transcript.
    
    Args:
        transcript: Raw transcript
        parsed_messages: Parsed messages
        
    Returns:
        Email address if found, None otherwise
    """
    # Pattern for email address
    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    
    matches = re.findall(email_pattern, transcript)
    if matches:
        # Return the first email found
        return matches[0]
    
    return None


def extract_phone_numbers(transcript: str, parsed_messages: List[Dict]) -> List[str]:
    """Extract phone numbers mentioned in transcript.
    
    Args:
        transcript: Raw transcript
        parsed_messages: Parsed messages
        
    Returns:
        List of phone numbers found
    """
    # Pattern for phone numbers
    phone_pattern = r'\b(?:\+?1[-.\s]?)?\(?(?:\d{3})\)?[-.\s]?(?:\d{3})[-.\s]?(?:\d{4})\b'
    
    matches = re.findall(phone_pattern, transcript)
    return matches


# Example usage
if __name__ == "__main__":
    # Test transcript
    test_transcript = """
    AI: Hi, this is Jennifer. Can I help you?
    User: Yes, send me an email with more information.
    AI: Of course, I'll email you details.
    User: Great, thanks.
    """
    
    test_parsed = [
        {"role": "agent", "message": "Hi, this is Jennifer. Can I help you?"},
        {"role": "customer", "message": "Yes, send me an email with more information."},
        {"role": "agent", "message": "Of course, I'll email you details."},
        {"role": "customer", "message": "Great, thanks."},
    ]
    
    detector = CallActionDetector()
    intents = detector.detect_intents(test_transcript, test_parsed)
    actions = detector.get_recommended_actions(intents)
    
    print(f"Detected Intents: {[i.value for i in intents]}")
    print(f"Recommended Actions: {actions}")
    print(f"Email: {extract_email_addresses(test_transcript, test_parsed)}")
