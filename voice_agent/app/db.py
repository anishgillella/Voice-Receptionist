"""Database connection and utilities for Supabase."""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional
from uuid import UUID, uuid4

import psycopg2
from psycopg2.extras import RealDictCursor

from .config import settings
from .models import Customer, CustomerCreate

logger = logging.getLogger(__name__)


def get_table_name(table: str) -> str:
    """Get fully qualified table name with schema.
    
    Args:
        table: Table name without schema
        
    Returns:
        Fully qualified table name (schema.table)
    """
    return f"{settings.supabase_schema}.{table}"


class DatabaseConnection:
    """PostgreSQL database connection manager."""

    def __init__(self):
        """Initialize database connection."""
        self.conn = None
        self.connect()

    def connect(self) -> None:
        """Establish connection to Supabase PostgreSQL."""
        try:
            self.conn = psycopg2.connect(settings.supabase_url)
            logger.info("Connected to Supabase PostgreSQL")
            
            # Set the search_path to use the configured schema
            with self.conn.cursor() as cur:
                cur.execute(f"SET search_path TO {settings.supabase_schema}, public")
            self.conn.commit()
            logger.info(f"Set search_path to {settings.supabase_schema} schema")
        except psycopg2.Error as e:
            logger.error(f"Failed to connect to database: {e}")
            raise

    def close(self) -> None:
        """Close database connection."""
        if self.conn:
            self.conn.close()
            logger.info("Closed database connection")

    def execute(self, query: str, params: tuple = ()) -> list[Dict[str, Any]]:
        """Execute query and return results."""
        try:
            with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(query, params)
                results = cur.fetchall()
                return results if results else []
        except psycopg2.Error as e:
            logger.error(f"Database query error: {e}")
            # Rollback transaction on error to prevent "transaction aborted" state
            self.conn.rollback()
            raise

    def execute_one(self, query: str, params: tuple = ()) -> Optional[Dict[str, Any]]:
        """Execute query and return single result."""
        results = self.execute(query, params)
        return results[0] if results else None

    def insert(self, query: str, params: tuple = ()) -> Optional[Dict[str, Any]]:
        """Insert record and return it."""
        try:
            with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(query, params)
                self.conn.commit()
                result = cur.fetchone()
                return dict(result) if result else None
        except psycopg2.Error as e:
            self.conn.rollback()
            logger.error(f"Insert error: {e}")
            raise

    def update(self, query: str, params: tuple = ()) -> int:
        """Update records and return count."""
        try:
            with self.conn.cursor() as cur:
                cur.execute(query, params)
                self.conn.commit()
                return cur.rowcount
        except psycopg2.Error as e:
            self.conn.rollback()
            logger.error(f"Update error: {e}")
            raise


# Global database connection instance
_db_instance: Optional[DatabaseConnection] = None


def get_db() -> DatabaseConnection:
    """Get or create database connection."""
    global _db_instance
    if _db_instance is None:
        _db_instance = DatabaseConnection()
    return _db_instance


# ============================================================================
# Customer operations
# ============================================================================

def get_or_create_customer(phone_number: str) -> Customer:
    """Get existing customer or create new one by phone number."""
    db = get_db()

    # Try to find existing customer
    query = f"SELECT id, company_name, phone_number, first_name, last_name, email, industry, location, created_at FROM {get_table_name('customers')} WHERE phone_number = %s"
    result = db.execute_one(query, (phone_number,))

    if result:
        return Customer(**result)

    # Create new customer
    customer_id = str(uuid4())
    insert_query = f"""
        INSERT INTO {get_table_name('customers')} (id, phone_number, company_name, first_name, last_name, email, industry, location, created_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW())
        RETURNING id, company_name, phone_number, first_name, last_name, email, industry, location, created_at
    """

    company_name = settings.customer_company_name or "Unknown"
    industry = settings.customer_industry or "Insurance"
    location = settings.customer_location or "Unknown"
    first_name = settings.customer_first_name if hasattr(settings, 'customer_first_name') else None
    last_name = settings.customer_last_name if hasattr(settings, 'customer_last_name') else None
    email = settings.customer_email if hasattr(settings, 'customer_email') else None

    result = db.insert(insert_query, (customer_id, phone_number, company_name, first_name, last_name, email, industry, location))
    if result:
        return Customer(**result)

    raise ValueError(f"Failed to create customer for phone {phone_number}")


def get_customer_by_id(customer_id: UUID) -> Optional[Customer]:
    """Get customer by ID."""
    db = get_db()
    query = f"SELECT id, company_name, phone_number, first_name, last_name, email, industry, location, created_at FROM {get_table_name('customers')} WHERE id = %s"
    result = db.execute_one(query, (str(customer_id),))
    return Customer(**result) if result else None


