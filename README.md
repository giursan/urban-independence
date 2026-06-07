# Companion — an agentic AI friend for older adults

A warm, patient AI companion that helps reduce loneliness. The same "companion brain"
meets people wherever they are — a web app, a **phone call**, **Telegram**, or a native
**iOS** app — and remembers them across all of it. It chats about the day, reflects
(Socratic), reminisces, plays light cognitive games, and can pull in **live local
information** (weather, air quality, transit, news, calendar). On top of conversations it
generates gentle, non-clinical **wellbeing summaries** that a relative can read, download
as a PDF, or open through a consented, expiring share link.

> ⚠️ **Not a medical device.** Wellbeing summaries (including the cognitive-awareness
> fields) reflect patterns in friendly conversation and are **not** a diagnosis. The app
> includes crisis detection that surfaces help resources, but it does not replace
> professional care or real human connection.

## Architecture

A monorepo with three apps over one shared Supabase project:

```
apps/web    Next.js 16 PWA (App Router, Tailwind v4, AI SDK v6 useChat) — accessible,
            elderly-first chat UI, onboarding, the caregiver "Care" page, and wellbeing summaries
apps/api    FastAPI + Pydantic AI — the companion brain: persona, adaptive behavior, memory,
            caregiver facts, live tools, safety screen, diagnostics, and the chat/voice/telegram transports
apps/ios    Native SwiftUI chat client (MVP) — streams the same /chat SSE protocol as the web app
supabase    Postgres + pgvector schema, RLS, and RPCs (migrations/0001 → 0007)
deploy      Docker Compose + Caddy + ngrok for single-origin self-hosting (e.g. a home NAS)
```

**One brain, many front doors.** Every surface funnels into the same Pydantic AI agent and
the same Supabase tables, so memory, safety, and wellbeing summaries are consistent no matter
how the person reached the companion:

- **Web chat** — the PWA's `useChat` → `POST /chat`, where Pydantic AI's `VercelAIAdapter`
  streams the agent over the AI SDK data-stream protocol (SSE, `sdk_version=6`).
- **Phone** — Twilio Voice webhooks → `POST /voice`. Each `CallSid` maps to one persisted
  conversation. Callers are **identity-verified** first (see below), and replies are spoken with
  a warm Amazon Polly neural voice via TwiML `<Gather>`.
- **Telegram** — Telegram Bot webhooks → `POST /telegram/webhook`. Each chat maps to a
  persisted conversation; the companion can also message a configured caregiver.
- **iOS** — a SwiftUI app that POSTs to `/chat` and parses the same SSE stream.

**The companion brain (`apps/api`):**

- **Adaptive posture** — a single prompt; the model reads each message and chooses the right
  stance turn by turn (warm chat, Socratic reflection, reminiscence, or light cognitive play)
  instead of being locked into one "mode" for a session. Phone and Telegram add a delivery
  overlay for short, spoken, screenless replies.
- **Long-term memory** — OpenAI embeddings + pgvector (`match_memories` RPC). The agent has
  `save_memory` / `recall_memory` / `log_mood` tools, and relevant memories are injected as
  dynamic instructions each turn.
- **Caregiver facts** — relatives enter durable background (relatives, routines, sensitivities,
  topics to avoid, a companion brief) on the **Care** page; the agent reads them with the
  `lookup_companion_context` tool.
- **Live local tools** — ~10 read-only Hong Kong tools: weather + forecast (HKO), air quality
  (AQHI, with elderly-specific advice), MTR train status + MTR bus ETAs, Transport Department
  traffic advisories, Hong Kong Free Press headlines, general web search/scrape (Firecrawl),
  and Google Calendar. The companion quotes specific values back ("AQHI is 4 — moderate — in Central").
- **Safety** — a deterministic crisis screen on every inbound message → resources in the UI and a
  logged `safety_event`.
- **Diagnostics** — a structured-output agent (`WellbeingSnapshot`) over recent transcripts →
  stored, rendered, exportable to PDF, and shareable via a `SECURITY DEFINER` token RPC. Includes
  strengths-first wellbeing fields plus conservative, non-diagnostic cognitive-awareness notes.

**Privacy & auth.** Web/iOS users authenticate with Supabase (email + password). The backend
verifies each request's JWT against the project's **JWKS** (asymmetric ES256/RS256, with an
HS256 shared-secret fallback) and runs PostgREST under that user's JWT, so **Row Level Security**
applies per user on every table. The service-role key (which bypasses RLS) is used only for the
public share-resolution endpoint and the server-trusted phone/Telegram transports. Phone callers
are verified by caller-ID or a name + security-question challenge; security answers are stored
only as salted hashes.

## Repository layout

