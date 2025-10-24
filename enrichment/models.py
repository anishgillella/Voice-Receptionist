"""Data models for Task MCP enrichment."""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class TaskStatus(str, Enum):
    """Status of a task."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskType(str, Enum):
    """Type of task to execute."""

    DEEP_RESEARCH = "deep_research"
    TASK_GROUP = "task_group"


class EnrichmentItem(BaseModel):
    """A single item to be enriched."""

    id: str = Field(..., description="Unique identifier for this item")
    data: Dict[str, Any] = Field(..., description="Item data to be enriched")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


class DeepResearchRequest(BaseModel):
    """Request for deep research on a topic."""

    query: str = Field(..., description="Research query/topic")
    description: Optional[str] = Field(None, description="Detailed description of what to research")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


class TaskGroupRequest(BaseModel):
    """Request to enrich multiple items in parallel."""

    name: str = Field(..., description="Name of the task group")
    items: List[EnrichmentItem] = Field(..., description="Items to enrich")
    enrichment_prompt: str = Field(..., description="Prompt describing what enrichment to perform")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")
    
    class Config:
        json_schema_extra = {
            "example": {
                "name": "customer_enrichment",
                "items": [
                    {
                        "id": "cust_123",
                        "data": {
                            "company_name": "TechCorp Inc",
                            "industry": "Software"
                        }
                    }
                ],
                "enrichment_prompt": "Find company revenue, employee count, and funding info"
            }
        }


class TaskResult(BaseModel):
    """Result of a completed task."""

    task_id: str = Field(..., description="ID of the completed task")
    item_id: str = Field(..., description="ID of the enriched item")
    status: TaskStatus = Field(..., description="Status of the task")
    enriched_data: Optional[Dict[str, Any]] = Field(None, description="Enriched data")
    raw_result: Optional[Any] = Field(None, description="Raw result from the API")
    error: Optional[str] = Field(None, description="Error message if task failed")
    completed_at: Optional[datetime] = Field(None, description="When the task completed")


class TaskGroupResponse(BaseModel):
    """Response from creating a task group."""

    task_group_id: str = Field(..., description="ID of the created task group")
    status: TaskStatus = Field(default=TaskStatus.PENDING, description="Initial status")
    items_count: int = Field(..., description="Number of items in the group")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="When the group was created")
    progress_url: Optional[str] = Field(None, description="URL to track progress")


class DeepResearchResponse(BaseModel):
    """Response from creating a deep research task."""

    task_id: str = Field(..., description="ID of the research task")
    status: TaskStatus = Field(default=TaskStatus.PENDING, description="Initial status")
    query: str = Field(..., description="The research query")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="When the task was created")
    progress_url: Optional[str] = Field(None, description="URL to track progress")


class TaskResultsResponse(BaseModel):
    """Response containing results from completed tasks."""

    task_id: str = Field(..., description="ID of the task")
    status: TaskStatus = Field(..., description="Final status")
    results: List[TaskResult] = Field(..., description="Results for each item")
    completed_count: int = Field(..., description="Number of completed items")
    failed_count: int = Field(..., description="Number of failed items")
    completed_at: datetime = Field(..., description="When the task completed")
