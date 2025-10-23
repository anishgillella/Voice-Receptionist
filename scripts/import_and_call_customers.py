"""
CLI script for bulk customer import and outbound calling.

Usage:
    python scripts/import_and_call_customers.py --import customers.json
    python scripts/import_and_call_customers.py --call all
    python scripts/import_and_call_customers.py --call-phones 4698674545,1234567890
    python scripts/import_and_call_customers.py --list
"""

import asyncio
import csv
import json
import logging
import sys
from pathlib import Path
from typing import Any, Dict, List

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from cli_utils import print_section, print_subsection, setup_environment
from app.customer_manager import CustomerManager
from app.call_manager import CallManager
from app.models import CustomerCreate

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


class CustomerImportCLI:
    """CLI for customer import and bulk calling."""

    def __init__(self):
        """Initialize CLI."""
        self.customer_manager = CustomerManager()
        self.call_manager = CallManager()

    def load_customers_from_json(self, filepath: str) -> List[Dict[str, Any]]:
        """Load customers from JSON file.

        Args:
            filepath: Path to JSON file

        Returns:
            List of customer dictionaries

        Raises:
            FileNotFoundError: If file doesn't exist
            json.JSONDecodeError: If JSON is invalid
        """
        print_subsection("Loading from JSON", 50)
        path = Path(filepath)

        if not path.exists():
            raise FileNotFoundError(f"File not found: {filepath}")

        with open(path, "r") as f:
            data = json.load(f)

        # Handle both list and dict formats
        if isinstance(data, dict):
            customers = data.get("customers", [data])
        else:
            customers = data

        print(f"✓ Loaded {len(customers)} customers from {filepath}\n")
        return customers

    def load_customers_from_csv(self, filepath: str) -> List[Dict[str, Any]]:
        """Load customers from CSV file.

        Args:
            filepath: Path to CSV file (must have headers)

        Returns:
            List of customer dictionaries

        Raises:
            FileNotFoundError: If file doesn't exist
        """
        print_subsection("Loading from CSV", 50)
        path = Path(filepath)

        if not path.exists():
            raise FileNotFoundError(f"File not found: {filepath}")

        customers = []
        with open(path, "r") as f:
            reader = csv.DictReader(f)
            for row in reader:
                customers.append(dict(row))

        print(f"✓ Loaded {len(customers)} customers from {filepath}\n")
        return customers

    def import_customers(self, filepath: str) -> Dict[str, Any]:
        """Import customers from file (JSON or CSV).

        Args:
            filepath: Path to customer file

        Returns:
            Import results dictionary
        """
        print_section("📥 CUSTOMER IMPORT", 70)

        # Determine file type
        if filepath.endswith(".json"):
            customers = self.load_customers_from_json(filepath)
        elif filepath.endswith(".csv"):
            customers = self.load_customers_from_csv(filepath)
        else:
            raise ValueError("File must be .json or .csv")

        # Import customers
        results = self.customer_manager.bulk_import_customers(customers)

        # Print results
        print_subsection("Import Results", 50)
        print(f"Total:    {results['total']}")
        print(f"Created:  {results['created']} ✓")
        print(f"Existing: {results['existing']} ✓")
        print(f"Failed:   {results['failed']} ✗")

        if results["errors"]:
            print("\n❌ Errors:")
            for error in results["errors"]:
                print(f"   {error}")

        print(f"\n✅ Import complete!\n")
        return results

    def list_customers(self, limit: int = 10) -> None:
        """List customers in database.

        Args:
            limit: Maximum customers to show
        """
        print_section("📋 CUSTOMER LIST", 70)

        customers = self.customer_manager.get_all_customers()

        if not customers:
            print("No customers found in database\n")
            return

        print(f"Found {len(customers)} total customers. Showing last {min(len(customers), limit)}:\n")

        for i, customer in enumerate(customers[:limit], 1):
            print(f"{i}. {customer.company_name}")
            print(f"   Phone:    {customer.phone_number}")
            print(f"   Industry: {customer.industry or 'N/A'}")
            print(f"   Location: {customer.location or 'N/A'}")
            print(f"   Created:  {customer.created_at.strftime('%Y-%m-%d %H:%M:%S')}\n")

    async def call_all_customers(self, delay: float = 2.0) -> Dict[str, Any]:
        """Call all customers in database.

        Args:
            delay: Delay between calls in seconds

        Returns:
            Call results dictionary
        """
        print_section("📞 BULK CALLING ALL CUSTOMERS", 70)

        customers = self.customer_manager.get_customers_for_calling()

        if not customers:
            print("❌ No customers found in database\n")
            return {"total": 0, "successful": 0, "failed": 0, "calls": [], "errors": ["No customers"]}

        print(f"Found {len(customers)} customers ready for calling.\n")
        confirm = input("Proceed with calls? (yes/no): ").strip().lower()
        if confirm != "yes":
            print("Cancelled.\n")
            return {"total": 0, "successful": 0, "failed": 0, "calls": [], "errors": ["User cancelled"]}

        return await self.call_manager.bulk_call_customers(customers, delay)

    async def call_customers_by_phone(self, phone_numbers: List[str], delay: float = 2.0) -> Dict[str, Any]:
        """Call specific customers by phone number.

        Args:
            phone_numbers: List of phone numbers
            delay: Delay between calls in seconds

        Returns:
            Call results dictionary
        """
        print_section("📞 CALLING SPECIFIC CUSTOMERS", 70)

        return await self.call_manager.call_customers_by_phone_list(phone_numbers, delay)

    def print_call_results(self, results: Dict[str, Any]) -> None:
        """Print call results summary.

        Args:
            results: Call results dictionary
        """
        print_subsection("Call Results", 50)
        print(f"Total:      {results['total']}")
        print(f"Successful: {results['successful']} ✓")
        print(f"Failed:     {results['failed']} ✗")

        if results["calls"]:
            print("\n📞 Call Details:")
            for call in results["calls"]:
                status = "✓" if call["status"] == "success" else "✗"
                call_id = call.get("call_id", "N/A")
                error = call.get("error", "")
                print(
                    f"   {status} {call['phone_number']} ({call['company_name']}) - {call_id} {error}"
                )

        if results["errors"]:
            print("\n❌ Errors:")
            for error in results["errors"][:5]:  # Show first 5 errors
                print(f"   - {error}")

        print(f"\n✅ Calling complete!\n")

    async def _trigger_backend_processing(self) -> None:
        """Trigger backend processing of calls (transcripts and embeddings)."""
        try:
            import httpx
            from app.config import get_settings
            
            settings = get_settings()
            backend_url = settings.backend_base_url or "http://localhost:8000"
            
            # Wait for calls to complete (typically 30-40 seconds)
            print("\n⏳ Waiting 60 seconds for calls to complete...")
            for i in range(60):
                await asyncio.sleep(1)
                if (i + 1) % 10 == 0:
                    print(f"   {i + 1}/60 seconds...")
            
            print("\n🔄 Processing calls (fetching transcripts & generating embeddings)...")
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(f"{backend_url}/process-calls")
                result = response.json()
                
                processed = result.get("processed", 0)
                failed = result.get("failed", 0)
                
                if processed > 0:
                    print(f"✅ Successfully processed {processed} call(s)")
                    if result.get("processed_calls"):
                        for call_id in result["processed_calls"]:
                            print(f"   - {call_id}")
                
                if failed > 0:
                    print(f"⚠️ Failed: {failed} call(s)")
                    for err in result.get("failed_calls", []):
                        print(f"   - {err.get('call_id')}: {err.get('error')}")
                
                if processed == 0 and failed == 0:
                    print("ℹ️ No pending calls to process")
        except Exception as e:
            print(f"⚠️ Backend processing error: {e}")


