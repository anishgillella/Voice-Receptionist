# 📋 Phase 1 — Voice Agent MVP

## 🎯 Overview

**Duration:** 3-4 weeks  
**Foundation:** This is the foundational phase with no dependencies. All subsequent phases build upon Phase 1.

AI Brokerage's first phase establishes the core voice agent infrastructure, evaluation systems, and monitoring foundation needed for a production-grade outbound prospecting agent.

---

## 🎯 Phase 1 Objectives

- Build a working outbound prospecting agent that can make real calls
- Establish evaluation infrastructure (MLLM-as-a-Judge)
- Create visibility into voice quality and business metrics
- Prove sub-700ms latency is achievable

---

## 🧩 Modular Components

### **Component 1: Voice Agent Core**
**Purpose:** Real-time call handling and conversation management  
**Technology Stack:** Retell, FastAPI, Deepgram (STT), ElevenLabs (TTS)

**Deliverables:**
- ✅ Retell + FastAPI integration
  - Webhook handlers for call events (call_started, call_ended, speech_recognized, etc.)
  - Session management for concurrent calls
  - Error handling and retry logic
- ✅ Speech-to-Text (STT) Pipeline
  - Deepgram streaming integration
  - Real-time transcription with minimal latency
  - Fallback error handling
- ✅ Text-to-Speech (TTS) Pipeline
  - ElevenLabs low-latency voice synthesis
  - Voice persona configuration
  - Streaming audio delivery to Retell

**Success Criteria:**
- Calls connect within 2 seconds
- STT → Response → TTS latency < 700ms (p95)
- 99%+ uptime for voice pipeline

---

### **Component 2: Conversation & Prospecting Logic**
**Purpose:** Agent reasoning, response generation, and outbound prospecting workflow  
**Technology Stack:** GPT-4o, FastAPI, conversation state management

**Deliverables:**
- ✅ Outbound Prospecting Agent
  - Cold outreach script generation
  - Warm intro → Pain point discovery → Value prop → Objection handling → CTA (book call/get quote)
  - Typical duration: 3-7 minutes per call
  - Conversation state management across turns
- ✅ System Prompts & Personas
  - Professional tone configuration
  - Industry-specific objection handling playbooks
  - Lead qualification scoring logic

**Success Criteria:**
- Agent responds within 500ms (inference + streaming)
- Qualification logic correctly identifies 80%+ of qualified leads

---

### **Component 3: MLLM-as-a-Judge Evaluation System**
**Purpose:** Automated evaluation of voice agent responses for compliance, accuracy, and tone  
**Technology Stack:** GPT-4o, Logfire, Postgres

**Deliverables:**
- ✅ Judge Scoring System with 5 Rubrics
  - `compliance_score` (0-1) — regulatory adherence (state-specific insurance rules)
  - `accuracy_score` (0-1) — factual correctness of insurance info
  - `clarity_score` (0-1) — understandability for non-experts
  - `empathy_score` (0-1) — emotional appropriateness
  - `conversion_score` (0-1) — likelihood to move deal forward
- ✅ Domain-Specific Rubrics
  - Insurance compliance rules by state
  - Factual accuracy benchmarks
  - Tone appropriateness guidelines
- ✅ Judge Execution Pipeline
  - Run GPT-4o + rubrics against conversation logs
  - Store scores in Postgres for historical tracking
  - Integration with feedback loop for training

