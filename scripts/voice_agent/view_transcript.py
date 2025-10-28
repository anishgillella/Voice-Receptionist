#!/usr/bin/env python
"""View and display call transcripts in a readable format."""

import sys
import json
from pathlib import Path

def display_transcript(transcript_file: Path) -> None:
    """Display a transcript file in a readable conversation format."""
    
    with open(transcript_file) as f:
        data = json.load(f)
    
    # Extract data
    call_id = data.get("call_id")
    customer = data.get("customer", {})
    parsed = data.get("parsed_transcript", {})
    raw = data.get("raw_transcript", "")
    created_at = data.get("created_at", "")
    
    messages = parsed.get("messages", [])
    
    # Display header
    print("\n" + "=" * 90)
    print("📞 CALL TRANSCRIPT")
    print("=" * 90)
    
    print(f"\n📊 CALL INFORMATION:")
    print(f"  • Call ID: {call_id}")
    print(f"  • Customer: {customer.get('name')} ({customer.get('phone')})")
    print(f"  • Company: {customer.get('company')}")
    print(f"  • Date: {created_at[:10]} at {created_at[11:19]} UTC")
    print(f"  • Messages: {parsed.get('message_count')} total")
    print(f"    - Agent: {parsed.get('agent_messages')}")
    print(f"    - Customer: {parsed.get('customer_messages')}")
    
    # Display conversation
    print(f"\n" + "-" * 90)
    print("CONVERSATION:")
    print("-" * 90 + "\n")
    
    if messages:
        for i, msg in enumerate(messages, 1):
            role = msg.get("role", "unknown")
            speaker = msg.get("speaker", "Unknown")
            message = msg.get("message", "")
            
            if role == "agent":
                print(f"  [{i}] 🤖 {speaker}:")
                print(f"       \"{message}\"")
            else:
                print(f"  [{i}] 👤 {speaker}:")
                print(f"       \"{message}\"")
            print()
    else:
        print("  (No parsed messages found)")
    
    print("-" * 90 + "\n")
    
    # Display raw transcript
    if raw:
        print(f"📝 RAW TRANSCRIPT:\n")
        print(raw)
    
    print("\n" + "=" * 90 + "\n")

def main():
    """Main entry point."""
    
    if len(sys.argv) < 2:
        # List recent transcripts
        transcripts_dir = Path("data/transcripts")
        if not transcripts_dir.exists():
            print("❌ No transcripts directory found")
            sys.exit(1)
        
        print("\n📂 AVAILABLE TRANSCRIPTS:\n")
        transcript_files = sorted(transcripts_dir.glob("*.json"), reverse=True)
        
        if not transcript_files:
            print("   (No transcripts found)")
            sys.exit(0)
        
        for i, f in enumerate(transcript_files[:10], 1):
            print(f"  [{i}] {f.name}")
        
        print(f"\n💡 Usage: python view_transcript.py <filename>")
        print(f"   Example: python view_transcript.py {transcript_files[0].name}")
        print()
        sys.exit(0)
    
    # Display specific transcript
    transcript_path = Path("data/transcripts") / sys.argv[1]
    
    if not transcript_path.exists():
        print(f"❌ Transcript not found: {sys.argv[1]}")
        sys.exit(1)
    
    display_transcript(transcript_path)

if __name__ == "__main__":
    main()
