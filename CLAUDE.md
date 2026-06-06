# CLAUDE.md — operating manual for AI agents working on this repo

You are picking up an in-progress project. Read this whole file before editing.

## What this is

A training system that puts elderly Hong Kong residents through real-time decision-making scenarios grounded in **live HK data** (weather, MTR, air quality, typhoon signal, traffic, events). One Claude orchestrator runs the loop; tools fetch live context; the orchestrator generates a concrete decision scenario, then runs a Socratic dialogue challenging the user's reasoning.

This is text-in / text-out for now. Voice (Twilio / streaming TTS) is a later layer that sits in front of `Orchestrator.turn()`.

## Current state

**Built and working end-to-end against stubs.**

- ✅ Orchestrator with phase state machine
- ✅ Tool registry (`@tool` decorator)
- ✅ 8 HK API tools — **all stubbed with fake but realistic returns**. Real API integration is the team's next task.
- ✅ Structured scenario generation via `messages.parse(output_format=Scenario)`
- ✅ SQLite persistence (sessions + turns + tool calls + token usage)
- ✅ FastAPI HTTP surface
- ✅ Terminal CLI demo (`demo_cli.py`)

**Real API integrations done:**
- ✅ `get_air_quality` — wired to HK EPD AQHI RSS feed (see `agent/sources/aqhi.py`). 5-min in-memory cache. Pattern to follow for the other 7 tools.

**Not built yet** (do NOT add unless asked):
- Remaining 7 tools still stubbed (returns marked `"source": "STUB — …"`)
- Streaming for the dialogue phase (orchestrator uses non-streaming `messages.create`)
- Voice integration
- Multi-language output (English-only system prompts)
- Auth, rate limiting, multi-tenant isolation
- A real "DEBRIEF" agent pass — the prompt asks the model to debrief inline; we did not split it into its own phase

## SDK / model pins (DO NOT change without asking)

- `anthropic>=0.92.0` (needed for `messages.parse(output_format=…)`)
- Model: `claude-opus-4-7`
- Thinking: `{"type": "adaptive"}`
- Effort: `"high"` (set in `agent/config.py:AgentConfig`)
- **No `budget_tokens`** — removed in Opus 4.7, will 400 if added.
- **No `temperature` / `top_p` / `top_k`** — also removed in Opus 4.7.

## Architecture

```
ElderProfile + elder_id
        │
        ▼
┌──────────────────────────────────────────────────────────────┐
│ Orchestrator.start_session()                                 │
│                                                              │
│  Phase 1: FETCH_CONTEXT                                      │
│    └─ _run_tool_loop()  →  parallel tool calls               │
│        weather, AQI, MTR, typhoon, traffic, events…          │
│    → context snapshot saved to sessions.context_json         │
│                                                              │
│  Phase 2: GENERATE_SCENARIO                                  │
│    └─ messages.parse(output_format=Scenario)                 │
│    → Scenario saved to sessions.scenario_json                │
│                                                              │
│  returns Session (phase=DIALOGUE) to caller                  │
└──────────────────────────────────────────────────────────────┘

        ▼
┌──────────────────────────────────────────────────────────────┐
│ Orchestrator.turn(session_id, user_text)                     │
│  └─ _run_tool_loop() with dialogue/Socratic system prompt    │
│  → assistant reply saved as a turn row                       │
└──────────────────────────────────────────────────────────────┘

        ▼
Orchestrator.end_session(session_id)
```

## File map

```
agent/
  config.py         AgentConfig (model, effort, max_tokens), ElderProfile
  schemas.py        Pydantic: Scenario, ScenarioOption, Critique, Phase enum
  prompts.py        Three phase-aware system prompts
  tools.py          @tool decorator, REGISTRY, 8 tools (1 real, 7 stubbed)
  sources/          One file per real HK API (network + parsing). Imported by tools.py.
    aqhi.py         HK EPD Air Quality Health Index (RSS, hourly)
  persistence.py    Store class — SQLite (sessions, turns)
  orchestrator.py   THE main loop. _run_tool_loop is the heart.
app.py              FastAPI surface
demo_cli.py         Terminal demo
data/sessions.db    Created on first run (gitignored)
```

## Interface contracts

### Adding a tool (most common task)

Open `agent/tools.py`. Add one block at the bottom:

```python
@tool(
    name="get_<thing>",
    description="One sentence. Claude uses this to decide WHEN to call. Be specific.",
    parameters={
        "param_name": {
            "type": "string",
            "description": "What this parameter is and an example value.",
        },
    },
    required=["param_name"],
)
def get_thing(param_name: str) -> dict:
    # call the real API here
    return {...}
```

Rules:
- Return a `dict` (or any JSON-serialisable thing). The orchestrator does `json.dumps(result, default=str)` on it.
- If the API can fail, raise — `_run_tool_loop` catches and returns `is_error: true` to Claude.
- Function args must match `parameters` keys. The orchestrator filters kwargs by signature, so extra fields are tolerated.
- Do **not** register tools at request time. The registry is built at import.

