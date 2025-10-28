"""FastAPI application for initiating Vapi calls and handling webhooks."""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from ..core.config import Settings, get_settings
from ..services.vapi_client import initiate_outbound_call
from ..core.db import (
    close_db,
    get_or_create_customer,
    store_conversation,
    store_embedding,
    store_customer_memory,
    get_db,
    update_conversation_summary,
    get_table_name,
    store_call_metrics,
    store_call_judgment,
    get_customer_by_email,
    store_email_reply,
    get_customer_emails,
    store_email_analysis,
    store_auto_response,
    get_customer_conversations,
)
from ..llm.embeddings import generate_embedding
import httpx
from ..llm.summarization import summarize_transcript
from ..evaluation import judge_call, setup_logfire
from ..evaluation.logfire_tracing import log_call_metrics
from ..services.embedding_cache import get_redis_client, close_redis, get_cache_stats
from ..services.modal_client import get_modal_client, close_modal_client
from ..llm.call_analyzer import LLMCallAnalyzer
from ..services.email_sender import EmailSender
from ..llm.email_reply_analyzer import EmailReplyAnalyzer
from ..services.email_response_templates import EmailResponseTemplates, ResponseTemplate

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

app = FastAPI(title="Voice Agent", version="0.1.0")

# Track calls that need transcript processing
_pending_calls: Dict[str, Dict[str, Any]] = {}
_vapi_base_url = "https://api.vapi.ai"


class CallRequest(BaseModel):
    """Payload for making an outbound call."""

    phone_number: str = Field(..., description="E.164 formatted phone number, e.g. +15551234567")
    metadata: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Optional metadata to attach to the Vapi call",
    )


class InsuranceProspectCallRequest(BaseModel):
    """Payload for making an outbound call to an insurance prospect."""
    
    phone_number: str = Field(..., description="E.164 formatted phone number, e.g. +15551234567")
    prospect_name: str = Field(..., description="Prospect's full name")
    company_name: str = Field(..., description="Company/business name")
    industry: Optional[str] = Field(default=None, description="Industry/business type")
    lead_id: Optional[str] = Field(default=None, description="Internal lead ID")
    estimated_employees: Optional[int] = Field(default=None, description="Estimated number of employees")
    location: Optional[str] = Field(default=None, description="Business location/state")


@app.get("/health")
async def health() -> Dict[str, Any]:
    """Health check endpoint with service status."""
    redis_client = get_redis_client()
    modal_client = get_modal_client()
    
    # Check Redis
    redis_status = "disabled"
    if redis_client:
        try:
            redis_client.ping()
            redis_status = "connected"
        except Exception as e:
            redis_status = f"error: {str(e)[:50]}"
    
    # Check Modal
    modal_status = "disabled"
    if modal_client and modal_client.available:
        modal_status = "configured"
    
    return {
        "status": "ok",
        "services": {
            "redis": redis_status,
            "modal": modal_status,
        },
        "cache_stats": get_cache_stats() if redis_client else {"status": "disabled"},
    }


@app.get("/cache/stats")
async def cache_stats() -> Dict[str, Any]:
    """Get embedding cache statistics."""
    return get_cache_stats()


@app.post("/cache/clear")
async def clear_cache() -> Dict[str, str]:
    """Clear embedding cache (admin endpoint)."""
    from .embedding_cache import clear_embedding_cache
    
    success = clear_embedding_cache()
    return {
        "status": "success" if success else "failed",
        "message": "Cache cleared" if success else "Failed to clear cache",
    }


@app.post("/process-calls")
async def process_pending_calls() -> Dict[str, Any]:
    """Process all pending calls and generate transcripts/embeddings."""
    settings = get_settings()
    processed = []
    failed = []
    
    logger.info(f"Processing {len(_pending_calls)} pending calls")
    
    calls_to_process = list(_pending_calls.items())
    for call_id, call_info in calls_to_process:
        try:
            await _process_call_transcript(call_id, call_info["customer_phone"], settings)
            processed.append(call_id)
        except Exception as e:
            logger.error(f"Failed to process {call_id}: {e}")
            failed.append({"call_id": call_id, "error": str(e)})
    
    return {
        "status": "completed",
        "processed": len(processed),
        "failed": len(failed),
        "processed_calls": processed,
        "failed_calls": failed
    }


