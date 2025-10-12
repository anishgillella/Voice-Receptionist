# AI Appointment Scheduler

Design notes for the voice-enabled appointment scheduling agent that integrates Vapi, OpenAI, Google Calendar, and Supabase.

## Overview
- **Goal:** Build a salon-focused voice assistant that understands callers, reasons about scheduling intents, and persists context across sessions.
- **Modality:** Real-time phone conversations managed by Vapi for telephony, speech recognition, and speech synthesis.
- **Backend:** Custom API service (FastAPI or Node/Express) orchestrating LLM reasoning, calendar operations, and memory storage.
- **Data Stores & Services:** Google Calendar API for event management, Supabase for session memory and logging.

## System Architecture
```
User (phone caller)
       │ voice
       ▼
Vapi.ai (STT, TTS, call control, LLM bridge)
       │ webhook
       ▼
Custom Backend API
    ├─ OpenAI LLM reasoning
    ├─ Google Calendar orchestration
    └─ Supabase session storage

External Services:
    Google Calendar API (book, cancel, reschedule)
    Supabase (sessions, transcripts, logs)
```

## Core Components

### Vapi Agent
- Owns call handling, real-time speech-to-text, text-to-speech, and streaming responses.
- Forwards user utterances and context to the backend webhook for reasoning.
- Example configuration snippet:

```
{
  "name": "AppointmentSchedulerBot",
  "model": "openai:gpt-4o-mini",
  "voice": "alloy",
  "webhook": "https://yourdomain.com/vapi-webhook",
  "persona": "Friendly, professional scheduling assistant for a salon.",
  "endCallPhrases": ["goodbye", "thanks, that's all"]
}
```

### Backend Orchestration Layer
- Exposes `/vapi-webhook` to receive Vapi event payloads.
- Retrieves session memory from Supabase, calls OpenAI for conversational reasoning, and determines follow-up actions.
- Applies LLM tool calls or structured outputs to interact with Google Calendar through helper functions.
- Stores transcript turns and assistant replies back into Supabase for continuity.

Pseudo-code outline:

```python
@app.post("/vapi-webhook")
def handle_vapi(req: Request):
    user_message = req.json().get("text")
    session_id = req.json().get("session_id")

    history = get_memory_from_supabase(session_id)

    llm_response = openai.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are a salon scheduling assistant using Google Calendar."},
            *history,
            {"role": "user", "content": user_message}
        ],
        tools=[
            {
                "name": "schedule_appointment",
                "description": "Book, reschedule, or cancel appointments in Google Calendar",
                "parameters": {"type": "object", "properties": {"action": {"type": "string"}}}
            }
        ]
    )

    if "tool_calls" in llm_response:
        perform_calendar_action(llm_response["tool_calls"])

    save_memory(session_id, user_message, llm_response["content"])

    return {"response": llm_response["content"]}
```

### Google Calendar Integration
- Uses OAuth or a service account to authenticate with Google APIs.
- Supports lookup, creation, updates, and cancellations of events.
- Helper example:

```
service.events().insert(
    calendarId="primary",
    body={
        "summary": summary,
        "start": {"dateTime": start_time, "timeZone": "America/New_York"},
        "end": {"dateTime": end_time, "timeZone": "America/New_York"}
    }
).execute()
```

### Supabase Memory Layer
- Persists conversational state across turns using `session_id` as partition key.
- Captures transcripts and assistant responses for analytics and debugging.
- Potential schema columns: `session_id`, `message_role`, `message_text`, `timestamp`, `metadata`.

## MVP Configuration Snapshot

### Voice & Caller Workflow
- Entry points: Vapi WebRTC widget for browser demos plus a single PSTN number (`+1-555-0101`) for live testing.
- Call flow: greet with salon branding, collect service + preferred date/time, propose available slots, confirm intent, then summarize before hanging up.
- Fallbacks: if Google Calendar or Supabase fail, apologize and offer a manual follow-up; if the model is uncertain after two retries, escalate to human voicemail.
- Escalation phrases: caller says “talk to a human”, “operator”, or “this isn’t working” → trigger voicemail recording and end call.
- End-call phrases: “that’s all”, “goodbye”, “thanks, bye”.

### Salon Operations (Assumed)
- Time zone: `America/New_York`.
- Business hours: Mon–Fri 9:00–18:00, Sat 10:00–16:00, closed Sun.
- Services and durations:
  - `Standard Haircut` — 45 minutes — stylists: Kim, Alex
  - `Color & Highlights` — 120 minutes — stylist: Jordan
  - `Kids Cut` — 30 minutes — stylist: Kim
- Buffers: auto-add 10 minutes cleanup buffer after each service.
- Rescheduling: allowed up to 2 hours before start time; cancellations within 2 hours flagged for manual follow-up.

