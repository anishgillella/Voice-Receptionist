"""Pydantic models for database entities."""

from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class CustomerBase(BaseModel):
    """Base customer model."""

    phone_number: str
    company_name: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[str] = None
    industry: Optional[str] = None
    location: Optional[str] = None


class CustomerCreate(CustomerBase):
    """Customer creation model."""

    pass


class Customer(CustomerBase):
    """Customer model with database fields."""

    id: UUID
    created_at: datetime

    class Config:
        from_attributes = True


class ConversationBase(BaseModel):
    """Base conversation model."""

    call_id: str
    customer_id: UUID
    transcript: str


class ConversationCreate(ConversationBase):
    """Conversation creation model."""

    pass


class Conversation(ConversationBase):
    """Conversation model with database fields."""

    id: UUID
    created_at: datetime

    class Config:
        from_attributes = True


class EmbeddingBase(BaseModel):
    """Base embedding model."""

    call_id: str
    embedding: list[float]
    embedding_type: str = Field(default="full")


class EmbeddingCreate(EmbeddingBase):
    """Embedding creation model."""

    pass


class Embedding(EmbeddingBase):
    """Embedding model with database fields."""

    created_at: datetime

    class Config:
        from_attributes = True


class CustomerMemoryBase(BaseModel):
    """Base customer memory model."""

    customer_id: UUID
    call_id: str
    memory_type: str  # 'objection', 'commitment', 'profile', etc.
    content: str


class CustomerMemoryCreate(CustomerMemoryBase):
    """Customer memory creation model."""

    pass


class CustomerMemory(CustomerMemoryBase):
    """Customer memory model with database fields."""

    id: UUID
    created_at: datetime

    class Config:
        from_attributes = True


class ConversationWithCustomer(Conversation):
    """Conversation with associated customer data."""

    customer: Optional[Customer] = None


class CustomerWithCallHistory(Customer):
    """Customer with call history."""

    total_calls: int = 0
    last_call_date: Optional[datetime] = None
    call_history: list[Conversation] = []

# ============================================================================
# Call Evaluation Models
# ============================================================================


class CallMetrics(BaseModel):
    """Extracted metrics from a single call evaluation."""

    call_id: str
    customer_id: UUID

    # TIER 1: Critical metrics
    frc_achieved: bool = Field(..., description="First Call Resolution - did they take action?")
    frc_type: Optional[str] = Field(
        None,
        description="Type of resolution: quote, consultation_booked, follow_up_requested, none",
    )
    intent_detected: str = Field(..., description="Main customer intent detected")
    intent_accuracy_score: float = Field(
        default=0.0, ge=0.0, le=1.0, description="Confidence in intent detection (0-1)"
    )

    # TIER 2: Important metrics
    call_quality_score: float = Field(
        default=0.0, ge=0.0, le=1.0, description="Overall call quality (0-1)"
    )
    customer_sentiment: str = Field(
        default="neutral", description="Customer sentiment: very_positive, positive, neutral, negative, very_negative"
    )
    script_compliance_score: float = Field(
        default=0.0, ge=0.0, le=1.0, description="Adherence to system prompt (0-1)"
    )

    # Supporting data
    key_objections: list[str] = Field(default_factory=list, description="Objections raised by customer")
    agent_responses_to_objections: list[str] = Field(
        default_factory=list, description="How agent handled each objection"
    )
    next_steps_agreed: Optional[str] = Field(None, description="What customer agreed to do next")
    call_duration_seconds: int = Field(default=0, description="Total call duration in seconds")

    created_at: datetime = Field(default_factory=datetime.now)

    class Config:
        from_attributes = True


class CallJudgment(BaseModel):
    """LLM judge evaluation of a call."""

    call_id: str
    customer_id: UUID

    metrics: CallMetrics = Field(..., description="Extracted call metrics")
    judge_reasoning: str = Field(..., description="Why judge scored this way")
    judge_model: str = Field(default="gpt-5-nano", description="Which LLM model was used for judgment")

    # Recommendations
    strengths: list[str] = Field(default_factory=list, description="What agent did well")
    improvements: list[str] = Field(default_factory=list, description="Areas for improvement")

    created_at: datetime = Field(default_factory=datetime.now)

    class Config:
        from_attributes = True