```
apps/api/app/
  companion.py        the agent + memory/mood tools
  persona.py          base persona, adaptive/phone/telegram overlays, diagnostics instructions
  memory.py           pgvector recall/save (match_memories RPC)
  persistence.py      conversations, transcripts, safety events
  diagnostics.py      WellbeingSnapshot structured-output agent
  safety.py           deterministic crisis screen
  identity.py         phone-call identity verification (hashing, name/number resolution, call state)
  caregiver_tools.py  lookup_companion_context tool over companion_facts
  hk_tools.py + sources/   live HK data tools (weather, aqhi, mtr, traffic, news, web, calendar)
  telegram_tools.py   send_telegram_message tool + Telegram send helper
  auth.py             Supabase JWT verification (JWKS + HS256 fallback)
  supabase_client.py  per-user (RLS) and service-role client factories
  routes/             chat, conversations, diagnostics, reports, voice, telegram, identity
apps/web/app/         /login, /onboarding, /talk, /me (summaries), /report/[id], /share/[token], /care
apps/web/components/  ConversationWorkspace, Chat, CaregiverWorkspace, ReportView, ShareControls, …
supabase/migrations/  0001 init → 0007 enable_auth
deploy/               compose.yml, Caddyfile, .env.example, README.md
```

## Prerequisites

