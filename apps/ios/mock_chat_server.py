"""Tiny stand-in for the real backend's POST /chat, for iOS app verification.

This is NOT the companion. It emits the same Vercel AI SDK v6 data-stream (SSE)
the real backend speaks, with a canned reply, so the iOS app's full path —
request -> SSE parse -> chat bubble -> text-to-speech — can be exercised without
OpenAI or Supabase credentials. Stdlib only.

    python3 apps/ios/mock_chat_server.py    # serves http://localhost:8000
"""
from __future__ import annotations

import json
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


def _last_user_text(body: dict) -> str:
    for msg in reversed(body.get("messages", []) or []):
        if msg.get("role") != "user":
            continue
        parts = msg.get("parts") or []
        texts = [p.get("text", "") for p in parts if p.get("type") == "text"]
        if any(texts):
            return " ".join(t for t in texts if t).strip()
    return ""


def _reply_for(user_text: str) -> str:
    if user_text:
        return (
            f"It's lovely to hear from you. You said: \"{user_text}\". "
            "I'm doing well, thank you for asking. "
            "How has your day in Hong Kong been so far?"
        )
    return "Hello! I'm your companion. How are you feeling today?"


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):  # quieter console
        pass

    def do_GET(self):
        if self.path == "/health":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"ok": true, "mock": true}')
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        if self.path != "/chat":
            self.send_response(404)
            self.end_headers()
            return

        length = int(self.headers.get("Content-Length", 0))
        try:
            body = json.loads(self.rfile.read(length) or b"{}")
        except json.JSONDecodeError:
            body = {}

        reply = _reply_for(_last_user_text(body))

        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "keep-alive")
        self.end_headers()

        def emit(obj: dict) -> None:
            self.wfile.write(f"data: {json.dumps(obj)}\n\n".encode())
            self.wfile.flush()

        emit({"type": "start"})
        emit({"type": "start-step"})
        emit({"type": "text-start", "id": "0"})
        for word in reply.split(" "):
            emit({"type": "text-delta", "id": "0", "delta": word + " "})
            time.sleep(0.06)  # simulate token streaming
        emit({"type": "text-end", "id": "0"})
        emit({"type": "finish-step"})
        emit({"type": "finish"})
        self.wfile.write(b"data: [DONE]\n\n")
        self.wfile.flush()


if __name__ == "__main__":
    print("Mock /chat (SSE) on http://localhost:8000  —  NOT the real companion")
    ThreadingHTTPServer(("127.0.0.1", 8000), Handler).serve_forever()
