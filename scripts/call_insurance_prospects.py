"""
Script to initiate outbound calls to insurance prospects.

This script demonstrates how to use the insurance prospect calling API
to make outbound calls with prospect information that personalizes the conversation.

Usage:
    python scripts/call_insurance_prospects.py                  # Call sample prospects
    python scripts/call_insurance_prospects.py --list-prospects # Show prospect list
"""

import asyncio
import json
import sys
from pathlib import Path
from typing import Any, Dict, List

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import get_settings
from app.vapi_client import initiate_outbound_call


# Sample insurance prospects for testing
SAMPLE_PROSPECTS: List[Dict[str, Any]] = [
    {
        "phone_number": "+14155552671",
        "prospect_name": "John Smith",
        "company_name": "Smith Manufacturing Co.",
        "industry": "Manufacturing",
        "estimated_employees": 45,
        "location": "California",
        "lead_id": "lead_001",
    },
    {
        "phone_number": "+14155552672",
        "prospect_name": "Sarah Johnson",
        "company_name": "Johnson Logistics Inc.",
        "industry": "Logistics & Transportation",
        "estimated_employees": 120,
        "location": "Texas",
        "lead_id": "lead_002",
    },
    {
        "phone_number": "+14155552673",
        "prospect_name": "Michael Chen",
        "company_name": "Chen's Retail Group",
        "industry": "Retail",
        "estimated_employees": 28,
        "location": "New York",
        "lead_id": "lead_003",
    },
    {
        "phone_number": "+14155552674",
        "prospect_name": "Emily Rodriguez",
        "company_name": "Rodriguez Tech Solutions",
        "industry": "Software Development",
        "estimated_employees": 15,
        "location": "Florida",
        "lead_id": "lead_004",
    },
    {
        "phone_number": "+14155552675",
        "prospect_name": "David Thompson",
        "company_name": "Thompson Construction LLC",
        "industry": "Construction",
        "estimated_employees": 75,
        "location": "Washington",
        "lead_id": "lead_005",
    },
]


async def call_prospect(prospect: Dict[str, Any]) -> Dict[str, Any]:
    """Make an outbound call to a prospect.
    
    Args:
        prospect: Prospect information dictionary
        
    Returns:
        Response from Vapi API
    """
    
    prospect_info = {
        "prospect_name": prospect["prospect_name"],
        "company_name": prospect["company_name"],
        "call_type": "insurance_prospect",
        "industry": prospect["industry"],
        "estimated_employees": prospect["estimated_employees"],
        "location": prospect["location"],
        "lead_id": prospect["lead_id"],
    }
    
    try:
        response = await initiate_outbound_call(
            prospect["phone_number"],
            prospect_info=prospect_info,
        )
        return {
            "status": "success",
            "prospect": prospect["prospect_name"],
            "company": prospect["company_name"],
            "phone": prospect["phone_number"],
            "call_id": response.get("id"),
            "response": response,
        }
    except Exception as e:
        return {
            "status": "failed",
            "prospect": prospect["prospect_name"],
            "company": prospect["company_name"],
            "phone": prospect["phone_number"],
            "error": str(e),
        }


async def call_all_prospects(prospects: List[Dict[str, Any]] | None = None) -> None:
    """Make outbound calls to all prospects.
    
    Args:
        prospects: List of prospect dictionaries. Uses SAMPLE_PROSPECTS if None.
    """
    
    if prospects is None:
        prospects = SAMPLE_PROSPECTS
    
    print(f"\n{'='*70}")
    print(f"🎯 Insurance Prospect Outbound Calling Campaign")
    print(f"{'='*70}")
    print(f"Initiating calls to {len(prospects)} prospects...\n")
    
    results = []
    for i, prospect in enumerate(prospects, 1):
        print(f"[{i}/{len(prospects)}] Calling {prospect['prospect_name']} at {prospect['company_name']}...")
        result = await call_prospect(prospect)
        results.append(result)
        
        if result["status"] == "success":
            print(f"  ✅ Call queued successfully (ID: {result['call_id']})")
        else:
            print(f"  ❌ Call failed: {result['error']}")
        
        # Small delay between calls to avoid rate limiting
        if i < len(prospects):
            await asyncio.sleep(2)
    
    # Print summary
    print(f"\n{'='*70}")
    print("📊 Campaign Summary")
    print(f"{'='*70}")
    
    successful = sum(1 for r in results if r["status"] == "success")
    failed = sum(1 for r in results if r["status"] == "failed")
    
    print(f"Total calls attempted: {len(results)}")
    print(f"Successful: {successful} ✅")
    print(f"Failed: {failed} ❌")
    print(f"Success rate: {(successful/len(results)*100):.1f}%")
    
    # Save detailed results
    results_file = Path("data/prospect_calls_log.json")
    results_file.parent.mkdir(parents=True, exist_ok=True)
    results_file.write_text(json.dumps(results, indent=2))
    print(f"\n📝 Detailed results saved to: {results_file}")


def list_prospects(prospects: List[Dict[str, Any]] | None = None) -> None:
    """Display list of prospects.
    
    Args:
        prospects: List of prospect dictionaries. Uses SAMPLE_PROSPECTS if None.
    """
    
    if prospects is None:
        prospects = SAMPLE_PROSPECTS
    
    print(f"\n{'='*70}")
    print(f"📋 Insurance Prospects")
    print(f"{'='*70}\n")
    
    for i, prospect in enumerate(prospects, 1):
        print(f"{i}. {prospect['prospect_name']}")
        print(f"   Company: {prospect['company_name']}")
        print(f"   Industry: {prospect['industry']}")
        print(f"   Employees: {prospect['estimated_employees']}")
        print(f"   Location: {prospect['location']}")
        print(f"   Phone: {prospect['phone_number']}")
        print(f"   Lead ID: {prospect['lead_id']}\n")


async def main() -> None:
    """Main entry point."""
    
    # Validate environment
    settings = get_settings()
    
    if not settings.vapi_agent_id:
        print("❌ Error: VAPI_AGENT_ID not set in environment")
        print("Please run: python scripts/start_call.py create-agent")
        sys.exit(1)
    
    # Parse arguments
    if len(sys.argv) > 1:
        if sys.argv[1] == "--list-prospects":
            list_prospects()
            return
        elif sys.argv[1] == "--help":
            print(__doc__)
            return
    
    # Run the calling campaign
    await call_all_prospects()


if __name__ == "__main__":
    asyncio.run(main())
