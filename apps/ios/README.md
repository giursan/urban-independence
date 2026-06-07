# Aporia — iOS app

A native SwiftUI client for the Aporia backend (`apps/api`). Single-screen,
streaming text chat, designed with large type for older users.

## What it does

- One chat screen that talks to `POST /chat` on the FastAPI backend.
- Streams the assistant reply token-by-token by parsing the backend's
  **Vercel AI SDK v6 data-stream (SSE)** protocol — the same wire format the
  Next.js web app consumes.
- Generates a per-session `conversation_id` (a UUID); the backend upserts a
  conversation row for it, so transcripts land in Supabase like the web client.

Scope is intentionally a **chat-only MVP**. Conversation history, reports, and
voice exist in the backend but are not wired into this app yet.

## Requirements

- Xcode 16+ (built against Xcode 26.3) and the iOS Simulator.
- [XcodeGen](https://github.com/yonsm/XcodeGen) (`brew install xcodegen`) — the
  `.xcodeproj` is generated, not committed.

## Run

1. **Start the backend** (in `apps/api`):

   ```bash
   uv run uvicorn app.main:app --reload   # serves http://localhost:8000
   ```

   Auth is disabled in the backend, so no sign-in/token is needed — every
   request acts as the fixed dev user.

2. **Generate and open the Xcode project** (in `apps/ios`):

   ```bash
   xcodegen generate
   open Aporia.xcodeproj
   ```

   Then pick an iPhone simulator and press Run. Or from the CLI:

   ```bash
   xcodebuild -project Aporia.xcodeproj -scheme Aporia \
     -sdk iphonesimulator -destination 'platform=iOS Simulator,name=iPhone 17 Pro' build
   ```

## Configuration

`CompanionApp/AppConfig.swift` holds the single base URL:

```swift
static let apiBaseURL = URL(string: "http://localhost:8000")!
```

- **Simulator:** `localhost` reaches the Mac host, so the default works.
- **Physical device:** change it to your Mac's LAN IP (e.g.
  `http://192.168.1.20:8000`) and add that host to `NSAppTransportSecurity` in
  `Info.plist` — `NSAllowsLocalNetworking` only covers loopback/.local.

## Files

| File | Purpose |
|---|---|
| `CompanionApp.swift` | App entry / navigation shell. |
| `ChatView.swift` | The chat UI (bubbles, composer, autoscroll). |
| `ChatViewModel.swift` | Conversation state; drives streaming turns. |
| `ChatService.swift` | POSTs to `/chat`, parses the AI-SDK SSE stream into text deltas. |
| `Models.swift` | `ChatMessage`. |
| `AppConfig.swift` | Base URL + conversation mode. |
| `project.yml` | XcodeGen spec. |