@app.post("/process-call/{call_id}")
async def process_specific_call(call_id: str) -> Dict[str, Any]:
    """Process a specific call by call_id."""
    settings = get_settings()
    customer_phone = "+14698674545"  # Default customer
    
    print(f"Processing specific call: {call_id}")
    logger.info(f"Processing specific call: {call_id}")
    
    try:
        await _process_call_transcript(call_id, customer_phone, settings)
        return {
            "status": "success",
            "call_id": call_id,
            "message": "Call processed successfully"
        }
    except Exception as e:
        logger.error(f"Failed to process call {call_id}: {e}")
        return {
            "status": "failed",
            "call_id": call_id,
            "error": str(e)
        }


@app.post("/fetch-recent-transcripts")
async def fetch_recent_transcripts() -> Dict[str, Any]:
    """Fetch transcripts from VAPI for recent calls and process them."""
    settings = get_settings()
    processed = []
    failed = []
    
    logger.info("Fetching recent calls from VAPI")
    
    try:
        # Get recent calls from VAPI
        async with httpx.AsyncClient(timeout=30.0) as client:
            headers = {"Authorization": f"Bearer {settings.vapi_api_key}"}
            response = await client.get(f"{_vapi_base_url}/call?limit=10", headers=headers)
            response.raise_for_status()
        
        calls = response.json() if isinstance(response.json(), list) else response.json().get("calls", [])
        logger.info(f"Found {len(calls)} recent calls from VAPI")
        
        # Get customer phone for context
        db = get_db()
        customer = db.execute(
            f"SELECT phone_number FROM brokerage.customers LIMIT 1",
            ()
        )
        customer_phone = customer[0]['phone_number'] if customer else settings.customer_phone_number
        
        for call in calls[:5]:  # Process last 5 calls
            if isinstance(call, dict):
                call_id = call.get("id")
                
                # Skip if already processed
                existing = db.execute(
                    f"SELECT id FROM brokerage.conversations WHERE call_id = %s",
                    (call_id,)
                )
                
                if not existing:
                    try:
                        logger.info(f"Processing call from VAPI: {call_id}")
                        await _process_call_transcript(call_id, customer_phone, settings)
                        processed.append(call_id)
                    except Exception as e:
                        logger.error(f"Failed to process {call_id}: {e}")
                        failed.append({"call_id": call_id, "error": str(e)})
    
    except Exception as e:
        logger.error(f"Error fetching calls from VAPI: {e}")
        failed.append({"error": str(e)})
    
    return {
        "status": "completed",
        "processed": len(processed),
        "failed": len(failed),
        "processed_calls": processed,
        "failed_calls": failed
    }


@app.post("/call")
async def trigger_call(
    payload: CallRequest,
    settings: Settings = Depends(get_settings),
) -> JSONResponse:
    """Trigger an outbound Vapi call to the provided number."""

    # Trigger call via the Vapi API
    try:
        response = await initiate_outbound_call(
            payload.phone_number,
            metadata=payload.metadata,
        )
    except Exception as exc:  # pragma: no cover - propagated to caller
        logger.exception("Failed to initiate Vapi call")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc

    logger.info("Queued call via Vapi", extra={"response": response})

    return JSONResponse(content=response, status_code=status.HTTP_202_ACCEPTED)


