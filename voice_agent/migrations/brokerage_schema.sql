-- Voice Agent Database Schema in brokerage schema
-- Run this script in Supabase SQL editor to initialize tables in the brokerage schema

-- Step 1: Create the brokerage schema if it doesn't exist
CREATE SCHEMA IF NOT EXISTS brokerage;

-- Step 2: Enable pgvector extension for vector embeddings (if not already enabled)
CREATE EXTENSION IF NOT EXISTS vector;

-- Create customers table
CREATE TABLE IF NOT EXISTS brokerage.customers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    phone_number TEXT NOT NULL UNIQUE,
    company_name TEXT NOT NULL,
    first_name TEXT,
    last_name TEXT,
    email TEXT,
    industry TEXT,
    location TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create conversations table
CREATE TABLE IF NOT EXISTS brokerage.conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    call_id TEXT NOT NULL UNIQUE,
    customer_id UUID NOT NULL REFERENCES brokerage.customers(id) ON DELETE CASCADE,
    transcript TEXT NOT NULL,
    summary TEXT,
    summary_embedding vector(1024),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (customer_id) REFERENCES brokerage.customers(id)
);

-- Create embeddings table (with pgvector support)
CREATE TABLE IF NOT EXISTS brokerage.embeddings (
    call_id TEXT NOT NULL REFERENCES brokerage.conversations(call_id) ON DELETE CASCADE,
    embedding vector(1024) NOT NULL,
    embedding_type TEXT DEFAULT 'full',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (call_id, embedding_type),
    FOREIGN KEY (call_id) REFERENCES brokerage.conversations(call_id)
);

-- Create customer_memory table (for cross-session memory)
CREATE TABLE IF NOT EXISTS brokerage.customer_memory (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_id UUID NOT NULL REFERENCES brokerage.customers(id) ON DELETE CASCADE,
    call_id TEXT NOT NULL REFERENCES brokerage.conversations(call_id) ON DELETE CASCADE,
    memory_type TEXT NOT NULL,
    content TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (customer_id) REFERENCES brokerage.customers(id),
    FOREIGN KEY (call_id) REFERENCES brokerage.conversations(call_id)
);

-- Create indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_customers_phone ON brokerage.customers(phone_number);
CREATE INDEX IF NOT EXISTS idx_conversations_customer_id ON brokerage.conversations(customer_id);
CREATE INDEX IF NOT EXISTS idx_conversations_call_id ON brokerage.conversations(call_id);
CREATE INDEX IF NOT EXISTS idx_conversations_created_at ON brokerage.conversations(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_embeddings_call_id ON brokerage.embeddings(call_id);
CREATE INDEX IF NOT EXISTS idx_customer_memory_customer_id ON brokerage.customer_memory(customer_id);
CREATE INDEX IF NOT EXISTS idx_customer_memory_memory_type ON brokerage.customer_memory(memory_type);

-- Enable vector search on embeddings (for pgvector similarity queries)
CREATE INDEX IF NOT EXISTS idx_embeddings_vector ON brokerage.embeddings USING ivfflat (embedding vector_cosine_ops);

-- Enable vector search on conversation summaries
CREATE INDEX IF NOT EXISTS idx_conversations_summary_vector ON brokerage.conversations USING ivfflat (summary_embedding vector_cosine_ops);

-- Add updated_at trigger for customers table
CREATE OR REPLACE FUNCTION brokerage.update_customers_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_update_customers_updated_at ON brokerage.customers;
CREATE TRIGGER trigger_update_customers_updated_at
BEFORE UPDATE ON brokerage.customers
FOR EACH ROW
EXECUTE FUNCTION brokerage.update_customers_updated_at();
