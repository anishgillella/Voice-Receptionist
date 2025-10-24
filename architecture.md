# 🏗️ Voice Agent MVP - Production Architecture

## System Overview

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                    VOICE AGENT MVP - PRODUCTION FLOW                         │
│        Call Stack + Email Campaigns + Vector DB + Post-Call Forms           │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## 📞 CALL STACK - Voice Pipeline with Voicemail Fallback

### Call Stack Naming Convention

```
OUTBOUND_CALL_STACK:
├── va:call:outbound:{campaign_id}:{prospect_id} (Redis key)
├── va:voicemail:{call_id}:{timestamp} (Voicemail tracking)
└── va:inbound:{agent_id}:{call_id} (Inbound agent routing)

CALL STATES:
├── INITIATED (call placed)
├── RINGING (customer phone ringing)
├── CONNECTED (customer answers)
├── VOICEMAIL (customer unavailable)
├── COMPLETED (natural end)
└── FAILED (connection error)
```

### Call Flow with Voicemail Fallback

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    OUTBOUND CALL SEQUENCE WITH FALLBACK                     │
└─────────────────────────────────────────────────────────────────────────────┘

STEP 1: INITIATE OUTBOUND CALL
┌──────────────────────────────────────────────────────────────────────────┐
│ POST /call/initiate                                                      │
│ Input: {                                                                 │
│   campaign_id: "camp_001",                                              │
│   prospect_id: "prospect_123",                                          │
│   phone_number: "+15551234567",                                         │
│   prospect_data: {...enriched data...}                                  │
│ }                                                                        │
│                                                                          │
│ Actions:                                                                │
│ 1. Create Redis entry: va:call:outbound:camp_001:prospect_123          │
│ 2. Store call state: INITIATED                                         │
│ 3. Call VAPI with prospect context                                     │
│ 4. Return 202 Accepted (non-blocking)                                  │
└──────────────────────────────────────────────────────────────────────────┘

STEP 2: CUSTOMER AVAILABILITY CHECK (3 Scenarios)
┌──────────────────────────────────────────────────────────────────────────┐
│                                                                          │
│ SCENARIO A: CUSTOMER ANSWERS ✅                                         │
│ ├─ Update call state: CONNECTED                                        │
│ ├─ Start conversation with agent                                       │
│ ├─ Real-time transcript collection                                     │
│ └─ Continue normal conversation flow                                   │
│                                                                          │
│ SCENARIO B: CUSTOMER DECLINES / UNAVAILABLE ❌                         │
│ ├─ VAPI detects: No answer after 6 rings (30 seconds)                 │
│ ├─ Update call state: VOICEMAIL_PENDING                               │
│ ├─ Trigger voicemail playback (pre-recorded or TTS)                   │
│ └─ Jump to STEP 3                                                      │
│                                                                          │
│ SCENARIO C: CONNECTION ERROR / NETWORK FAILURE 🔴                      │
│ ├─ Update call state: FAILED                                           │
│ ├─ Log error with retry flag                                           │
│ ├─ Queue for retry (max 3 retries)                                     │
│ └─ Mark as: RETRY_SCHEDULED                                            │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘

STEP 3: VOICEMAIL DELIVERY WITH CALLBACK LINK
┌──────────────────────────────────────────────────────────────────────────┐
│ VOICEMAIL MESSAGE STRUCTURE:                                             │
│                                                                          │
│ "Hi {prospect_name}, this is Jennifer from InsureFlow Solutions.        │
│  We help businesses like {company_name} save 20-40% on insurance.      │
│  I couldn't reach you, but I'd love to discuss your coverage needs.     │
│                                                                          │
│  Click here to schedule a callback: {callback_link}                    │
│  Or call us back: {toll_free_number}                                   │
│                                                                          │
│  [Voicemail duration: 20-30 seconds]"                                  │
│                                                                          │
│ ACTIONS:                                                                 │
│ 1. Store voicemail event with unique callback token (7-day expiry)     │
│ 2. Create clickable link: https://api.insureflow.com/callback/{token}  │
│ 3. Track: delivered, clicked, time-to-callback, conversion rate        │
└──────────────────────────────────────────────────────────────────────────┘

STEP 4: INBOUND CALLBACK ROUTING
┌──────────────────────────────────────────────────────────────────────────┐
│ WHEN PROSPECT CALLS BACK OR CLICKS CALLBACK LINK:                       │
│                                                                          │
│ 1. VAPI receives inbound call on assigned number                        │
│ 2. Route to INBOUND AGENT (dedicated)                                   │
│ 3. Load prospect context from Supabase                                  │
│ 4. Inject full context into agent system prompt                         │
│ 5. Connect customer to agent with warm greeting                         │
│                                                                          │
│ Context includes:                                                        │
│ - Previous outbound call summary                                         │
│ - Enriched company data                                                  │
│ - Research findings                                                      │
│ - Email campaign engagement                                              │
└──────────────────────────────────────────────────────────────────────────┘