@app.post("/call/insurance-prospect")
async def trigger_insurance_prospect_call(
    payload: InsuranceProspectCallRequest,
    settings: Settings = Depends(get_settings),
) -> JSONResponse:
    """Trigger an outbound call to an insurance prospect.
    
    This endpoint initiates a call with insurance prospect information that the
    agent will use to personalize the conversation.
    """
    
    # Build prospect metadata
    prospect_info = {
        "prospect_name": payload.prospect_name,
        "company_name": payload.company_name,
        "call_type": "insurance_prospect",
    }
    
    if payload.industry:
        prospect_info["industry"] = payload.industry
    if payload.lead_id:
        prospect_info["lead_id"] = payload.lead_id
    if payload.estimated_employees:
        prospect_info["estimated_employees"] = payload.estimated_employees
    if payload.location:
        prospect_info["location"] = payload.location
    
    # Trigger call via the Vapi API
    try:
        response = await initiate_outbound_call(
            payload.phone_number,
            prospect_info=prospect_info,
        )
    except Exception as exc:  # pragma: no cover - propagated to caller
        logger.exception("Failed to initiate insurance prospect call")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc
    
    logger.info(
        "Queued insurance prospect call",
        extra={
            "prospect": payload.prospect_name,
            "company": payload.company_name,
            "phone": payload.phone_number,
            "response": response,
        },
    )
    
    return JSONResponse(content=response, status_code=status.HTTP_202_ACCEPTED)


async def _generate_embeddings(call_id: str, transcript: str) -> None:
    """Async job to generate and store embeddings for a transcript.
    
    Args:
        call_id: VAPI call ID
        transcript: Full conversation transcript
    """
    try:
        logger.info(f"Starting embedding generation for call {call_id}")
        
        # Generate embedding for full transcript
        embedding = generate_embedding(transcript)
        logger.info(f"Generated embedding for call {call_id} (1024 dims)")
        
        # Store embedding in database
        store_embedding(call_id, embedding, embedding_type="full")
        logger.info(f"Stored embedding for call {call_id}")
        
    except Exception as e:
        logger.error(f"Error generating embeddings for call {call_id}: {e}")


async def _judge_call_async(call_id: str, customer_id: str, transcript: str) -> None:
    """Async job to judge call quality and extract metrics.
    
    Args:
        call_id: VAPI call ID
        customer_id: Customer UUID as string
        transcript: Full conversation transcript
    """
    try:
        from uuid import UUID
        
        logger.info(f"Starting call judgment for {call_id}")
        
        # Judge the call using LLM
        judgment = await judge_call(transcript, call_id, UUID(customer_id))
        
        if not judgment:
            logger.warning(f"Failed to generate judgment for call {call_id}")
            return
        
        # Store metrics in database
        metrics_result = store_call_metrics(
            call_id=call_id,
            customer_id=UUID(customer_id),
            frc_achieved=judgment.metrics.frc_achieved,
            frc_type=judgment.metrics.frc_type,
            intent_detected=judgment.metrics.intent_detected,
            intent_accuracy_score=judgment.metrics.intent_accuracy_score,
            call_quality_score=judgment.metrics.call_quality_score,
            customer_sentiment=judgment.metrics.customer_sentiment,
            script_compliance_score=judgment.metrics.script_compliance_score,
            key_objections=judgment.metrics.key_objections,
            agent_responses_to_objections=judgment.metrics.agent_responses_to_objections,
            next_steps_agreed=judgment.metrics.next_steps_agreed,
            call_duration_seconds=judgment.metrics.call_duration_seconds,
        )
        
        if metrics_result:
            metrics_id = metrics_result.get("id")
            
            # Store judgment in database
            store_call_judgment(
                call_id=call_id,
                customer_id=UUID(customer_id),
                metrics_id=metrics_id,
                judge_reasoning=judgment.judge_reasoning,
                judge_model=judgment.judge_model,
                strengths=judgment.strengths,
                improvements=judgment.improvements,
            )
            
            logger.info(f"✅ Call judgment complete for {call_id}")
            
            # Log to Logfire
            log_call_metrics(
                call_id,
                {
                    "frc_achieved": judgment.metrics.frc_achieved,
                    "call_quality_score": judgment.metrics.call_quality_score,
                    "intent_detected": judgment.metrics.intent_detected,
                    "customer_sentiment": judgment.metrics.customer_sentiment,
                    "script_compliance_score": judgment.metrics.script_compliance_score,
                },
            )
        else:
            logger.error(f"Failed to store metrics for call {call_id}")
    
    except Exception as e:
        logger.error(f"Error judging call {call_id}: {e}")


