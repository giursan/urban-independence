# UGREEN NAS deployment

This deployment runs four containers:

- `api`: FastAPI companion backend on the Docker network.
- `web`: Next.js standalone server on the Docker network.
- `gateway`: Caddy reverse proxy. It serves the web app and forwards API paths.
- `ngrok`: public HTTPS tunnel to the gateway.

This uses ngrok's normal free dynamic tunnel by default. The URL changes whenever
ngrok restarts, so Supabase redirects, the iPhone app, Telegram, and Twilio need
to be updated after each new tunnel URL.

## 1. Prepare env

On the NAS:

```bash
cd deploy
cp .env.example .env
```

Fill `deploy/.env` with real values. Set:

```bash
NGROK_AUTHTOKEN=...
```

After startup, get the generated ngrok URL:

```bash
docker compose -f deploy/compose.yml --env-file deploy/.env logs ngrok
```

Look for `url=https://...ngrok-free.app`. Use that URL as `PUBLIC_ORIGIN`.

For Supabase auth, add the same ngrok URL in the Supabase dashboard:

- Authentication -> URL Configuration -> Site URL
- Authentication -> URL Configuration -> Redirect URLs

## 2. Start

From the repo root:

```bash
docker compose -f deploy/compose.yml --env-file deploy/.env up -d --build
```

Then check:

```bash
docker compose -f deploy/compose.yml --env-file deploy/.env ps
curl http://localhost:${GATEWAY_PORT:-8088}/health
```

Open the ngrok URL in a browser. The web app uses same-origin API calls, so `/chat`,
`/voice`, `/telegram/webhook`, and the share/report endpoints are all served through
the same ngrok URL.

## 3. iPhone app

Point the iOS app at the ngrok URL:

```swift
static let apiBaseURL = URL(string: "https://your-generated-url.ngrok-free.app")!
```

Because this is HTTPS, you do not need LAN IPs or local-network exceptions for normal use.

## 4. Optional webhooks

Telegram webhook:

```bash
curl "https://api.telegram.org/bot$TELEGRAM_BOT_TOKEN/setWebhook" \
  -d "url=https://your-generated-url.ngrok-free.app/telegram/webhook" \
  -d "secret_token=$TELEGRAM_WEBHOOK_SECRET"
```

Twilio Voice webhook:

```text
POST https://your-generated-url.ngrok-free.app/voice
```

## 5. Update

After pulling new code on the NAS:

```bash
docker compose -f deploy/compose.yml --env-file deploy/.env up -d --build
```
