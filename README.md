# Kyron Medical — AI Patient Scheduling

Kyron Medical is a patient-facing web application that lets people schedule appointments with the right specialist using plain language. Instead of navigating a portal, patients describe their symptoms in a chat interface and an AI assistant routes them to the correct provider, checks real-time availability, and books the appointment — all in one conversation. It is designed to be sold as a white-label SaaS product to physician groups.

---

## Live Demo

| | |
|---|---|
| Patient app | http://34.224.101.240 |
| Admin dashboard | http://34.224.101.240/#admin |
| Admin password | `testadmin` |

**Suggested flow:** Open the patient app, fill out the intake form, and ask to schedule an appointment for knee pain. Watch the AI match to the orthopedics specialist, check live availability, and confirm a booking. Then open the admin dashboard and hit Refresh — the slot shows as Booked with the patient's name and reason.

---

## Features

- **AI appointment scheduling** — patients describe symptoms in natural language; the AI handles provider selection, availability lookup, and booking through a tool-use loop
- **Semantic provider matching** — symptom or body part maps to the right specialist (orthopedics, cardiology, dermatology, neurology)
- **Real-time availability sync** — admin dashboard changes (blocking/unblocking slots) are reflected immediately in the AI's next availability query
- **Voice call handoff** — "Voice call" button initiates an outbound Vapi call with the full chat context injected into the voice assistant's system prompt, so the conversation continues without repeating
- **Session persistence** — conversation state is stored server-side and keyed to `localStorage`; a page refresh resumes exactly where the patient left off
- **Slot conflict handling** — if a slot is booked by someone else between when the AI shows it and the patient confirms, the system apologizes and immediately offers the next 3 available slots
- **Confirmation numbers** — every booking gets a `KM-XXXXXXXX` reference number
- **Admin dashboard** — live view of all provider availability grouped by date, with patient name, reason, and phone number on booked slots; auto-refreshes every 30 seconds

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React 18 + TypeScript + Vite |
| Backend | FastAPI (Python 3.11) + SQLAlchemy async |
| AI Model | Claude claude-sonnet-4-20250514 (Anthropic) |
| Database | PostgreSQL on AWS RDS (SQLite for local dev) |
| Hosting | AWS EC2 (t3.small) + Nginx |
| Voice AI | Vapi — outbound phone calls with injected context |
| Email | SendGrid — appointment confirmation emails |
| SMS | Twilio — opt-in appointment reminders |

---

## Architecture

```
Patient browser
    │  React frontend (Vite)
    │  Streaming SSE ← text_delta events
    ▼
FastAPI backend (uvicorn)
    │  POST /chat
    │  Loads session state from PostgreSQL
    ▼
Claude tool-use loop (services/ai.py)
    │  stop_reason == "tool_use" → execute tool → append result → loop
    │  stop_reason == "end_turn"  → stream reply back
    ▼
Tool executors (tools/)
    │  get_availability   → SELECT from availability table
    │  book_appointment   → UPDATE availability + INSERT appointment
    │  get_provider_info  → SELECT from providers table
    │  lookup_office_info → static lookup dict
    ▼
PostgreSQL RDS
    └─ patients, sessions, providers, availability, appointments
```

Session state (full message history) is persisted to the database after every turn. The frontend stores `session_id` and `patient_id` in `localStorage`; on reload it validates the session against the server before rendering.

---

## Project Structure

```
kyron-interview/
├── backend/
│   ├── main.py                  # FastAPI app, router registration
│   ├── routers/
│   │   ├── chat.py              # POST /chat, POST /intake, GET /sessions/:id
│   │   ├── admin.py             # GET /admin/providers, PATCH slot toggle
│   │   ├── calls.py             # POST /call — Vapi outbound call
│   │   ├── appointments.py      # CRUD for appointments
│   │   └── providers.py         # Provider queries
│   ├── services/
│   │   ├── ai.py                # Claude client, system prompt, agentic loop
│   │   ├── matching.py          # Symptom → provider matching
│   │   ├── notifications.py     # Email (SendGrid) + SMS (Twilio)
│   │   └── session.py           # Session load/save
│   ├── tools/
│   │   ├── get_availability.py  # Real-time slot query, returns ET-formatted times
│   │   ├── book_appointment.py  # Atomic slot booking with conflict detection
│   │   ├── get_provider_info.py # Provider detail lookup
│   │   └── lookup_office_info.py# Static office info (hours, address, parking)
│   ├── db/
│   │   ├── models.py            # SQLAlchemy ORM models
│   │   ├── schemas.py           # Pydantic request/response schemas
│   │   └── seed.py              # Seed: 4 providers, 45 days of slots
│   ├── tests/
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── IntakeForm.tsx   # Step 1: patient info collection
│   │   │   ├── ChatWindow.tsx   # Step 2: streaming chat interface
│   │   │   ├── VoiceButton.tsx  # Vapi outbound call trigger
│   │   │   └── AdminDashboard.tsx
│   │   ├── hooks/
│   │   │   ├── useChat.ts       # Streaming message state
│   │   │   └── useSession.ts    # localStorage session persistence
│   │   ├── lib/
│   │   │   └── api.ts           # Typed fetch wrappers for all endpoints
│   │   └── App.tsx              # Route: intake → chat, /admin → dashboard
│   └── package.json
└── infra/
    ├── nginx.conf               # Reverse proxy (port 80 → 8000, static assets)
    ├── deploy.sh                # EC2 deploy script
    └── schema.sql               # Canonical PostgreSQL schema
```

---

## Local Development

