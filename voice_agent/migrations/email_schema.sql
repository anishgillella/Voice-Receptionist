-- Email communication schema for storing Gmail integration and email data

-- Default email account configuration
CREATE TABLE IF NOT EXISTS email_config (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    config_key VARCHAR(255) NOT NULL UNIQUE,
    email_address VARCHAR(255) NOT NULL,
    access_token TEXT NOT NULL,
    refresh_token TEXT NOT NULL,
    token_expiry TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Gmail OAuth tokens per customer
CREATE TABLE IF NOT EXISTS gmail_accounts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    customer_id UUID NOT NULL REFERENCES public.customers(id) ON DELETE CASCADE,
    email_address VARCHAR(255) NOT NULL,
    access_token TEXT NOT NULL,
    refresh_token TEXT NOT NULL,
    token_expiry TIMESTAMP WITH TIME ZONE,
    scopes TEXT[] DEFAULT ARRAY['https://www.googleapis.com/auth/gmail.modify'],
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(customer_id, email_address)
);

-- Email messages
CREATE TABLE IF NOT EXISTS emails (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    customer_id UUID NOT NULL REFERENCES public.customers(id) ON DELETE CASCADE,
    gmail_account_id UUID REFERENCES gmail_accounts(id) ON DELETE CASCADE,
    gmail_message_id VARCHAR(255) NOT NULL, -- Gmail's unique message ID
    gmail_thread_id VARCHAR(255),
    sender_email VARCHAR(255) NOT NULL,
    sender_name VARCHAR(255),
    recipient_email VARCHAR(255) NOT NULL,
    recipient_name VARCHAR(255),
    subject VARCHAR(512),
    body_text TEXT,
    body_html TEXT,
    email_type VARCHAR(50) DEFAULT 'received', -- 'received', 'sent', 'draft'
    received_at TIMESTAMP WITH TIME ZONE,
    sent_at TIMESTAMP WITH TIME ZONE,
    is_read BOOLEAN DEFAULT FALSE,
    has_attachments BOOLEAN DEFAULT FALSE,
    attachment_count INTEGER DEFAULT 0,
    labels TEXT[] DEFAULT ARRAY[], -- Gmail labels/tags
    metadata JSONB, -- Store additional Gmail metadata
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(gmail_message_id)
);

-- Email attachments (documents)
CREATE TABLE IF NOT EXISTS email_attachments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email_id UUID NOT NULL REFERENCES emails(id) ON DELETE CASCADE,
    customer_id UUID NOT NULL REFERENCES public.customers(id) ON DELETE CASCADE,
    filename VARCHAR(255) NOT NULL,
    mime_type VARCHAR(100),
    file_size_bytes INTEGER,
    file_extension VARCHAR(10), -- 'pdf', 'docx', 'doc'
    s3_key VARCHAR(512) NOT NULL, -- Full S3 path: customers/{first_name}_{last_name}/emails/{email_id}/{filename}
    s3_url TEXT NOT NULL, -- Full S3 URL for direct access
    upload_status VARCHAR(50) DEFAULT 'pending', -- 'pending', 'uploading', 'success', 'failed'
    upload_error TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Email conversations/threads with customer context
CREATE TABLE IF NOT EXISTS email_conversations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    customer_id UUID NOT NULL REFERENCES public.customers(id) ON DELETE CASCADE,
    gmail_account_id UUID REFERENCES gmail_accounts(id) ON DELETE CASCADE,
    gmail_thread_id VARCHAR(255) NOT NULL,
    subject VARCHAR(512),
    participant_emails TEXT[] NOT NULL, -- All emails in the thread
    ordered_message_ids UUID[] DEFAULT ARRAY[], -- Ordered list of message IDs [msg-1, msg-2, msg-3]
    message_count INTEGER DEFAULT 0,
    last_message_at TIMESTAMP WITH TIME ZONE,
    is_archived BOOLEAN DEFAULT FALSE,
    conversation_summary TEXT, -- Optional AI-generated summary
    conversation_thread JSONB DEFAULT '{}'::jsonb, -- Complete thread structure with messages & attachments
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(gmail_thread_id)
);

