"""Webhook handlers for Parallel API task completion callbacks."""

from __future__ import annotations

import logging
from typing import Any, Callable, Dict, Optional

from fastapi import HTTPException, Request, status
from pydantic import BaseModel, Field

from .manager import TaskManager
from .models import TaskStatus
from .storage import EnrichmentResultsStorage

logger = logging.getLogger(__name__)


class WebhookPayload(BaseModel):
    """Payload from Parallel API webhook."""

    event_type: str = Field(..., description="Event type (e.g., 'task.completed')")
    task_id: str = Field(..., description="ID of the completed task")
    status: str = Field(..., description="Task status")
    results: Optional[Dict[str, Any]] = Field(None, description="Task results")
    error: Optional[str] = Field(None, description="Error message if failed")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Custom metadata")
    completed_at: Optional[str] = Field(None, description="ISO timestamp of completion")


class WebhookHandler:
    """Handle incoming webhooks from Parallel API."""

    def __init__(
        self,
        task_manager: Optional[TaskManager] = None,
        storage: Optional[EnrichmentResultsStorage] = None,
    ):
        """Initialize webhook handler.

        Args:
            task_manager: TaskManager instance (optional)
            storage: EnrichmentResultsStorage instance (optional)
        """
        self.task_manager = task_manager
        self.storage = storage or EnrichmentResultsStorage()
        self._callbacks: Dict[str, list[Callable]] = {}

    def register_callback(
        self,
        event_type: str,
        callback: Callable[[WebhookPayload], None],
    ) -> None:
        """Register a callback for an event type.

        Args:
            event_type: Event type (e.g., 'task.completed')
            callback: Async callback function
        """
        if event_type not in self._callbacks:
            self._callbacks[event_type] = []
        self._callbacks[event_type].append(callback)
        logger.info(f"Registered callback for event: {event_type}")

    async def handle_webhook(self, request: Request) -> Dict[str, str]:
        """Handle incoming webhook from Parallel API.

        Args:
            request: FastAPI Request object

        Returns:
            Dict with status

        Raises:
            HTTPException: If webhook validation fails
        """
        try:
            payload = await request.json()
        except Exception as e:
            logger.error(f"Invalid JSON payload: {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid JSON payload",
            )

        try:
            webhook_payload = WebhookPayload(**payload)
        except Exception as e:
            logger.error(f"Invalid webhook payload: {e}")
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Invalid payload: {str(e)}",
            )

        logger.info(
            f"Received webhook for task {webhook_payload.task_id}: "
            f"{webhook_payload.event_type}"
        )

        # Process event
        try:
            await self._process_webhook(webhook_payload)
        except Exception as e:
            logger.error(f"Error processing webhook: {e}")
            # Don't raise - we want to acknowledge receipt even if processing fails
            return {
                "status": "acknowledged",
                "warning": "Processing error - will retry",
            }

        return {"status": "processed"}

    async def _process_webhook(self, payload: WebhookPayload) -> None:
        """Process webhook payload based on event type.

        Args:
            payload: WebhookPayload
        """
        if payload.event_type == "task.completed":
            await self._handle_task_completed(payload)
        elif payload.event_type == "task.failed":
            await self._handle_task_failed(payload)
        else:
            logger.warning(f"Unknown event type: {payload.event_type}")

        # Call registered callbacks
        callbacks = self._callbacks.get(payload.event_type, [])
        for callback in callbacks:
            try:
                if hasattr(callback, "__await__"):
                    await callback(payload)
                else:
                    callback(payload)
            except Exception as e:
                logger.error(f"Error in callback: {e}")

    async def _handle_task_completed(self, payload: WebhookPayload) -> None:
        """Handle task.completed event.

        Args:
            payload: WebhookPayload
        """
        task_id = payload.task_id
        customer_id = payload.metadata.get("customer_id") if payload.metadata else None

        logger.info(f"✓ Task completed: {task_id}")

        if not customer_id:
            logger.warning(
                f"No customer_id in metadata for task {task_id}. "
                f"Skipping S3 storage."
            )
            return

        # Try to retrieve full results using task manager
        if self.task_manager:
            try:
                results = await self.task_manager.get_results(task_id)

                # Store results in S3
                storage_info = await self.storage.store_results(
                    results=results,
                    customer_id=customer_id,
                    task_name=f"task_{task_id}.json",
                )

                logger.info(
                    f"Stored results in S3: {storage_info['s3_url']}"
                )

            except Exception as e:
                logger.error(f"Failed to process completed task: {e}")
        else:
            # Just store the webhook payload
            try:
                storage_info = await self.storage.store_results(
                    results=payload.results or {},
                    customer_id=customer_id,
                    task_name=f"task_{task_id}_webhook.json",
                )
                logger.info(
                    f"Stored webhook payload in S3: {storage_info['s3_url']}"
                )
            except Exception as e:
                logger.error(f"Failed to store webhook payload: {e}")

    async def _handle_task_failed(self, payload: WebhookPayload) -> None:
        """Handle task.failed event.

        Args:
            payload: WebhookPayload
        """
        task_id = payload.task_id
        customer_id = payload.metadata.get("customer_id") if payload.metadata else None

        logger.error(
            f"✗ Task failed: {task_id}. Error: {payload.error}"
        )

        if customer_id:
            try:
                # Store error info in S3
                error_info = {
                    "task_id": task_id,
                    "status": "failed",
                    "error": payload.error,
                    "failed_at": payload.completed_at,
                    "metadata": payload.metadata,
                }

                import json
                from datetime import datetime
                s3_key = self.storage.build_s3_key(
                    customer_id,
                    task_id,
                    f"error_{task_id}.json",
                )

                json_content = json.dumps(error_info, indent=2)
                self.storage.s3_client.put_object(
                    Bucket=self.storage.bucket_name,
                    Key=s3_key,
                    Body=json_content.encode("utf-8"),
                    ContentType="application/json",
                )

                s3_url = self.storage.get_s3_url(s3_key)
                logger.info(f"Stored error info in S3: {s3_url}")

            except Exception as e:
                logger.error(f"Failed to store error info: {e}")

    def get_fastapi_route(self):
        """Get FastAPI route handler for this webhook.

        Returns:
            Async function to use as FastAPI route handler
        """
        async def route(request: Request) -> Dict[str, str]:
            return await self.handle_webhook(request)

        return route
