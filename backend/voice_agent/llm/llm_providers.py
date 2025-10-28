"""LLM provider integration and fallback logic."""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from openai import OpenAI

from ..core.config import settings

logger = logging.getLogger(__name__)


class LLMProvider:
    """Base class for LLM providers."""
    
    def __init__(self, provider_name: str):
        """Initialize provider.
        
        Args:
            provider_name: Name of the provider (openai, cerebras, openrouter)
        """
        self.provider_name = provider_name
    
    def generate_response(
        self,
        system_prompt: str,
        user_message: str,
        temperature: float = 0.7,
        max_tokens: int = 500,
    ) -> Optional[str]:
        """Generate response from LLM.
        
        Args:
            system_prompt: System prompt for the model
            user_message: User message/query
            temperature: Sampling temperature
            max_tokens: Maximum tokens in response
            
        Returns:
            Generated response or None if failed
        """
        raise NotImplementedError


class CerebrasProvider(LLMProvider):
    """Cerebras API provider for fast inference."""
    
    def __init__(self):
        """Initialize Cerebras provider."""
        super().__init__("cerebras")
        
        if not settings.cerebras_api_key:
            raise ValueError("CEREBRAS_API_KEY not configured")
        
        # Cerebras uses OpenAI-compatible API
        self.client = OpenAI(
            api_key=settings.cerebras_api_key,
            base_url="https://api.cerebras.ai/v1"
        )
        logger.info("✅ Cerebras provider initialized")
    
    def generate_response(
        self,
        system_prompt: str,
        user_message: str,
        temperature: float = 0.7,
        max_tokens: int = 500,
        model: str = "llama-3.1-70b",
    ) -> Optional[str]:
        """Generate response using Cerebras.
        
        Args:
            system_prompt: System prompt
            user_message: User message
            temperature: Temperature (0.7 good for balance)
            max_tokens: Max response length
            model: Cerebras model to use
            
        Returns:
            Generated response
        """
        try:
            logger.info(f"Calling Cerebras ({model}) with {len(user_message)} chars")
            
            response = self.client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message},
                ],
                temperature=temperature,
                max_tokens=max_tokens,
            )
            
            result = response.choices[0].message.content.strip()
            logger.info(f"✅ Cerebras response: {len(result)} chars")
            return result
            
        except Exception as e:
            logger.error(f"Cerebras error: {e}")
            return None


class OpenRouterProvider(LLMProvider):
    """OpenRouter API provider."""
    
    def __init__(self):
        """Initialize OpenRouter provider."""
        super().__init__("openrouter")
        
        if not settings.openrouter_api_key:
            raise ValueError("OPENROUTER_API_KEY not configured")
        
        self.client = OpenAI(
            api_key=settings.openrouter_api_key,
            base_url="https://openrouter.ai/api/v1"
        )
        logger.info("✅ OpenRouter provider initialized")
    
    def generate_response(
        self,
        system_prompt: str,
        user_message: str,
        temperature: float = 0.7,
        max_tokens: int = 500,
        model: str = "openai/gpt-4o-mini",
    ) -> Optional[str]:
        """Generate response using OpenRouter.
        
        Args:
            system_prompt: System prompt
            user_message: User message
            temperature: Temperature
            max_tokens: Max response length
            model: Model to use (e.g., "openai/gpt-4o-mini")
            
        Returns:
            Generated response
        """
        try:
            logger.info(f"Calling OpenRouter ({model})")
            
            response = self.client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message},
                ],
                temperature=temperature,
                max_tokens=max_tokens,
            )
            
            result = response.choices[0].message.content.strip()
            return result
            
        except Exception as e:
            logger.error(f"OpenRouter error: {e}")
            return None


class OpenAIProvider(LLMProvider):
    """OpenAI API provider."""
    
    def __init__(self):
        """Initialize OpenAI provider."""
        super().__init__("openai")
        
        if not settings.openai_api_key:
            raise ValueError("OPENAI_API_KEY not configured")
        
        self.client = OpenAI(api_key=settings.openai_api_key)
        logger.info("✅ OpenAI provider initialized")
    
    def generate_response(
        self,
        system_prompt: str,
        user_message: str,
        temperature: float = 0.7,
        max_tokens: int = 500,
        model: str = "gpt-4o-mini",
    ) -> Optional[str]:
        """Generate response using OpenAI.
        
        Args:
            system_prompt: System prompt
            user_message: User message
            temperature: Temperature
            max_tokens: Max response length
            model: Model to use
            
        Returns:
            Generated response
        """
        try:
            logger.info(f"Calling OpenAI ({model})")
            
            response = self.client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message},
                ],
                temperature=temperature,
                max_tokens=max_tokens,
            )
            
            result = response.choices[0].message.content.strip()
            return result
            
        except Exception as e:
            logger.error(f"OpenAI error: {e}")
            return None


def get_llm_provider(provider_name: Optional[str] = None) -> LLMProvider:
    """Get LLM provider instance.
    
    Args:
        provider_name: Provider to use (cerebras, openrouter, openai)
                      If None, uses LLM_PROVIDER env var or cerebras default
    
    Returns:
        Initialized provider
    """
    provider = provider_name or settings.llm_provider
    
    if provider == "cerebras":
        return CerebrasProvider()
    elif provider == "openrouter":
        return OpenRouterProvider()
    elif provider == "openai":
        return OpenAIProvider()
    else:
        raise ValueError(f"Unknown LLM provider: {provider}")