### `Scenario` (structured output)

Defined in `agent/schemas.py`. Every `live_factors` entry **must** reference a real value from the fetched context — this is enforced by the system prompt in `prompts.py:system_prompt_scenario`, not by the schema. If you change the schema, update that prompt.

### `Orchestrator` public API

| Method | Returns | Notes |
|---|---|---|
| `start_session(elder: ElderProfile)` | `Session` | Runs FETCH_CONTEXT + GENERATE_SCENARIO synchronously. Slow (~5–15s). |
| `turn(session_id, user_text)` | `str` | One dialogue turn. Idempotent on failure: nothing is committed if Claude raises. |
| `end_session(session_id, summary=None)` | `None` | Marks the row ended and drops in-memory state. |
| `get_session(session_id)` | `Session` | In-memory only. Use `Store.get_session` for the DB row. |

In-memory `Session` objects do **not** survive a process restart. The SQLite rows do. If you need session resume after restart, that's new code — ask before adding.

### `Store` (SQLite)

Schema is in `agent/persistence.py:SCHEMA`. Two tables:

- `sessions(id, elder_id, started_at, ended_at, status, context_json, scenario_json, summary)`
- `turns(id, session_id, ts, phase, role, content, tool_calls_json, usage_json)`

`usage_json` includes `cache_read_input_tokens` / `cache_creation_input_tokens` — useful for the team's analysis later.

To query: `store.list_sessions(elder_id=…)`, `store.get_turns(session_id)`. Or just `sqlite3 data/sessions.db`.

### HTTP surface (`app.py`)

```
POST   /sessions                     → { session_id, scenario_text, scenario, context }
POST   /sessions/turn                → { reply }
POST   /sessions/{id}/end
GET    /sessions/{id}                → session row + turns
GET    /elders/{id}/sessions         → list
GET    /health
```

## Working rules

1. **Don't change the model, thinking mode, or effort** without asking. They are SOTA defaults for this model.
2. **Don't replace `messages.parse` with `messages.create` + manual JSON parsing.** The typed Pydantic path is the SOTA way to do structured outputs on this SDK.
3. **Don't add `budget_tokens`, `temperature`, `top_p`, `top_k`.** They will 400 on Opus 4.7.
4. **Don't introduce a multi-agent setup** (separate scenario / coach / judge agents). One orchestrator with phase-aware prompts is intentional — it preserves prompt caching and keeps the code small.
5. **Don't add tools outside `agent/tools.py`.** The decorator must run at import time so `REGISTRY` is populated before the orchestrator boots.
6. **Don't loosen the "all live_factors must reference real fetched values" rule** in `system_prompt_scenario`. It's the only thing stopping the model from making up numbers.
7. **Real API integration** — when wiring a real HK API into a stub, keep the function signature and return-dict shape. Downstream prompts read those keys.
8. **If a tool needs an API key**, read it from `os.environ` inside the function, not at import. Don't fail-fast on missing env — let the tool call raise and surface the error to Claude.
9. **Persistence is append-only by design.** Don't mutate past turn rows. If you need to redact, add a column.
10. **No medical reasoning, no clinical advice.** The system prompts already restrict this. Don't loosen them.

## Where to start by task type

- **"Wire up the real HK Observatory API"** → follow the `aqhi.py` pattern:
  1. Create `agent/sources/<name>.py` with a `fetch_*` function. Put the HTTP call, parsing, and any in-memory caching there.
  2. Import the module in `agent/tools.py` and replace the stub body of the matching `@tool` function with a call into it.
  3. Keep the tool's return-dict keys stable — prompts read them. Always include `"source"` and `"source_url"` for auditability.
- **"Add Cantonese output"** → edit `agent/prompts.py:system_prompt_dialogue` to add a voice rule, and pass `locale` through `AgentConfig`. The schema is language-agnostic.
- **"Stream the dialogue reply"** → swap `client.messages.create` for `client.messages.stream` in `_run_tool_loop`, **only for the dialogue phase**. Tool-fetch loop should stay non-streaming.
- **"Add a new phase (e.g. RECAP)"** → add it to `Phase` enum in `schemas.py`, add the prompt in `prompts.py`, add the transition in `orchestrator.py`.
- **"Analyse past sessions"** → query SQLite directly, don't go through the orchestrator. The `usage_json` column has the token-cost breakdown.
- **"Twilio voice"** → new file `voice.py`. Calls `Orchestrator.start_session` once on dial-in, then `Orchestrator.turn(session_id, transcribed_text)` per gather. Do not modify the orchestrator.

## Run

```bash
pip install -r requirements.txt
cp .env.example .env  # fill in ANTHROPIC_API_KEY
python demo_cli.py        # terminal end-to-end
# or
uvicorn app:app --reload  # HTTP server on :8000
```
