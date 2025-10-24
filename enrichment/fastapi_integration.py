"""FastAPI integration examples for enrichment with webhooks and S3 storage."""

from __future__ import annotations

import asyncio
import logging
from typing import List, Optional

from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel

from .manager import TaskManager
from .models import EnrichmentItem, TaskStatus
from .storage import EnrichmentResultsStorage
from .webhooks import WebhookHandler

logger = logging.getLogger(__name__)


class EnrichmentRequest(BaseModel):
    """Request to start enrichment."""

    customer_id: str
    items: List[dict]
    enrichment_prompt: str
    batch_size: Optional[int] = 50
    wait_for_results: bool = False


class EnrichmentResponse(BaseModel):
    """Response from starting enrichment."""

    status: str
    task_ids: List[str]
    message: str


def setup_enrichment_routes(
    app: FastAPI,
    task_manager: Optional[TaskManager] = None,
    storage: Optional[EnrichmentResultsStorage] = None,
) -> WebhookHandler:
    """Set up enrichment routes on a FastAPI app.

    Args:
        app: FastAPI application
        task_manager: Optional TaskManager instance
        storage: Optional EnrichmentResultsStorage instance

    Returns:
        WebhookHandler instance for custom callbacks
    """
    manager = task_manager or TaskManager()
    storage_instance = storage or EnrichmentResultsStorage()
    webhook_handler = WebhookHandler(task_manager=manager, storage=storage_instance)

    @app.post("/api/enrichment/enrich")
    async def trigger_enrichment(request: EnrichmentRequest) -> EnrichmentResponse:
        """Trigger data enrichment.

        Args:
            request: EnrichmentRequest with items and prompt

        Returns:
            EnrichmentResponse with task IDs

        Example:
            ```python
            response = await client.post(
                "/api/enrichment/enrich",
                json={
                    "customer_id": "cust_123",
                    "items": [
                        {"id": "1", "data": {"company": "Acme Corp"}}
                    ],
                    "enrichment_prompt": "Find employee count and revenue"
                }
            )
            ```
        """
        try:
            # Convert to EnrichmentItems
            items = [
                EnrichmentItem(
                    id=item["id"],
                    data=item.get("data", {}),
                    metadata={"customer_id": request.customer_id},
                )
                for item in request.items
            ]

            logger.info(
                f"Starting enrichment for customer {request.customer_id} "
                f"with {len(items)} items"
            )

            # Start enrichment
            responses = await manager.enrich_items_parallel(
                items=items,
                enrichment_prompt=request.enrichment_prompt,
                batch_size=request.batch_size,
                poll=request.wait_for_results,
            )

            task_ids = [r.task_group_id for r in responses]

            # If not waiting, return task IDs immediately
            if not request.wait_for_results:
                return EnrichmentResponse(
                    status="started",
                    task_ids=task_ids,
                    message=f"Enrichment started for {len(items)} items. "
                    f"Task IDs: {', '.join(task_ids)}",
                )

            # If waiting, store results and return
            stored_results = []
            for response in responses:
                try:
                    results = await manager.get_results(response.task_group_id)
                    storage_info = await storage_instance.store_results(
                        results=results,
                        customer_id=request.customer_id,
                    )
                    stored_results.append(storage_info)
                except Exception as e:
                    logger.error(f"Failed to store results: {e}")

            return EnrichmentResponse(
                status="completed",
                task_ids=task_ids,
                message=f"Enrichment completed and stored in S3",
            )

        except Exception as e:
            logger.error(f"Failed to start enrichment: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    @app.get("/api/enrichment/status/{task_id}")
    async def get_task_status(task_id: str) -> dict:
        """Get status of an enrichment task.

        Args:
            task_id: Task ID from enrichment response

        Returns:
            Task status and progress information

        Example:
            ```python
            response = await client.get("/api/enrichment/status/task_123")
            ```
        """
        try:
            status_info = await manager.get_task_status(task_id)
            return status_info
        except Exception as e:
            logger.error(f"Failed to get task status: {e}")
            raise HTTPException(status_code=404, detail=f"Task not found: {task_id}")

    @app.get("/api/enrichment/results/{customer_id}/{task_id}")
    async def get_results(customer_id: str, task_id: str) -> dict:
        """Get enrichment results from S3.

        Args:
            customer_id: Customer ID
            task_id: Task ID

        Returns:
            Enrichment results from S3

        Example:
            ```python
            response = await client.get(
                "/api/enrichment/results/cust_123/task_456"
            )
            ```
        """
        try:
            results = await storage_instance.retrieve_results(
                customer_id=customer_id,
                task_id=task_id,
            )
            if not results:
                raise HTTPException(status_code=404, detail="Results not found")
            return results
        except Exception as e:
            logger.error(f"Failed to retrieve results: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    @app.get("/api/enrichment/list/{customer_id}")
    async def list_customer_enrichments(customer_id: str) -> dict:
        """List all enrichment results for a customer.

        Args:
            customer_id: Customer ID

        Returns:
            List of enrichment results in S3

        Example:
            ```python
            response = await client.get("/api/enrichment/list/cust_123")
            ```
        """
        try:
            results = await storage_instance.list_results(customer_id=customer_id)
            return {
                "customer_id": customer_id,
                "count": len(results),
                "results": results,
            }
        except Exception as e:
            logger.error(f"Failed to list results: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    @app.post("/api/enrichment/webhook")
    async def handle_enrichment_webhook(request: Request) -> dict:
        """Handle Parallel API webhook callback.

        This endpoint receives callbacks when enrichment tasks complete.

        **Setup in Parallel API Dashboard:**
        1. Go to Webhooks settings
        2. Set webhook URL to: `{your_domain}/api/enrichment/webhook`
        3. Select events: `task.completed`, `task.failed`
        4. Enable webhook

        Args:
            request: FastAPI Request with webhook payload

        Returns:
            Acknowledgment of webhook receipt

        Example payload:
            ```json
            {
                "event_type": "task.completed",
                "task_id": "task_123",
                "status": "completed",
                "results": {...},
                "metadata": {"customer_id": "cust_123"},
                "completed_at": "2024-10-23T12:34:56Z"
            }
            ```
        """
        return await webhook_handler.handle_webhook(request)

    @app.get("/api/enrichment/active-tasks")
    async def get_active_tasks() -> dict:
        """Get list of active enrichment tasks.

        Returns:
            Dict with active task information

        Example:
            ```python
            response = await client.get("/api/enrichment/active-tasks")
            ```
        """
        active_tasks = manager.get_active_tasks()
        return {
            "count": len(active_tasks),
            "tasks": active_tasks,
        }

    logger.info("✓ Enrichment routes registered on FastAPI app")

    return webhook_handler


async def setup_webhook_callbacks(webhook_handler: WebhookHandler):
    """Set up custom callbacks for webhook events.

    Args:
        webhook_handler: WebhookHandler instance
    """

    async def on_task_completed(payload):
        """Handle task.completed event."""
        logger.info(f"✓ Custom handler: Task {payload.task_id} completed")

    async def on_task_failed(payload):
        """Handle task.failed event."""
        logger.error(f"✗ Custom handler: Task {payload.task_id} failed: {payload.error}")

    # Register callbacks
    webhook_handler.register_callback("task.completed", on_task_completed)
    webhook_handler.register_callback("task.failed", on_task_failed)

    logger.info("✓ Webhook callbacks registered")


# Example usage in a FastAPI application
def example_app_setup():
    """Example of setting up enrichment with FastAPI.

    Usage:
        ```python
        from fastapi import FastAPI
        from enrichment.fastapi_integration import example_app_setup

        app = FastAPI()
        setup_enrichment_routes(app)
        ```
    """
    app = FastAPI(title="Enrichment Service")

    # Set up enrichment routes
    webhook_handler = setup_enrichment_routes(app)

    # Set up webhook callbacks
    @app.on_event("startup")
    async def startup():
        await setup_webhook_callbacks(webhook_handler)

    return app
