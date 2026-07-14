# AI-First CRM — HCP Module: Log Interaction Screen

A conceptual + working build of the **Log Interaction Screen** for an AI-first
Healthcare Professional (HCP) CRM, built for field representatives. Reps can
log an interaction either through a **structured form** or a **conversational
chat interface** backed by a LangGraph agent.

## Tech stack

| Layer      | Choice |
|------------|--------|
| Frontend   | React + Redux Toolkit |
| Backend    | Python, FastAPI |
| AI agent   | LangGraph |
| LLM        | Groq — `gemma2-9b-it` (primary), `llama-3.3-70b-versatile` (fallback/heavier reasoning) |
| Database   | PostgreSQL or MySQL (SQLAlchemy, works with either) |
| Font       | Google Inter |

## Why this design

A field rep's real workflow is messy: sometimes they want to fill in a clean
form after a scheduled meeting, and sometimes they just want to talk/type a
quick note right after walking out of a hallway conversation with a doctor.
The screen supports both without forcing a rep to translate one into the
other themselves — the chat side hands that translation work to the LLM.

## Role of the LangGraph agent

The agent sits between the free-text chat box and the structured
`interactions` table. It's a single looping graph: an **agent node** (the
Groq-backed LLM, bound to five tools) decides what to do with the rep's
message, and a **tools node** executes whichever tool(s) it picks. The graph
loops agent → tools → agent until the LLM responds with plain text instead
of a tool call, at which point that text goes back to the UI as the
assistant's reply.

Concretely, the agent:
- Extracts structured fields (HCP name, topics, materials, sentiment,
  outcomes, follow-ups) out of unstructured notes and saves them.
- Lets a rep correct something they just logged ("actually make that
  neutral, not positive") without re-typing the whole note.
- Pulls up an HCP's interaction history for context before logging a new
  one.
- Condenses long voice-note transcripts into a clean summary.
- Proposes concrete next-step follow-ups after an interaction is logged.

## The five LangGraph tools

1. **`log_interaction_tool`** — Takes a free-text note, prompts the Groq LLM
   to extract HCP name, interaction type, topics discussed, materials/samples
   shared, sentiment, outcomes, and follow-up actions as JSON, then creates
   (or reuses) the HCP record and persists a new `Interaction` row. This is
   the tool that does the "structured form or chat, your choice" bridging —
   the chat path ends up in the exact same table as the form path.
2. **`edit_interaction_tool`** — Takes an `interaction_id`, a field name
   (`interaction_type`, `topics_discussed`, `sentiment`, `outcomes`, or
   `follow_up_actions`), and a new value, and updates just that field. Used
   when a rep corrects something after the fact via chat.
3. **`summarize_interaction_tool`** — Condenses a long note or voice-note
   transcript into 2–3 sentences for the "Topics Discussed" field.
4. **`suggest_followups_tool`** — Given a logged interaction, asks the LLM
   for 2–4 concrete follow-up actions based on what was discussed and the
   outcome (mirrors the "AI Suggested Follow-ups" panel in the mock).
5. **`search_hcp_history_tool`** — Looks up an HCP's past interactions by
   name so the rep (or the agent itself, before logging a new interaction)
   has context.

## Project structure

```
hcp-crm/
├── backend/
│   ├── app/
│   │   ├── agent/
│   │   │   ├── graph.py        # LangGraph StateGraph wiring
│   │   │   └── tools.py        # the 5 tools
│   │   ├── database.py         # SQLAlchemy engine/session (Postgres or MySQL)
│   │   ├── models.py           # HCP, Interaction tables
│   │   ├── schemas.py          # Pydantic request/response models
│   │   └── main.py             # FastAPI app + routes
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── StructuredForm.jsx
│   │   │   └── ChatPanel.jsx
│   │   ├── redux/
│   │   │   ├── store.js
│   │   │   └── interactionSlice.js
│   │   ├── App.jsx
│   │   ├── main.jsx
│   │   └── index.css
│   ├── index.html
│   ├── package.json
│   └── vite.config.js
└── README.md
```

## Running it locally

### 1. Database
Create a Postgres or MySQL database named `hcp_crm` (or point `DATABASE_URL`
at whatever you already have running). Tables are auto-created on backend
startup via SQLAlchemy.

### 2. Backend
```bash
cd backend
python -m venv venv && source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# edit .env: add your GROQ_API_KEY (create one at https://console.groq.com/keys)
# and your DATABASE_URL
uvicorn app.main:app --reload --port 8000
```

### 3. Frontend
```bash
cd frontend
npm install
npm run dev
```
Visit `http://localhost:5173`. The Vite dev server proxies `/api/*` to the
FastAPI backend on port 8000.

## API summary

| Method | Route | Purpose |
|--------|-------|---------|
| POST | `/interactions` | Create an interaction from the structured form |
| GET  | `/interactions` | List all logged interactions |
| PUT  | `/interactions/{id}` | Edit a field on an existing interaction |
| POST | `/chat` | Send a chat message to the LangGraph agent |

## Notes / assumptions

- HCPs are created on the fly the first time they're mentioned (by name,
  case-insensitive match) — there's no separate "create HCP" step in this
  screen's scope.
- Chat history is kept in memory per `session_id` for simplicity; swap in a
  DB-backed or Redis-backed store for multi-device/production use.
- `gemma2-9b-it` is used for the day-to-day extraction/summarization calls
  since it's fast and cheap; `llama-3.3-70b-versatile` is named in `.env` as
  a drop-in upgrade for cases that need heavier reasoning (e.g. richer
  follow-up suggestions), swappable via `GROQ_FALLBACK_MODEL`.
