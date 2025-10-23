"""
Simple script to add a customer to the database.

Usage:
    python scripts/add_customer.py --phone "+14698674545" --company "Gillella Tech Solutions" --industry "Software Development" --location "California"
    
    python scripts/add_customer.py --phone "+15551234567" --company "Smith Manufacturing" --industry "Manufacturing" --location "Texas"
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.customer_manager import CustomerManager
from app.models import CustomerCreate
from scripts.cli_utils import print_section, print_subsection, setup_environment


def main():
    """Main entry point."""
    import argparse

    setup_environment()

    parser = argparse.ArgumentParser(
        description="Add a customer to the database",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Add Anish's company
  python scripts/add_customer.py \\
    --phone "+14698674545" \\
    --company "Gillella Tech Solutions" \\
    --industry "Software Development" \\
    --location "California"

  # Add another company
  python scripts/add_customer.py \\
    --phone "+15551234567" \\
    --company "Smith Manufacturing Co." \\
    --industry "Manufacturing" \\
    --location "Texas"

  # Minimal (only required fields)
  python scripts/add_customer.py \\
    --phone "+14155551234" \\
    --company "My Company"
        """,
    )

    # Required arguments
    parser.add_argument(
        "--phone",
        type=str,
        required=True,
        help="Phone number (E.164 format, e.g., +14698674545)",
    )
    parser.add_argument(
        "--company",
        type=str,
        required=True,
        help="Company name",
    )

    # Optional arguments
    parser.add_argument(
        "--first-name",
        type=str,
        default=None,
        help="Contact person first name (optional)",
    )
    parser.add_argument(
        "--last-name",
        type=str,
        default=None,
        help="Contact person last name (optional)",
    )
    parser.add_argument(
        "--email",
        type=str,
        default=None,
        help="Email address (optional)",
    )
    parser.add_argument(
        "--industry",
        type=str,
        default=None,
        help="Industry/business type (optional)",
    )
    parser.add_argument(
        "--location",
        type=str,
        default=None,
        help="Location/state (optional)",
    )

    args = parser.parse_args()

    print_section("➕ ADD CUSTOMER TO DATABASE", 70)

    try:
        # Validate phone number
        if not args.phone.startswith("+"):
            print("⚠️  Warning: Phone number should be in E.164 format (e.g., +14698674545)")

        # Create customer data
        customer_data = CustomerCreate(
            phone_number=args.phone,
            company_name=args.company,
            first_name=args.first_name,
            last_name=args.last_name,
            email=args.email,
            industry=args.industry,
            location=args.location,
        )

        # Initialize manager
        manager = CustomerManager()

        # Check if customer already exists
        print_subsection("Checking for existing customer", 50)
        existing = manager.get_customer_by_phone(args.phone)

        if existing:
            print(f"⚠️  Customer already exists!")
            print(f"   ID: {existing.id}")
            print(f"   First Name: {existing.first_name or 'N/A'}")
            print(f"   Last Name: {existing.last_name or 'N/A'}")
            print(f"   Email: {existing.email or 'N/A'}")
            print(f"   Company: {existing.company_name}")
            print(f"   Phone: {existing.phone_number}")
            print(f"   Industry: {existing.industry or 'N/A'}")
            print(f"   Location: {existing.location or 'N/A'}")
            print(f"   Created: {existing.created_at.strftime('%Y-%m-%d %H:%M:%S')}\n")

            confirm = input("Overwrite with new data? (yes/no): ").strip().lower()
            if confirm != "yes":
                print("Cancelled.\n")
                return

        # Create/update customer
        print_subsection("Creating/updating customer", 50)
        if existing:
            customer = manager.update_customer(args.phone, customer_data)
        else:
            customer = manager.create_customer(customer_data)

        print(f"✅ Customer created/updated successfully!")
        print(f"\n📋 Customer Details:")
        print(f"   ID:         {customer.id}")
        print(f"   First Name: {customer.first_name or 'N/A'}")
        print(f"   Last Name:  {customer.last_name or 'N/A'}")
        print(f"   Email:      {customer.email or 'N/A'}")
        print(f"   Company:    {customer.company_name}")
        print(f"   Phone:      {customer.phone_number}")
        print(f"   Industry:   {customer.industry or 'N/A'}")
        print(f"   Location:   {customer.location or 'N/A'}")
        print(f"   Created:    {customer.created_at.strftime('%Y-%m-%d %H:%M:%S')}\n")

        print("🎯 Next steps:")
        print(f"   1. Call customer: python scripts/import_and_call_customers.py --call-phones {args.phone}")
        print(f"   2. List customers: python scripts/import_and_call_customers.py --list\n")

    except Exception as e:
        print(f"\n❌ Error: {e}\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
