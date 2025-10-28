"""LLM-based call quality evaluation."""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, Optional
from uuid import UUID

from openai import OpenAI

from ..core.config import settings
from ..core.models import CallJudgment, CallMetrics
from .logfire_tracing import trace_llm_call, log_call_judgment

logger = logging.getLogger(__name__)

JUDGE_SYSTEM_PROMPT = """You are an expert insurance call quality analyst. Your job is to evaluate call transcripts and extract key metrics.

SCORING RULES:

1. **First Call Resolution (FCR)**:
   - TRUE if customer: booked consultation, requested quote, or agreed to specific follow-up
   - FALSE if customer: is still deciding, hung up, or rejected proposal

2. **Intent Detection**:
   - Identify customer's main need: quote_inquiry, policy_questions, renewal, new_business, complaint, other

3. **Call Quality Score (0-1)**:
   - 1.0 = Perfect (strong opening, discovered needs, handled objections smoothly, closed with clear action)
   - 0.8 = Excellent (mostly smooth, minor gaps)
   - 0.6 = Good (basic requirements met, some issues)
   - 0.4 = Fair (scattered engagement, weak close)
   - 0.2 = Poor (minimal discovery, no engagement)
   - 0.0 = Failed (agent error or hang-up)

4. **Customer Sentiment**:
   - very_positive: Enthusiastic, agreed readily
   - positive: Engaged, interested
   - neutral: Polite but non-committal
   - negative: Skeptical, resistant
   - very_negative: Hostile, hung up

5. **Script Compliance (0-1)**:
   - Did agent follow system prompt guidelines?
   - Was opening warm? Did they discover needs? Did they handle objections?

EXTRACT AND RETURN ONLY valid JSON with NO markdown:

{
  "frc_achieved": boolean,
  "frc_type": "quote" | "consultation_booked" | "follow_up_requested" | "none",
  "intent_detected": "quote_inquiry" | "policy_questions" | "renewal" | "new_business" | "complaint" | "other",
  "intent_accuracy_score": 0.0-1.0,
  "call_quality_score": 0.0-1.0,
  "customer_sentiment": "very_positive" | "positive" | "neutral" | "negative" | "very_negative",
  "script_compliance_score": 0.0-1.0,
  "key_objections": ["objection1", "objection2"],
  "agent_responses_to_objections": ["response1", "response2"],
  "next_steps_agreed": "string describing next steps",
  "judge_reasoning": "string explaining the scores",
  "strengths": ["strength1", "strength2"],
  "improvements": ["improvement1", "improvement2"]
}
"""


@trace_llm_call("judge")
async def judge_call(
    transcript: str,
    call_id: str,
    customer_id: UUID,
) -> Optional[CallJudgment]:
    """Evaluate a call transcript using GPT-5-nano and extract metrics.
    
    Args:
        transcript: Full call transcript text
        call_id: VAPI call ID
        customer_id: Customer UUID
        
    Returns:
        CallJudgment object with extracted metrics or None if failed
    """
    if not transcript or len(transcript.strip()) < 50:
        logger.warning(f"Transcript too short for call {call_id}")
        return None
    
    try:
        logger.info(f"Starting LLM judgment for call {call_id} using GPT-5-nano")
        
        # Create OpenAI client for OpenRouter (GPT-5-nano endpoint)
        client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=settings.openrouter_api_key
        )
        
        # Call GPT-5-nano for judgment
        response = client.chat.completions.create(
            model="openai/gpt-5-nano",
            messages=[
                {
                    "role": "system",
                    "content": JUDGE_SYSTEM_PROMPT,
                },
                {
                    "role": "user",
                    "content": f"Analyze this call transcript and extract metrics:\n\n{transcript}",
                }
            ],
            temperature=0.3,  # Factual extraction
            max_tokens=2000,
        )
        
        # Extract JSON from response
        response_text = response.choices[0].message.content.strip()
        logger.debug(f"Judge response: {response_text[:200]}...")
        
        # Parse JSON response
        try:
            judgment_data = json.loads(response_text)
        except json.JSONDecodeError:
            logger.error(f"Failed to parse judge response as JSON for call {call_id}")
            return None
        
        # Extract call duration from transcript (approximate word count)
        call_duration_seconds = len(transcript.split()) * 0.5  # Rough estimate
        
        # Create CallMetrics from extracted data
        metrics = CallMetrics(
            call_id=call_id,
            customer_id=customer_id,
            frc_achieved=judgment_data.get("frc_achieved", False),
            frc_type=judgment_data.get("frc_type"),
            intent_detected=judgment_data.get("intent_detected", "unknown"),
            intent_accuracy_score=float(judgment_data.get("intent_accuracy_score", 0.0)),
            call_quality_score=float(judgment_data.get("call_quality_score", 0.0)),
            customer_sentiment=judgment_data.get("customer_sentiment", "neutral"),
            script_compliance_score=float(judgment_data.get("script_compliance_score", 0.0)),
            key_objections=judgment_data.get("key_objections", []),
            agent_responses_to_objections=judgment_data.get("agent_responses_to_objections", []),
            next_steps_agreed=judgment_data.get("next_steps_agreed"),
            call_duration_seconds=int(call_duration_seconds),
        )
        
        # Create CallJudgment
        judgment = CallJudgment(
            call_id=call_id,
            customer_id=customer_id,
            metrics=metrics,
            judge_reasoning=judgment_data.get("judge_reasoning", ""),
            judge_model="gpt-5-nano",
            strengths=judgment_data.get("strengths", []),
            improvements=judgment_data.get("improvements", []),
        )
        
        logger.info(
            f"✅ Judgment completed for call {call_id}: "
            f"FCR={metrics.frc_achieved}, Quality={metrics.call_quality_score:.2f}"
        )
        
        # Log to Logfire
        log_call_judgment(
            call_id,
            {
                "frc_achieved": metrics.frc_achieved,
                "call_quality_score": metrics.call_quality_score,
                "intent_detected": metrics.intent_detected,
                "customer_sentiment": metrics.customer_sentiment,
            }
        )
        
        return judgment
        
    except Exception as e:
        logger.error(f"Error during call judgment for {call_id}: {e}")
        return None

