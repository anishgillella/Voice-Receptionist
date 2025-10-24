-- Call Evaluation Database Schema
-- Run this in Supabase SQL editor to initialize evaluation tables

-- Step 1: Create call_metrics table
CREATE TABLE IF NOT EXISTS brokerage.call_metrics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    call_id TEXT NOT NULL UNIQUE REFERENCES brokerage.conversations(call_id) ON DELETE CASCADE,
    customer_id UUID NOT NULL REFERENCES brokerage.customers(id) ON DELETE CASCADE,
    
    -- TIER 1: Critical metrics
    frc_achieved BOOLEAN NOT NULL,
    frc_type VARCHAR(50),
    intent_detected VARCHAR(100) NOT NULL,
    intent_accuracy_score FLOAT DEFAULT 0.0 CHECK (intent_accuracy_score >= 0 AND intent_accuracy_score <= 1),
    
    -- TIER 2: Important metrics
    call_quality_score FLOAT DEFAULT 0.0 CHECK (call_quality_score >= 0 AND call_quality_score <= 1),
    customer_sentiment VARCHAR(50) DEFAULT 'neutral',
    script_compliance_score FLOAT DEFAULT 0.0 CHECK (script_compliance_score >= 0 AND script_compliance_score <= 1),
    
    -- Supporting data
    key_objections TEXT[] DEFAULT ARRAY[]::TEXT[],
    agent_responses_to_objections TEXT[] DEFAULT ARRAY[]::TEXT[],
    next_steps_agreed TEXT,
    call_duration_seconds INT DEFAULT 0,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Step 2: Create call_judgments table
CREATE TABLE IF NOT EXISTS brokerage.call_judgments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    call_id TEXT NOT NULL UNIQUE REFERENCES brokerage.conversations(call_id) ON DELETE CASCADE,
    customer_id UUID NOT NULL REFERENCES brokerage.customers(id) ON DELETE CASCADE,
    metrics_id UUID REFERENCES brokerage.call_metrics(id) ON DELETE CASCADE,
    
    judge_reasoning TEXT NOT NULL,
    judge_model VARCHAR(50) DEFAULT 'gpt-5-nano',
    
    strengths TEXT[] DEFAULT ARRAY[]::TEXT[],
    improvements TEXT[] DEFAULT ARRAY[]::TEXT[],
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Step 3: Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_call_metrics_call_id ON brokerage.call_metrics(call_id);
CREATE INDEX IF NOT EXISTS idx_call_metrics_customer_id ON brokerage.call_metrics(customer_id);
CREATE INDEX IF NOT EXISTS idx_call_metrics_frc ON brokerage.call_metrics(frc_achieved);
CREATE INDEX IF NOT EXISTS idx_call_metrics_quality ON brokerage.call_metrics(call_quality_score);
CREATE INDEX IF NOT EXISTS idx_call_metrics_created_at ON brokerage.call_metrics(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_call_metrics_intent ON brokerage.call_metrics(intent_detected);

CREATE INDEX IF NOT EXISTS idx_call_judgments_call_id ON brokerage.call_judgments(call_id);
CREATE INDEX IF NOT EXISTS idx_call_judgments_customer_id ON brokerage.call_judgments(customer_id);
CREATE INDEX IF NOT EXISTS idx_call_judgments_created_at ON brokerage.call_judgments(created_at DESC);

-- Step 4: Add updated_at triggers
CREATE OR REPLACE FUNCTION brokerage.update_call_metrics_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_update_call_metrics_updated_at ON brokerage.call_metrics;
CREATE TRIGGER trigger_update_call_metrics_updated_at
BEFORE UPDATE ON brokerage.call_metrics
FOR EACH ROW
EXECUTE FUNCTION brokerage.update_call_metrics_updated_at();

CREATE OR REPLACE FUNCTION brokerage.update_call_judgments_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_update_call_judgments_updated_at ON brokerage.call_judgments;
CREATE TRIGGER trigger_update_call_judgments_updated_at
BEFORE UPDATE ON brokerage.call_judgments
FOR EACH ROW
EXECUTE FUNCTION brokerage.update_call_judgments_updated_at();

-- Step 5: Add RLS (Row Level Security) if using Supabase Auth
ALTER TABLE brokerage.call_metrics ENABLE ROW LEVEL SECURITY;
ALTER TABLE brokerage.call_judgments ENABLE ROW LEVEL SECURITY;

-- RLS Policies (adjust based on your auth model)
CREATE POLICY "System can manage call metrics" ON brokerage.call_metrics
    USING (true);

CREATE POLICY "System can manage call judgments" ON brokerage.call_judgments
    USING (true);
