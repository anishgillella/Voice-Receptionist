"""Customer management operations for bulk import and management."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
from uuid import UUID

from .db import get_db
from .models import Customer, CustomerCreate

logger = logging.getLogger(__name__)


class CustomerManager:
    """Manages customer operations including bulk import."""

    def __init__(self):
        """Initialize customer manager."""
        self.db = get_db()

    def update_customer(self, phone_number: str, customer_data: CustomerCreate) -> Customer:
        """Update an existing customer.

        Args:
            phone_number: Phone number of customer to update
            customer_data: Updated customer data

        Returns:
            Updated customer object

        Raises:
            ValueError: If customer not found or update fails
        """
        update_query = """
            UPDATE customers 
            SET company_name = %s, first_name = %s, last_name = %s, email = %s, industry = %s, location = %s, updated_at = NOW()
            WHERE phone_number = %s
            RETURNING id, company_name, phone_number, first_name, last_name, email, industry, location, created_at
        """

        result = self.db.insert(
            update_query,
            (
                customer_data.company_name,
                customer_data.first_name,
                customer_data.last_name,
                customer_data.email,
                customer_data.industry,
                customer_data.location,
                phone_number,
            ),
        )

        if result:
            logger.info(f"Updated customer: {phone_number}")
            return Customer(**result)

        raise ValueError(f"Failed to update customer {phone_number}")

    def create_customer(self, customer_data: CustomerCreate) -> Customer:
        """Create a new customer.

        Args:
            customer_data: Customer creation data

        Returns:
            Created customer object

        Raises:
            ValueError: If customer creation fails
        """
        from uuid import uuid4

        customer_id = str(uuid4())

        insert_query = """
            INSERT INTO customers (id, phone_number, company_name, first_name, last_name, email, industry, location, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW())
            RETURNING id, company_name, phone_number, first_name, last_name, email, industry, location, created_at
        """

        result = self.db.insert(
            insert_query,
            (
                customer_id,
                customer_data.phone_number,
                customer_data.company_name,
                customer_data.first_name,
                customer_data.last_name,
                customer_data.email,
                customer_data.industry,
                customer_data.location,
            ),
        )

        if result:
            logger.info(f"Created customer: {customer_data.phone_number}")
            return Customer(**result)

        raise ValueError(f"Failed to create customer {customer_data.phone_number}")

    def get_or_create_customer(self, customer_data: CustomerCreate) -> Customer:
        """Get existing customer or create if doesn't exist.

        Args:
            customer_data: Customer data (for creation if needed)

        Returns:
            Customer object (existing or newly created)
        """
        # Try to find existing
        query = "SELECT id, company_name, phone_number, first_name, last_name, email, industry, location, created_at FROM customers WHERE phone_number = %s"
        result = self.db.execute_one(query, (customer_data.phone_number,))

        if result:
            logger.info(f"Found existing customer: {customer_data.phone_number}")
            return Customer(**result)

        # Create new
        logger.info(f"Creating new customer: {customer_data.phone_number}")
        return self.create_customer(customer_data)

    def bulk_import_customers(
        self, customers_data: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Import multiple customers in bulk.

        Args:
            customers_data: List of customer dictionaries

        Returns:
            Dictionary with results: {
                'total': int,
                'created': int,
                'existing': int,
                'failed': int,
                'errors': List[str],
                'customers': List[Customer]
            }
        """
        logger.info(f"Starting bulk import of {len(customers_data)} customers")

        results = {
            "total": len(customers_data),
            "created": 0,
            "existing": 0,
            "failed": 0,
            "errors": [],
            "customers": [],
        }

        for idx, cust_data in enumerate(customers_data, 1):
            try:
                # Validate required fields
                if "phone_number" not in cust_data or not cust_data["phone_number"]:
                    raise ValueError(f"Row {idx}: Missing phone_number")
                if "company_name" not in cust_data or not cust_data["company_name"]:
                    raise ValueError(f"Row {idx}: Missing company_name")

                # Create Pydantic model
                customer_input = CustomerCreate(
                    phone_number=cust_data["phone_number"],
                    company_name=cust_data["company_name"],
                    first_name=cust_data.get("first_name"),
                    last_name=cust_data.get("last_name"),
                    email=cust_data.get("email"),
                    industry=cust_data.get("industry"),
                    location=cust_data.get("location"),
                )

                # Check if exists first
                existing_query = "SELECT id FROM customers WHERE phone_number = %s"
                existing = self.db.execute_one(existing_query, (cust_data["phone_number"],))

                if existing:
                    results["existing"] += 1
                    logger.debug(f"Row {idx}: Customer already exists - {cust_data['phone_number']}")
                    customer = self.get_or_create_customer(customer_input)
                else:
                    customer = self.create_customer(customer_input)
                    results["created"] += 1
                    logger.info(f"Row {idx}: Created customer - {cust_data['phone_number']}")

                results["customers"].append(customer)

            except Exception as e:
                results["failed"] += 1
                error_msg = f"Row {idx}: {str(e)}"
                results["errors"].append(error_msg)
                logger.error(error_msg)

        logger.info(
            f"Bulk import complete: {results['created']} created, "
            f"{results['existing']} existing, {results['failed']} failed"
        )

        return results

    def get_all_customers(self) -> List[Customer]:
        """Get all customers from database.

        Returns:
            List of customer objects
        """
        query = "SELECT id, company_name, phone_number, first_name, last_name, email, industry, location, created_at FROM customers ORDER BY created_at DESC"
        results = self.db.execute(query)
        customers = [Customer(**dict(r)) for r in results]
        logger.info(f"Retrieved {len(customers)} customers")
        return customers

    def get_customers_for_calling(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get customers ready for outbound calling.

        Args:
            limit: Maximum number of customers to return

        Returns:
            List of customers with call-ready data
        """
        if limit:
            query = """
                SELECT id, phone_number, company_name, first_name, last_name, email, industry, location
                FROM customers
                ORDER BY created_at DESC
                LIMIT %s
            """
            results = self.db.execute(query, (limit,))
        else:
            query = """
                SELECT id, phone_number, company_name, first_name, last_name, email, industry, location
                FROM customers
                ORDER BY created_at DESC
            """
            results = self.db.execute(query)

        customers = [dict(r) for r in results]
        logger.info(f"Retrieved {len(customers)} customers for calling")
        return customers

    def get_customer_by_phone(self, phone_number: str) -> Optional[Customer]:
        """Get customer by phone number.

        Args:
            phone_number: Phone number to search

        Returns:
            Customer object or None if not found
        """
        query = "SELECT id, company_name, phone_number, first_name, last_name, email, industry, location, created_at FROM customers WHERE phone_number = %s"
        result = self.db.execute_one(query, (phone_number,))
        return Customer(**result) if result else None

    def get_customer_by_id(self, customer_id: UUID) -> Optional[Customer]:
        """Get customer by ID.

        Args:
            customer_id: Customer UUID

        Returns:
            Customer object or None if not found
        """
        query = "SELECT id, company_name, phone_number, first_name, last_name, email, industry, location, created_at FROM customers WHERE id = %s"
        result = self.db.execute_one(query, (str(customer_id),))
        return Customer(**result) if result else None
