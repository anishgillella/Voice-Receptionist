# 🎙️ Voice Agent - MVP Phase 1

Real-time outbound prospecting agent using **Retell** for voice orchestration and **GPT-4o** for conversational reasoning.

## 📋 Overview

This is **Component 1: Voice Agent Core** from Phase 1 of AI Brokerage.

**What it does:**
- Manages call sessions (state stored in Redis)
- Routes webhook events from Retell
- Generates intelligent responses using GPT-4o
- Tracks conversation history and lead qualification
- Provides REST API for call management

**What it uses:**
- **Retell** - Voice platform (handles STT/TTS natively)
- **GPT-4o** - Agent reasoning and lead qualification
- **Redis** - Session state management
- **FastAPI** - Web framework
- **Pydantic** - Type validation

---

## 🚀 Quick Start

### 1. Install Dependencies

```bash
# Using uv (recommended)
uv sync

# Or pip
pip install -e ".[dev]"
```

### 2. Setup Environment

```bash
# Copy template and fill in your API keys
cp env.example .env

# Required keys:
# - RETELL_API_KEY (from https://retell.ai/dashboard)
# - OPENAI_API_KEY (from https://platform.openai.com)
```

### 3. Start Redis (for session management)

```bash
# Docker
docker run -d -p 6379:6379 redis:latest

# Or local installation
redis-server
```

### 4. Run the Server

```bash
# Development
uvicorn voice_agent.main:app --reload --port 8000

# Or directly
python -m voice_agent.main
```

The API will be available at:
- **http://localhost:8000** - Root
- **http://localhost:8000/docs** - Interactive API docs (Swagger UI)
- **http://localhost:8000/health** - Health check

---

## 🔌 API Endpoints

### Health & Status

```bash
# Health check
curl http://localhost:8000/health

# System status
curl http://localhost:8000/api/v1/status
```

### Call Management

```bash
# Initiate outbound call
curl -X POST http://localhost:8000/api/v1/calls/initiate \
  -H "Content-Type: application/json" \
  -d '{
    "phone_number": "+15551234567",
    "lead_name": "John Doe",
    "company": "Acme Corp",
    "lead_id": "lead_123"
  }'

# Get call details
curl http://localhost:8000/api/v1/calls/call_abc123def456

# Qualify lead (get lead quality score)
curl -X POST http://localhost:8000/api/v1/calls/call_abc123def456/qualify
```

### Agent Messaging

```bash
# Process customer message
curl -X POST http://localhost:8000/api/v1/agent/message \
  -H "Content-Type: application/json" \
  -d '{
    "call_id": "call_abc123def456",
    "customer_message": "Hi, I need insurance for my business"
  }'
```

### Webhooks

```bash
# Retell will POST to this endpoint with call events
POST /webhook/retell/call-event

# Payload format:
{
  "event": "call_started|call_ended|speech_recognized",
  "call_id": "call_abc123def456",
  "phone_number": "+15551234567",
  "timestamp": 1234567890,
  "data": {
    "transcript": "Customer message here"
  }
}
```

---

## 📂 Project Structure

```
voice_agent/
├── __init__.py                # Package init
├── config.py                  # Settings & environment variables
├── models.py                  # Pydantic data models
├── main.py                    # FastAPI application & routes
├── services/
│   ├── __init__.py
│   ├── retell_client.py       # Retell API wrapper
│   ├── call_manager.py        # Session state management (Redis)
│   └── agent_service.py       # GPT-4o response generation
└── README.md                  # This file
```

---

## 🏗️ Architecture

```
┌─────────────┐
│   Retell    │ (Voice Orchestration)
│  (STT/TTS)  │
└──────┬──────┘
       │ Webhook: call_started, speech_recognized, call_ended
       ↓
┌──────────────────────────┐
│    FastAPI App           │
│  (voice_agent/main.py)   │
├──────────────────────────┤
│ ✓ Webhook handlers       │
│ ✓ Call management        │
│ ✓ Message processing     │
└──────────────────────────┘
       │
       ├─→ Redis (CallManager)
       │   └─ Session state, conversation history
       │
       └─→ GPT-4o (AgentService)
           ├─ Response generation
           └─ Lead qualification
```

---

## 🔧 Configuration

All settings come from environment variables (see `env.example`):