async def main():
    """Main CLI entry point."""
    import argparse

    setup_environment()

    parser = argparse.ArgumentParser(
        description="Bulk customer import and calling system",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Import customers from JSON
  python scripts/import_and_call_customers.py --import data/customers.json

  # Import customers from CSV
  python scripts/import_and_call_customers.py --import data/customers.csv

  # List all customers
  python scripts/import_and_call_customers.py --list

  # Call all customers
  python scripts/import_and_call_customers.py --call all

  # Call specific customers
  python scripts/import_and_call_customers.py --call-phones +14698674545,+15551234567

  # Call with delay between calls
  python scripts/import_and_call_customers.py --call all --delay 3
        """,
    )

    parser.add_argument("--import", type=str, dest="import_file", help="Import customers from JSON/CSV file")
    parser.add_argument("--list", action="store_true", help="List all customers")
    parser.add_argument("--call", type=str, choices=["all"], help="Call all customers")
    parser.add_argument(
        "--call-phones", type=str, help="Call specific customers (comma-separated phone numbers)"
    )
    parser.add_argument("--delay", type=float, default=2.0, help="Delay between calls (seconds)")
    parser.add_argument("--limit", type=int, default=10, help="Limit for --list (default 10)")

    args = parser.parse_args()

    cli = CustomerImportCLI()

    try:
        if args.import_file:
            cli.import_customers(args.import_file)
        elif args.list:
            cli.list_customers(limit=args.limit)
        elif args.call == "all":
            results = await cli.call_all_customers(delay=args.delay)
            cli.print_call_results(results)
            # Auto-process calls
            await cli._trigger_backend_processing()
        elif args.call_phones:
            phones = [p.strip() for p in args.call_phones.split(",")]
            results = await cli.call_customers_by_phone(phones, delay=args.delay)
            cli.print_call_results(results)
            # Auto-process calls
            await cli._trigger_backend_processing()
        else:
            parser.print_help()

    except Exception as e:
        print(f"\n❌ Error: {e}\n")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