-- Create indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_email_config_key ON email_config(config_key);
CREATE INDEX IF NOT EXISTS idx_emails_customer_id ON emails(customer_id);
CREATE INDEX IF NOT EXISTS idx_emails_gmail_account_id ON emails(gmail_account_id);
CREATE INDEX IF NOT EXISTS idx_emails_received_at ON emails(received_at DESC);
CREATE INDEX IF NOT EXISTS idx_emails_sender_email ON emails(sender_email);
CREATE INDEX IF NOT EXISTS idx_emails_thread_id ON emails(gmail_thread_id);
CREATE INDEX IF NOT EXISTS idx_email_attachments_customer_id ON email_attachments(customer_id);
CREATE INDEX IF NOT EXISTS idx_email_attachments_email_id ON email_attachments(email_id);
CREATE INDEX IF NOT EXISTS idx_email_conversations_customer_id ON email_conversations(customer_id);
CREATE INDEX IF NOT EXISTS idx_email_conversations_thread_id ON email_conversations(gmail_thread_id);
CREATE INDEX IF NOT EXISTS idx_gmail_accounts_customer_id ON gmail_accounts(customer_id);

-- Enable RLS (Row Level Security) for email tables
ALTER TABLE email_config ENABLE ROW LEVEL SECURITY;
ALTER TABLE gmail_accounts ENABLE ROW LEVEL SECURITY;
ALTER TABLE emails ENABLE ROW LEVEL SECURITY;
ALTER TABLE email_attachments ENABLE ROW LEVEL SECURITY;
ALTER TABLE email_conversations ENABLE ROW LEVEL SECURITY;

-- RLS Policies (adjust based on your authentication model)
CREATE POLICY "System can read email config" ON email_config
    FOR SELECT USING (true);

CREATE POLICY "Users can view their own Gmail accounts" ON gmail_accounts
    FOR SELECT USING (auth.uid()::text = customer_id::text);

CREATE POLICY "Users can view their own emails" ON emails
    FOR SELECT USING (auth.uid()::text = customer_id::text);

CREATE POLICY "Users can view their own attachments" ON email_attachments
    FOR SELECT USING (auth.uid()::text = customer_id::text);

CREATE POLICY "Users can view their own conversations" ON email_conversations
    FOR SELECT USING (auth.uid()::text = customer_id::text);

-- ====================================================================
-- FUNCTIONS FOR BUILDING CONVERSATION THREADS
-- ====================================================================

-- Function to build complete conversation thread JSONB
CREATE OR REPLACE FUNCTION build_conversation_thread(p_thread_id VARCHAR(255))
RETURNS JSONB AS $$
DECLARE
    v_thread JSONB;
    v_message RECORD;
    v_attachments JSONB;
BEGIN
    -- Build the thread structure with all messages and attachments
    SELECT jsonb_build_object(
        'thread_id', p_thread_id,
        'created_at', MIN(e.created_at)::TEXT,
        'updated_at', MAX(e.updated_at)::TEXT,
        'messages', jsonb_agg(
            jsonb_build_object(
                'id', e.id::TEXT,
                'message_id', e.gmail_message_id,
                'from', e.sender_email,
                'from_name', e.sender_name,
                'to', e.recipient_email,
                'to_name', e.recipient_name,
                'subject', e.subject,
                'body_text', e.body_text,
                'body_html', e.body_html,
                'received_at', e.received_at::TEXT,
                'sent_at', e.sent_at::TEXT,
                'email_type', e.email_type,
                'attachments', COALESCE((
                    SELECT jsonb_agg(
                        jsonb_build_object(
                            'id', ea.id::TEXT,
                            'filename', ea.filename,
                            'mime_type', ea.mime_type,
                            'file_size_bytes', ea.file_size_bytes,
                            's3_key', ea.s3_key,
                            's3_url', ea.s3_url,
                            'upload_status', ea.upload_status
                        )
                    )
                    FROM email_attachments ea
                    WHERE ea.email_id = e.id
                ), '[]'::jsonb)
            )
            ORDER BY COALESCE(e.received_at, e.sent_at, e.created_at)
        )
    ) INTO v_thread
    FROM emails e
    WHERE e.gmail_thread_id = p_thread_id;
    
    RETURN v_thread;
END;
$$ LANGUAGE plpgsql STABLE;

-- Function to update conversation thread after new email added
CREATE OR REPLACE FUNCTION update_conversation_thread()
RETURNS TRIGGER AS $$
DECLARE
    v_new_thread JSONB;
    v_message_ids UUID[];
