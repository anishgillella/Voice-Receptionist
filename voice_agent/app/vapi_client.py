"""Helper utilities for interacting with the Vapi REST API."""

from __future__ import annotations

from typing import Any, Dict, Optional

import httpx

from .config import settings, INSURANCE_PROSPECT_SYSTEM_PROMPT, INBOUND_PROSPECT_SYSTEM_PROMPT

VAPI_BASE_URL = "https://api.vapi.ai"


def get_model_config_for_provider(provider: str = "cerebras") -> Dict[str, Any]:
    """Get model configuration based on selected provider.
    
    Args:
        provider: LLM provider (cerebras, openai, openrouter)
        
    Returns:
        Model configuration dict for VAPI
    """
    if provider == "cerebras":
        return {
            "provider": "custom-llm",
            "model": settings.cerebras_model,  # llama-3.1-70b by default
            "baseUrl": "https://api.cerebras.ai/v1",
            "apiKey": settings.cerebras_api_key,
            "temperature": 0.7,
            "maxTokens": 200,
        }
    elif provider == "openai":
        return {
            "provider": "openai",
            "model": "gpt-4o-mini",
            "temperature": 0.7,
            "maxTokens": 200,
        }
    else:  # openrouter
        return {
            "provider": "openai",
            "model": "gpt-4o-mini",
            "temperature": 0.7,
            "maxTokens": 200,
        }


def get_agent_id_for_call_type(call_type: str = "outbound") -> str:
    """Get the appropriate agent ID based on call type.
    
    Args:
        call_type: "outbound" or "inbound"
        
    Returns:
        The agent ID to use for this call type
    """
    if call_type.lower() == "inbound" and settings.vapi_agent_id_inbound:
        return settings.vapi_agent_id_inbound
    elif call_type.lower() == "outbound" and settings.vapi_agent_id_outbound:
        return settings.vapi_agent_id_outbound
    else:
        # Fallback to default
        return settings.vapi_agent_id


def get_phone_number_id_for_call_type(call_type: str = "outbound") -> str:
    """Get the appropriate phone number ID based on call type.
    
    Args:
        call_type: "outbound" or "inbound"
        
    Returns:
        The phone number ID to use for this call type
    """
    if call_type.lower() == "inbound" and settings.vapi_phone_number_id_inbound:
        return settings.vapi_phone_number_id_inbound
    elif call_type.lower() == "outbound" and settings.vapi_phone_number_id_outbound:
        return settings.vapi_phone_number_id_outbound
    else:
        # Fallback to default
        return settings.vapi_phone_number_id


async def create_or_update_insurance_agent(
    agent_name: str = "Jennifer - Insurance Sales Agent",
    agent_id: Optional[str] = None,
    call_type: str = "outbound",
) -> Dict[str, Any]:
    """Create or update a Vapi agent with insurance prospecting configuration.
    
    Args:
        agent_name: Name for the agent
        agent_id: Optional existing agent ID to update
        call_type: "outbound" or "inbound"
        
    Returns:
        Agent configuration from Vapi API
    """
    
    # Select appropriate system prompt based on call type
    if call_type.lower() == "inbound":
        system_prompt = INBOUND_PROSPECT_SYSTEM_PROMPT
    else:
        system_prompt = INSURANCE_PROSPECT_SYSTEM_PROMPT
    
    # Get the backend URL for webhooks
    backend_url = settings.backend_base_url or "http://localhost:8000"
    webhook_url = f"{backend_url}/webhook"
    
    payload: Dict[str, Any] = {
        "name": agent_name,
        "model": get_model_config_for_provider(settings.llm_provider) | {
            "messages": [
                {
                    "role": "system",
                    "content": system_prompt,
                }
            ],
        },
        "voice": {
            "provider": "11labs",  # ElevenLabs - use '11labs' not 'elevenlabs'
            "voiceId": "paula",  # Professional female voice
        },
        "transcriber": {
            "provider": "deepgram",
            "model": "nova-3",
            "language": "en",
            "endpointing": 100,  # Reduced from 150ms for faster speech detection
        },
        "firstMessageMode": "assistant-speaks-first-with-model-generated-message",
        "startSpeakingPlan": {
            "waitSeconds": 0.4,
            "smartEndpointingEnabled": "livekit",
        },
        "server": {
            "url": webhook_url,
            "timeoutSeconds": 20,
            "headers": {},
        },
        "endCallPhrases": ["goodbye", "thank you for calling"],  # More specific phrases to avoid accidental triggers
        "maxDurationSeconds": 600,  # 10 minute limit for safety
        "backgroundDenoisingEnabled": False,
        "hipaaEnabled": False,
    }
    
    headers = {
        "Authorization": f"Bearer {settings.vapi_api_key}",
        "Content-Type": "application/json",
    }
    
    async with httpx.AsyncClient(base_url=VAPI_BASE_URL, timeout=30.0) as client:
        try:
            if agent_id:
                # Update existing agent
                print(f"Updating agent {agent_id}...")
                response = await client.patch(f"/assistant/{agent_id}", json=payload, headers=headers)
            else:
                # Create new agent
                print("Creating new insurance agent...")
                response = await client.post("/assistant", json=payload, headers=headers)
            
            response.raise_for_status()
            result = response.json()
            
            agent_id = result.get("id")
            print(f"✅ Agent configured successfully!")
            print(f"   Agent ID: {agent_id}")
            print(f"   Webhook URL: {webhook_url}")
            
            return result
            
        except httpx.HTTPStatusError as e:
            print(f"❌ Error configuring agent: {e}")
            print(f"   Response: {e.response.text}")
            # Return helpful debug info
            return {
                "error": str(e),
                "status_code": e.response.status_code,
                "response_text": e.response.text,
                "payload": payload,
                "webhook_url": webhook_url,
                "instructions": "Check Vapi API documentation or verify API key"
            }


async def initiate_outbound_call(
    customer_number: str,
    *,
    metadata: Optional[Dict[str, Any]] = None,
    prospect_info: Optional[Dict[str, Any]] = None,
    call_type: str = "outbound",
    system_prompt: Optional[str] = None,
) -> Dict[str, Any]:
    """Trigger an outbound call via Vapi.

    Args:
        customer_number: E.164-formatted phone number for the customer.
        metadata: Optional metadata dict to include with the call.
        prospect_info: Insurance prospect information
        call_type: "outbound" or "inbound"
        system_prompt: Optional custom system prompt (overrides default)

    Returns:
        Parsed JSON response from Vapi.
    """

    # Merge prospect info into metadata
    call_metadata = metadata or {}
    if prospect_info:
        call_metadata.update(prospect_info)
    
    # Get the appropriate agent ID for this call type
    agent_id = get_agent_id_for_call_type(call_type)

    payload: Dict[str, Any] = {
        "assistantId": agent_id,
        "phoneNumberId": get_phone_number_id_for_call_type(call_type),
        "customer": {"number": customer_number},
    }

    if call_metadata:
        payload["metadata"] = call_metadata

    # If custom system prompt provided, override the assistant's system prompt
    if system_prompt:
        payload["assistantOverrides"] = {
            "model": {
                "provider": "openai",
                "model": "gpt-4o-mini",
                "messages": [
                    {
                        "role": "system",
                        "content": system_prompt,
                    }
                ]
            }
        }

    headers = {
        "Authorization": f"Bearer {settings.vapi_api_key}",
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(base_url=VAPI_BASE_URL, timeout=30.0) as client:
        response = await client.post("/call", json=payload, headers=headers)
        try:
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            print(f"VAPI Error Response: {e.response.text}")
            raise