**Success Criteria:**
- Judge evaluation completes in < 5 seconds per conversation
- ≥80% of 20 test calls are scorable (judge doesn't error)
- Judge scores correlate with human feedback

---

### **Component 4: Synthetic Insurance Dataset**
**Purpose:** Generate realistic insurance conversations for training and evaluation  
**Technology Stack:** Python, JSON, Logfire

**Deliverables:**
- ✅ Synthetic Prospecting Dataset
  - 500+ conversations with realistic commercial insurance scenarios
  - Structured format: conversation_id, turns (customer/agent), metadata
  - Risk scores, industry tags, outcome labels
- ✅ Evaluation Pairs
  - Each entry: model output + judge score + feedback signal
  - Used for post-training alignment (Phase 5)
- ✅ Insurance Domain Coverage
  - Multiple industries (logistics, manufacturing, retail, etc.)
  - Various objection scenarios
  - Qualified vs. unqualified lead examples

**Success Criteria:**
- 500+ conversations generated
- Covers ≥5 distinct insurance scenarios
- Judge scores match expected ranges (0.6-0.95 for quality examples)

---

### **Component 5: Twilio Outbound Dialer Integration**
**Purpose:** Enable outbound calling at scale with predictive pacing  
**Technology Stack:** Twilio, FastAPI, Redis (queue management)

**Deliverables:**
- ✅ Twilio Integration
  - Outbound call initiation via Twilio API
  - Webhook integration with Retell for media
  - Call recording and metadata logging
- ✅ Predictive Dialer
  - Lead queue management (Redis)
  - Predictive pacing to minimize agent idle time
  - Call distribution logic
- ✅ Call Tracking
  - Call ID correlation across Twilio, Retell, Logfire
  - Call duration, answer rate, completion rate metrics

**Success Criteria:**
- Outbound calls initiate without errors
- Call abandonment rate < 5%
- Predictive pacing reduces idle time by 20%+

---

### **Component 6: Conversation Analytics Dashboard**
**Purpose:** Real-time visibility into voice agent performance and business metrics  
**Technology Stack:** React/Next.js, Postgres, Logfire

**Deliverables:**
- ✅ Real-Time Metrics Dashboard
  - Live call count (ongoing)
  - Call duration distribution
  - Completion rate (% reaching goal)
  - Booking/qualification rate
  - Cost per call
- ✅ Judge Score Visualization
  - Average compliance, accuracy, clarity, empathy, conversion scores
  - Score trends over time
  - Failure pattern identification
- ✅ Call Drill-Down
  - Search conversations by ID, date, outcome
  - Listen to call recordings
  - View transcripts with judge feedback
- ✅ Business KPIs
  - Top objections (pattern clustering)
  - Lead quality distribution
  - Cost per qualified lead

**Success Criteria:**
- Dashboard renders within 2 seconds
- Real-time data updates every 5-10 seconds
- All metrics queryable and exportable

---

### **Component 7: Logfire Monitoring & Observability**
**Purpose:** Production-grade metrics tracking and latency monitoring  
**Technology Stack:** Logfire, Python SDK

**Deliverables:**
- ✅ Latency Tracking
  - p50, p95, p99 latency percentiles (STT, inference, TTS)
  - End-to-end call latency monitoring
  - Per-component latency breakdown
- ✅ Judge Score Tracking
  - Average and distribution of all 5 judge rubrics
  - Correlation analysis (judge scores vs. business outcomes)
  - Anomaly detection
- ✅ Cost Monitoring
  - Cost per call (Retell + Deepgram + ElevenLabs + GPT-4o)
  - Cost per successful interaction (booking/qualification)
  - Cost trend analysis
- ✅ Alerting
  - Latency SLA violations (p95 > 700ms)
  - Judge score degradation (trending down)
  - System availability alerts
  - Cost anomaly detection

**Success Criteria:**
- Logfire dashboard accessible and live
- All metrics logged with <100ms overhead
- Alerts trigger within 5 minutes of SLA violation

---

## 📊 Success Criteria (Phase 1 Overall)

| Metric | Target | Type |
|--------|--------|------|
| Call connection time | < 2 seconds | Latency |
| STT→Response→TTS latency | < 700ms (p95) | Latency |
| Judge evaluation speed | < 5 seconds per conversation | Latency |
| Judge scorability | ≥80% of test calls | Reliability |
| Dashboard responsiveness | < 2 seconds render | UX |
| Cost per call | < $0.50 | Cost |
| Judge score correlation | ≥0.75 with human feedback | Accuracy |

---

## 📊 Scope Boundaries

**In Scope:**
- ✅ Outbound prospecting workflow only
- ✅ GPT-4o for inference (no fine-tuning yet)
- ✅ Dashboard visualization and monitoring
- ✅ Synthetic dataset generation

**Out of Scope:**
- ❌ Email agent (Phase 3)
- ❌ Form-filling / Underwriting conversations (Phase 3)
- ❌ Claims intake agent (Phase 3)
- ❌ Model fine-tuning / alignment training (Phase 5)
- ❌ Production-scale infrastructure (10-100 concurrent calls max)
- ❌ Internal no-code workflow builder (Phase 2)
- ❌ A/B testing framework (Phase 2)

---

## ⚙️ Technical Dependencies

**No upstream dependencies** — Phase 1 is the foundation.

**External Services Required:**
- Retell API account (voice orchestration)
- Twilio API account (outbound calling)
- Deepgram API key (STT)
- ElevenLabs API key (TTS)
- OpenAI API key (GPT-4o)
- Logfire account (monitoring)
- Postgres database (conversation storage)

**Infrastructure:**
- FastAPI server (local dev or cloud)
- Redis instance (optional, for call queue management)

---

## 📅 Timeline & Effort Breakdown

| Component | Effort | Duration |
|-----------|--------|----------|
| Voice Agent Core (Retell + STT/TTS) | 40 hours | 1 week |
| Prospecting Logic | 30 hours | 4-5 days |
| MLLM-as-a-Judge System | 35 hours | 1 week |
| Synthetic Dataset Generation | 20 hours | 3-4 days |
| Twilio Integration | 25 hours | 3-4 days |
| Analytics Dashboard | 40 hours | 1 week |
| Logfire Monitoring Setup | 20 hours | 2-3 days |
| Testing & Integration | 30 hours | 3-4 days |
| **Total** | **~240 hours** | **3-4 weeks** |

---

## 🔗 Next Phase Gate

Phase 1 is complete and Phase 2 can begin when:

1. ✅ Judge system passes accuracy test on holdout dataset
2. ✅ Latency meets sub-700ms target (p95)
3. ✅ Dashboard is accessible and shows real data
4. ✅ ≥20 successful test calls completed
5. ✅ Synthetic dataset (500+) generated and labeled

---

## 📋 Component Integration Map

```
Twilio Dialer
    ↓
Retell Voice Orchestration
    ├─ Deepgram STT ─→ FastAPI Prospecting Agent ─→ GPT-4o
    └─ ElevenLabs TTS ←
    
FastAPI Agent
    ↓
Conversation Storage (Postgres)
    ↓
MLLM-as-a-Judge System
    ├─ Judge Scores → Logfire
    └─ Judge Scores → Postgres
    
Logfire Monitoring
    ↓
Analytics Dashboard (React)
```

---

## 🚀 Deployment Strategy (Phase 1)

| Environment | Platform | Purpose |
|-------------|----------|---------|
| **Local Dev** | Docker Compose | Development and testing |
| **Staging** | FastAPI on Railway/Render | Pre-production validation |
| **Production** | Vercel for FastAPI | Edge-optimized voice endpoints |
| **Database** | Supabase Postgres | Conversation and score storage |
| **Monitoring** | Logfire Cloud | Real-time metrics and dashboards |

---

## ✅ Key Milestones

1. **Week 1:** Voice infrastructure (Retell, STT/TTS, Twilio) operational
2. **Week 2:** Prospecting agent logic + MLLM-as-a-Judge system live
3. **Week 3:** Analytics dashboard + monitoring dashboard live
4. **Week 3-4:** Synthetic dataset generation, testing, refinement
5. **End of Phase 1:** 20+ successful test calls, all metrics validated

---

## 📌 Component Ownership & Skills

| Component | Primary Skills | Difficulty |
|-----------|----------------|------------|
| Voice Agent Core | FastAPI, async Python, Retell API, Twilio | Beginner→Intermediate |
| Prospecting Logic | Prompt engineering, GPT-4o, conversation design | Intermediate |
| MLLM-as-a-Judge | Prompt engineering, eval rubrics, GPT-4o | Intermediate |
| Dataset Generation | Python scripting, JSON, domain knowledge | Beginner |
| Twilio Integration | REST APIs, webhook handling | Beginner→Intermediate |
| Analytics Dashboard | React/Next.js, SQL queries, real-time updates | Intermediate |
| Logfire Monitoring | Logfire SDK, metrics instrumentation | Beginner→Intermediate |
