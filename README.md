# 🎤 Voice Agent - AI-Powered Insurance Sales

An intelligent voice agent system that handles outbound insurance sales calls with LLM-powered analysis, automatic email follow-ups, and vector-based semantic search for customer context.

## 🚀 Features

### Voice Calling
- **Outbound calls** via VAPI with customer context injection
- **Deepgram STT** for accurate speech-to-text
- **ElevenLabs TTS** for natural voice synthesis
- **GPT-4o-mini** for intelligent conversation

### Call Processing
- Automatic transcript capture and storage
- AI-powered call summarization
- Sentiment analysis and engagement scoring
- LLM-based action detection (send email, schedule callback, etc.)
- Vector embeddings for semantic search

### Email Integration
- SendGrid webhook for incoming email replies
- Automatic email sending with follow-ups
- LLM analysis of customer replies
- Smart response templates with context awareness
- Email reply embeddings for vector search

### Vector Database
- **PostgreSQL with pgvector** for semantic search
- 1024-dimensional embeddings (BGE-Large model)
- Semantic similarity search for calls and emails
- Redis caching for performance

## 📋 Prerequisites

- Python 3.10+
- PostgreSQL with pgvector extension
- Redis (optional, for caching)
- VAPI account (voice calls)
- OpenRouter API key (GPT-4o-mini)
- SendGrid account (email)

## 🏗️ Project Structure

```
Voice Agent/
├── backend/
│   ├── voice_agent/           # Voice call handling
│   │   ├── api/              # FastAPI endpoints
│   │   ├── core/             # Config & database
│   │   ├── llm/              # LLM integrations
│   │   ├── services/         # VAPI, email, embeddings
│   │   ├── evaluation/       # Call quality analysis
│   │   └── ml/               # ML optimizations
│   └── email_agent/          # Email handling (in backend)
│       ├── api/              # Email endpoints
│       ├── core/             # Config & database
│       └── services/         # Gmail, S3, embeddings
├── scripts/
│   └── voice_agent/
│       ├── make_call.py      # Initiate outbound call
│       └── process_call.py   # Post-process call
├── tests/
│   ├── voice_agent/          # Voice agent tests
│   └── email_agent/          # Email agent tests
├── data/
│   └── transcripts/          # Call transcripts
├── architecture.md           # System architecture
└── roadmap.md               # Development roadmap
```

## 🚀 Quick Start

### 1. Setup Environment

```bash
# Clone repository
git clone https://github.com/anishgillella/Voice-Receptionist.git
cd "Voice Agent"

# Install dependencies
pip install -r requirements.txt

# Setup environment variables
cp .env.example .env
# Edit .env with your API keys:
# - VAPI_API_KEY
# - OPENROUTER_API_KEY
# - SENDGRID_API_KEY
# - SUPABASE_URL, SUPABASE_KEY
# - etc.
```

### 2. Initialize Database

```bash
# Create database tables (migrations handled automatically via Supabase)
```

### 3. Make Your First Call

```bash
# Start backend
uvicorn backend.voice_agent.api.main:app --host 0.0.0.0 --port 8000

# In another terminal, make a call
python scripts/voice_agent/make_call.py

# Get the call ID from output, then process it after 30 seconds
python scripts/voice_agent/process_call.py <CALL_ID>
```

## 🤖 How It Works

### Call Flow

```
1. make_call.py
   └─> Initiates outbound call via VAPI
   
2. Customer answers
   └─> Agent (GPT-4o-mini) engages with context
   
3. Call ends
   └─> VAPI sends webhook to backend
   
4. process_call.py
   ├─> Fetches transcript from VAPI
   ├─> Generates AI summary
   ├─> Creates vector embeddings
   ├─> Analyzes with LLM for intent/actions
   ├─> Executes actions (send email, etc.)
   └─> Stores everything in database
```

### Email Flow

