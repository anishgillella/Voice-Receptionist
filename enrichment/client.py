"""Task MCP Client for interacting with Parallel API."""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, List, Optional

import httpx

from .config import EnrichmentSettings, get_enrichment_settings
from .models import (
    TaskStatus,
    TaskType,
    EnrichmentItem,
    DeepResearchRequest,
    TaskGroupRequest,
    TaskGroupResponse,
    DeepResearchResponse,
    TaskResult,
    TaskResultsResponse,
)

logger = logging.getLogger(__name__)


class TaskMCPClient:
    """Client for interacting with Task MCP (Parallel API)."""

    def __init__(self, settings: Optional[EnrichmentSettings] = None):
        """Initialize the Task MCP client.

        Args:
            settings: EnrichmentSettings instance (uses cached defaults if not provided)
        """
        self.settings = settings or get_enrichment_settings()
        self.base_url = self.settings.parallel_api_base_url.rstrip("/")
        self.api_key = self.settings.parallel_api_key
        self._client: Optional[httpx.AsyncClient] = None

    async def __aenter__(self) -> TaskMCPClient:
        """Async context manager entry."""
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            headers={"Authorization": f"Bearer {self.api_key}"},
            timeout=self.settings.task_timeout_seconds,
        )
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit."""
        if self._client:
            await self._client.aclose()

    def _get_client(self) -> httpx.AsyncClient:
        """Get or create the HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                headers={"Authorization": f"Bearer {self.api_key}"},
                timeout=self.settings.task_timeout_seconds,
            )
        return self._client

    async def create_deep_research_task(
        self,
        request: DeepResearchRequest,
    ) -> DeepResearchResponse:
        """Create a deep research task.

        Args:
            request: Deep research request details

        Returns:
            Response with task ID and status

        Raises:
            httpx.HTTPError: If the API request fails
        """
        client = self._get_client()
        payload = {
            "query": request.query,
            "description": request.description,
            "metadata": request.metadata,
        }

        logger.info(f"Creating deep research task for query: {request.query}")

        response = await client.post("/task/deep-research", json=payload)
        response.raise_for_status()
        
        data = response.json()
        
        return DeepResearchResponse(
            task_id=data.get("task_id"),
            status=TaskStatus(data.get("status", "pending")),
            query=request.query,
            progress_url=data.get("progress_url"),
        )

    async def create_task_group(
        self,
        request: TaskGroupRequest,
    ) -> TaskGroupResponse:
        """Create a task group for parallel enrichment.

        Args:
            request: Task group request with items and enrichment prompt

        Returns:
            Response with task group ID and status

        Raises:
            httpx.HTTPError: If the API request fails
        """
        client = self._get_client()
        payload = {
            "name": request.name,
            "items": [
                {
                    "id": item.id,
                    "data": item.data,
                    "metadata": item.metadata,
                }
                for item in request.items
            ],
            "enrichment_prompt": request.enrichment_prompt,
            "metadata": request.metadata,
        }

        logger.info(f"Creating task group '{request.name}' with {len(request.items)} items")

        response = await client.post("/task/group", json=payload)
        response.raise_for_status()
        
        data = response.json()
        
        return TaskGroupResponse(
            task_group_id=data.get("task_group_id"),
            status=TaskStatus(data.get("status", "pending")),
            items_count=len(request.items),
            progress_url=data.get("progress_url"),
        )

    async def get_result(self, task_id: str) -> TaskResultsResponse:
        """Get results of a completed task.

        Args:
            task_id: ID of the task to retrieve results for

        Returns:
            Response containing task results

        Raises:
            httpx.HTTPError: If the API request fails
        """
        client = self._get_client()
        
        logger.info(f"Fetching results for task: {task_id}")
        
        response = await client.get(f"/task/{task_id}/result")
        response.raise_for_status()
        
        data = response.json()
        
        # Parse individual results
        results = []
        for result_data in data.get("results", []):
            result = TaskResult(
                task_id=task_id,
                item_id=result_data.get("item_id"),
                status=TaskStatus(result_data.get("status", "failed")),
                enriched_data=result_data.get("enriched_data"),
                raw_result=result_data.get("raw_result"),
                error=result_data.get("error"),
                completed_at=result_data.get("completed_at"),
            )
            results.append(result)
        
        return TaskResultsResponse(
            task_id=task_id,
            status=TaskStatus(data.get("status")),
            results=results,
            completed_count=data.get("completed_count", 0),
            failed_count=data.get("failed_count", 0),
            completed_at=data.get("completed_at"),
        )

    async def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """Get the current status of a task.

        Args:
            task_id: ID of the task

        Returns:
            Task status information

        Raises:
            httpx.HTTPError: If the API request fails
        """
        client = self._get_client()
        
        response = await client.get(f"/task/{task_id}/status")
        response.raise_for_status()
        
        return response.json()

    async def cancel_task(self, task_id: str) -> Dict[str, Any]:
        """Cancel a running task.

        Args:
            task_id: ID of the task to cancel

        Returns:
            Cancellation response

        Raises:
            httpx.HTTPError: If the API request fails
        """
        client = self._get_client()
        
        logger.info(f"Cancelling task: {task_id}")
        
        response = await client.post(f"/task/{task_id}/cancel")
        response.raise_for_status()
        
        return response.json()

    async def close(self) -> None:
        """Close the HTTP client connection."""
        if self._client:
            await self._client.aclose()
