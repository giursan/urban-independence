# Urban Independence

A phone-call interface that helps elderly people stay independent in a digitalising city. They call a normal phone number, talk to an assistant in natural language, and get help with their calendar, local events, routes, and reminders. Relatives can feed context (appointments, birthdays, instructions) through a separate UI — the elder never has to install or learn an app.

## Why this exists

City information, public services, and personal scheduling are increasingly digital-only. Many elderly people are excluded by this shift: they don't use smartphones, don't trust apps, can't read small screens, or can't remember passwords. But almost all of them can use a phone.

The bet: a voice-first system reached through a familiar interface (a phone call) can restore the independence that digitalisation took away — *without* asking the user to adapt to new technology.

## Users

- **Primary user — the elder.** Interacts only by calling a phone number. Never sees a screen. Never logs in. Identified by caller ID.
- **Secondary user — a relative or caregiver.** Uses a small web UI to enter context about the elder (calendar entries, medical reminders, instructions, important contacts).

The two users share state but never share the interface.

## What the system does (MVP scope)

The elder calls the number and can:

1. Ask what's on their calendar today / tomorrow / this week.
2. Ask what's happening in their city (events, markets, public notices).
3. Ask about a route: "Can I walk to the church today?" — the system warns about closures, marathons, weather, etc.
4. Ask general assistant-style questions ("what day is it", "when is my daughter's birthday").

The relative can:

1. Add calendar entries for the elder.
2. Add medical reminders (stubbed in MVP — surfaced as plain text, no clinical logic).
3. Add notes ("don't take the bus on Thursdays, she gets confused").

## What is explicitly out of scope for the hackathon MVP

- Outbound calls from the system to the elder (proactive reminders).
- Real medical advice or anything that could be mistaken for it.
- Real city APIs — events and route advisories are stubbed with realistic data.
- Authentication beyond caller ID matching.
- A real relatives UI — for the demo, a JSON file or a single HTML form is enough.
- Multi-language support (English first; German is a stretch goal because the team is in a German city).

## Architecture

```
   ┌──────────┐    PSTN    ┌────────┐   HTTPS    ┌──────────────┐
   │  Phone   │──────────▶ │ Twilio │──────────▶ │  FastAPI app │
   └──────────┘            └────────┘  webhook   │   (this repo)│
                                                 └──────┬───────┘
                                                        │
                                ┌───────────────────────┼───────────────────────┐
                                ▼                       ▼                       ▼
                        ┌──────────────┐        ┌──────────────┐        ┌──────────────┐
                        │ Claude API   │        │  Tool layer  │        │ State store  │
                        │ (tool use)   │        │ calendar /   │        │ SQLite or    │
                        │              │        │ events /     │        │ JSON file    │
                        └──────────────┘        │ routes       │        └──────────────┘
                                                └──────────────┘
```

### Call flow (MVP — using Twilio `<Gather>`)

1. Elder dials the Twilio number.
2. Twilio POSTs to `/voice` on our FastAPI app.
3. We return TwiML: `<Say>` a greeting, then `<Gather input="speech" action="/turn">`.
4. Twilio transcribes the speech, POSTs the transcript to `/turn` along with the call SID.
5. We look up the conversation history for that call SID, append the user message, call Claude with the tool list.
6. If Claude calls a tool, we run it locally (calendar/events/routes are all in-process stubs) and feed the result back to Claude.
7. We take Claude's final text response, return TwiML: `<Say>` it, then `<Gather>` again for the next turn.
8. Loop until the caller hangs up or says "goodbye".

`<Gather>` was chosen over Twilio ConversationRelay for the MVP because it has zero setup beyond a webhook URL — good enough to demo, and the latency (~2s per turn) is acceptable for a slower-paced elderly user. The upgrade path is documented below.

### Why this stack

- **Twilio** — easiest way to get a real phone number that hits an HTTP endpoint. Free trial covers the hackathon.
- **FastAPI + ngrok** — one process, one public URL, redeploys in seconds.
- **Claude (Anthropic)** — tool use is reliable; `claude-haiku-4-5` is fast enough for voice; `claude-sonnet-4-6` is the quality fallback.
- **SQLite (or JSON)** — the relative UI and the call handler both read/write the same file. No database server to run during a demo.

### Upgrade path (post-hackathon, do not implement now)

- Replace `<Gather>` with **Twilio ConversationRelay** for streaming STT/TTS — drops turn latency to ~300ms.
- Replace SQLite with Postgres.
- Add an outbound-call worker for proactive reminders (Twilio REST API + a cron).
- Add real city event sources (each city = one connector).
- Add German + dialect support.

## Tools exposed to the model (MVP)

Three tools, all stubbed with realistic in-process data. Tools are the *only* way the assistant should answer factual questions about the elder's life or the city.

1. **`get_calendar(date_range)`** — returns the elder's calendar entries for a given range. Reads from `data/calendar.json`.
2. **`get_city_events(date)`** — returns public events in the city for a given date. Reads from `data/events.json`.
3. **`get_route_advisory(from_location, to_location)`** — returns route notes (closures, weather, "marathon today, avoid Hauptstraße"). Reads from `data/advisories.json`.

A fourth, simpler tool for the demo:

4. **`get_elder_profile()`** — returns name, important contacts, birthdays, notes the relative entered. Reads from `data/profile.json`.

## System prompt (the personality)

The assistant is:

- **Patient.** Waits, doesn't rush, offers to repeat.
- **Concrete.** Short sentences. Names dates explicitly ("Tuesday the 9th") rather than relative ("in three days").
- **Honest about limits.** If a tool returns nothing, says so. Never invents calendar entries or events.
- **Non-clinical.** Never gives medical advice. If asked about medication or symptoms, repeats only what the relative wrote, and suggests calling the relative or doctor.
- **Warm but not performative.** No "I'm so happy to help you today!". Just helpful.

## Repository layout

```
.
├── PROJECT.md          # this file
├── README.md           # how to run the MVP
├── requirements.txt
├── .env.example
├── app.py              # FastAPI app, Twilio webhooks, Claude loop
├── tools.py            # tool definitions + implementations
├── prompts.py          # system prompt
├── state.py            # per-call conversation state (in-memory dict)
└── data/
    ├── calendar.json
    ├── events.json
    ├── advisories.json
    └── profile.json
```

## How a demo will look

1. Presenter shows the relative UI (or just the JSON files) and adds "Doctor's appointment Thursday 10am, Dr. Weber".
2. Presenter dials the Twilio number from their phone.
3. "Hello, this is your assistant. How can I help?"
4. "What do I have on Thursday?" → assistant calls `get_calendar`, replies "On Thursday the 11th you have a doctor's appointment at 10am with Dr. Weber."
5. "Is there a market this weekend?" → assistant calls `get_city_events`.
6. "Can I walk to the church on Sunday?" → assistant calls `get_route_advisory`, replies with the marathon warning.
7. Hang up.

## Instructions for other agents implementing against this spec

- The webhook contract with Twilio is fixed; don't change the TwiML response shape without testing in a real call.
- All factual answers must come from a tool. The system prompt enforces this; don't loosen it.
- Tools must be safe to call repeatedly and must return structured JSON, not prose.
- Keep per-call state keyed on Twilio `CallSid`. In-memory `dict` is fine for the MVP — do not introduce Redis.
- Do not add medical reasoning. Medical fields are passed through verbatim from what the relative entered.
- If you add a new tool, also add a one-line note to `PROJECT.md` under "Tools exposed to the model".
