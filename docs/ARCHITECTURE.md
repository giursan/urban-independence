# Architecture — `tools/conversation-integration`

An AI **companion** for elderly Hong Kong residents. One Pydantic-AI agent powers
every channel (iOS voice, web chat, phone, Telegram), grounded in live HK data,
with long-term memory, crisis safety screening, and caregiver-facing wellbeing
reports. Auth is currently disabled — every request runs as a fixed dev user.

## System overview

```mermaid
flowchart TB
    subgraph Clients
        ios["📱 iOS app — apps/ios<br/>SwiftUI, voice-first orb<br/>(STT + TTS on device)"]
        web["💻 Web app — apps/web<br/>Next.js, Vercel AI useChat"]
        phone["☎️ Twilio phone<br/>(TwiML voice webhooks)"]
        tg["💬 Telegram<br/>(bot webhook)"]
    end

    subgraph API["FastAPI backend — apps/api (app.main)"]
        direction TB
        auth["auth.py<br/>(disabled → fixed dev user)"]
        subgraph Routes
            chat["POST /chat<br/>SSE · Vercel AI v6 · VercelAIAdapter"]
            convo["/conversations<br/>list · messages · delete"]
            reports["/reports + /share<br/>expiring share links"]
            diag["/diagnostics<br/>wellbeing snapshots"]
            voice["/voice · /voice/turn<br/>(TwiML)"]
            tgroute["/telegram<br/>(webhook)"]
            health["/health"]
        end
        safety["safety.py<br/>deterministic crisis screen"]
        persistence["persistence.py<br/>conversations · messages · mood"]
    end

    subgraph Agent["Companion agent — Pydantic AI (companion.py)"]
        direction TB
        persona["Persona + adaptive overlay<br/>(persona.py)"]
        instr["Dynamic instructions:<br/>profile + recalled memories"]
        memtools["User tools:<br/>save_memory · recall_memory · log_mood<br/>lookup_companion_context · send_telegram_message"]
        hktools["Live HK tools (hk_tools.py):<br/>weather · forecast · AQHI · traffic<br/>MTR · MTR-bus · HKFP news · calendar · web"]
    end

    diagagent["diagnostics_agent<br/>structured WellbeingSnapshot"]
    memory["MemoryService (memory.py)<br/>embeddings + pgvector recall"]

    subgraph External["External services"]
        openai["OpenAI<br/>gpt-4o (chat) + embeddings"]
        subgraph HK["Live HK / city sources (app/sources)"]
            hko["HKO weather"]
            epd["EPD AQHI"]
            td["Transport Dept traffic"]
            mtr["MTR / MTR-bus"]
            hkfp["HKFP news"]
            gcal["Google Calendar"]
            fc["Firecrawl web"]
        end
    end

    supabase[("Supabase — Postgres + pgvector (RLS)<br/>profiles · conversations · messages · mood_logs<br/>companion_facts/memories · safety_events · reports")]

    ios -->|"POST /chat (SSE)"| chat
    web --> chat
    web --> convo
    web --> reports
    web --> diag
    phone --> voice
    tg --> tgroute

    chat --> auth --> safety --> Agent
    voice --> Agent
    tgroute --> Agent

    Agent -->|"messages.run (per-run model)"| openai
    instr --> memory
    memtools --> memory
    memory -->|"embeddings"| openai
    memory -->|"match_memories RPC"| supabase

    hktools -.->|read live data| HK

    Routes --> persistence --> supabase
    diag --> diagagent --> openai
    memtools --> supabase
    Agent --> persistence
```

## A voice turn, end to end

```mermaid
sequenceDiagram
    participant U as Elder (voice)
    participant App as iOS app (VoiceView)
    participant API as FastAPI /chat
    participant Safe as Safety screen
    participant Agent as Companion agent
    participant AI as OpenAI gpt-4o
    participant DB as Supabase

    U->>App: speaks
    Note over App: SFSpeechRecognizer → text<br/>auto-send on ~1.6s pause
    App->>API: POST /chat (messages + conversation_id, trigger)
    API->>DB: upsert conversation · persist user message
    API->>Safe: screen newest message (crisis?)
    Safe-->>DB: log safety_event (if flagged)
    API->>Agent: run with deps (profile, memory, history)
    Agent->>DB: match_memories (recall)
    Agent->>AI: chat completion (+ tool calls)
    AI-->>Agent: streamed tokens
    Agent-->>API: text deltas
    API-->>App: SSE: text-delta … finish · [DONE]
    Note over App: bubble streams in<br/>AVSpeechSynthesizer speaks reply
    App-->>U: companion speaks, then listens again
    API->>DB: persist assistant message (on_complete)
```

## Key facts

- **One agent, many channels.** `companion_agent` (Pydantic AI) is shared by web
  chat, phone (`/voice`), and Telegram. The model (`openai:gpt-4o`) is supplied
  **per run** so importing the module needs no key — `/health` and tests work
  offline.
- **`/chat` streams** the Vercel AI SDK v6 data-stream (SSE) via
  `VercelAIAdapter`; requires a `trigger:"submit-message"` discriminator. The web
  app consumes it with `useChat`; the iOS app parses the SSE directly.
- **Memory** is OpenAI embeddings + pgvector retrieval through the RLS-scoped
  `match_memories` Supabase RPC; injected into the agent's dynamic instructions.
- **Safety** is a deterministic regex screen on each incoming message — surfaces
  crisis resources and writes a `safety_events` row; it is a safety net, not a
  classifier.
- **Wellbeing reports** come from a separate structured-output `diagnostics_agent`
  producing a non-clinical `WellbeingSnapshot`, shared with relatives via expiring
  links (`/reports`, `/share`).
- **Auth is disabled** (`auth.py`): every request is the fixed `dev_user_id`;
  `user_client("")` falls back to the Supabase service-role client.
- **Live HK tools** are `@tool_plain` (no user context) reading public HK feeds in
  `app/sources/`; persona-driven user tools are `@tool` (carry `CompanionDeps`).
