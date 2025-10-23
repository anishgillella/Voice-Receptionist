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
