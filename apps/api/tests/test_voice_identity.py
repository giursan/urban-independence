"""Phone-call identity verification: known-number bypass, the name + security
question challenge for unknown numbers, and the failure path."""
from __future__ import annotations

from itertools import count
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app import identity
from app.main import app
from app.routes import voice

FORM = {"content-type": "application/x-www-form-urlencoded"}


# --- A small in-memory Supabase stand-in that honours on_conflict upserts -----

class _Query:
    def __init__(self, db: "FakeDB", table: str) -> None:
        self.db = db
        self.table_name = table
        self.action = "select"
        self.payload: Any = None
        self.on_conflict: str | None = None
        self.filters: list[tuple[str, Any]] = []
        self.order_field: str | None = None
        self.limit_count: int | None = None

    def select(self, *a, **k):
        self.action = "select"
        return self

    def insert(self, payload):
        self.action, self.payload = "insert", payload
        return self

    def upsert(self, payload, on_conflict=None):
        self.action, self.payload, self.on_conflict = "upsert", payload, on_conflict
        return self

    def delete(self):
        self.action = "delete"
        return self

    def eq(self, field, value):
        self.filters.append((field, value))
        return self

    def order(self, field, desc=False):
        self.order_field = field
        return self

    def limit(self, n):
        self.limit_count = n
        return self

    def _matches(self, row):
        return all(row.get(f) == v for f, v in self.filters)

    def execute(self):
        rows = self.db.rows.setdefault(self.table_name, [])
        if self.action == "insert":
            items = self.payload if isinstance(self.payload, list) else [self.payload]
            new = [self._defaults(dict(it)) for it in items]
            rows.extend(new)
            return _Result(new)
        if self.action == "upsert":
            payload = dict(self.payload)
            key = self.on_conflict or "id"
            existing = next((r for r in rows if r.get(key) == payload.get(key)), None)
            if existing:
                existing.update(payload)
                return _Result([existing])
            rows.append(self._defaults(payload))
            return _Result([rows[-1]])
        if self.action == "delete":
            kept = [r for r in rows if not self._matches(r)]
            removed = [r for r in rows if self._matches(r)]
            self.db.rows[self.table_name] = kept
            return _Result(removed)
        selected = [r for r in rows if self._matches(r)]
        if self.order_field:
            selected.sort(key=lambda r: r.get(self.order_field) or "")
        if self.limit_count is not None:
            selected = selected[: self.limit_count]
        return _Result([dict(r) for r in selected])

    def _defaults(self, row):
        n = next(self.db._ids)
        row.setdefault("id", f"{self.table_name}-{n}")
        if self.table_name == "messages":
            row.setdefault("created_at", f"2026-06-07T10:{n:02d}:00+00:00")
        return row


class _Result:
    def __init__(self, data):
        self.data = data


class FakeDB:
    def __init__(self) -> None:
        self.rows: dict[str, list[dict]] = {}
        self._ids = count(1)

    def table(self, name):
        return _Query(self, name)


class FakeMemory:
    async def recall(self, query, k=5):
        return []

    async def save(self, content, kind="fact", salience=0.6):
        return None


class FakeAgent:
    def __init__(self):
        self.calls = 0

    async def run(self, prompt, **kwargs):
        self.calls += 1
        return type("R", (), {"output": "Hello there, lovely to hear from you."})()


def _wire(monkeypatch, db, agent):
    monkeypatch.setattr(voice, "user_client", lambda token: db)
    monkeypatch.setattr(voice, "MemoryService", lambda *a, **k: FakeMemory())
    monkeypatch.setattr(voice, "companion_agent", agent)


def _profile(db, user_id, display_name, preferred_name=None):
    db.rows.setdefault("profiles", []).append(
        {
            "id": user_id,
            "display_name": display_name,
            "preferred_name": preferred_name,
            "locale": "en",
            "interests": [],
            "life_context": {},
            "onboarded": True,
        }
    )


# --- Unit: normalization + answer hashing ------------------------------------

def test_normalize_is_robust_to_noisy_speech():
    assert identity.normalize("  The Blue! ") == identity.normalize("blue")
    assert identity.normalize("José") == "jose"
    assert identity.normalize_phone("+1 (555) 555-0100") == "15555550100"


