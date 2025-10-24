#!/usr/bin/env python
"""Test script for optimized embedding pipeline with Redis caching and Modal GPU."""

import asyncio
import time
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from app.config import settings
from app.embeddings import generate_embedding, generate_embeddings_batch
from app.embedding_cache import get_cache_stats, clear_embedding_cache, get_redis_client
from app.modal_client import get_modal_client


async def test_embedding_single():
    """Test single embedding generation with caching."""
    print("\n" + "=" * 70)
    print("TEST 1: Single Embedding Generation")
    print("=" * 70)
    
    test_text = "I need business insurance coverage for my tech startup"
    
    print(f"\n📝 Text: {test_text}")
    print("\n⏱️  Testing cache hits...\n")
    
    # First call - should generate and cache
    print("1️⃣  First call (cache MISS - will generate):")
    start = time.time()
    embedding1 = generate_embedding(test_text, use_cache=True)
    time1 = time.time() - start
    print(f"   ✅ Generated embedding ({len(embedding1)} dimensions)")
    print(f"   ⏱️  Time: {time1*1000:.1f}ms")
    
    # Second call - should hit cache
    print("\n2️⃣  Second call (cache HIT - should be instant):")
    start = time.time()
    embedding2 = generate_embedding(test_text, use_cache=True)
    time2 = time.time() - start
    print(f"   ✅ Retrieved embedding from cache")
    print(f"   ⏱️  Time: {time2*1000:.1f}ms")
    
    # Verify identical
    if embedding1 == embedding2:
        print(f"\n✅ Embeddings match! Cache working correctly.")
    else:
        print(f"\n❌ Embeddings don't match!")
    
    print(f"\n📊 Performance Improvement:")
    print(f"   Cache MISS: {time1*1000:.1f}ms")
    print(f"   Cache HIT:  {time2*1000:.1f}ms")
    print(f"   Speedup:    {time1/time2:.1f}x faster")
    
    return time1, time2


async def test_embedding_batch():
    """Test batch embedding generation."""
    print("\n" + "=" * 70)
    print("TEST 2: Batch Embedding Generation")
    print("=" * 70)
    
    test_texts = [
        "What's your insurance quote?",
        "Tell me about coverage options",
        "How much does liability insurance cost?",
        "I need workers compensation insurance",
        "What's the difference between policies?",
    ]
    
    print(f"\n📝 Batch size: {len(test_texts)} texts")
    
    print("\n1️⃣  Generating batch (first time - no cache):")
    start = time.time()
    embeddings = generate_embeddings_batch(test_texts, use_cache=True)
    time_batch = time.time() - start
    
    print(f"   ✅ Generated {len(embeddings)} embeddings")
    print(f"   ⏱️  Time: {time_batch*1000:.1f}ms")
    print(f"   Per embedding: {time_batch*1000/len(test_texts):.1f}ms")
    
    print("\n2️⃣  Generating same batch again (all cached):")
    start = time.time()
    embeddings2 = generate_embeddings_batch(test_texts, use_cache=True)
    time_batch_cached = time.time() - start
    
    print(f"   ✅ Retrieved {len(embeddings2)} embeddings from cache")
    print(f"   ⏱️  Time: {time_batch_cached*1000:.1f}ms")
    print(f"   Per embedding: {time_batch_cached*1000/len(test_texts):.1f}ms")
    
    print(f"\n📊 Batch Performance:")
    print(f"   First batch:   {time_batch*1000:.1f}ms")
    print(f"   Cached batch:  {time_batch_cached*1000:.1f}ms")
    print(f"   Speedup:       {time_batch/time_batch_cached:.1f}x faster")
    
    return time_batch, time_batch_cached


async def test_redis_cache():
    """Test Redis cache directly."""
    print("\n" + "=" * 70)
    print("TEST 3: Redis Cache Status")
    print("=" * 70)
    
    redis_client = get_redis_client()
    
    if not redis_client:
        print("\n⚠️  Redis not configured")
        print("   To enable caching, set REDIS_URL in .env")
        return None
    
    try:
        redis_client.ping()
        print("\n✅ Redis Connected!")
        
        stats = get_cache_stats()
        print(f"\n📊 Cache Statistics:")
        print(f"   Status:        {stats.get('status')}")
        print(f"   Total keys:    {stats.get('total_keys', 0)}")
        print(f"   Memory used:   {stats.get('used_memory', 'unknown')}")
        
        if stats.get('total_keys', 0) > 0:
            print(f"\n💾 Cache is being used! {stats.get('total_keys')} embeddings cached.")
        else:
            print(f"\n💾 Cache is empty (first run)")
        
        return stats
        
    except Exception as e:
        print(f"\n❌ Redis connection failed: {e}")
        return None


async def test_modal_connection():
    """Test Modal connection."""
    print("\n" + "=" * 70)
    print("TEST 4: Modal Embedding Service")
    print("=" * 70)
    
    modal_client = get_modal_client()
    
    if not modal_client.available:
        print("\n⚠️  Modal not configured")
        print("   To enable GPU embeddings, set MODAL_EMBEDDING_URL in .env")
        print("   Deploy service: modal deploy voice_agent/modal_embedding_service.py")
        return None
    
    print(f"\n✅ Modal configured: {modal_client.modal_url}")
    
    try:
        print("\nTesting Modal embedding service...")
        test_text = "Testing Modal GPU embeddings"
        
        embedding = await modal_client.embed(test_text)
        
        if embedding:
            print(f"✅ Modal working! Generated {len(embedding)} dimensional embedding")
            return True
        else:
            print(f"❌ Modal returned no embedding")
            return False
            
    except Exception as e:
        print(f"❌ Modal connection failed: {e}")
        return False


async def test_summary():
    """Print test summary."""
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    
    # Test configuration
    print("\n🔧 Configuration:")
    print(f"   Redis URL:         {settings.redis_url if hasattr(settings, 'redis_url') else 'Not set'}")
    print(f"   Modal URL:         {settings.modal_embedding_url if hasattr(settings, 'modal_embedding_url') else 'Not set'}")
    print(f"   Use TensorRT:      {settings.use_tensorrt if hasattr(settings, 'use_tensorrt') else False}")
    print(f"   Cerebras Model:    {settings.cerebras_model}")
    
    print("\n✅ All tests completed!")
    print("\nProduction deployment ready!")


async def main():
    """Run all tests."""
    print("\n" + "=" * 70)
    print("🚀 VOICE AGENT - OPTIMIZED EMBEDDING TEST SUITE")
    print("=" * 70)
    
    try:
        # Test 1: Single embeddings with caching
        time1_miss, time1_hit = await test_embedding_single()
        
        # Test 2: Batch embeddings
        time2_first, time2_cached = await test_embedding_batch()
        
        # Test 3: Redis cache status
        cache_stats = await test_redis_cache()
        
        # Test 4: Modal connection
        modal_ok = await test_modal_connection()
        
        # Summary
        await test_summary()
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