```
1. Customer replies to email
   └─> SendGrid captures reply
   
2. POST to /webhooks/sendgrid/inbound-parse
   ├─> Extract email content
   ├─> Find customer by email
   ├─> Generate vector embedding
   ├─> Analyze with LLM
   └─> Execute actions (auto-response, etc.)
   
3. Results stored in database
   └─> Available for next call context
```

## 📊 Database Schema

### Main Tables

- **customers** - Customer profiles
- **conversations** - Call transcripts and summaries
- **embeddings** - Vector embeddings for calls (1024-D)
- **email_conversations** - Sent and received emails
- **email_embeddings** - Vector embeddings for emails
- **email_analysis** - LLM analysis of email replies
- **auto_responses** - Generated email responses

## 🔌 API Endpoints

### Voice Agent
- `POST /call` - Initiate outbound call
- `POST /webhooks/vapi` - VAPI call status webhook
- `POST /process-call/{call_id}` - Process specific call

### Email Agent
- `POST /webhooks/sendgrid/inbound-parse` - Receive email replies
- `POST /customer/search-context` - Semantic search past calls
- `POST /customer/search-emails-vector` - Semantic search emails
- `GET /customer/{customer_id}/profile` - Get customer profile

## 🔍 Vector Search

Search for relevant customer context using semantic similarity:

```python
from backend.voice_agent.services.context_manager import SemanticVectorSearch

search = SemanticVectorSearch()

# Search past calls
calls = search.search_customer_context(
    customer_id=customer_id,
    query="What did we discuss about pricing?",
    top_k=3
)

# Search emails
emails = search.search_emails_by_vector(
    customer_id=customer_id,
    query="Customer interest level",
    top_k=3
)
```

## 📧 Email Setup (SendGrid)

To receive email replies, configure SendGrid Inbound Parse:

1. Set up ngrok tunnel (exposes localhost publicly):
   ```bash
   ngrok http 8000
   ```

2. Configure in SendGrid dashboard (https://app.sendgrid.com/settings/parse):
   - Subdomain: your-domain.com
   - Webhook URL: `https://your-ngrok-url/webhooks/sendgrid/inbound-parse`

3. Add MX record to domain DNS (SendGrid will provide details)

## 🧠 LLM Models

- **Call Analysis**: OpenRouter (GPT-4o-mini)
- **Summarization**: OpenRouter (GPT-4o-mini)
- **Email Analysis**: OpenRouter (GPT-4o-mini)
- **Embeddings**: BGE-Large (1024-D vectors)

## 💾 Configuration

Edit `.env` file:

```bash
# Voice API
VAPI_API_KEY=your_key
VAPI_AGENT_ID=your_agent
VAPI_PHONE_NUMBER_ID=your_number

# Database
SUPABASE_URL=your_url
SUPABASE_KEY=your_key
SUPABASE_SCHEMA=brokerage

# LLM
OPENROUTER_API_KEY=your_key
OPENROUTER_MODEL=openai/gpt-4o-mini

# Email
SENDGRID_API_KEY=your_key
SENDER_EMAIL=noreply@yourcompany.com

# Embeddings
HF_TOKEN=your_token
EMBEDDING_MODEL=BAAI/bge-large-en-v1.5

# Optional
REDIS_URL=redis://localhost:6379
LOGFIRE_API_KEY=your_key
```

## 🧪 Testing

```bash
# Run voice agent tests
python -m pytest tests/voice_agent/

# Run email agent tests  
python -m pytest tests/email_agent/

# Manual test: process a recent call
python scripts/voice_agent/process_call.py 019a2f47-04e7-777c-accd-306dbb54d4e5
```

## 📊 Monitoring

- **Transcripts**: View in `data/transcripts/` or git history
- **Logs**: Check `uvicorn.log` and terminal output
- **Database**: Query PostgreSQL directly
- **Email**: Check SendGrid dashboard

## 🚀 Deployment

See `architecture.md` for production deployment details.

## 📝 License

MIT

## 👥 Author

Anish Gillella

---

**Made with ❤️ for AI-powered sales automation**