STEP 5: END-OF-CALL PROCESSING (Async Tasks)
┌──────────────────────────────────────────────────────────────────────────┐
│ Non-blocking operations triggered:                                       │
│ ├─ Generate & store transcript embedding                                │
│ ├─ Create AI summary                                                    │
│ ├─ Extract form-fillable data                                           │
│ ├─ Generate post-call documents (PDF quote)                            │
│ └─ Update call metrics & analytics                                      │
│                                                                          │
│ All tasks run in parallel - webhook returns <100ms                      │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## 📧 EMAIL BLAST CAMPAIGNS - AI-Driven Campaign Selection

### Campaign Types & AI Logic

```
CAMPAIGN DECISION TREE:

Step 1: Check Company History
├─ No prior interactions? → COLD_CAMPAIGN
├─ Past failed calls? → WARM_RECONNECT_CAMPAIGN
├─ Past successful calls? → FOLLOW_UP_CAMPAIGN
└─ Recent voicemail? → VOICEMAIL_NURTURE_CAMPAIGN

Step 2: AI Recommendation Analysis
Based on enriched data + deep research:
├─ Company revenue: Size-specific messaging
├─ Industry-specific: Tech, Manufacturing, Retail, Services
├─ Recent news: Funding, leadership, expansion, regulations
└─ Call history: Prior responses, objections, interests

Step 3: Campaign Assignment
├─ COLD_OUTREACH: Generic value prop + research
├─ WARM_ENGAGEMENT: Personalized from previous calls
├─ NURTURE_SEQUENCE: Multi-touch voicemail follow-up
└─ TARGETED_ATTACK: Trigger-based, industry-specific
```

### Email Campaign Workflow

```
1. CAMPAIGN SETUP
   └─ Input: campaign_type, prospects, personalization settings
   └─ Actions: Fetch enriched data, fetch call history, generate personalized emails

2. PERSONALIZED EMAIL GENERATION
   └─ LLM generates unique email for each prospect
   └─ References specific company details, recent news, industry pain points

3. BATCH STORAGE IN S3
   └─ Path: /email-campaigns/{campaign_id}/drafts/{prospect_id}_email.json
   └─ Includes metadata: subject, body, personalization tokens

4. SEND EMAILS
   └─ SendGrid/Mailgun batch API
   └─ Add unique tracking tokens & click links
   └─ Store sent metadata in Supabase

5. REAL-TIME ANALYTICS
   └─ Opens (35%), Clicks (12%), Responses (5%), Conversions (2%)
   └─ Auto follow-ups: reminders, value-prop emails, outbound calls

RESULT: Multi-touch campaign with automated nurture sequences
```

---

## 🗄️ UNIFIED DATA MODEL - Pydantic + Supabase + pgvector

### Data Schema (Pydantic Models + Database Tables)

```
PYDANTIC MODELS (Validation):
├─ CompanyData: enrichment_data, industry, revenue_range, technology_stack
├─ CallData: transcript, embeddings, summary, sentiment, intent, metrics
├─ EmailData: campaign_type, personalization, tracking, responses
└─ ResearchData: findings, sources, confidence_score, embeddings

SUPABASE TABLES (Storage):
├─ companies: enrichment_data (JSONB)
├─ conversations: transcript_embedding (vector, 1024 dims) ← pgvector
├─ emails: campaign_data (JSONB), tracking_data (JSONB)
├─ research_corpus: findings_embedding (vector, 1024 dims)
└─ conversation_metadata: sentiment, intent, quality_score, voicemail_delivered
```

### pgvector Implementation

```
SETUP:
1. Enable pgvector extension: CREATE EXTENSION IF NOT EXISTS vector;
2. Add vector columns: transcript_embedding vector(1024)
3. Create indexes: USING ivfflat with cosine_ops

SEMANTIC SEARCH:
SELECT call_id, summary FROM conversations c
WHERE 1 - (transcript_embedding <=> query_embedding) > 0.7
ORDER BY transcript_embedding <=> query_embedding
LIMIT 3;

SCALING TO PINECONE (at 1000+ calls/day):
├─ pgvector handles: 0-100K embeddings (~10K calls/day)
├─ Migrate path: Create Pinecone index → Backfill → Dual-write → Migrate reads
├─ Benefits: Optimized for millions, faster similarity search (<50ms)
└─ Cost: ~$200-500/month at scale
```

---

## 🔄 CONTEXT RETRIEVAL - Information Corpus Integration

```
WHEN AGENT NEEDS CONTEXT (during call):

1. Generate embedding for customer utterance
2. Search unified corpus:
   ├─ Similar past calls (conversations table)
   ├─ Relevant research (research_corpus table)
   ├─ Company data (companies table)
   └─ Email campaign responses (emails table)
3. Rank by cosine similarity
4. Inject top-10 results into system prompt

CONTEXT BUDGET (3000 tokens total):
├─ Company data: 300 tokens
├─ Research findings: 500 tokens
├─ Call history: 800 tokens
├─ Email campaign: 300 tokens
└─ Reserved for conversation: 1100 tokens

RESULT: Agent receives rich, contextual information for personalized interactions
```

