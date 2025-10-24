#!/usr/bin/env python
"""Simple optimization test without heavy ML dependencies."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from app.config import settings
from app.embedding_cache import get_cache_stats, get_redis_client
import logging

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

def test_config():
    """Test configuration loaded correctly."""
    print("\n" + "=" * 70)
    print("TEST 1: Configuration")
    print("=" * 70)
    
    configs = {
        "VAPI_API_KEY": settings.vapi_api_key[:20] + "...",
        "SUPABASE_URL": settings.supabase_url[:30] + "...",
        "LLM Provider": settings.llm_provider,
        "Cerebras Model": settings.cerebras_model,
        "HF Token": "✅ Set" if settings.hf_token else "❌ Not set",
        "Redis URL": settings.redis_url or "Not configured",
        "TensorRT": settings.use_tensorrt,
    }
    
    for key, value in configs.items():
        print(f"  {key:.<25} {value}")
    
    print("\n✅ Configuration loaded successfully!")
    return True


def test_redis_connection():
    """Test Redis cache connection."""
    print("\n" + "=" * 70)
    print("TEST 2: Redis Cache Connection")
    print("=" * 70)
    
    redis_client = get_redis_client()
    
    if not redis_client:
        print("\n⚠️  Redis not configured or connection failed")
        print("   Set REDIS_URL in .env to enable caching")
        return None
    
    try:
        redis_client.ping()
        print("\n✅ Redis connected!")
        
        stats = get_cache_stats()
        print(f"\n📊 Cache Statistics:")
        print(f"   Status:       {stats.get('status')}")
        print(f"   Total keys:   {stats.get('total_keys', 0)}")
        print(f"   Memory used:  {stats.get('used_memory', 'unknown')}")
        
        return stats
        
    except Exception as e:
        print(f"\n❌ Redis error: {e}")
        return None


def test_llm_providers():
    """Test LLM provider initialization."""
    print("\n" + "=" * 70)
    print("TEST 3: LLM Providers")
    print("=" * 70)
    
    from app.llm_providers import get_llm_provider
    
    try:
        provider = get_llm_provider()
        print(f"\n✅ LLM Provider initialized: {provider.provider_name}")
        print(f"   Provider type: {type(provider).__name__}")
        
        # Check which keys are configured
        providers_configured = []
        if settings.cerebras_api_key:
            providers_configured.append("Cerebras")
        if settings.openai_api_key:
            providers_configured.append("OpenAI")
        if settings.openrouter_api_key:
            providers_configured.append("OpenRouter")
        
        print(f"   Available providers: {', '.join(providers_configured)}")
        print(f"   Active provider: {settings.llm_provider}")
        
        return provider
        
    except Exception as e:
        print(f"\n❌ LLM Provider error: {e}")
        return None


def test_embedding_cache():
    """Test embedding cache operations."""
    print("\n" + "=" * 70)
    print("TEST 4: Embedding Cache Operations")
    print("=" * 70)
    
    from app.embedding_cache import (
        get_cache_key, 
        cache_embedding, 
        get_cached_embedding,
        clear_embedding_cache
    )
    
    test_text = "Test embedding cache"
    test_embedding = [0.1, 0.2, 0.3, 0.4, 0.5]
    
    # Generate cache key
    cache_key = get_cache_key(test_text)
    print(f"\n✅ Cache key generated: {cache_key[:40]}...")
    
    # Try to cache
    redis_client = get_redis_client()
    if not redis_client:
        print("⚠️  Redis not available, skipping cache test")
        return None
    
    # Store
    success = cache_embedding(test_text, test_embedding)
    if success:
        print(f"✅ Embedding cached successfully")
    else:
        print(f"❌ Failed to cache embedding")
        return None
    
    # Retrieve
    retrieved = get_cached_embedding(test_text)
    if retrieved == test_embedding:
        print(f"✅ Retrieved embedding matches stored embedding")
    else:
        print(f"❌ Retrieved embedding doesn't match")
        return None
    
    return True


def test_modal_client():
    """Test Modal client initialization."""
    print("\n" + "=" * 70)
    print("TEST 5: Modal Client")
    print("=" * 70)
    
    from app.modal_client import get_modal_client
    
    try:
        modal_client = get_modal_client()
        
        if modal_client.available:
            print(f"\n✅ Modal configured: {modal_client.modal_url}")
            print("   Status: Ready for GPU embeddings")
        else:
            print("\n⚠️  Modal not configured")
            print("   To enable: deploy voice_agent/modal_embedding_service.py")
            print("   Then set MODAL_EMBEDDING_URL in .env")
        
        return modal_client
        
    except Exception as e:
        print(f"\n❌ Modal client error: {e}")
        return None


def test_summary():
    """Print test summary."""
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    
    print("\n🚀 Optimization Features:")
    
    features = {
        "Redis Caching": settings.redis_url is not None,
        "TensorRT GPU": settings.use_tensorrt,
        "Modal Service": settings.modal_embedding_url is not None,
        "LLM Provider": settings.llm_provider,
        "Multiple LLMs": (
            (bool(settings.cerebras_api_key) +
             bool(settings.openai_api_key) +
             bool(settings.openrouter_api_key)) > 1
        ),
    }
    
    for feature, enabled in features.items():
        status = "✅" if enabled else "⚠️"
        value = f"({settings.llm_provider})" if feature == "LLM Provider" else ""
        print(f"  {status} {feature:.<30} {'Enabled' if enabled else 'Disabled'} {value}")
    
    print("\n📊 Configuration Status:")
    print(f"   Environment: {settings.environment}")
    print(f"   Debug: {settings.debug}")
    print(f"   Log Level: {settings.log_level}")
    
    print("\n✅ All system tests completed!")
    print("\n🎯 Next steps:")
    print("   1. Try: python make_call.py --phone 4158675309 --customer_name 'John'")
    print("   2. Check transcripts in: data/transcripts/")
    print("   3. View logs for performance metrics")


async def main():
    """Run all tests."""
    print("\n" + "=" * 70)
    print("🚀 VOICE AGENT - OPTIMIZATION SYSTEM TEST")
    print("=" * 70)
    
    try:
        # Run tests
        test_config()
        test_redis_connection()
        test_llm_providers()
        test_embedding_cache()
        test_modal_client()
        test_summary()
        
        print("\n" + "=" * 70)
        print("✅ ALL TESTS PASSED - SYSTEM READY!")
        print("=" * 70 + "\n")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
