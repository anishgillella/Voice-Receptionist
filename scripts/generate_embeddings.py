#!/usr/bin/env python
"""Generate embeddings for conversations without embeddings."""

import sys
import argparse
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db import get_db, store_embedding
from app.embeddings import generate_embedding


def generate_embeddings_for_all():
    """Generate embeddings for all conversations without embeddings."""
    db = get_db()
    
    # Get conversations without embeddings
    conversations = db.execute(
        """
        SELECT c.call_id, c.transcript
        FROM conversations c
        LEFT JOIN embeddings e ON c.call_id = e.call_id AND e.embedding_type = 'full'
        WHERE e.call_id IS NULL
        """,
        ()
    )
    
    print(f"🔍 Found {len(conversations)} conversations without embeddings\n")
    
    if not conversations:
        print("✅ All conversations have embeddings!")
        return
    
    processed = 0
    failed = 0
    
    for i, conv in enumerate(conversations, 1):
        call_id = conv['call_id']
        transcript = conv['transcript']
        
        try:
            print(f"[{i}/{len(conversations)}] Generating embedding for {call_id}...", end=" ", flush=True)
            embedding = generate_embedding(transcript)
            store_embedding(call_id, embedding, "full")
            print("✅")
            processed += 1
        except Exception as e:
            print(f"❌ Error: {e}")
            failed += 1
    
    print(f"\n{'='*60}")
    print(f"✅ Completed!")
    print(f"   Generated: {processed}")
    print(f"   Failed: {failed}")
    print(f"{'='*60}")


def generate_embedding_for_call(call_id: str):
    """Generate embedding for a specific call."""
    db = get_db()
    
    # Get transcript
    result = db.execute(
        "SELECT transcript FROM conversations WHERE call_id = %s",
        (call_id,)
    )
    
    if not result:
        print(f"❌ Call {call_id} not found")
        return
    
    transcript = result[0]['transcript']
    print(f"📝 Transcript for {call_id}:")
    print(f"   {transcript[:100]}...\n")
    
    print("Generating embedding...")
    embedding = generate_embedding(transcript)
    
    print(f"✅ Embedding generated: {len(embedding)} dimensions\n")
    
    print("Storing in database...")
    store_embedding(call_id, embedding, "full")
    
    print(f"✅ Stored successfully!\n")
    print(f"Embedding preview (first 10 values):")
    for i, val in enumerate(embedding[:10], 1):
        print(f"   [{i}] {val:.6f}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Generate embeddings for conversation transcripts"
    )
    
    parser.add_argument(
        "--all",
        action="store_true",
        help="Generate embeddings for all conversations without embeddings"
    )
    parser.add_argument(
        "--call-id",
        type=str,
        help="Generate embedding for a specific call ID"
    )
    
    args = parser.parse_args()
    
    if args.all:
        generate_embeddings_for_all()
    elif args.call_id:
        generate_embedding_for_call(args.call_id)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()

