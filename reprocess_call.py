#!/usr/bin/env python
"""Reprocess the last call that was stored."""

import sys
import asyncio
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from app.config import settings
from app.main import _process_call_transcript

async def main():
    # The call ID from the transcript file
    call_id = "019a0e6d-f431-7ff1-a62f-f032c0e69744"
    customer_phone = "+14698674545"
    
    print("=" * 70)
    print(f"🔄 Reprocessing Call: {call_id}")
    print("=" * 70)
    
    try:
        await _process_call_transcript(call_id, customer_phone, settings)
        print("\n✅ Call reprocessed successfully!")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