async def _handle_end_of_call_report(message: Dict[str, Any], settings: Settings) -> None:
    """Process an ``end-of-call-report`` payload."""

    artifact = message.get("artifact", {})
    transcript = artifact.get("transcript")
    recording = artifact.get("recording")
    messages = artifact.get("messages")
    ended_reason = message.get("endedReason")
    call_data = message.get("call", {})
    call_id = call_data.get("id") or message.get("id") or message.get("callId")
    customer_number = call_data.get("phoneNumber")

    logger.info("Call ended", extra={"ended_reason": ended_reason, "call_id": call_id})
    
    if transcript and call_id:
        try:
            # 1. Get or create customer by phone number
            if customer_number:
                customer = get_or_create_customer(customer_number)
                logger.info(f"Customer {customer.id} identified: {customer.company_name}")
            else:
                logger.warning(f"No phone number in call {call_id}, using default customer")
                customer = get_or_create_customer(settings.customer_phone_number)
            
            # 2. Store conversation with customer link
            conv_result = store_conversation(call_id, customer.id, transcript)
            logger.info(f"Stored conversation {conv_result.get('id')} for customer {customer.id}")
            
            # 3. Trigger async embedding generation (non-blocking)
            asyncio.create_task(_generate_embeddings(call_id, transcript))
            logger.info(f"Queued embedding generation for call {call_id}")
            
            # 3.5. Trigger async call judgment (non-blocking)
            asyncio.create_task(_judge_call_async(call_id, str(customer.id), transcript))
            logger.info(f"Queued call judgment for {call_id}")
            
            # 4. Also persist to JSON for backward compatibility
            await _persist_transcript(
                transcript,
                settings=settings,
                call_id=call_id,
                ended_reason=ended_reason,
                recording=recording,
                messages=messages,
                raw_message=message,
            )
            
        except Exception as e:
            logger.error(f"Error handling end-of-call for {call_id}: {e}")
    
    if recording:
        logger.info("Recording info", extra={"recording": recording})


async def _handle_status_update(message: Dict[str, Any]) -> None:
    """Process a status-update webhook message."""

    status_value = message.get("status")
    if status_value == "ended":
        logger.info("Call status ended", extra={"call": message.get("call")})


@app.post("/webhook")
async def webhook(request: Request) -> Dict[str, str]:
    """Receive webhook callbacks from Vapi."""

    try:
        payload = await request.json()
    except json.JSONDecodeError as exc:  # pragma: no cover - FastAPI handles silently
        logger.warning("Invalid JSON payload received from Vapi", exc_info=exc)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid JSON")

    message = payload.get("message")
    if not isinstance(message, dict):
        logger.warning("Webhook payload missing message field: %s", payload)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing message field")

    message_type = message.get("type")
    logger.debug("Received webhook message", extra={"message_type": message_type})

    settings = get_settings()

    if message_type == "end-of-call-report":
        asyncio.create_task(_handle_end_of_call_report(message, settings))
    elif message_type == "status-update":
        asyncio.create_task(_handle_status_update(message))
    else:
        logger.info("Ignored webhook message type", extra={"type": message_type, "call_id": message.get("call", {}).get("id")})

    return {"status": "received"}


