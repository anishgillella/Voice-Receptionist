## Voice Agent MVP Roadmap & Execution Log

### Phase 1 — Planning & Architecture
- Captured high-level system design in `README.md`, outlining Vapi voice layer, FastAPI backend, Google Calendar integration, and Supabase (future).
- Defined MVP scope: local-only deployment, FastAPI stack, personal Google Calendar for scheduling, no Supabase persistence yet.
- Enumerated required environment variables and sourcing instructions.

### Phase 2 — Credential Setup
- Downloaded Google OAuth client JSON; guided refresh token retrieval.
- Encountered `redirect_uri_mismatch` error; resolved by adding `http://localhost:8765/` redirect in Google Cloud Console.
- Encountered `access_denied` (app not verified); resolved by adding `anish.gillella@gmail.com` as OAuth test user.
- Ran `get_refresh_token.py` to obtain refresh token and verified Calendar access (observed birthday events).
- Attempted to remove contact birthdays; discovered they are read-only.

### Phase 3 — FastAPI MVP Scaffold
- Created `app/` package with `__init__.py`, `config.py`, `main.py`, `llm.py`, `calendar.py`, `sessions.py`, and Pydantic models.
- Added `.env` loading via `pydantic` settings; configured required environment variables (Vapi, OpenAI, Google, timezone, backend URL).
- Implemented in-memory session store for call context (`.sessions`).
- Added OpenAI wrapper with scheduling tool schema (`llm.py`).
- Built Google Calendar helper functions (list, create, delete events) with OAuth credentials (`calendar.py`).
- Implemented `/health` and `/vapi-webhook` endpoints in `main.py` to process Vapi transcripts, run LLM, handle tool calls, and respond to caller.
- Added dependencies to `requirements.txt` and installed them (noted downgrades causing compatibility warnings with other globally installed packages).

### Phase 4 — Testing & Adjustments
- Ran `python get_refresh_token.py` to list upcoming events; confirmed Google API connectivity.
- Refined `main.py` to handle OpenAI tool calls for listing, creating, and canceling appointments.
- Configured README MVP instructions (installation, env setup, ngrok tunnel, testing flow).

### Phase 5 — Outbound Call Support
- Needed outbound call capability to dial `+1 469-867-4545` using Vapi.
- Added `httpx` dependency and created `vapi_client.py` to call Vapi REST API.
- Initial attempts used `/v1/calls` and `/api/v1/calls`; received 404 errors (“Cannot POST”).
- Updated code per Vapi docs to use `/call` endpoint with payload `{assistantId, phoneNumberId, customer.number}`.
- Encountered `assistant_id` missing error; set `VAPI_AGENT_ID` when instantiating client.
- Successfully triggered outbound call; Vapi returned `status: queued` with monitor URLs and call metadata.
- Recommended persisting `VAPI_AGENT_ID` in `.env` for future requests.

### Known Issues & Lessons Learned
- Global Python environment now has older versions of fastapi/pydantic/openai; consider using a virtual environment to avoid conflicts with other packages.
- Outbound call endpoint path differed from initial assumption; confirmed correct `/call` usage via docs.
- Google Contacts birthdays cannot be removed via Calendar API; requires contact update or calendar toggle.

### Next Opportunities
- Enhance system prompts to match salon tone (“Riley” vs salon-specific voice) and align with service catalog.
- Add structured parsing between OpenAI tool outputs and calendar helper to ensure valid appointment windows.
- Introduce Supabase or alternative persistence for transcripts and analytics.
- Implement outbound call scheduling (automatic reminders) and status callbacks.
