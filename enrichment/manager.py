"""Task Manager for orchestrating enrichment tasks with parallel processing."""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Callable, Dict, List, Optional

from .config import EnrichmentSettings, get_enrichment_settings
from .client import TaskMCPClient
from .models import (
    TaskStatus,
    EnrichmentItem,
    TaskGroupRequest,
    DeepResearchRequest,
    TaskGroupResponse,
    DeepResearchResponse,
    TaskResult,
    TaskResultsResponse,
)

logger = logging.getLogger(__name__)


class TaskManager:
    """Manager for orchestrating enrichment tasks with parallel processing."""

    def __init__(self, settings: Optional[EnrichmentSettings] = None):
        """Initialize the Task Manager.

        Args:
            settings: EnrichmentSettings instance (uses cached defaults if not provided)
        """
        self.settings = settings or get_enrichment_settings()
        self.client = TaskMCPClient(settings)
        self._active_tasks: Dict[str, Dict[str, Any]] = {}

    async def enrich_items_parallel(
        self,
        items: List[EnrichmentItem],
        enrichment_prompt: str,
        batch_size: Optional[int] = None,
        task_name: Optional[str] = None,
        poll: bool = False,
        poll_timeout_seconds: Optional[int] = None,
    ) -> List[TaskGroupResponse]:
        """Enrich multiple items in parallel using task groups.

        Args:
            items: List of items to enrich
            enrichment_prompt: Prompt describing the enrichment to perform
            batch_size: Max items per batch (defaults to settings.max_batch_size)
            task_name: Name for the task group (defaults to auto-generated)
            poll: Whether to wait for completion (default: False - async/fire-and-forget)
            poll_timeout_seconds: Max time to wait for completion (defaults to settings.task_timeout_seconds)

        Returns:
            List of TaskGroupResponse objects for each batch

        Raises:
            ValueError: If items list is empty
            httpx.HTTPError: If API requests fail
        """
        if not items:
            raise ValueError("Items list cannot be empty")

        batch_size = batch_size or self.settings.max_batch_size
        timeout = poll_timeout_seconds or self.settings.task_timeout_seconds

        # Split items into batches
        batches = [
            items[i : i + batch_size]
            for i in range(0, len(items), batch_size)
        ]

        logger.info(
            f"Splitting {len(items)} items into {len(batches)} batch(es) "
            f"(batch_size={batch_size})"
        )

        responses = []
        
        async with self.client:
            for batch_idx, batch in enumerate(batches):
                batch_name = task_name or f"batch_{batch_idx}_{len(items)}_items"
                
                request = TaskGroupRequest(
                    name=batch_name,
                    items=batch,
                    enrichment_prompt=enrichment_prompt,
                )
                
                response = await self.client.create_task_group(request)
                responses.append(response)
                self._active_tasks[response.task_group_id] = {
                    "type": "task_group",
                    "batch_idx": batch_idx,
                    "items": batch,
                    "created_at": response.created_at,
                }
                
                logger.info(
                    f"Created task group batch {batch_idx + 1}/{len(batches)}: "
                    f"{response.task_group_id}"
                )

        if poll:
            # Wait for all batches to complete
            logger.info("Polling for task completion...")
            for response in responses:
                await self._poll_task_completion(
                    response.task_group_id,
                    timeout_seconds=timeout,
                )

        return responses

    async def deep_research(
        self,
        query: str,
        description: Optional[str] = None,
        poll: bool = False,
        poll_timeout_seconds: Optional[int] = None,
    ) -> DeepResearchResponse:
        """Create a deep research task.

        Args:
            query: Research query/topic
            description: Detailed description of what to research
            poll: Whether to wait for completion (default: False - async/fire-and-forget)
            poll_timeout_seconds: Max time to wait for completion

        Returns:
            DeepResearchResponse with task details

        Raises:
            httpx.HTTPError: If API request fails
        """
        request = DeepResearchRequest(query=query, description=description)
        
        async with self.client:
            response = await self.client.create_deep_research_task(request)
            self._active_tasks[response.task_id] = {
                "type": "deep_research",
                "query": query,
                "created_at": response.created_at,
            }

        logger.info(f"Created deep research task: {response.task_id}")

        if poll:
            timeout = poll_timeout_seconds or self.settings.task_timeout_seconds
            await self._poll_task_completion(response.task_id, timeout_seconds=timeout)

        return response

    async def get_results(
        self,
        task_id: str,
        retry_attempts: Optional[int] = None,
    ) -> TaskResultsResponse:
        """Get results of a completed task.

        Args:
            task_id: ID of the task
            retry_attempts: Number of retry attempts (defaults to settings.retry_attempts)

        Returns:
            TaskResultsResponse with enriched data

        Raises:
            httpx.HTTPError: If API request fails after retries
        """
        retry_attempts = retry_attempts or self.settings.retry_attempts
        
        async with self.client:
            for attempt in range(retry_attempts):
                try:
                    results = await self.client.get_result(task_id)
                    logger.info(
                        f"Retrieved results for task {task_id}: "
                        f"{results.completed_count} completed, "
                        f"{results.failed_count} failed"
                    )
                    return results
                except Exception as e:
                    if attempt < retry_attempts - 1:
                        logger.warning(
                            f"Failed to get results (attempt {attempt + 1}/{retry_attempts}): {e}"
                        )
                        await asyncio.sleep(self.settings.retry_delay_seconds)
                    else:
                        logger.error(f"Failed to get results after {retry_attempts} attempts")
                        raise

    async def _poll_task_completion(
        self,
        task_id: str,
        timeout_seconds: int = 300,
    ) -> TaskResultsResponse:
        """Poll a task until completion or timeout.

        Args:
            task_id: ID of the task to poll
            timeout_seconds: Maximum time to wait

        Returns:
            TaskResultsResponse when task completes

        Raises:
            TimeoutError: If task doesn't complete within timeout
            httpx.HTTPError: If API requests fail
        """
        import time
        
        start_time = time.time()
        
        async with self.client:
            while True:
                elapsed = time.time() - start_time
                if elapsed > timeout_seconds:
                    raise TimeoutError(
                        f"Task {task_id} did not complete within {timeout_seconds} seconds"
                    )
                
                try:
                    status_data = await self.client.get_task_status(task_id)
                    status = TaskStatus(status_data.get("status"))
                    
                    logger.debug(f"Task {task_id} status: {status} ({elapsed:.1f}s elapsed)")
                    
                    if status in (TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED):
                        # Task finished, get results
                        return await self.client.get_result(task_id)
                    
                    # Still running, wait before polling again
                    await asyncio.sleep(self.settings.task_poll_interval_seconds)
                    
                except Exception as e:
                    logger.error(f"Error polling task {task_id}: {e}")
                    await asyncio.sleep(self.settings.task_poll_interval_seconds)

    async def process_results_callback(
        self,
        task_id: str,
        callback: Callable[[TaskResult], None],
        error_callback: Optional[Callable[[TaskResult], None]] = None,
    ) -> None:
        """Process task results with a callback function.

        Args:
            task_id: ID of the completed task
            callback: Function to call for each successful result
            error_callback: Function to call for each failed result

        Raises:
            httpx.HTTPError: If API request fails
        """
        results = await self.get_results(task_id)
        
        for result in results.results:
            if result.status == TaskStatus.COMPLETED:
                callback(result)
            elif error_callback and result.status == TaskStatus.FAILED:
                error_callback(result)

    def get_active_tasks(self) -> Dict[str, Dict[str, Any]]:
        """Get currently active tasks.

        Returns:
            Dictionary of active task IDs and their metadata
        """
        return self._active_tasks.copy()

    async def cancel_task(self, task_id: str) -> None:
        """Cancel a running task.

        Args:
            task_id: ID of the task to cancel

        Raises:
            httpx.HTTPError: If API request fails
        """
        async with self.client:
            await self.client.cancel_task(task_id)
        
        if task_id in self._active_tasks:
            del self._active_tasks[task_id]
        
        logger.info(f"Cancelled task: {task_id}")

    async def close(self) -> None:
        """Close all connections and cleanup resources."""
        await self.client.close()