**Essential:**
- `RETELL_API_KEY` - Retell API key
- `OPENAI_API_KEY` - OpenAI API key
- `REDIS_URL` - Redis connection

**Optional:**
- `ENVIRONMENT` - "development" or "production"
- `DEBUG` - True/False
- `AGENT_NAME` - Agent display name
- `AGENT_COMPANY` - Company name
- `VOICE_WARMTH` - 0.0 (professional) to 1.0 (friendly)

---

## 🧪 Testing

### Manual Testing with cURL

```bash
# 1. Create a call session
CALL_ID=$(curl -s -X POST http://localhost:8000/api/v1/calls/initiate \
  -H "Content-Type: application/json" \
  -d '{"phone_number": "+15551234567", "lead_name": "Jane Doe", "company": "Tech Startup"}' \
  | jq -r '.call_id')

echo "Call ID: $CALL_ID"

# 2. Send customer message
curl -X POST http://localhost:8000/api/v1/agent/message \
  -H "Content-Type: application/json" \
  -d "{
    \"call_id\": \"$CALL_ID\",
    \"customer_message\": \"Hi, we need business insurance for our startup\"
  }"

# 3. Get call details
curl http://localhost:8000/api/v1/calls/$CALL_ID

# 4. Qualify the lead
curl -X POST http://localhost:8000/api/v1/calls/$CALL_ID/qualify
```

### Unit Tests (Coming in Phase 2)

```bash
# Run tests
pytest tests/

# With coverage
pytest tests/ --cov=voice_agent
```

---

## 📊 Data Models

### CallSession
```python
{
  "call_id": "call_abc123def456",
  "status": "in_progress",  # initiated, in_progress, completed, failed
  "phone_number": "+15551234567",
  "lead_id": "lead_123",
  "lead_name": "John Doe",
  "company": "Acme Corp",
  "conversation": [
    {
      "role": "customer",
      "content": "Hi, I need insurance",
      "timestamp": "2024-01-15T10:30:00Z"
    },
    {
      "role": "agent",
      "content": "Hello! I'd be happy to help...",
      "timestamp": "2024-01-15T10:30:05Z"
    }
  ],
  "lead_quality": "warm",
  "qualification_score": 0.75,
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-15T10:30:10Z"
}
```

### MessageResponse
```python
{
  "agent_message": "Great! Let me learn more about your business...",
  "confidence_score": 0.85,
  "should_escalate": false,
  "next_action": "booking_call"
}
```

---

## 🐛 Debugging

### Enable Verbose Logging

```bash
# Set environment variable
export LOG_LEVEL=DEBUG

# Or modify config.py logging level
```

### Check Redis Connection

```python
import redis
r = redis.from_url("redis://localhost:6379")
r.ping()  # Should return True
```

### Test OpenAI Connection

```python
from openai import AsyncOpenAI
client = AsyncOpenAI(api_key="your-key")
# Will fail if invalid on first API call
```

---

## 🚀 Next Steps

After Phase 1 MVP is working:

**Phase 2:** Platform Tools
- No-code workflow builder for non-technical teams
- A/B testing framework
- Analytics dashboard

**Phase 3:** Multi-Workflow Expansion
- Form-filling agent (underwriting)
- Claims intake agent (FNOL)
- Multi-modal orchestration (voice → SMS → email)

**Phase 4:** Inference Optimization
- vLLM deployment
- Custom STT (Deepgram) + TTS (ElevenLabs)
- Multi-model routing

**Phase 5:** Fine-tuning & Alignment
- RLHF/DPO training
- Insurance-optimized models
- Alignment evaluation

---

## 📚 Resources

- [Retell Documentation](https://docs.retell.ai)
- [FastAPI Documentation](https://fastapi.tiangolo.com)
- [OpenAI API Documentation](https://platform.openai.com/docs)
- [Pydantic Documentation](https://docs.pydantic.dev)
- [Redis Documentation](https://redis.io/docs)

---

## 🤝 Contributing

This is part of the Harper AI Engineer training project. 

For phase 1, focus on:
1. ✅ Retell webhook integration
2. ✅ Session management
3. ✅ GPT-4o response generation
4. ✅ Lead qualification scoring

---

**Phase 1 Status:** 🚀 MVP Ready