@app.post("/webhooks/sendgrid/inbound-parse")
async def sendgrid_inbound_webhook(request: Request) -> JSONResponse:
    """Handle inbound emails from SendGrid.
    
    SendGrid will POST email content here when customer replies.
    """
    try:
        # Parse form data from SendGrid
        form_data = await request.form()
        
        from_email = form_data.get("from", "unknown@example.com")
        to_email = form_data.get("to", "unknown@example.com")
        subject = form_data.get("subject", "(No Subject)")
        text_body = form_data.get("text", "")
        html_body = form_data.get("html", "")
        
        # Use text or HTML, prefer text
        email_body = text_body or html_body or ""
        
        logger.info(f"📧 Received email webhook: {subject} from {from_email}")
        
        # Find customer by email
        customer = get_customer_by_email(to_email)  # We need to add this function
        if not customer:
            logger.warning(f"Customer not found for email {to_email}")
            return JSONResponse({"status": "ok"}, status_code=200)
        
        customer_id = customer.get("id")
        
        # Store email reply
        email_record = store_email_reply(
            customer_id=customer_id,
            from_email=from_email,
            to_email=to_email,
            subject=subject,
            body=email_body,
            email_type="reply"
        )
        
        if not email_record:
            logger.error(f"Failed to store email from {from_email}")
            return JSONResponse({"status": "failed"}, status_code=500)
        
        email_id = email_record.get("id")
        
        # Get full customer context
        customer_name = f"{customer.get('first_name', '')} {customer.get('last_name', '')}".strip()
        
        # Get previous call summary
        conversations = get_customer_conversations(customer_id, limit=1)
        previous_call_summary = conversations[0].get("summary") if conversations else None
        
        # Get past emails for context
        past_emails_records = get_customer_emails(customer_id, limit=10)
        past_emails = [f"From: {e['from_email']}\nTo: {e['to_email']}\nSubject: {e['subject']}\n\n{e['body']}" for e in past_emails_records]
        
        customer_profile = {
            "name": customer_name,
            "email": customer.get("email"),
            "phone": customer.get("phone_number"),
            "company": customer.get("company_name"),
            "industry": customer.get("industry"),
            "location": customer.get("location"),
        }
        
        # Analyze email reply with LLM
        analyzer = EmailReplyAnalyzer(settings=settings)
        analysis = await analyzer.analyze(
            email_reply=email_body,
            previous_call_summary=previous_call_summary,
            past_emails=past_emails,
            customer_profile=customer_profile,
        )
        
        logger.info(f"✅ Email analyzed")
        logger.info(f"  Sentiment: {analysis.sentiment}")
        logger.info(f"  Engagement: {analysis.engagement_level}")
        logger.info(f"  Intent: {analysis.customer_intent}")
        logger.info(f"  Actions: {[a.type.value for a in analysis.actions]}")
        
        # Store analysis
        store_email_analysis(
            customer_id=customer_id,
            email_id=email_id,
            sentiment=analysis.sentiment,
            engagement_level=analysis.engagement_level,
            customer_intent=analysis.customer_intent,
            interest_change=analysis.interest_change,
            actions=[a.type.value for a in analysis.actions],
            suggested_next_steps=analysis.suggested_next_steps,
        )
        
        # Execute recommended actions
        for action in analysis.actions:
            logger.info(f"Executing action: {action.type.value} (reason: {action.reason})")
            
            if action.type.value == "send_response":
                try:
                    # Suggest appropriate template
                    template_type = EmailResponseTemplates.suggest_template(
                        action.type.value,
                        analysis.sentiment,
                        analysis.engagement_level,
                    )
                    
                    if template_type:
                        # Render response from template
                        response_body = EmailResponseTemplates.render_template(
                            template_type,
                            customer_name=customer_name,
                            agent_name="InsureFlow Solutions",
                            company_name="InsureFlow Solutions",
                            topic="insurance solutions",
                            meeting_time="next week",
                        )
                        
                        # Send response email
                        email_sender = EmailSender(settings=settings)
                        success = email_sender.send_email(
                            to_email=from_email,
                            to_name=customer_name,
                            subject=f"Re: {subject}",
                            body=response_body,
                        )
                        
                        if success:
                            logger.info(f"✅ Sent auto-response to {from_email}")
                            store_auto_response(
                                customer_id=customer_id,
                                email_id=email_id,
                                response_body=response_body,
                                template_used=template_type.value,
                                action_type=action.type.value,
                            )
                        else:
                            logger.warning(f"Failed to send response to {from_email}")
                
                except Exception as e:
                    logger.error(f"Error sending response: {e}")
            
            elif action.type.value == "schedule_callback":
                logger.info(f"Customer {customer_name} requested callback")
                # TODO: Integrate with calendar system or store for sales team
                store_auto_response(
                    customer_id=customer_id,
                    email_id=email_id,
                    response_body="Callback scheduled",
                    template_used="callback_scheduled",
                    action_type=action.type.value,
                )
            
            elif action.type.value == "escalate_to_sales":
                logger.info(f"Escalating {customer_name} to sales team")
                store_auto_response(
                    customer_id=customer_id,
                    email_id=email_id,
                    response_body="Case escalated to sales team",
                    template_used="escalation_notice",
                    action_type=action.type.value,
                )
        
        logger.info(f"✅ Email webhook processed successfully for {customer_name}")
        return JSONResponse({"status": "ok"}, status_code=200)
    
    except Exception as e:
        logger.error(f"Error processing SendGrid webhook: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@app.on_event("startup")
async def startup_event() -> None:
    """Start background tasks on app startup."""
    logger.info("Starting background polling task for call transcripts")
    
    # Initialize Logfire
    setup_logfire()
    
    # Initialize Redis
    redis_client = get_redis_client()
    if redis_client:
        logger.info("✅ Redis cache initialized")
    else:
        logger.warning("⚠️  Redis not configured, embedding cache disabled")
    
    # Initialize Modal
    modal_client = get_modal_client()
    if modal_client.available:
        logger.info(f"✅ Modal embedding service configured: {modal_client.modal_url}")
    else:
        logger.info("ℹ️  Modal embedding service not configured, will use local embeddings")
    
    # Start background task
    asyncio.create_task(_poll_pending_calls())


@app.on_event("shutdown")
async def shutdown_event() -> None:
    """Clean up resources on shutdown."""
    logger.info("Shutting down...")
    
    # Close database
    close_db()
    
    # Close Redis
    close_redis()
    logger.info("✅ Redis connection closed")
    
    # Close Modal
    await close_modal_client()
    logger.info("✅ Modal client closed")


async def _persist_transcript(
    transcript: str,
    *,
    settings: Settings,
    call_id: Optional[str],
    ended_reason: Optional[str],
    recording: Optional[Dict[str, Any]],
    messages: Optional[Any],
    raw_message: Dict[str, Any],
) -> None:
    """Persist call transcript and metadata to disk (backward compatibility)."""

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    safe_call_id = call_id or "unknown"

    target_dir = Path(settings.transcript_dir).expanduser()
    target_dir.mkdir(parents=True, exist_ok=True)

    file_path = target_dir / f"{timestamp}_{safe_call_id}.json"

    payload = {
        "call_id": call_id,
        "ended_reason": ended_reason,
        "recording": recording,
        "messages": messages,
        "transcript": transcript,
        "raw_message": raw_message,
        "written_at": datetime.now(timezone.utc).isoformat(),
    }

    def _write() -> None:
        file_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    await asyncio.to_thread(_write)
    logger.info("Stored transcript", extra={"path": str(file_path)})


async def _process_call_transcript(call_id: str, customer_phone: str, settings: Settings) -> None:
    """Fetch transcript from VAPI and store in database."""
    
    def parse_transcript(raw_transcript: str) -> list[Dict[str, str]]:
        """Parse raw transcript string into structured messages.
        
        Format: "AI: message\\nUser: message\\nAI: message..."
        Returns: [{"role": "agent", "message": "..."}, {"role": "customer", "message": "..."}]
        """
        messages = []
        lines = raw_transcript.strip().split('\n')
        
        for line in lines:
            if not line.strip():
                continue
            
            if line.startswith("AI:"):
                message = line.replace("AI:", "").strip()
                if message:  # Only add non-empty messages
                    messages.append({
                        "role": "agent",
                        "speaker": "Jennifer (Agent)",
                        "message": message
                    })
            elif line.startswith("User:"):
                message = line.replace("User:", "").strip()
                if message:  # Only add non-empty messages
                    messages.append({
                        "role": "customer",
                        "speaker": "Customer",
                        "message": message
                    })
        
        return messages
    
    try:
        db = get_db()
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            headers = {"Authorization": f"Bearer {settings.vapi_api_key}"}
            response = await client.get(f"{_vapi_base_url}/call/{call_id}", headers=headers)
            response.raise_for_status()
            
        call_data = response.json()
        
        # Check if call is ended and has transcript
        if call_data.get("status") != "ended":
            logger.debug(f"Call {call_id} not ended yet, will retry")
            return
        
        artifact = call_data.get("artifact", {})
        transcript = artifact.get("transcript")
        
        if not transcript:
            logger.warning(f"No transcript found for call {call_id}")
            return
        
        # Get or create customer
        customer = get_or_create_customer(customer_phone)
        logger.info(f"Processing transcript for customer {customer.first_name} {customer.last_name}")
        
        # Check if conversation already exists
        existing = db.execute(
            "SELECT id FROM conversations WHERE call_id = %s",
            (call_id,)
        )
        
        if not existing:
            # Store conversation
            conv_result = store_conversation(call_id, customer.id, transcript)
            logger.info(f"Stored conversation {call_id} for customer {customer.id}")
        else:
            logger.debug(f"Conversation {call_id} already exists in database")
        
        # Generate and store embedding
        try:
            embedding = generate_embedding(transcript)
            store_embedding(call_id, embedding, "full")
            logger.info(f"✅ Generated and stored embedding for call {call_id}")
        except Exception as e:
            logger.warning(f"Failed to generate embedding for {call_id}: {e}")
        
        # Generate and store summary
        try:
            summary = await summarize_transcript(transcript)
            if summary:
                # Generate embedding for the summary
                summary_embedding = generate_embedding(summary)
                # Update conversation with summary and summary embedding
                update_conversation_summary(call_id, summary, summary_embedding)
                logger.info(f"✅ Generated and stored summary for call {call_id}")
            else:
                logger.warning(f"Failed to generate summary for {call_id}")
        except Exception as e:
            logger.warning(f"Failed to process summary for {call_id}: {e}")
        
        # Detect intents and recommend actions using LLM
        try:
            call_analyzer = LLMCallAnalyzer(settings=settings)
            analysis_result = await call_analyzer.analyze(transcript)
            
            logger.info(f"✅ Call analyzed")
            logger.info(f"  Sentiment: {analysis_result.sentiment}")
            logger.info(f"  Interest level: {analysis_result.customer_interest_level}")
            logger.info(f"  Actions: {[a.type.value for a in analysis_result.actions]}")
            
            # Execute recommended actions
            for action in analysis_result.actions:
                logger.info(f"Executing action: {action.type.value} (reason: {action.reason})")
                
                if action.type.value == "send_email":
                    try:
                        email_sender = EmailSender(settings=settings)
                        success = email_sender.send_from_template(
                            to_email=customer.email or customer.phone_number,
                            to_name=f"{customer.first_name} {customer.last_name}",
                            first_name=customer.first_name,
                            company_name=customer.company_name,
                            template_key="follow_up_info"
                        )
                        
                        if success:
                            logger.info(f"✅ Sent follow-up email to {customer.email}")
                            # Store action in database
                            store_customer_memory(
                                call_id=call_id,
                                customer_id=customer.id,
                                memory_type="email_sent",
                                content=f"Follow-up email sent: {action.reason}"
                            )
                        else:
                            logger.warning(f"Failed to send email to {customer.email}")
                    except Exception as e:
                        logger.warning(f"Error sending email: {e}")
                
                elif action.type.value == "add_to_dnc":
                    logger.info(f"Adding {customer.phone_number} to Do Not Call list")
                    store_customer_memory(
                        call_id=call_id,
                        customer_id=customer.id,
                        memory_type="dnc_flag",
                        content=f"Customer marked DNC: {action.reason}"
                    )
                
                elif action.type.value == "schedule_callback":
                    logger.info(f"Scheduling callback for {customer.phone_number}")
                    store_customer_memory(
                        call_id=call_id,
                        customer_id=customer.id,
                        memory_type="callback_scheduled",
                        content=f"Callback scheduled: {action.reason}"
                    )
                
                elif action.type.value == "add_to_followup":
                    logger.info(f"Adding {customer.company_name} to follow-up list")
                    store_customer_memory(
                        call_id=call_id,
                        customer_id=customer.id,
                        memory_type="followup_required",
                        content=f"Follow-up needed: {action.reason}"
                    )
        
        except Exception as e:
            logger.warning(f"Error analyzing call: {e}")
        
        # Save transcript file to disk for reference with both raw and parsed formats
        try:
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            target_dir = Path(settings.transcript_dir).expanduser()
            target_dir.mkdir(parents=True, exist_ok=True)
            
            filename = target_dir / f"{timestamp}_{call_id}.json"
            payload = {
                "call_id": call_id,
                "raw_transcript": transcript,
                "parsed_transcript": {
                    "messages": parse_transcript(transcript),
                    "message_count": len(parse_transcript(transcript)),
                    "agent_messages": len([m for m in parse_transcript(transcript) if m["role"] == "agent"]),
                    "customer_messages": len([m for m in parse_transcript(transcript) if m["role"] == "customer"])
                },
                "customer": {
                    "id": str(customer.id),
                    "name": f"{customer.first_name} {customer.last_name}",
                    "phone": customer.phone_number,
                    "company": customer.company_name
                },
                "created_at": datetime.now(timezone.utc).isoformat()
            }
            
            def _write() -> None:
                filename.write_text(json.dumps(payload, indent=2), encoding="utf-8")
            
            await asyncio.to_thread(_write)
            logger.info(f"✅ Saved transcript to {filename}")
        except Exception as e:
            logger.warning(f"Failed to save transcript file for {call_id}: {e}")
        
        # Remove from pending calls
        if call_id in _pending_calls:
            del _pending_calls[call_id]
        
    except Exception as e:
        logger.error(f"Error processing transcript for {call_id}: {e}")


async def _poll_pending_calls() -> None:
    """Background task to poll VAPI for pending call completions and generate embeddings."""
    settings = get_settings()
    db = get_db()
    
    # Track which calls we've already processed
    processed_calls = set()
    
    while True:
        try:
            await asyncio.sleep(8)  # Poll every 8 seconds
            
            # 1. Process explicitly pending calls
            calls_to_check = list(_pending_calls.items())
            for call_id, call_info in calls_to_check:
                if call_id not in processed_calls:
                    logger.info(f"Processing pending call: {call_id}")
                    await _process_call_transcript(call_id, call_info["customer_phone"], settings)
                    processed_calls.add(call_id)
            
            # 2. Check for conversations without embeddings (already in DB)
            results = db.execute(
                """SELECT c.call_id, p.phone_number 
                   FROM brokerage.conversations c
                   LEFT JOIN brokerage.customers p ON c.customer_id = p.id
                   LEFT JOIN brokerage.embeddings e ON c.call_id = e.call_id AND e.embedding_type = 'full'
                   WHERE e.call_id IS NULL
                   LIMIT 10""",
                ()
            )
            
            for row in results:
                call_id = row['call_id']
                phone = row['phone_number']
                if call_id not in processed_calls:
                    logger.info(f"Auto-processing conversation without embedding: {call_id}")
                    await _process_call_transcript(call_id, phone, settings)
                    processed_calls.add(call_id)
        
        except Exception as e:
            logger.error(f"Error in polling task: {e}")
            await asyncio.sleep(10)  # Back off on error

