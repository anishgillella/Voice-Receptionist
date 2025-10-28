"""Analyze email replies with full customer context and conversation history."""

from __future__ import annotations

import logging
import json
from typing import List, Optional, TYPE_CHECKING
from enum import Enum
from pydantic import BaseModel, Field
from datetime import datetime

if TYPE_CHECKING:
    from ..core.config import Settings

logger = logging.getLogger(__name__)


class EmailReplyActionType(str, Enum):
    """Types of actions to take based on email reply."""
    SEND_RESPONSE = "send_response"
    SCHEDULE_CALLBACK = "schedule_callback"
    SEND_PROPOSAL = "send_proposal"
    REQUEST_PAYMENT = "request_payment"
    ADD_TO_FOLLOWUP = "add_to_followup"
    ESCALATE_TO_SALES = "escalate_to_sales"
    NO_ACTION = "no_action"


class EmailReplyAction(BaseModel):
    """Action to take based on email reply."""
    type: EmailReplyActionType = Field(..., description="Type of action")
    reason: str = Field(..., description="Why this action is recommended")
    priority: int = Field(default=1, description="Priority (1=highest)")
    suggested_response: Optional[str] = Field(None, description="Suggested response template to use")
    metadata: Optional[dict] = Field(None, description="Additional metadata")


class EmailReplyAnalysis(BaseModel):
    """Analysis of an email reply with recommended actions."""
    sentiment: str = Field(..., description="Email sentiment (positive/neutral/negative)")
    engagement_level: str = Field(default="medium", description="Engagement level (high/medium/low)")
    key_topics: List[str] = Field(default=[], description="Topics mentioned in reply")
    customer_intent: str = Field(..., description="What the customer is trying to accomplish")
    interest_change: str = Field(default="stable", description="Interest level change (increased/decreased/stable)")
    actions: List[EmailReplyAction] = Field(..., description="Recommended actions")
    suggested_next_steps: str = Field(..., description="What to do next")


class EmailReplyAnalyzer:
    """Analyze email replies with full context using LLM."""
    
    ANALYSIS_PROMPT = """You are an expert at analyzing customer email replies in a sales context.

Analyze the following email reply and provide a comprehensive analysis including recommended actions.

CUSTOMER HISTORY:
- Previous Call: {previous_call_summary}
- Past Emails: {past_emails}
- Customer Profile: {customer_profile}

CURRENT EMAIL REPLY:
{email_reply}

Based on this complete context, provide:
1. Sentiment analysis (positive/neutral/negative)
2. Current engagement level (high/medium/low)
3. Key topics mentioned
4. Customer's intent (what are they trying to accomplish?)
5. Change in interest level compared to the initial call
6. Recommended actions with priorities
7. Suggested next steps

Return as JSON matching this structure:
{{
    "sentiment": "positive|neutral|negative",
    "engagement_level": "high|medium|low",
    "key_topics": ["topic1", "topic2"],
    "customer_intent": "What the customer wants",
    "interest_change": "increased|decreased|stable",
    "actions": [
        {{
            "type": "ACTION_TYPE",
            "reason": "Why this action",
            "priority": 1,
            "suggested_response": "Draft response template or null",
            "metadata": {{"key": "value"}}
        }}
    ],
    "suggested_next_steps": "What to do next"
}}

AVAILABLE ACTIONS:
- send_response: Send a thoughtful response to the customer's email
- schedule_callback: Customer wants a phone call/meeting
- send_proposal: Customer is interested in a proposal or quote
- request_payment: Customer is ready to purchase
- add_to_followup: Customer needs follow-up but not immediate
- escalate_to_sales: Customer should speak with sales team
- no_action: No immediate action needed

Respond ONLY with valid JSON, no other text."""

    def __init__(self, settings: Optional[Settings] = None):
        """Initialize analyzer with settings."""
        self.settings = settings
        self._llm_client = None
    
    @property
    def llm_client(self):
        """Lazy load LLM client."""
        if self._llm_client is None:
            from ..llm.llm_providers import get_llm_provider
            provider_name = self.settings.llm_provider if self.settings else None
            self._llm_client = get_llm_provider(provider_name)
        return self._llm_client
    
    async def analyze(
        self,
        email_reply: str,
        previous_call_summary: Optional[str] = None,
        past_emails: Optional[List[str]] = None,
        customer_profile: Optional[dict] = None,
    ) -> EmailReplyAnalysis:
        """Analyze email reply with full context.
        
        Args:
            email_reply: The customer's email reply
            previous_call_summary: Summary from the initial voice call
            past_emails: List of previous email exchanges
            customer_profile: Customer information dict
            
        Returns:
            EmailReplyAnalysis with recommended actions
        """
        try:
            # Format context
            call_summary = previous_call_summary or "No previous call context"
            email_history = "\n---\n".join(past_emails) if past_emails else "No previous emails"
            profile = json.dumps(customer_profile or {}, indent=2)
            
            # Prepare prompt
            prompt = self.ANALYSIS_PROMPT.format(
                previous_call_summary=call_summary,
                past_emails=email_history,
                customer_profile=profile,
                email_reply=email_reply
            )
            
            logger.info(f"Analyzing email reply ({len(email_reply)} chars) with context...")
            
            # Call LLM
            import asyncio
            response = await asyncio.to_thread(
                self.llm_client.generate_response,
                system_prompt="You are an expert customer engagement analyst. Extract structured insights from email replies.",
                user_message=prompt,
                temperature=0.7,
                max_tokens=1500,
                model="openai/gpt-4o-mini"
            )
            
            if not response:
                logger.warning("Empty response from LLM")
                return self._default_analysis()
            
            # Parse JSON response
            try:
                analysis_json = json.loads(response)
            except json.JSONDecodeError:
                import re
                json_match = re.search(r'\{.*\}', response, re.DOTALL)
                if json_match:
                    analysis_json = json.loads(json_match.group())
                else:
                    logger.warning("Failed to parse LLM response as JSON")
                    return self._default_analysis()
            
            # Convert to Pydantic model
            result = EmailReplyAnalysis(
                sentiment=analysis_json.get("sentiment", "neutral"),
                engagement_level=analysis_json.get("engagement_level", "medium"),
                key_topics=analysis_json.get("key_topics", []),
                customer_intent=analysis_json.get("customer_intent", ""),
                interest_change=analysis_json.get("interest_change", "stable"),
                suggested_next_steps=analysis_json.get("suggested_next_steps", ""),
                actions=[
                    EmailReplyAction(
                        type=EmailReplyActionType(a["type"]),
                        reason=a.get("reason", ""),
                        priority=a.get("priority", 1),
                        suggested_response=a.get("suggested_response"),
                        metadata=a.get("metadata")
                    )
                    for a in analysis_json.get("actions", [])
                ]
            )
            
            logger.info(f"✅ Email reply analyzed: {len(result.actions)} actions detected")
            return result
            
        except Exception as e:
            logger.error(f"Error analyzing email reply: {e}")
            return self._default_analysis()
    
    def _default_analysis(self) -> EmailReplyAnalysis:
        """Return default analysis if LLM fails."""
        return EmailReplyAnalysis(
            sentiment="neutral",
            engagement_level="medium",
            customer_intent="Unable to determine",
            actions=[EmailReplyAction(
                type=EmailReplyActionType.NO_ACTION,
                reason="Unable to analyze reply"
            )],
            suggested_next_steps="Review reply manually"
        )