def get_customer_call_count(customer_id: UUID) -> int:
    """Get total calls for a customer."""
    db = get_db()
    query = f"SELECT COUNT(*) as count FROM {get_table_name('conversations')} WHERE customer_id = %s"
    result = db.execute_one(query, (str(customer_id),))
    return result["count"] if result else 0


# ============================================================================
# Conversation operations
# ============================================================================

def store_conversation(call_id: str, customer_id: UUID, transcript: str) -> Dict[str, Any]:
    """Store conversation transcript linked to customer."""
    db = get_db()
    conv_id = str(uuid4())

    insert_query = f"""
        INSERT INTO {get_table_name('conversations')} (id, call_id, customer_id, transcript, created_at)
        VALUES (%s, %s, %s, %s, NOW())
        RETURNING id, call_id, customer_id, transcript, created_at
    """

    result = db.insert(insert_query, (conv_id, call_id, str(customer_id), transcript))
    return dict(result) if result else {}


def get_conversation_by_call_id(call_id: str) -> Optional[Dict[str, Any]]:
    """Get conversation by VAPI call ID."""
    db = get_db()
    query = f"SELECT id, call_id, customer_id, transcript, created_at FROM {get_table_name('conversations')} WHERE call_id = %s"
    result = db.execute_one(query, (call_id,))
    return dict(result) if result else None


def update_conversation_summary(call_id: str, summary: str, summary_embedding: Optional[list[float]] = None) -> bool:
    """Update conversation with summary and optional summary embedding.
    
    Args:
        call_id: VAPI call ID
        summary: Summary text
        summary_embedding: Optional embedding vector for the summary
        
    Returns:
        True if update was successful, False otherwise
    """
    try:
        db = get_db()
        
        if summary_embedding:
            embedding_str = "[" + ",".join(str(x) for x in summary_embedding) + "]"
            update_query = f"""
                UPDATE {get_table_name('conversations')}
                SET summary = %s, summary_embedding = %s::vector
                WHERE call_id = %s
            """
            db.update(update_query, (summary, embedding_str, call_id))
        else:
            update_query = f"""
                UPDATE {get_table_name('conversations')}
                SET summary = %s
                WHERE call_id = %s
            """
            db.update(update_query, (summary, call_id))
        
        logger.info(f"✅ Updated summary for call {call_id}")
        return True
    except Exception as e:
        logger.error(f"Failed to update summary for call {call_id}: {e}")
        return False


def get_customer_conversations(customer_id: UUID, limit: int = 10) -> list[Dict[str, Any]]:
    """Get recent conversations for a customer."""
    db = get_db()
    query = """
        SELECT id, call_id, customer_id, transcript, summary, created_at
        FROM {get_table_name('conversations')}
        WHERE customer_id = %s
        ORDER BY created_at DESC
        LIMIT %s
    """
    results = db.execute(query, (str(customer_id), limit))
    return [dict(r) for r in results]


# ============================================================================
# Conversation Summary operations
# ============================================================================

def store_conversation_summary(call_id: str, summary: str, summary_embedding: Optional[list[float]] = None) -> Dict[str, Any]:
    """Store conversation summary and optional embedding."""
    db = get_db()
    
    if summary_embedding:
        embedding_str = "[" + ",".join(str(x) for x in summary_embedding) + "]"
        insert_query = f"""
            INSERT INTO conversation_summaries (call_id, summary, summary_embedding, created_at)
            VALUES (%s, %s, %s::vector, NOW())
            ON CONFLICT (call_id) DO UPDATE
            SET summary = %s, summary_embedding = %s::vector
            RETURNING call_id, summary, created_at
        """
        result = db.insert(insert_query, (call_id, summary, embedding_str, summary, embedding_str))
    else:
        insert_query = f"""
            INSERT INTO conversation_summaries (call_id, summary, created_at)
            VALUES (%s, %s, NOW())
            ON CONFLICT (call_id) DO UPDATE
            SET summary = %s
            RETURNING call_id, summary, created_at
        """
        result = db.insert(insert_query, (call_id, summary, summary))
    
    return dict(result) if result else {}


def get_conversation_summary(call_id: str) -> Optional[Dict[str, Any]]:
    """Get conversation summary by call ID."""
    db = get_db()
    query = "SELECT call_id, summary, summary_embedding, created_at FROM conversation_summaries WHERE call_id = %s"
    result = db.execute_one(query, (call_id,))
    return dict(result) if result else None


# ============================================================================
# Embedding operations
# ============================================================================