- Node 20.9+ (tested on 22), pnpm 10, Python 3.13, [uv](https://docs.astral.sh/uv/)
- An OpenAI API key
- A Supabase project (or local stack via `supabase start`, which needs Docker)
- Optional, per feature: Twilio number (phone), a Telegram bot (`@BotFather`), Firecrawl key
  (web search), Google Calendar API key + calendar id, Xcode 16+ and XcodeGen (iOS)

## Setup

### 1) Database

Apply the schema to your Supabase project. The migration chain `0001 → 0007` builds the schema
(pgvector, tables, RPCs); the intermediate `*_dev_disable_auth` migrations toggled RLS off during
development — **applying the full chain ends at `0007_enable_auth`, with RLS and per-user auth ON**,
which is what the app expects.

```bash
# Option A: hosted project
supabase link --project-ref <your-ref>
supabase db push            # applies supabase/migrations/0001 … 0007 in order

# Option B: local (requires Docker running)
supabase start
supabase db reset
```

A `profiles` row is auto-created on signup via the `on_auth_user_created` trigger. Configure email
confirmation under **Authentication → Providers → Email** to taste (with confirmation off, sign-up
logs the user straight in).

Tables created: `profiles`, `conversations`, `messages`, `memories`, `companion_facts`,
`mood_logs`, `safety_events`, `wellbeing_snapshots`, `reports`, `report_shares`,
`caller_phone_numbers`, `security_questions`, `call_sessions`.

### 2) Backend (`apps/api`)

```bash
cp .env.example apps/api/.env     # fill OPENAI_API_KEY + SUPABASE_*
uv run --directory apps/api uvicorn app.main:app --reload --port 8000
curl localhost:8000/health        # {"ok": true}
```

### 3) Frontend (`apps/web`)

```bash
cp .env.example apps/web/.env.local   # NEXT_PUBLIC_SUPABASE_* + NEXT_PUBLIC_API_BASE_URL
cd apps/web && pnpm install
pnpm dev                              # http://localhost:3000
```

Create an account on **/login**, complete onboarding, and start chatting. Generate a wellbeing
summary from **Summaries**, then download the PDF or create a share link. Relatives use **Care** to
fill in background the companion should know, and to set the person's phone number and a security
question for phone access.

### 4) iOS app (optional)

See `apps/ios/README.md`. It needs XcodeGen (`brew install xcodegen`), then `xcodegen generate` and
run in the simulator. Point `AppConfig.swift` at the backend base URL.

## Environment variables

The same `.env.example` template covers both apps (each reads only what it needs). **Never commit
real keys** — `apps/api/.env`, `apps/web/.env.local`, and `.env` are gitignored; `.env.example`
holds placeholders only.

### Backend (`apps/api/.env`)

| Variable | Required | Notes |
|---|---|---|
| `OPENAI_API_KEY` | ✅ | chat, embeddings, diagnostics |
| `OPENAI_MODEL` | | default `gpt-4o` |
| `OPENAI_EMBEDDING_MODEL` / `EMBEDDING_DIM` | | default `text-embedding-3-small` / `1536`; `EMBEDDING_DIM` must match the `vector(N)` in `0001_init.sql` |
| `SUPABASE_URL` | ✅ | base project URL (no `/rest/v1`) |
| `SUPABASE_ANON_KEY` | ✅ | also used for the JWKS lookup |
| `SUPABASE_SERVICE_ROLE_KEY` | ✅ | server-only; share resolution + phone/Telegram transports |
| `SUPABASE_JWT_SECRET` | | only for legacy HS256 tokens; JWKS is used for modern asymmetric keys |
| `ALLOWED_ORIGINS` | | CSV of web origins, default `http://localhost:3000` |
| `IDENTITY_SECRET` | | salt for hashed phone security answers (set a real value in prod) |
| `VOICE_TTS_VOICE` / `VOICE_TTS_RATE` / `VOICE_SENTENCE_PAUSE_MS` | | Twilio/Polly voice tuning |
| `TELEGRAM_BOT_TOKEN` / `TELEGRAM_CAREGIVER_CHAT_ID` / `TELEGRAM_WEBHOOK_SECRET` | | Telegram transport + caregiver messaging |
| `FIRECRAWL_API_KEY` | | enables `web_search` / `web_scrape` tools |
| `GOOGLE_CALENDAR_API_KEY` / `GOOGLE_CALENDAR_ID` | | enables `get_calendar_events` tool |

### Frontend (`apps/web/.env.local`)

| Variable | Required | Notes |
|---|---|---|
| `NEXT_PUBLIC_SUPABASE_URL` | ✅ | base project URL |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | ✅ | anon/publishable key |
| `NEXT_PUBLIC_API_BASE_URL` | ✅ | FastAPI origin, e.g. `http://localhost:8000` |

## API surface

| Method & path | Auth | Purpose |
|---|---|---|
| `GET /health` | — | liveness |
| `POST /chat` | user JWT | streaming companion chat (AI SDK SSE) |
| `GET /conversations` | user JWT | sessions list (with last message) |
| `GET /conversations/{id}/messages` | user JWT | transcript |
| `DELETE /conversations/{id}` | user JWT | delete a session |
| `POST /diagnostics/generate` · `GET /diagnostics` | user JWT | create / list wellbeing snapshots |
| `POST /reports/from-snapshot/{id}` · `POST /reports/{id}/share` · `POST /shares/{token}/revoke` | user JWT | reports and consented share links |
| `GET /shares/{token}` | public | resolve a share link (SECURITY DEFINER RPC; revoked/expired → 404) |
| `GET/POST/DELETE /security-questions` · `PUT /profile/phone` | user JWT | phone-identity authoring (answers hashed server-side) |
| `POST /voice` · `POST /voice/turn` · `POST /voice/timeout` | Twilio | phone call setup, turns, timeout (TwiML) |
| `POST /telegram/webhook` | secret token | Telegram updates |

### Phone identity verification

`POST /voice` resolves the caller: a **known number** identifies the user outright; an **unknown
number** is challenged for first + last name, then a security question. Spoken names/answers are
normalized (speech-to-text is noisy), answers are checked against salted hashes, and there are 3
attempts before the call ends. Verified numbers are remembered so future calls skip the challenge,
and failed attempts are logged as `safety_events` so a relative can notice suspicious calls.

For phone/Telegram setup details (webhook URLs, ngrok, secrets), see `deploy/README.md`.

## Testing & verification

```bash
# Backend: agent tools, voice/Telegram transports, safety, diagnostics
# (uses Pydantic AI TestModel — no API key or network needed)
uv run --directory apps/api pytest -q

# Frontend: type-check + production build
cd apps/web && pnpm build
```

End-to-end runtime needs real credentials (OpenAI + Supabase). Manual happy path: sign in → onboard
→ chat → confirm memory recall in a **new** session → type a (test) crisis phrase → see the
resources banner → on **Care**, add a background fact and confirm the companion uses it → create a
wellbeing summary → download the PDF → create a share link → open it in a private window → revoke →
confirm it 404s.

## Deployment

- **Vercel (web)** — deploy `apps/web` as a Next.js project; set the `NEXT_PUBLIC_*` envs.
  Installable PWA (manifest + service worker) included.
- **Vercel / container (api)** — deploy `apps/api` (Python / Fluid Compute, or any container). Set
  the backend envs and `ALLOWED_ORIGINS` to the web origin.
- **Single-origin self-host** — `deploy/` runs four containers (FastAPI, the Next.js standalone
  server, a Caddy reverse proxy, and an ngrok tunnel) behind **one public HTTPS origin**, so the
  web app, `/chat`, `/voice`, `/telegram/webhook`, and share links are all same-origin — ideal for
  the stable callback URL that Supabase redirects, Twilio, Telegram, and the iOS app all want. See
  `deploy/README.md`.

## What's implemented vs. deferred

- ✅ Accessible chat PWA, email/password auth + onboarding, per-user RLS, adaptive companion
  behavior, long-term memory, caregiver "Care" page (background facts + phone/security setup), live
  Hong Kong tools (weather, air quality, MTR, traffic, news, web, calendar), Twilio **phone calls
  with identity verification**, Telegram bot + caregiver messaging, crisis safety, wellbeing
  diagnostics with cognitive-awareness notes, PDF export, consented expiring share links, and a
  SwiftUI iOS chat client.
- ⏭️ Deferred / known gaps: the **iOS app and Telegram transport don't yet send a per-user JWT**
  (the iOS client posts `/chat` without a token, and Telegram routes through a single shared dev
  user) — both predate per-user auth and need wiring up before multi-user use. Also designed-for but
  not built: OpenAI Realtime streaming voice, full caregiver accounts/dashboards, scheduled cron
  diagnostics, i18n, and validated check-in scales.

## Demonstration
- Technical Demo: https://youtu.be/VgCcMsIHqFI
```