### Prerequisites

- Python 3.11+
- Node.js 18+
- An Anthropic API key

### Backend

```bash
cd backend
python -m venv venv && source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env          # fill in ANTHROPIC_API_KEY at minimum
python db/seed.py             # creates kyron.db and seeds 4 providers + slots
uvicorn main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev                   # runs on :5173, proxies /api → :8000
```

Open http://localhost:5173. The admin dashboard is at http://localhost:5173/#admin.

### Environment Variables

| Variable | Required | Description |
|---|---|---|
| `ANTHROPIC_API_KEY` | Yes | Claude API key |
| `DATABASE_URL` | Yes | `postgresql+asyncpg://...` for prod, auto-set to SQLite for local |
| `ADMIN_SECRET` | Yes | Password for admin dashboard |
| `VAPI_API_KEY` | Voice | Vapi API key for outbound calls |
| `VAPI_PHONE_NUMBER_ID` | Voice | Vapi phone number to call from |
| `SENDGRID_API_KEY` | Email | SendGrid key for confirmation emails |
| `FROM_EMAIL` | Email | Sender address (e.g. `noreply@kyronmedical.com`) |
| `TWILIO_ACCOUNT_SID` | SMS | Twilio account SID |
| `TWILIO_AUTH_TOKEN` | SMS | Twilio auth token |
| `TWILIO_PHONE_NUMBER` | SMS | Twilio number to send from |

---

## Deployment

Infrastructure is EC2 (t3.small) + RDS PostgreSQL + Nginx. After provisioning:

```bash
git clone <repo> && cd kyron-interview
cp backend/.env.example backend/.env    # fill in production values
sudo cp infra/nginx.conf /etc/nginx/sites-available/kyron
sudo certbot --nginx -d yourdomain.com  # optional TLS
bash infra/deploy.sh
```

`deploy.sh` builds the React app, starts FastAPI under `gunicorn` with `uvicorn` workers, and reloads Nginx to serve the static bundle and proxy API requests.

---

## API Endpoints

| Method | Path | Description |
|---|---|---|
| `POST` | `/intake` | Create patient record, return `patient_id` + `session_id` |
| `POST` | `/chat` | Main conversation endpoint — streams SSE `text_delta` + `end` events |
| `GET` | `/sessions/:id` | Fetch session state for page-reload resume |
| `POST` | `/call` | Initiate Vapi outbound call with conversation context |
| `GET` | `/providers` | List all providers and their availability |
| `GET` | `/appointments/:patient_id` | List appointments for a patient |
| `GET` | `/admin/providers` | Admin: providers + booked slot patient info (auth required) |
| `PATCH` | `/admin/providers/:id/availability/:slot_id` | Admin: toggle slot open/blocked |

All admin endpoints require `X-Admin-Secret` header.

---

## AI Tool Architecture

The AI layer (`services/ai.py`) runs a standard agentic loop against Claude claude-sonnet-4-20250514. On each patient turn:

1. The full message history is sent to the Claude API with four tool definitions
2. If `stop_reason == "tool_use"`, all tool calls in the response are executed concurrently, results are appended as a `user` turn, and the loop continues
3. If `stop_reason == "end_turn"`, the text reply is streamed back to the patient and the updated message history is saved to the database

**The four tools:**

| Tool | Input | What it does |
|---|---|---|
| `get_availability` | `provider_id?`, `body_part?`, `date_range_start`, `date_range_end` | Queries the `availability` table for open slots; returns human-readable ET-formatted times so the AI can quote them directly |
| `book_appointment` | `patient_id`, `slot_id`, `reason` | Marks the slot `is_booked=True`, creates an `appointments` row, flushes within the caller's transaction; returns `KM-XXXXXXXX` confirmation number |
| `get_provider_info` | `provider_id?` | Returns provider name, specialty, body parts, and bio; used when the AI needs to explain why it's routing to a particular doctor |
| `lookup_office_info` | `query` | Static lookup for office hours, address, parking, cancellation policy |

Provider matching uses a two-stage approach: exact substring match against each provider's `body_parts` array first, then a Claude fallback if no direct match is found.

---

## Non-Happy-Path Scenarios

**Slot conflict** — the most important edge case for a multi-user booking system:

1. AI calls `get_availability` and presents open slots to the patient
2. While the patient is deciding, another patient (or the admin) books the same slot
3. Patient confirms — AI calls `book_appointment`
4. Inside `book_appointment`, the slot is re-checked before committing: if `is_booked` is already `True`, the tool returns `{"error": "slot_taken", "next_available": [...]}`
5. The AI receives this result, apologizes, and immediately presents the next 3 available slots without requiring the patient to ask again

This is demonstrable live: block a slot in the admin dashboard while the patient is mid-conversation, then have the patient try to book it.

---

## What's Next

Items cut from MVP that would be required before production use:

- **HIPAA compliance** — encryption at rest for PII fields, audit logging for all data access, BAA with infrastructure providers
- **SMS double opt-in** — proper TCPA-compliant opt-in confirmation flow before sending any messages
- **Cancellation and rescheduling** — currently appointments can only be cancelled by freeing the slot in the admin dashboard
- **Multi-tenant support** — all data is currently scoped to a single practice; production would need per-tenant data isolation
- **Patient authentication** — session is currently keyed to `localStorage` only; a returning patient on a new device loses their history
- **Timezone handling** — slots are seeded with a fixed EDT offset (UTC-4); production would need proper `pytz`/`zoneinfo` handling for EST/EDT transitions and non-Eastern practices
