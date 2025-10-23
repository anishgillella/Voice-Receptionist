"""Call management operations for bulk outbound calling."""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, List, Optional
from datetime import datetime

import httpx

from .config import settings, INSURANCE_PROSPECT_SYSTEM_PROMPT, get_settings
from .context_manager import ContextManager
from .customer_manager import CustomerManager
from .vapi_client import initiate_outbound_call

logger = logging.getLogger(__name__)


class CallManager:
    """Manages outbound calls for customers."""

    def __init__(self):
        """Initialize call manager."""
        self.base_url = settings.backend_base_url or "http://localhost:8000"
        self.vapi_api_key = settings.vapi_api_key
        self.context_manager = ContextManager()
        self.customer_manager = CustomerManager()

    async def call_customer(
        self, customer_data: Dict[str, Any], delay_between_calls: float = 2.0
    ) -> Dict[str, Any]:
        """Make an outbound call to a single customer with personalized context.

        Args:
            customer_data: Customer dictionary with phone_number, company_name, industry, location
            delay_between_calls: Delay in seconds before next call (to avoid rate limiting)

        Returns:
            Dictionary with call result: {
                'status': 'success' | 'failed',
                'phone_number': str,
                'company_name': str,
                'call_id': str (if successful),
                'error': str (if failed)
            }
        """
        try:
            phone = customer_data.get("phone_number")
            company = customer_data.get("company_name")
            industry = customer_data.get("industry")
            location = customer_data.get("location")

            logger.info(f"Initiating call to {phone} ({company})")

            # Get customer from database to build context
            customer = self.customer_manager.get_customer_by_phone(phone)
            
            if customer:
                # Build personalized context
                context = self.context_manager.build_agent_context(
                    customer=customer,
                    current_topic=f"Calling {company} about insurance solutions",
                    include_conversations=True,
                )
                
                logger.info(f"Built context for {phone}: ~{context['token_estimate']} tokens")
                personalized_prompt = self.context_manager.inject_context_to_system_prompt(
                    base_prompt=INSURANCE_PROSPECT_SYSTEM_PROMPT,
                    context=context,
                )
            else:
                logger.warning(f"Customer not found for {phone}, using default prompt")
                personalized_prompt = INSURANCE_PROSPECT_SYSTEM_PROMPT

            # Prepare call data
            call_payload = {
                "phone_number": phone,
                "prospect_name": company.split()[0] if company else "Prospect",
                "company_name": company,
                "industry": industry or "Insurance",
                "location": location or "Unknown",
                "estimated_employees": 50,  # Default
                "system_prompt": personalized_prompt,  # NEW: Pass personalized prompt
            }

            # Make the call via FastAPI endpoint
            response = await initiate_outbound_call(
                phone,
                prospect_info={
                    "prospect_name": call_payload["prospect_name"],
                    "company_name": company,
                    "industry": industry,
                    "location": location,
                    "call_type": "insurance_prospect",
                },
                system_prompt=personalized_prompt,  # NEW: Pass personalized prompt
            )

            call_id = response.get("id")
            logger.info(f"Call initiated successfully: {call_id} to {phone}")

            # Track call for transcript processing
            from . import main
            main._pending_calls[call_id] = {"customer_phone": phone, "initiated_at": datetime.now()}
            logger.info(f"Added call {call_id} to pending transcript queue")
            
            # Trigger immediate background processing after call
            async def process_after_delay():
                """Wait for call to complete, then process transcript."""
                await asyncio.sleep(45)  # Wait for call to complete
                logger.info(f"Auto-processing call {call_id} after delay")
                settings = get_settings()
                await main._process_call_transcript(call_id, phone, settings)
            
            asyncio.create_task(process_after_delay())

            return {
                "status": "success",
                "phone_number": phone,
                "company_name": company,
                "call_id": call_id,
            }

        except Exception as e:
            error_msg = str(e)
            logger.error(f"Failed to call {customer_data.get('phone_number')}: {error_msg}")
            return {
                "status": "failed",
                "phone_number": customer_data.get("phone_number"),
                "company_name": customer_data.get("company_name"),
                "error": error_msg,
            }

    async def bulk_call_customers(
        self,
        customers: List[Dict[str, Any]],
        delay_between_calls: float = 2.0,
        max_concurrent: int = 1,
    ) -> Dict[str, Any]:
        """Call multiple customers in bulk.

        Args:
            customers: List of customer dictionaries
            delay_between_calls: Seconds to wait between calls
            max_concurrent: Maximum concurrent calls (default 1 to avoid rate limiting)

        Returns:
            Dictionary with bulk call results: {
                'total': int,
                'successful': int,
                'failed': int,
                'calls': List[Dict],
                'errors': List[str]
            }
        """
        logger.info(f"Starting bulk calling for {len(customers)} customers")

        results = {
            "total": len(customers),
            "successful": 0,
            "failed": 0,
            "calls": [],
            "errors": [],
        }

        # Make calls sequentially to avoid rate limiting
        for idx, customer in enumerate(customers, 1):
            try:
                logger.info(f"[{idx}/{len(customers)}] Calling {customer.get('company_name')}")

                call_result = await self.call_customer(customer, delay_between_calls)

                if call_result["status"] == "success":
                    results["successful"] += 1
                    logger.info(f"✓ Call {call_result['call_id']} queued")
                else:
                    results["failed"] += 1
                    error = call_result.get("error", "Unknown error")
                    results["errors"].append(f"{customer.get('phone_number')}: {error}")
                    logger.error(f"✗ Call failed: {error}")

                results["calls"].append(call_result)

                # Delay before next call
                if idx < len(customers):
                    await asyncio.sleep(delay_between_calls)

            except Exception as e:
                results["failed"] += 1
                error_msg = f"Exception on {customer.get('phone_number')}: {str(e)}"
                results["errors"].append(error_msg)
                logger.error(error_msg)

        logger.info(
            f"Bulk calling complete: {results['successful']} successful, "
            f"{results['failed']} failed out of {results['total']}"
        )

        return results

    async def call_customers_by_phone_list(
        self, phone_numbers: List[str], delay_between_calls: float = 2.0
    ) -> Dict[str, Any]:
        """Call customers by phone number list (requires database lookup).

        Args:
            phone_numbers: List of phone numbers to call
            delay_between_calls: Delay between calls in seconds

        Returns:
            Bulk call results
        """
        customers = []

        logger.info(f"Looking up {len(phone_numbers)} customers")

        for phone in phone_numbers:
            customer = self.customer_manager.get_customer_by_phone(phone)
            if customer:
                customers.append(
                    {
                        "id": str(customer.id),
                        "phone_number": customer.phone_number,
                        "company_name": customer.company_name,
                        "industry": customer.industry,
                        "location": customer.location,
                    }
                )
            else:
                logger.warning(f"Customer not found for phone: {phone}")

        if not customers:
            logger.warning("No customers found for calling")
            return {
                "total": 0,
                "successful": 0,
                "failed": 0,
                "calls": [],
                "errors": ["No customers found in database"],
            }

        return await self.bulk_call_customers(customers, delay_between_calls)

