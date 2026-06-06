# Companion — an agentic AI friend for older adults

A warm, patient AI companion that helps reduce loneliness: chat to share the day,
reflect (Socratic), reminisce, and play light cognitive games — with long-term memory
so it feels like a consistent friend. On top of conversations it can generate gentle,
non-clinical **wellbeing summaries** that can be downloaded as a PDF or shared with a
relative via a consented, expiring link.

> ⚠️ **Not a medical device.** Wellbeing summaries reflect patterns in friendly
> conversation and are **not** a diagnosis. The app includes crisis detection that surfaces
> help resources, but it does not replace professional care or real human connection.

## Architecture

Monorepo with two deployables sharing one Supabase project:

```
apps/web   Next.js 16 PWA (App Router, Tailwind v4, AI SDK v6 useChat) — accessible, elderly-first UI
apps/api   FastAPI + Pydantic AI (v1.106) — the "companion brain": persona, modes,
           memory tools, safety screen, and wellbeing diagnostics
supabase   Postgres + pgvector schema, RLS, and RPCs (migrations/0001_init.sql)
```

- **Chat** flows from the PWA's `useChat` → FastAPI `/chat`, where Pydantic AI's
  `VercelAIAdapter` streams the agent over the AI SDK protocol (SSE, `sdk_version=6`).
- **Memory/continuity**: OpenAI embeddings + pgvector (`match_memories` RPC); the agent has
  `save_memory` / `recall_memory` / `log_mood` tools, and relevant memories are injected as
  dynamic instructions each turn.
- **Modes**: `companion` (warm chat), `reflect` (Socratic), `reminiscence`, `engage` (cognitive play).
- **Safety**: a deterministic crisis screen on each message → resources in the UI + a logged `safety_event`.
- **Diagnostics**: a structured-output agent (`WellbeingSnapshot`) over recent transcripts →
  stored, rendered, exportable to PDF, and shareable via a `SECURITY DEFINER` token RPC.
- **Privacy**: Row Level Security on every table; the API uses the caller's JWT (RLS applies);
  the service-role key is used only for the public share-resolution endpoint.

**Voice (chat-first decision):** voice calls are intentionally deferred. The design target is
the OpenAI Realtime API (browser WebRTC + a backend ephemeral-token endpoint) reusing the same
persona/tools — no persistent-WebSocket host needed.

## Prerequisites

- Node 20.9+ (tested on 22), pnpm 10, Python 3.13, uv
- An OpenAI API key
- A Supabase project (or local stack via `supabase start`, which needs Docker)

## 1) Database

Apply the schema to your Supabase project (enables `pgvector`, tables, RLS, and RPCs):

```bash
# Option A: hosted project
supabase link --project-ref <your-ref>
supabase db push            # applies supabase/migrations/0001_init.sql

# Option B: local (requires Docker running)
supabase start
supabase db reset
```

Profiles are auto-created on signup via the `on_auth_user_created` trigger.

## 2) Backend (apps/api)

```bash
cp .env.example apps/api/.env     # fill OPENAI_API_KEY + SUPABASE_* (incl. JWT secret)
uv run --directory apps/api uvicorn app.main:app --reload --port 8000
# health check:
curl localhost:8000/health        # {"ok": true}
```

Key env (see `.env.example`): `OPENAI_API_KEY`, `OPENAI_MODEL` (default `gpt-4o`),
`OPENAI_EMBEDDING_MODEL` (default `text-embedding-3-small`), `SUPABASE_URL`,
`SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY`, `SUPABASE_JWT_SECRET`, `ALLOWED_ORIGINS`.

## 3) Frontend (apps/web)

```bash
cp .env.example apps/web/.env.local   # NEXT_PUBLIC_SUPABASE_* + NEXT_PUBLIC_API_BASE_URL
cd apps/web && pnpm install
pnpm dev                              # http://localhost:3000
```

Sign in with a magic link, complete onboarding, and start chatting. Create a wellbeing
summary from **Summaries**, then download the PDF or create a share link.

## Testing & verification

```bash
# Backend: agent tools, modes, safety, diagnostics (uses Pydantic AI TestModel — no API key needed)
uv run --directory apps/api pytest -q          # 8 passing

# Frontend: type-check + production build
cd apps/web && pnpm build
```

End-to-end runtime needs real credentials (OpenAI key + Supabase project). Manual happy path:
sign in → onboard → chat → confirm memory recall in a **new** session → switch modes →
type a (test) crisis phrase → see the resources banner → create a wellbeing summary →
download PDF → create a share link → open it in a private window → revoke → confirm it 404s.

## Deployment (Vercel)

- **Web**: deploy `apps/web` as a Next.js project. Set `NEXT_PUBLIC_*` envs. Installable PWA
  (manifest + service worker) included.
- **API**: deploy `apps/api` as a Python (Fluid Compute) project, or any container host. Set the
  backend envs and `ALLOWED_ORIGINS` to the web origin.
- **Weekly diagnostics (optional)**: add a Vercel Cron hitting a protected variant of
  `/diagnostics/generate` per user (a scheduled batch job) to produce summaries automatically.

## What's implemented vs. deferred

- ✅ Accessible chat PWA, auth + onboarding, 4 engagement modes, long-term memory, crisis safety,
  wellbeing diagnostics, PDF export, consented expiring share links, full RLS.
- ⏭️ Deferred (designed-for): voice (OpenAI Realtime), caregiver accounts/dashboard, scheduled
  cron diagnostics, i18n, validated check-in scales.