def store_embedding(call_id: str, embedding: list[float], embedding_type: str = "full") -> Dict[str, Any]:
    """Store embedding vector for a conversation."""
    db = get_db()

    # Convert embedding list to pgvector format: [1.0, 2.0, 3.0]
    embedding_str = "[" + ",".join(str(x) for x in embedding) + "]"

    insert_query = f"""
        INSERT INTO {get_table_name('embeddings')} (call_id, embedding, embedding_type, created_at)
        VALUES (%s, %s::vector, %s, NOW())
        ON CONFLICT (call_id, embedding_type) DO UPDATE
        SET embedding = %s::vector
        RETURNING call_id, embedding_type, created_at
    """

    result = db.insert(insert_query, (call_id, embedding_str, embedding_type, embedding_str))
    return dict(result) if result else {}


def get_embedding(call_id: str, embedding_type: str = "full") -> Optional[list[float]]:
    """Get embedding for a conversation."""
    db = get_db()
    query = f"SELECT embedding FROM {get_table_name('embeddings')} WHERE call_id = %s AND embedding_type = %s"
    result = db.execute_one(query, (call_id, embedding_type))
    return result["embedding"] if result else None


# ============================================================================
# Customer memory operations
# ============================================================================

def store_customer_memory(customer_id: UUID, call_id: str, memory_type: str, content: str) -> Dict[str, Any]:
    """Store extracted customer memory (objections, commitments, profile data)."""
    db = get_db()
    memory_id = str(uuid4())

    insert_query = f"""
        INSERT INTO {get_table_name('customer_memory')} (id, customer_id, call_id, memory_type, content, created_at)
        VALUES (%s, %s, %s, %s, %s, NOW())
        RETURNING id, customer_id, call_id, memory_type, content, created_at
    """

    result = db.insert(insert_query, (memory_id, str(customer_id), call_id, memory_type, content))
    return dict(result) if result else {}


def get_customer_memory(customer_id: UUID, memory_type: Optional[str] = None, limit: int = 20) -> list[Dict[str, Any]]:
    """Get customer memory entries."""
    db = get_db()

    if memory_type:
        query = """
            SELECT id, customer_id, call_id, memory_type, content, created_at
            FROM {get_table_name('customer_memory')}
            WHERE customer_id = %s AND memory_type = %s
            ORDER BY created_at DESC
            LIMIT %s
        """
        results = db.execute(query, (str(customer_id), memory_type, limit))
    else:
        query = """
            SELECT id, customer_id, call_id, memory_type, content, created_at
            FROM {get_table_name('customer_memory')}
            WHERE customer_id = %s
            ORDER BY created_at DESC
            LIMIT %s
        """
        results = db.execute(query, (str(customer_id), limit))

    return [dict(r) for r in results]


def close_db() -> None:
    """Close database connection."""
    global _db_instance
    if _db_instance:
        _db_instance.close()
        _db_instance = None


# ============================================================================
# Call Metrics operations
# ============================================================================

def store_call_metrics(
    call_id: str,
    customer_id: UUID,
    frc_achieved: bool,
    frc_type: Optional[str],
    intent_detected: str,
    intent_accuracy_score: float,
    call_quality_score: float,
    customer_sentiment: str,
    script_compliance_score: float,
    key_objections: Optional[list[str]] = None,
    agent_responses_to_objections: Optional[list[str]] = None,
    next_steps_agreed: Optional[str] = None,
    call_duration_seconds: int = 0,
) -> Dict[str, Any]:
    """Store extracted call metrics to database.
    
    Args:
        call_id: VAPI call ID
        customer_id: Customer UUID
        frc_achieved: Whether first call resolution was achieved
        frc_type: Type of resolution (quote, consultation_booked, etc)
        intent_detected: Customer intent detected
        intent_accuracy_score: Intent detection confidence (0-1)
        call_quality_score: Overall call quality (0-1)
        customer_sentiment: Customer sentiment classification
        script_compliance_score: Adherence to system prompt (0-1)
        key_objections: List of objections raised
        agent_responses_to_objections: List of how objections were handled
        next_steps_agreed: What customer agreed to do next
        call_duration_seconds: Total call duration
        
    Returns:
        Dictionary with stored metrics or empty dict if failed
    """
    db = get_db()
    metrics_id = str(uuid4())
    
    try:
        # Convert lists to PostgreSQL arrays
        objections_str = "{" + ",".join([f'"{o}"' for o in (key_objections or [])]) + "}"
        responses_str = "{" + ",".join([f'"{r}"' for r in (agent_responses_to_objections or [])]) + "}"
        
        insert_query = f"""
            INSERT INTO {get_table_name('call_metrics')} (
                id, call_id, customer_id, frc_achieved, frc_type, 
                intent_detected, intent_accuracy_score, call_quality_score,
                customer_sentiment, script_compliance_score, key_objections,
                agent_responses_to_objections, next_steps_agreed, call_duration_seconds,
                created_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
            RETURNING id, call_id, customer_id, frc_achieved, call_quality_score, created_at
        """
        
        result = db.insert(
            insert_query,
            (
                metrics_id,
                call_id,
                str(customer_id),
                frc_achieved,
                frc_type,
                intent_detected,
                intent_accuracy_score,
                call_quality_score,
                customer_sentiment,
                script_compliance_score,
                objections_str,
                responses_str,
                next_steps_agreed,
                call_duration_seconds,
            ),
        )
        
        logger.info(f"✅ Stored call metrics for {call_id}: FCR={frc_achieved}, Quality={call_quality_score:.2f}")
        return dict(result) if result else {}
    
    except Exception as e:
        logger.error(f"Failed to store call metrics for {call_id}: {e}")
        return {}


