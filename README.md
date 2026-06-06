# Urban Independence — MVP

Phone-call assistant for elderly people. See [PROJECT.md](./PROJECT.md) for the full concept.

## Run locally

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # then fill in TWILIO_AUTH_TOKEN, TWILIO_PHONE_NUMBER, ANTHROPIC_API_KEY
uvicorn app:app --reload --port 8000
```

In a second terminal:

```bash
ngrok http 8000
```

Copy the `https://....ngrok.app` URL ngrok prints.

## Wire up Twilio

1. Buy or claim a phone number in the Twilio Console.
2. Open the number's settings → **Voice & Fax** → "A call comes in".
3. Set it to **Webhook**, `POST`, URL = `https://YOUR_NGROK_URL/voice`.
4. Save.

Dial the number from your phone. You should hear the assistant greet you. Try:

- "What do I have on Thursday?"
- "Is there a market this weekend?"
- "Can I walk to the city centre on the 14th?"
- "When is Lena's birthday?"

## Editing the fake data

The four JSON files in `data/` are the world. Edit them and reload — no restart needed (they're read on every tool call).

- `data/calendar.json` — the elder's appointments
- `data/events.json` — public city events
- `data/advisories.json` — closures, weather, route warnings
- `data/profile.json` — name, family contacts, birthdays, notes from family

## Notes

- State is in-memory and keyed on `CallSid`. Restarting the server drops all in-flight calls — fine for the hackathon.
- Medical content is intentionally stubbed. See `PROJECT.md` for why.
- Latency per turn is ~2s (Twilio `<Gather>` + Claude). Upgrade path to Twilio ConversationRelay documented in `PROJECT.md`.
