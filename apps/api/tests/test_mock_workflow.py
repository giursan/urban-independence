from __future__ import annotations

from dataclasses import dataclass
from itertools import count
from typing import Any

from fastapi.testclient import TestClient

from app.config import settings
from app.main import app
from app.routes import conversations, telegram, voice
from app.routes.telegram import _conversation_id as telegram_conversation_id
from app.routes.voice import _conversation_id as voice_conversation_id


class InMemoryDB:
    def __init__(self) -> None:
        self.rows: dict[str, list[dict[str, Any]]] = {
            "profiles": [
                {
                    "id": settings.dev_user_id,
                    "preferred_name": "Rose",
                    "display_name": "Rose",
                    "locale": "en",
                    "interests": ["gardening"],
                    "life_context": {"family": "Daughter Mia"},
                    "onboarded": True,
                }
            ],
            "conversations": [],
            "messages": [],
            "safety_events": [],
        }
        self._ids = count(1)

    def table(self, name: str):
        return Query(self, name)


class Query:
    def __init__(self, db: InMemoryDB, table: str) -> None:
        self.db = db
        self.table = table
        self.filters: list[tuple[str, Any]] = []
        self.payload: Any = None
        self.action: str = "select"
        self.order_field: str | None = None
        self.order_desc = False
        self.limit_count: int | None = None

    def select(self, *args, **kwargs):
        self.action = "select"
        return self

    def insert(self, payload):
        self.action = "insert"
        self.payload = payload
        return self

    def upsert(self, payload, on_conflict=None):
        self.action = "upsert"
        self.payload = payload
        return self

    def delete(self):
        self.action = "delete"
        return self

    def eq(self, field: str, value):
        self.filters.append((field, value))
        return self

    def order(self, field: str, desc: bool = False):
        self.order_field = field
        self.order_desc = desc
        return self

    def limit(self, count: int):
        self.limit_count = count
        return self

    def execute(self):
        rows = self.db.rows.setdefault(self.table, [])
        if self.action == "insert":
            payloads = self.payload if isinstance(self.payload, list) else [self.payload]
            inserted = [self._with_defaults(dict(payload)) for payload in payloads]
            rows.extend(inserted)
            return Result(inserted)
        if self.action == "upsert":
            payload = self._with_defaults(dict(self.payload))
            existing = next((row for row in rows if row.get("id") == payload.get("id")), None)
            if existing:
                existing.update(payload)
                return Result([existing])
            rows.append(payload)
            return Result([payload])
        if self.action == "delete":
            kept = [row for row in rows if not self._matches(row)]
            deleted = [row for row in rows if self._matches(row)]
            self.db.rows[self.table] = kept
            return Result(deleted)

        selected = [row for row in rows if self._matches(row)]
        if self.order_field:
            selected.sort(
                key=lambda row: row.get(self.order_field) or "",
                reverse=self.order_desc,
            )
        if self.limit_count is not None:
            selected = selected[: self.limit_count]
        return Result([dict(row) for row in selected])

    def _matches(self, row: dict[str, Any]) -> bool:
        return all(row.get(field) == value for field, value in self.filters)

    def _with_defaults(self, row: dict[str, Any]) -> dict[str, Any]:
        n = next(self.db._ids)
        row.setdefault("id", f"{self.table}-{n}")
        if self.table == "conversations":
            row.setdefault("started_at", f"2026-06-07T10:{n:02d}:00+00:00")
        if self.table == "messages":
            row.setdefault("created_at", f"2026-06-07T10:{n:02d}:30+00:00")
        return row


@dataclass
class Result:
    data: list[dict[str, Any]]


class FakeMemory:
    async def recall(self, query: str, k: int = 5) -> list[dict]:
        return [{"content": "Rose's daughter is Mia"}] if query else []

    async def save(self, content: str, kind: str = "fact", salience: float = 0.6) -> None:
        return None


class FakeAgent:
    async def run(self, prompt: str, **kwargs):
        mode = kwargs["deps"].mode
        if mode == "phone":
            text = "Phone reply: I can help you think that through."
        elif mode == "telegram":
            text = "Telegram reply: I remember Mia and can help."
        else:
            text = "Companion reply."
        return type("RunResult", (), {"output": text})()


def test_mock_transport_workflow(monkeypatch):
    db = InMemoryDB()
    sent_telegram: list[tuple[str | int, str]] = []

    def fake_user_client(token: str):
        return db

    async def fake_send_message(chat_id: str | int, text: str):
        sent_telegram.append((chat_id, text))
        return {"ok": True, "chat_id": chat_id, "message_id": len(sent_telegram)}

    for module in (voice, telegram, conversations):
        monkeypatch.setattr(module, "user_client", fake_user_client)
    monkeypatch.setattr(voice, "MemoryService", lambda *args, **kwargs: FakeMemory())
    monkeypatch.setattr(telegram, "MemoryService", lambda *args, **kwargs: FakeMemory())
    monkeypatch.setattr(voice, "companion_agent", FakeAgent())
    monkeypatch.setattr(telegram, "companion_agent", FakeAgent())
    monkeypatch.setattr(telegram, "send_message", fake_send_message)

    client = TestClient(app)

    phone = client.post(
        "/voice/turn",
        content="CallSid=CA-MOCK&SpeechResult=I%20miss%20Mia",
        headers={"content-type": "application/x-www-form-urlencoded"},
    )
    assert phone.status_code == 200
    assert "Phone reply" in phone.text

    tg = client.post(
        "/telegram/webhook",
        json={
            "update_id": 10,
            "message": {
                "message_id": 5,
                "chat": {"id": 999},
                "from": {"first_name": "Rose"},
                "text": "Can you help me remember Mia?",
            },
        },
    )
    assert tg.status_code == 200
    assert sent_telegram == [("999", "Telegram reply: I remember Mia and can help.")]

    listed = client.get("/conversations")
    assert listed.status_code == 200
    sessions = listed.json()
    assert {session["mode"] for session in sessions} == {"phone", "telegram"}
    assert any("Phone reply" in (session["last_message"] or "") for session in sessions)
    assert any("Telegram reply" in (session["last_message"] or "") for session in sessions)

    phone_messages = client.get(f"/conversations/{voice_conversation_id('CA-MOCK')}/messages")
    assert [m["role"] for m in phone_messages.json()] == ["user", "assistant"]
    assert phone_messages.json()[0]["content"] == "I miss Mia"

    telegram_id = telegram_conversation_id("999")
    deleted = client.delete(f"/conversations/{telegram_id}")
    assert deleted.status_code == 200
    remaining = client.get("/conversations").json()
    assert [session["mode"] for session in remaining] == ["phone"]