def store_call_judgment(
    call_id: str,
    customer_id: UUID,
    metrics_id: str,
    judge_reasoning: str,
    judge_model: str,
    strengths: Optional[list[str]] = None,
    improvements: Optional[list[str]] = None,
) -> Dict[str, Any]:
    """Store call judgment from LLM judge.
    
    Args:
        call_id: VAPI call ID
        customer_id: Customer UUID
        metrics_id: ID of associated call_metrics record
        judge_reasoning: Explanation of judgment
        judge_model: Which LLM model performed judgment
        strengths: List of call strengths
        improvements: List of improvement areas
        
    Returns:
        Dictionary with stored judgment or empty dict if failed
    """
    db = get_db()
    judgment_id = str(uuid4())
    
    try:
        # Convert lists to PostgreSQL arrays
        strengths_str = "{" + ",".join([f'"{s}"' for s in (strengths or [])]) + "}"
        improvements_str = "{" + ",".join([f'"{i}"' for i in (improvements or [])]) + "}"
        
        insert_query = f"""
            INSERT INTO {get_table_name('call_judgments')} (
                id, call_id, customer_id, metrics_id, judge_reasoning,
                judge_model, strengths, improvements, created_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW())
            RETURNING id, call_id, customer_id, created_at
        """
        
        result = db.insert(
            insert_query,
            (
                judgment_id,
                call_id,
                str(customer_id),
                metrics_id,
                judge_reasoning,
                judge_model,
                strengths_str,
                improvements_str,
            ),
        )
        
        logger.info(f"✅ Stored call judgment for {call_id}")
        return dict(result) if result else {}
    
    except Exception as e:
        logger.error(f"Failed to store call judgment for {call_id}: {e}")
        return {}


def get_call_metrics(call_id: str) -> Optional[Dict[str, Any]]:
    """Get call metrics by call ID.
    
    Args:
        call_id: VAPI call ID
        
    Returns:
        Dictionary with metrics or None if not found
    """
    db = get_db()
    query = f"""
        SELECT * FROM {get_table_name('call_metrics')}
        WHERE call_id = %s
        LIMIT 1
    """
    result = db.execute_one(query, (call_id,))
    return dict(result) if result else None


def get_customer_call_metrics(customer_id: UUID, limit: int = 50) -> list[Dict[str, Any]]:
    """Get call metrics for a customer.
    
    Args:
        customer_id: Customer UUID
        limit: Maximum results to return
        
    Returns:
        List of metric dictionaries
    """
    db = get_db()
    query = f"""
        SELECT * FROM {get_table_name('call_metrics')}
        WHERE customer_id = %s
        ORDER BY created_at DESC
        LIMIT %s
    """
    results = db.execute(query, (str(customer_id), limit))
    return [dict(r) for r in results]


def get_call_quality_stats(customer_id: Optional[UUID] = None) -> Dict[str, Any]:
    """Get call quality statistics.
    
    Args:
        customer_id: Optional customer UUID to filter by
        
    Returns:
        Dictionary with statistics
    """
    db = get_db()
    
    if customer_id:
        query = f"""
            SELECT
                COUNT(*) as total_calls,
                SUM(CASE WHEN frc_achieved THEN 1 ELSE 0 END)::FLOAT / COUNT(*) as fcr_rate,
                AVG(call_quality_score) as avg_quality,
                AVG(intent_accuracy_score) as avg_intent_accuracy,
                AVG(script_compliance_score) as avg_compliance
            FROM {get_table_name('call_metrics')}
            WHERE customer_id = %s
        """
        result = db.execute_one(query, (str(customer_id),))
    else:
        query = f"""
            SELECT
                COUNT(*) as total_calls,
                SUM(CASE WHEN frc_achieved THEN 1 ELSE 0 END)::FLOAT / COUNT(*) as fcr_rate,
                AVG(call_quality_score) as avg_quality,
                AVG(intent_accuracy_score) as avg_intent_accuracy,
                AVG(script_compliance_score) as avg_compliance
            FROM {get_table_name('call_metrics')}
        """
        result = db.execute_one(query, ())
    
    return dict(result) if result else {}

