# HONESTY.md

> Mandatory disclosure for the hackathon. This file lives at the root of your repository. Judges cross-check it against your code and your technical video.
>
> **The deal:** disclosed shortcuts are **not** penalized — that is the entire point of this file. Hidden ones are. Undisclosed pre-built code is heavily penalized, each undisclosed mock carries a small penalty, and a faked demo is heavily penalized. Telling the truth here costs you nothing.

> _Drafted from the code + `git` history, with live verification on 2026-06-07 (a real `/chat` turn and a 9/9 HK-sources smoke test). **Team: please review and confirm the rows marked "(team to confirm)" — GitHub handles, per-person split, and pre-kickoff code — before submitting.**_

---

## 1. Team — who did what
Judges compare this against `git shortlog -sn`, so keep it honest. _(Contributions below are derived from `git` history per author; GitHub handles to be added by the team.)_

| Member | GitHub handle | Main contributions |
|---|---|---|
| Silvio Kempf | _(add)_ | Backend: FastAPI app, Pydantic-AI companion agent, Supabase schema/persistence, parts of web |
| Phi Linh | _(add)_ | Web frontend (Next.js `apps/web`) + API wiring |
| Yvonne Creter | _(add)_ | Live HK data tools / sources (transport, web, social) |
| Sandra Giurgea | _(add)_ | iOS app (`apps/ios`, SwiftUI voice companion) + architecture docs |

---

## 2. What is fully working
Features that run end-to-end on the live app, with real data and real logic.

_Verified by live run on 2026-06-07:_

- **Companion chat (web + iOS)** — real **OpenAI gpt-4o**. Input: the user's message + prior conversation history; output: a streamed companion reply over the Vercel AI SDK v6 SSE protocol. Each turn upserts the conversation and persists user + assistant messages to Supabase. _Verified with a live `/chat` request returning a streamed, persisted reply._
- **Live Hong Kong data tools** — the agent calls real public APIs and quotes live values in conversation. **9/9 passed** a smoke test (`apps/api/scripts/smoke_hk_sources.py`) against real endpoints: HKO weather + multi-day forecast, EPD **AQHI** air quality, Transport Dept **traffic** incidents, **MTR** next-train arrivals, **HKFP** news headlines.
- **Long-term memory** — OpenAI embeddings (`text-embedding-3-small`) + **pgvector** retrieval via the RLS-scoped `match_memories` Supabase RPC. The agent has real `save_memory` / `recall_memory` tools and injects recalled facts into its instructions.
- **Crisis safety screen** — deterministic regex screen on every incoming message; a positive screen surfaces crisis resources to the UI and writes a `safety_events` row. Real logic, runs on every turn.
- **iOS voice companion** (`apps/ios`) — SwiftUI voice-first "orb" UI; on-device **STT** (`SFSpeechRecognizer`) + **TTS** (`AVSpeechSynthesizer`); hands-free listen → reply-aloud → listen loop, talking to the real backend. _Verified: builds, runs on the iOS 17 simulator, completes a real streamed turn with a spoken reply._ (STT is reliable on a physical device; flaky on the Simulator — see §6.)

---

## 3. What is mocked, stubbed, or hardcoded
**Undisclosed mocks carry a small penalty each. Anything you list here = free.**

| What is faked | Where (file:line or folder) | Why we mocked it | What the real version would do |
|---|---|---|---|
| **Authentication is disabled** — every request runs as one fixed dev user | `apps/api/app/auth.py` (`current_user` returns `settings.dev_user_id`); dev profile seeded in `supabase/migrations/0002_dev_disable_auth.sql` | Removed sign-in to iterate fast during the hackathon | Verify the Supabase JWT, return the real user id, and scope all data per-user via RLS |
| **iOS offline chat mock server** — canned SSE responder | `apps/ios/mock_chat_server.py` | Lets the iOS app be demoed/tested without OpenAI + Supabase credentials | Not used in the real flow — the app talks to the real FastAPI `/chat`. This file is a dev convenience only |

_The backend itself contains no stubbed data: every HK source (`apps/api/app/sources/*`) makes real `httpx` calls to live public APIs. (Note: the **root `CLAUDE.md` is stale** — it describes an earlier all-stubbed design that no longer matches the code. See §6.)_

---

## 4. External APIs, services & data sources

