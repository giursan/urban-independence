# Urban Independence — HK Elder Decision Coach

An agentic system that trains elderly Hong Kong residents in real-time decision-making in a fast-changing city. The agent fetches **live HK data** (weather, MTR, air quality, traffic, typhoon signals…), generates a **concrete decision scenario** grounded in that snapshot, then runs a **Socratic dialogue** with the elder — challenging *why* they would choose a given option.

## Architecture

```
                ┌────────────────────────────────────────────────────────┐
                │                  Orchestrator (Claude)                 │
                │                                                        │
   ElderProfile ─┼─▶ Phase 1: FETCH_CONTEXT     (tool loop, parallel)    │
                │     └── tool calls → live HK snapshot                  │
                │                                                        │
                │   Phase 2: GENERATE_SCENARIO  (structured output)      │
                │     └── messages.parse(output_format=Scenario)         │
                │                                                        │
   user turn ───┼─▶ Phase 3: DIALOGUE / CHALLENGE (tool loop, streaming) │
                │     └── Socratic follow-up, can re-call tools          │
                │                                                        │
                │   Phase 4: DEBRIEF / DONE                              │
                └─────────────┬──────────────────────────────────────────┘
                              │
                              ▼
                       SQLite (sessions, turns, tool_calls, usage)
```

**Key choices (SOTA defaults):**

- `claude-opus-4-7` with `thinking: {type: "adaptive"}` and `effort: "high"`
- **Manual tool loop** — phase-aware control, error capture, full audit trail
- **Structured outputs** (`client.messages.parse` + Pydantic) for the scenario
- **Pluggable tool registry** — one decorator and your real HK API is wired in
- **SQLite persistence** — every session, turn, tool call, and token-usage record stored for later analysis

## Layout

```
agent/
  orchestrator.py   # main loop + phase state machine
  tools.py          # @tool decorator + 8 stubbed HK API tools
  prompts.py        # phase-aware system prompts
  schemas.py        # Pydantic models (Scenario, Critique, …)
  persistence.py    # SQLite store
  config.py         # AgentConfig + ElderProfile
app.py              # FastAPI: POST /sessions, /sessions/turn, /sessions/{id}/end
demo_cli.py         # terminal demo
data/
  sessions.db       # created on first run
```

## Run

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # then fill in ANTHROPIC_API_KEY
```

**Terminal demo:**
```bash
python demo_cli.py
```

**HTTP server:**
```bash
uvicorn app:app --reload --port 8000
```

```bash
curl -X POST localhost:8000/sessions -H 'content-type: application/json' \
  -d '{"elder_id":"e1","name":"Mrs Wong","home_district":"Sham Shui Po"}'

curl -X POST localhost:8000/sessions/turn -H 'content-type: application/json' \
  -d '{"session_id":"sess_xxx","message":"I will take the MTR"}'
```

## Wiring your HK API tools

Open `agent/tools.py`. Each stub is a tagged function:

```python
@tool(
    name="get_weather",
    description="…",
    parameters={"district": {"type": "string", "description": "…"}},
    required=["district"],
)
def get_weather(district: str) -> dict:
    return {...}   # ← replace with the real API call
```

The orchestrator picks tools up from `REGISTRY` automatically. To add a new tool, drop another `@tool(...)` block in the same file — no other wiring required.

**Tool stubs to replace** (current names → suggested HK sources):

| Stub | Suggested data source |
|---|---|
| `get_weather` | HK Observatory open data API |
| `get_air_quality` | EPD AQHI feed |
| `get_mtr_status` | MTR Next Train API |
| `get_bus_status` | KMB / Citybus ETA |
| `get_traffic_advisory` | Transport Department |
| `get_typhoon_signal` | HKO warnings |
| `get_local_events` | LCSD events |
| `get_pharmacy_hours` | Pharmacy directory |

## Persistence — what's stored

The SQLite store (`data/sessions.db`) holds three things you'll want for later analysis:

- **`sessions`** — one row per training session: elder_id, start/end timestamps, the live context snapshot, the generated scenario JSON, status.
- **`turns`** — every message in the conversation, with phase tag, role, content, captured tool calls, and token-usage breakdown (incl. cache hits).
- Both tables are indexed for fast retrieval per elder.

Inspect with:
```bash
sqlite3 data/sessions.db "SELECT id, elder_id, started_at, status FROM sessions ORDER BY started_at DESC;"
```

Or via the API: `GET /sessions/{id}` and `GET /elders/{elder_id}/sessions`.

## Phase model

The orchestrator advances a session through these phases:

| Phase | What happens | API used |
|---|---|---|
| `FETCH_CONTEXT` | Claude calls tools in parallel to build a live HK snapshot | `messages.create` + tool loop |
| `GENERATE_SCENARIO` | Claude designs one decision scenario grounded in the snapshot | `messages.parse` → `Scenario` |
| `DIALOGUE` / `CHALLENGE` | Elder picks an option and reasons; Claude probes one factor at a time | `messages.create` + streaming + tool loop |
| `DEBRIEF` / `DONE` | Session closed, summary stored | — |

## Out of scope (for now)

- Voice — the orchestrator is text-in / text-out. Plug Twilio ConversationRelay or a streaming TTS in front of it later.
- Multi-language output — system prompt is English; switch by changing `AgentConfig.locale` and the prompt templates.
- Multi-agent — one orchestrator is enough; revisit only if scenarios need an independent "judge" pass.
