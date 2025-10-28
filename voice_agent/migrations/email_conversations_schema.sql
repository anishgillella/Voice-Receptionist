-- Email Conversations Schema for multi-turn email interactions
-- This tracks incoming customer emails and auto-generated responses

CREATE SCHEMA IF NOT EXISTS brokerage;

-- Email conversation records (sent and received emails)
CREATE TABLE IF NOT EXISTS brokerage.email_conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_id UUID NOT NULL REFERENCES brokerage.customers(id) ON DELETE CASCADE,
    from_email VARCHAR(255) NOT NULL,
    to_email VARCHAR(255) NOT NULL,
    subject TEXT,
    body TEXT NOT NULL,
    email_type VARCHAR(50) DEFAULT 'reply', -- 'reply', 'initial', 'auto_response'
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_email_conversations_customer ON brokerage.email_conversations(customer_id);
CREATE INDEX idx_email_conversations_created ON brokerage.email_conversations(created_at DESC);

-- Email analysis records (LLM analysis of email replies)
CREATE TABLE IF NOT EXISTS brokerage.email_analysis (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_id UUID NOT NULL REFERENCES brokerage.customers(id) ON DELETE CASCADE,
    email_id UUID NOT NULL REFERENCES brokerage.email_conversations(id) ON DELETE CASCADE,
    sentiment VARCHAR(50), -- 'positive', 'neutral', 'negative'
    engagement_level VARCHAR(50), -- 'high', 'medium', 'low'
    customer_intent TEXT,
    interest_change VARCHAR(50), -- 'increased', 'decreased', 'stable'
    actions TEXT[], -- Array of action types
    suggested_next_steps TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_email_analysis_customer ON brokerage.email_analysis(customer_id);
CREATE INDEX idx_email_analysis_email ON brokerage.email_analysis(email_id);

-- Auto-generated responses sent to customers
CREATE TABLE IF NOT EXISTS brokerage.auto_responses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_id UUID NOT NULL REFERENCES brokerage.customers(id) ON DELETE CASCADE,
    email_id UUID NOT NULL REFERENCES brokerage.email_conversations(id) ON DELETE CASCADE,
    response_body TEXT NOT NULL,
    template_used VARCHAR(255), -- Template name (e.g., 'proposal_offer', 'meeting_confirmation')
    action_type VARCHAR(255), -- Action that triggered the response
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_auto_responses_customer ON brokerage.auto_responses(customer_id);
CREATE INDEX idx_auto_responses_email ON brokerage.auto_responses(email_id);

-- Customer engagement tracking (combines calls and emails for full context)
CREATE TABLE IF NOT EXISTS brokerage.customer_engagement (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_id UUID NOT NULL REFERENCES brokerage.customers(id) ON DELETE CASCADE,
    engagement_type VARCHAR(50), -- 'call', 'email_sent', 'email_received', 'response_auto'
    interaction_id UUID, -- ID of the call or email that triggered this
    notes TEXT,
    sentiment VARCHAR(50),
    interest_level VARCHAR(50),
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_engagement_customer ON brokerage.customer_engagement(customer_id);
CREATE INDEX idx_engagement_created ON brokerage.customer_engagement(created_at DESC);
CREATE INDEX idx_engagement_type ON brokerage.customer_engagement(engagement_type);