BEGIN
    -- Build new thread structure
    v_new_thread := build_conversation_thread(NEW.gmail_thread_id);
    
    -- Get ordered message IDs
    SELECT ARRAY_AGG(e.id ORDER BY COALESCE(e.received_at, e.sent_at, e.created_at))
    INTO v_message_ids
    FROM emails e
    WHERE e.gmail_thread_id = NEW.gmail_thread_id;
    
    -- Update or create email_conversations
    INSERT INTO email_conversations (
        customer_id,
        gmail_account_id,
        gmail_thread_id,
        subject,
        participant_emails,
        ordered_message_ids,
        message_count,
        last_message_at,
        conversation_thread
    )
    SELECT
        NEW.customer_id,
        NEW.gmail_account_id,
        NEW.gmail_thread_id,
        NEW.subject,
        ARRAY_AGG(DISTINCT COALESCE(e.sender_email, e.recipient_email)),
        v_message_ids,
        COUNT(*)::INTEGER,
        MAX(COALESCE(e.received_at, e.sent_at, e.created_at)),
        v_new_thread
    FROM emails e
    WHERE e.gmail_thread_id = NEW.gmail_thread_id
    ON CONFLICT (gmail_thread_id) DO UPDATE SET
        ordered_message_ids = EXCLUDED.ordered_message_ids,
        message_count = EXCLUDED.message_count,
        last_message_at = EXCLUDED.last_message_at,
        conversation_thread = EXCLUDED.conversation_thread,
        updated_at = NOW();
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger to update conversation thread when new email added
CREATE TRIGGER trigger_update_conversation_thread
AFTER INSERT ON emails
FOR EACH ROW
EXECUTE FUNCTION update_conversation_thread();

-- ====================================================================
-- HELPER FUNCTIONS FOR QUERIES
-- ====================================================================

-- Function to get thread with all messages for a customer
CREATE OR REPLACE FUNCTION get_customer_thread(
    p_customer_id UUID,
    p_thread_id VARCHAR(255)
)
RETURNS TABLE (
    thread_id UUID,
    customer_id UUID,
    gmail_thread_id VARCHAR(255),
    subject VARCHAR(512),
    message_count INTEGER,
    last_message_at TIMESTAMP WITH TIME ZONE,
    participant_emails TEXT[],
    conversation_thread JSONB
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        ec.id,
        ec.customer_id,
        ec.gmail_thread_id,
        ec.subject,
        ec.message_count,
        ec.last_message_at,
        ec.participant_emails,
        ec.conversation_thread
    FROM email_conversations ec
    WHERE ec.customer_id = p_customer_id
    AND ec.gmail_thread_id = p_thread_id;
END;
$$ LANGUAGE plpgsql STABLE;

-- Function to get all threads for a customer
CREATE OR REPLACE FUNCTION get_customer_threads(p_customer_id UUID)
RETURNS TABLE (
    thread_id UUID,
    customer_id UUID,
    gmail_thread_id VARCHAR(255),
    subject VARCHAR(512),
    message_count INTEGER,
    last_message_at TIMESTAMP WITH TIME ZONE,
    participant_emails TEXT[]
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        ec.id,
        ec.customer_id,
        ec.gmail_thread_id,
        ec.subject,
        ec.message_count,
        ec.last_message_at,
        ec.participant_emails
    FROM email_conversations ec
    WHERE ec.customer_id = p_customer_id
    ORDER BY ec.last_message_at DESC;
END;
$$ LANGUAGE plpgsql STABLE;

-- Function to get all documents in a thread
CREATE OR REPLACE FUNCTION get_thread_documents(p_thread_id VARCHAR(255))
RETURNS TABLE (
    document_id UUID,
    filename VARCHAR(255),
    mime_type VARCHAR(100),
    file_size_bytes INTEGER,
    s3_url TEXT,
    sender_email VARCHAR(255),
    received_at TIMESTAMP WITH TIME ZONE,
    upload_status VARCHAR(50)
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        ea.id,
        ea.filename,
        ea.mime_type,
        ea.file_size_bytes,
        ea.s3_url,
        e.sender_email,
        e.received_at,
        ea.upload_status
    FROM email_attachments ea
    JOIN emails e ON ea.email_id = e.id
    WHERE e.gmail_thread_id = p_thread_id
    ORDER BY e.received_at;
END;
$$ LANGUAGE plpgsql STABLE;