---

## 📋 POST-CALL WORKFLOW - Form Filling & Document Generation

```
TRIGGER: Call ends → webhook received

STEP 1: DATA EXTRACTION FROM TRANSCRIPT
├─ LLM extracts: name, company, email, employee_count, coverage_type, budget
├─ Validate with Pydantic (confidence threshold >0.8)
└─ Handle missing data gracefully

STEP 2: FORM TYPE SELECTION
├─ IF coverage_type = "Quote" → PDF_QUOTE_FORM
├─ IF coverage_type = "Proposal" → PDF_PROPOSAL_FORM
├─ IF customer_interested + wants_meeting → WEB_MEETING_FORM (Stagehand)
└─ IF needs_followup → CTA_EMAIL_FORM

STEP 3: DOCUMENT GENERATION
├─ JoyFill: Fill PDF template with extracted data + calculated premium
├─ Store: /quotes/{company_id}/{call_id}_quote.pdf in S3
└─ Generate: Shareable link (30-day expiry)

STEP 4: STAGEHAND WEB FORM (if applicable)
├─ Launch browser → Navigate to form URL
├─ Auto-fill: name, company, email, phone, preferred times
├─ Submit form → Capture confirmation
└─ Result: Meeting automatically scheduled!

STEP 5: EMAIL DELIVERY
├─ Send: Personalized email with PDF attachment
├─ Track: Opens, downloads, signature collection
└─ Auto follow-up: Reminders if no action

STEP 6: ANALYTICS & CONVERSION
├─ Metrics: Quote opened, signed, conversion to customer
├─ Smart follow-ups: 3-day reminder, sign-up link, onboarding
└─ CRM update: Ready for upsell
```

---

## 📊 MVP METRICS & SCALING ROADMAP

```
PHASE 1 - MVP (Current)
├─ Calls/day: 10-50
├─ Email campaigns/week: 2-5
├─ Vector DB: pgvector (Supabase)
├─ Context retrieval: <100ms
└─ Cost: ~$200-300/month

PHASE 2 - SCALING (100-500 calls/day)
├─ Calls/day: 100-500
├─ Email campaigns/week: 10-20
├─ Vector DB: pgvector (handles 100K+ embeddings)
├─ Context retrieval: ~50-100ms
└─ Cost: ~$500-1000/month

PHASE 3 - PRODUCTION SCALE (1000+ calls/day)
├─ Calls/day: 1000+
├─ Email campaigns/week: 50+
├─ Vector DB: MIGRATE TO PINECONE
│  ├─ Pinecone index (1024-dim, cosine)
│  ├─ Backfill embeddings from pgvector
│  ├─ Dual-write layer (Supabase + Pinecone)
│  └─ Migrate reads to Pinecone
├─ Context retrieval: <50ms
├─ Pinecone cost: ~$200-500/month
└─ Total infrastructure: ~$1500-2000/month

SCALING TRIGGERS:
├─ +Redis: 500+ calls/day (embedding cache)
├─ +Pinecone: 1000+ calls/day (pgvector limit)
├─ +Modal GPU: 5000+ calls/day (faster embeddings)
└─ +Multi-region: 10000+ calls/day (latency optimization)
```

---

## 🎯 Tech Stack Summary

```
VOICE ORCHESTRATION:
├─ VAPI: Call orchestration, agent management
├─ Deepgram nova-3: Real-time STT, 100ms endpointing
├─ ElevenLabs: TTS, paula voice, <500ms latency
└─ LiveKit: WebRTC media transport

BACKEND:
├─ FastAPI: Async webhook handler, <100ms response
├─ BGE-Large: 1024-dim embeddings (Supabase pgvector)
└─ Redis: Embedding cache, call state management

DATA & AI:
├─ Pydantic: Type-safe data validation
├─ Supabase PostgreSQL: Primary database + pgvector
├─ S3: Email campaigns, PDFs, transcripts
├─ LLM: Claude/GPT for summarization & extraction

AUTOMATION:
├─ Stagehand: Browser automation for web forms
├─ JoyFill: PDF form filling
├─ SendGrid/Mailgun: Email delivery at scale
└─ Parallel API: Company enrichment & research

OBSERVABILITY:
├─ Logfire: Distributed tracing
├─ Prometheus: Metrics collection
└─ Custom dashboards: Call metrics, latency, conversion
```

---

**MVP Status:** ✅ READY FOR IMPLEMENTATION
**Data Architecture:** ✅ Pydantic + Supabase + pgvector  
**Scaling Path:** ✅ Clear route to Pinecone at 1000+ calls/day
**Information Corpus:** ✅ Unified (Company + Calls + Emails + Research)
**Post-Call Forms:** ✅ Stagehand + JoyFill integrated
**Voicemail Strategy:** ✅ Callback links + inbound routing
**Email Campaigns:** ✅ AI-driven selection + automation