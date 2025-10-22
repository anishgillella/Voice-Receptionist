#!/usr/bin/env python3
"""
Monitor script to watch for new transcripts from Vapi calls.

Usage:
    python scripts/watch_transcript.py [--latest]
"""

import json
import sys
import time
from pathlib import Path
from typing import Optional

from cli_utils import print_section, print_subsection


def get_latest_transcript() -> Optional[Path]:
    """Get the most recently modified transcript file."""
    transcript_dir = Path("data/transcripts")
    if not transcript_dir.exists():
        return None
    
    transcript_files = sorted(
        transcript_dir.glob("*.json"),
        key=lambda x: x.stat().st_mtime,
        reverse=True
    )
    
    return transcript_files[0] if transcript_files else None


def display_transcript(file_path: Path) -> None:
    """Display transcript contents in a formatted way."""
    try:
        data = json.loads(file_path.read_text())
        
        print_section("📝 TRANSCRIPT", 70)
        
        # Display key info
        print(f"\n📞 Call ID: {data.get('call_id', 'Unknown')}")
        print(f"⏱️  Status: {data.get('ended_reason', 'Unknown')}")
        print(f"⏰ Recorded: {data.get('written_at', 'Unknown')}")
        
        # Display transcript
        transcript_text = data.get('transcript', '')
        if transcript_text:
            print_subsection("CONVERSATION:", 70)
            print(transcript_text)
        
        # Display recording info
        recording = data.get('recording', {})
        if recording:
            print_subsection("🎙️ RECORDING:", 70)
            print(f"Duration: {recording.get('duration', 'N/A')}s")
            if recording.get('url'):
                print(f"URL: {recording.get('url')}")
        
        print(f"\n{'='*70}\n")
        
    except Exception as e:
        print(f"Error reading transcript: {e}")


def watch_for_transcript(call_id: Optional[str] = None) -> None:
    """Watch for new transcript and display it."""
    print("👁️  Watching for new transcripts...")
    print("(This will monitor until a new transcript appears)\n")
    
    transcript_dir = Path("data/transcripts")
    if not transcript_dir.exists():
        print("❌ Transcripts directory not found")
        return
    
    # Get current files
    existing_files = set(transcript_dir.glob("*.json"))
    
    # Watch for new files
    for attempt in range(180):  # Watch for up to 3 minutes
        time.sleep(2)
        current_files = set(transcript_dir.glob("*.json"))
        new_files = current_files - existing_files
        
        if new_files:
            new_file = list(new_files)[0]
            print(f"✅ New transcript found: {new_file.name}")
            display_transcript(new_file)
            return
        
        if (attempt + 1) % 15 == 0:  # Print status every 30 seconds
            print(f"⏳ Still waiting... ({(attempt+1)*2}s)")
    
    print("⏱️  Timeout: No new transcript received in 3 minutes")
    print("The call may still be in progress. Try again later.")


def show_latest() -> None:
    """Show the latest transcript."""
    latest = get_latest_transcript()
    if latest:
        print(f"📂 Latest transcript: {latest.name}\n")
        display_transcript(latest)
    else:
        print("No transcripts found yet")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--latest":
        show_latest()
    else:
        watch_for_transcript()
