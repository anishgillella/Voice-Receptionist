-- Voice Agent Database Schema
-- Run this script in Supabase SQL editor to initialize tables

-- Enable pgvector extension for vector embeddings
CREATE EXTENSION IF NOT EXISTS vector;

-- Create customers table
CREATE TABLE IF NOT EXISTS customers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    phone_number TEXT NOT NULL UNIQUE,
    company_name TEXT NOT NULL,
    industry TEXT,
    location TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create conversations table
CREATE TABLE IF NOT EXISTS conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    call_id TEXT NOT NULL UNIQUE,
    customer_id UUID NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
    transcript TEXT NOT NULL,
    summary TEXT,
    summary_embedding vector(1024),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (customer_id) REFERENCES customers(id)
);

-- Create embeddings table (with pgvector support)
CREATE TABLE IF NOT EXISTS embeddings (
    call_id TEXT NOT NULL REFERENCES conversations(call_id) ON DELETE CASCADE,
    embedding vector(1024) NOT NULL,
    embedding_type TEXT DEFAULT 'full',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (call_id, embedding_type),
    FOREIGN KEY (call_id) REFERENCES conversations(call_id)
);

-- Create customer_memory table (for cross-session memory)
CREATE TABLE IF NOT EXISTS customer_memory (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_id UUID NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
    call_id TEXT NOT NULL REFERENCES conversations(call_id) ON DELETE CASCADE,
    memory_type TEXT NOT NULL,
    content TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (customer_id) REFERENCES customers(id),
    FOREIGN KEY (call_id) REFERENCES conversations(call_id)
);

-- Create indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_customers_phone ON customers(phone_number);
CREATE INDEX IF NOT EXISTS idx_conversations_customer_id ON conversations(customer_id);
CREATE INDEX IF NOT EXISTS idx_conversations_call_id ON conversations(call_id);
CREATE INDEX IF NOT EXISTS idx_conversations_created_at ON conversations(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_embeddings_call_id ON embeddings(call_id);
CREATE INDEX IF NOT EXISTS idx_customer_memory_customer_id ON customer_memory(customer_id);
CREATE INDEX IF NOT EXISTS idx_customer_memory_memory_type ON customer_memory(memory_type);

-- Enable vector search on embeddings (for pgvector similarity queries)
CREATE INDEX IF NOT EXISTS idx_embeddings_vector ON embeddings USING ivfflat (embedding vector_cosine_ops);

-- Add updated_at trigger for customers table
CREATE OR REPLACE FUNCTION update_customers_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_update_customers_updated_at ON customers;
CREATE TRIGGER trigger_update_customers_updated_at
BEFORE UPDATE ON customers
FOR EACH ROW
EXECUTE FUNCTION update_customers_updated_at();
