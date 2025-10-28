"""Unified call analysis using LLM to extract summary and actions together."""

from __future__ import annotations

import logging
import json
from typing import List, Optional, TYPE_CHECKING
from enum import Enum
from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from ..core.config import Settings

logger = logging.getLogger(__name__)


class ActionType(str, Enum):
    """Types of actions to take after a call."""
    SEND_EMAIL = "send_email"
    SCHEDULE_MEETING = "schedule_meeting"
    SCHEDULE_CALLBACK = "schedule_callback"
    ADD_TO_FOLLOWUP = "add_to_followup"
    ADD_TO_DNC = "add_to_dnc"  # Do Not Call
    SEND_PROPOSAL = "send_proposal"
    REQUEST_PAYMENT = "request_payment"
    NO_ACTION = "no_action"


class Action(BaseModel):
    """A single action to take after the call."""
    type: ActionType = Field(..., description="Type of action to take")
    reason: str = Field(..., description="Why this action should be taken")
    priority: int = Field(default=1, description="Priority level (1=highest, 5=lowest)")
    metadata: Optional[dict] = Field(default=None, description="Additional action metadata")


class CallAnalysisResult(BaseModel):
    """Complete analysis of a call including summary and recommended actions."""
    summary: str = Field(..., description="AI-generated call summary")
    sentiment: str = Field(..., description="Overall customer sentiment (positive/neutral/negative)")
    actions: List[Action] = Field(..., description="Recommended actions after call")
    key_topics: List[str] = Field(default=[], description="Main topics discussed")
    customer_interest_level: str = Field(default="medium", description="Interest level (high/medium/low)")
    next_steps: str = Field(default="", description="Recommended next steps")


class LLMCallAnalyzer:
    """Analyze calls using LLM to extract summary and actions."""
    
    ANALYSIS_PROMPT = """You are an expert at analyzing sales call transcripts. 
    
Your job is to analyze the following call transcript and extract:
1. A concise summary of the conversation
2. Customer sentiment (positive, neutral, or negative)
3. Recommended actions based on customer behavior
4. Key topics discussed
5. Customer's interest level
6. Next steps

Analyze what the CUSTOMER said (not the agent), and determine what actions should be taken.

IMPORTANT: Return your analysis as valid JSON matching this structure:
{{
    "summary": "Brief summary of the call",
    "sentiment": "positive|neutral|negative",
    "actions": [
        {{
            "type": "ACTION_TYPE",
            "reason": "Why this action",
            "priority": 1,
            "metadata": {{"key": "value"}}
        }}
    ],
    "key_topics": ["topic1", "topic2"],
    "customer_interest_level": "high|medium|low",
    "next_steps": "What to do next"
}}

AVAILABLE ACTIONS:
- send_email: Customer asked for information via email
- schedule_meeting: Customer wants to meet or discuss further
- schedule_callback: Customer asked to be called back later
- add_to_followup: Customer is interested but needs follow-up
- add_to_dnc: Customer explicitly doesn't want contact (Do Not Call)
- send_proposal: Customer asked for a proposal or quote
- request_payment: Customer is ready to purchase
- no_action: No specific action needed

TRANSCRIPT:
{transcript}

Respond ONLY with valid JSON, no other text."""

    def __init__(self, settings: Optional[Settings] = None):
        """Initialize analyzer with LLM settings.
        
        Args:
            settings: Voice agent settings with LLM config
        """
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
    
    async def analyze(self, transcript: str) -> CallAnalysisResult:
        """Analyze call transcript and extract summary + actions.
        
        Args:
            transcript: Raw call transcript
            
        Returns:
            CallAnalysisResult with summary and recommended actions
        """
        try:
            # Prepare prompt
            prompt = self.ANALYSIS_PROMPT.format(transcript=transcript)
            
            logger.info(f"Analyzing call transcript ({len(transcript)} chars)...")
            
            # Call LLM synchronously (wrap in thread pool to avoid blocking)
            import asyncio
            response = await asyncio.to_thread(
                self.llm_client.generate_response,
                system_prompt="You are an expert call analyst. Extract structured information from the transcript.",
                user_message=prompt,
                temperature=0.7,
                max_tokens=1000,
                model="openai/gpt-4o-mini"
            )
            
            if not response:
                logger.warning("Empty response from LLM")
                return self._default_analysis(transcript)
            
            # Parse JSON response
            try:
                analysis_json = json.loads(response)
            except json.JSONDecodeError:
                # Try to extract JSON from response
                import re
                json_match = re.search(r'\{.*\}', response, re.DOTALL)
                if json_match:
                    analysis_json = json.loads(json_match.group())
                else:
                    logger.warning("Failed to parse LLM response as JSON")
                    return self._default_analysis(transcript)
            
            # Convert to Pydantic model
            result = CallAnalysisResult(
                summary=analysis_json.get("summary", ""),
                sentiment=analysis_json.get("sentiment", "neutral"),
                key_topics=analysis_json.get("key_topics", []),
                customer_interest_level=analysis_json.get("customer_interest_level", "medium"),
                next_steps=analysis_json.get("next_steps", ""),
                actions=[
                    Action(
                        type=ActionType(a["type"]),
                        reason=a.get("reason", ""),
                        priority=a.get("priority", 1),
                        metadata=a.get("metadata")
                    )
                    for a in analysis_json.get("actions", [])
                ]
            )
            
            logger.info(f"✅ Call analyzed: {len(result.actions)} actions detected")
            return result
            
        except Exception as e:
            logger.error(f"Error analyzing call: {e}")
            return self._default_analysis(transcript)
    
    def _default_analysis(self, transcript: str) -> CallAnalysisResult:
        """Return default analysis if LLM fails."""
        return CallAnalysisResult(
            summary="Call analysis unavailable",
            sentiment="neutral",
            actions=[Action(
                type=ActionType.NO_ACTION,
                reason="Unable to analyze transcript"
            )],
            key_topics=[],
            customer_interest_level="medium",
            next_steps=""
        )