### Calendar Ownership
- Primary calendar: use owner’s personal Google Calendar (`primary`) during local development.
- Each stylist mapped to a color-coded event label (set via event description) rather than separate calendars to keep setup minimal.
- Future-ready path: convert to a dedicated Google Workspace calendar or shareable team calendar once deployed beyond local testing.

### Memory & Compliance Strategy
- Session memory retention: persist call transcript turns for 30 days in Supabase, then archive or delete.
- PII handling: store caller phone numbers and names only in Supabase; redact sensitive requests in logs via middleware before persistence.
- Audit trail: Supabase table `call_logs` captures Vapi payload metadata, LLM decisions, and calendar event IDs for troubleshooting.
- Manual deletion endpoint planned for compliance requests.

### Deployment Constraints
- Initial deployment: local development only (FastAPI backend served via `uvicorn`, Vapi webhook tunneled with `ngrok`).
- Preferred stack: Python FastAPI for the API layer, SQLModel/asyncpg for Supabase interactions, Google API Python client.
- Secrets management: `.env.local` loaded with `python-dotenv` for development; transition to secret manager (e.g., Doppler/Vault) before hosting in production.

### Environment Variables & Sources
- `VAPI_API_KEY` — Vapi dashboard → Settings → API Keys.
- `VAPI_AGENT_ID` *(optional)* — if pre-provisioning the agent via API; visible in Vapi agent settings.
- `OPENAI_API_KEY` — OpenAI dashboard → API Keys.
- `OPENAI_ORG` / `OPENAI_PROJECT` *(optional)* — if scoping usage to a specific OpenAI organization/project.
- `GOOGLE_SERVICE_ACCOUNT_JSON` — base64-encoded service account key from Google Cloud Console (IAM & Admin → Service Accounts → Keys). Grant Calendar scope and share target calendar with the service account email.
- `GOOGLE_CALENDAR_ID` — calendar identifier (use `primary` for personal calendar, or copy the Calendar ID from Google Calendar settings if using a dedicated calendar).
- `SUPABASE_URL` — Supabase project → Settings → API → Project URL.
- `SUPABASE_ANON_KEY` — Supabase project → Settings → API → anon public key (for client contexts if needed).
- `SUPABASE_SERVICE_ROLE_KEY` — Supabase Settings → API → service role key (server-only access for writing transcripts).
- `DEFAULT_TIMEZONE` — `America/New_York`.
- `BACKEND_BASE_URL` — public webhook URL exposed via ngrok (e.g., `https://abcd1234.ngrok.app`).
- `LOG_LEVEL` — optional verbosity toggle (`info`, `debug`).

Store these in `.env.local` for development and reference within FastAPI via `pydantic` settings or similar configuration loader.

## Conversation Flow Example
1. Caller: “I want to reschedule my haircut.”
2. Vapi: transcribes speech and posts to `/vapi-webhook`.
3. Backend: retrieves session memory, runs OpenAI reasoning, identifies reschedule intent.
4. Backend: queries Google Calendar, proposes alternative slot.
5. Vapi: speaks suggestion to caller.
6. Caller: “Yes, please.”
7. Backend: confirms availability, updates Google Calendar event, logs interaction.
8. Vapi: confirms booking and wraps up call.

## Optional Enhancements
- **Authentication:** Validate caller identity via caller ID, passphrase, or one-time code.
- **Fallback Handling:** Gracefully respond if calendar or Supabase calls fail; escalate to human follow-up.
- **Webhook Logging:** Store raw payloads and LLM decisions for audit trails.
- **Outbound Calls:** Use Vapi outbound call APIs for proactive reminders or confirmations.
- **Analytics Dashboard:** Build reporting on booking metrics and call outcomes using Supabase data.

## Implementation Plan (Next Steps)
- Create and configure the Vapi agent via dashboard or API.
- Scaffold backend service (FastAPI) with `/vapi-webhook` endpoint and health check.
- Set up Google Calendar credentials (OAuth) and helper utilities.
- Connect OpenAI to parse intents and issue structured tool calls.
- Configure Vapi agent to point at the ngrok-exposed webhook and test end-to-end with WebRTC or PSTN call.

## MVP Instructions
- Install dependencies: `pip install -r requirements.txt` (create virtualenv if desired).
- Populate `.env` with required secrets (Vapi key, OpenAI key, Google OAuth creds, refresh token, `BACKEND_BASE_URL`).
- Run the FastAPI app: `uvicorn app.main:app --reload --port 8000`.
- Start ngrok tunnel: `ngrok http 8000` and update `BACKEND_BASE_URL` plus Vapi webhook target.
- Use `python get_refresh_token.py` to verify Google access and list events.
- Call your Vapi agent and confirm the assistant reasons about appointments and interacts with Calendar.

## Next Iterations
- Flesh out the exact Vapi webhook payload contract.
- Provide full backend starter template with environment configuration.
- Document environment variables for OpenAI, Google, Supabase, and Vapi integration.