def test_verify_answer_round_trips():
    h = identity.hash_answer("Fluffy")
    assert identity.verify_answer("  fluffy ", h)
    assert not identity.verify_answer("rex", h)


# --- Known number → straight through, no challenge ---------------------------

def test_known_number_skips_challenge(monkeypatch):
    db = FakeDB()
    agent = FakeAgent()
    _wire(monkeypatch, db, agent)
    user_id = "11111111-1111-1111-1111-111111111111"
    _profile(db, user_id, "Margaret Lee")
    db.rows.setdefault("caller_phone_numbers", []).append(
        {"phone": "15555550100", "user_id": user_id, "verified": True}
    )

    client = TestClient(app)
    res = client.post("/voice", content="CallSid=CK1&From=%2B15555550100", headers=FORM)

    assert res.status_code == 200
    assert "<Gather" in res.text  # greeted and listening, not hung up
    assert agent.calls == 1  # companion ran as the identified user
    session = identity.get_call_session(db, "CK1")
    assert session["stage"] == identity.VERIFIED
    assert session["verified_user_id"] == user_id


# --- Unknown number → name + security question → verified --------------------

def test_unknown_number_name_and_question_flow(monkeypatch):
    db = FakeDB()
    agent = FakeAgent()
    _wire(monkeypatch, db, agent)
    user_id = "22222222-2222-2222-2222-222222222222"
    _profile(db, user_id, "Margaret Lee")
    db.rows.setdefault("security_questions", []).append(
        {
            "id": "sq1",
            "user_id": user_id,
            "question": "What is your first pet's name?",
            "answer_hash": identity.hash_answer("Fluffy"),
            "created_by": "onboarding",
            "created_at": "2026-01-01T00:00:00+00:00",
        }
    )

    client = TestClient(app)

    # 1) Unknown caller is asked for a name, no companion run yet.
    setup = client.post("/voice", content="CallSid=CK2&From=%2B19998887777", headers=FORM)
    assert "first and last name" in setup.text
    assert agent.calls == 0

    # 2) Spoken name resolves and we get the security question.
    named = client.post(
        "/voice/turn",
        content="CallSid=CK2&From=%2B19998887777&SpeechResult=Margaret%20Lee",
        headers=FORM,
    )
    assert "first pet" in named.text
    assert agent.calls == 0
    assert identity.get_call_session(db, "CK2")["stage"] == identity.AWAIT_SECURITY_ANSWER

    # 3) Correct answer → verified, greeted, and the number is remembered.
    answered = client.post(
        "/voice/turn",
        content="CallSid=CK2&From=%2B19998887777&SpeechResult=Fluffy",
        headers=FORM,
    )
    assert answered.status_code == 200
    assert "<Gather" in answered.text
    assert agent.calls == 1
    assert identity.get_call_session(db, "CK2")["stage"] == identity.VERIFIED
    assert identity.find_user_by_phone(db, "+19998887777") == user_id


def test_wrong_answer_hangs_up_and_logs(monkeypatch):
    db = FakeDB()
    agent = FakeAgent()
    _wire(monkeypatch, db, agent)
    user_id = "33333333-3333-3333-3333-333333333333"
    _profile(db, user_id, "Margaret Lee")
    db.rows.setdefault("security_questions", []).append(
        {
            "id": "sq1",
            "user_id": user_id,
            "question": "What is your first pet's name?",
            "answer_hash": identity.hash_answer("Fluffy"),
            "created_by": "onboarding",
            "created_at": "2026-01-01T00:00:00+00:00",
        }
    )

    client = TestClient(app)
    client.post("/voice", content="CallSid=CK3&From=%2B15550000000", headers=FORM)
    client.post(
        "/voice/turn",
        content="CallSid=CK3&From=%2B15550000000&SpeechResult=Margaret%20Lee",
        headers=FORM,
    )

    last = None
    for _ in range(identity.MAX_ATTEMPTS):
        last = client.post(
            "/voice/turn",
            content="CallSid=CK3&From=%2B15550000000&SpeechResult=Rex",
            headers=FORM,
        )

    assert "<Hangup" in last.text
    assert agent.calls == 0  # private companion never reached
    assert identity.get_call_session(db, "CK3")["stage"] == identity.FAILED
    assert db.rows.get("safety_events"), "a failed-verification event should be logged"