| Service / API / dataset | Used for | Real call or mocked? | Auth (sandbox / test key / none) |
|---|---|---|---|
| OpenAI **gpt-4o** | Companion replies (chat agent) | **Real** | API key |
| OpenAI embeddings (`text-embedding-3-small`) | Long-term memory vectors | **Real** | API key |
| **Supabase** (Postgres + pgvector + PostgREST) | Persistence, memory, RLS | **Real** (local stack on `127.0.0.1:54321`) | Local anon / service-role keys |
| HKO Open Data (weather + forecast) | Weather tools | **Real** (smoke-tested) | None (public) |
| EPD AQHI | Air-quality tool | **Real** (smoke-tested) | None (public) |
| HK Transport Dept traffic feed | Traffic advisories | **Real** (smoke-tested) | None (public) |
| MTR / data.gov.hk (next train, MTR-bus) | Transit tools | **Real** (smoke-tested) | None (public) |
| Hong Kong Free Press (RSS) | News headlines | **Real** (smoke-tested) | None (public) |
| Google Calendar API | Calendar-events tool | **Real call**, key-gated | API key (`GOOGLE_CALENDAR_API_KEY`) — _not exercised in the smoke test_ |
| Firecrawl | `web_search` / `web_scrape` fallback | **Real call**, key-gated | API key (`FIRECRAWL_API_KEY`) — _not exercised in the smoke test_ |
| Telegram Bot API | Caregiver messaging + webhook transport | **Real** integration, key-gated | Bot token — _not verified live in this pass_ |
| Twilio Voice | Phone channel (TwiML webhooks) | **Real** webhook handlers | Account SID / auth token + number — _not verified live in this pass_ |

---

## 5. Pre-existing code
**Undisclosed pre-built code is heavily penalized. Anything you list here = free.**

| Item | Source (URL or description) | Roughly how much | License |
|---|---|---|---|
| Next.js app scaffold (`apps/web`) | `create-next-app` boilerplate (see `apps/web/AGENTS.md`) | Standard scaffold, customized | MIT |
| FastAPI + Pydantic AI + Supabase client | Standard framework/library usage | Libraries (deps), not copied code | OSS (various) |
| XcodeGen-generated iOS project | `project.yml` → generated `.xcodeproj` (app code is original) | Project file only | MIT (XcodeGen) |

_Per `git` history, all **application** code was authored during the hackathon window (first commit 2026-06-06, last 2026-06-07). The items above are standard framework boilerplate/tooling used as-is. **(Team to confirm)** that no pre-kickoff personal projects, forks, or internal libraries were brought in beyond the above._

---

## 6. Known limitations & next steps

- **Auth is off** — single fixed dev user; multi-user accounts + RLS enforcement are not active yet.
- **Supabase is a local stack** (`supabase start`, `127.0.0.1:54321`), not a hosted/production project.
- **iOS STT is Simulator-flaky** — speech recognition depends on the Mac mic on the Simulator; reliable on a physical iPhone. The iOS app is voice/chat-only — no conversation-history or caregiver-report screens yet.
- **Implemented but not independently end-to-end verified in this pass:** Telegram transport + caregiver messaging, Twilio phone voice, wellbeing **diagnostics** (`WellbeingSnapshot`), and **share reports**. The code paths are real (no stubs), but we did not run them live for this submission — team to confirm.
- **Key-gated tools untested live:** Google Calendar and Firecrawl require API keys that were not exercised in the smoke test.
- **Stale docs:** the root `CLAUDE.md` describes an earlier all-stubbed architecture and no longer reflects the real (`apps/api`, live-API) codebase; it should be updated. Current accurate overview lives in `docs/ARCHITECTURE.md`.

---

## 7. AI assistance disclosure
This project was built with the help of an AI coding assistant (**Claude Code**). For transparency, the parts where AI assistance is known to be substantial:

- **iOS app** (`apps/ios`) — the SwiftUI voice companion (orb UI, streaming `/chat` client, on-device STT/TTS, the listen→reply→listen loop) was implemented with Claude Code.
- **Local dev / infra setup** — bringing up local Supabase (Docker + CLI), wiring env, and running/verifying the backend end-to-end was done with Claude Code.
- **Architecture docs** — `docs/ARCHITECTURE.md` and the rendered diagrams were generated with Claude Code.
- **This `HONESTY.md`** — drafted by Claude Code from the code, `git` history, and live verification, for the team to review and own.
- The Python backend (`apps/api`) and Next.js web app (`apps/web`) were primarily authored by the team; the extent of AI assistance there is **(team to confirm)**.

_AI assistance was used for implementation and verification; the design decisions, integrations, and review remain the team's._
