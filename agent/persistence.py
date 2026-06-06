from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

SCHEMA = """
CREATE TABLE IF NOT EXISTS sessions (
    id              TEXT PRIMARY KEY,
    elder_id        TEXT NOT NULL,
    started_at      TEXT NOT NULL,
    ended_at        TEXT,
    status          TEXT NOT NULL,
    context_json    TEXT,
    scenario_json   TEXT,
    summary         TEXT
);

CREATE TABLE IF NOT EXISTS turns (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id      TEXT NOT NULL,
    ts              TEXT NOT NULL,
    phase           TEXT NOT NULL,
    role            TEXT NOT NULL,
    content         TEXT,
    tool_calls_json TEXT,
    usage_json      TEXT,
    FOREIGN KEY(session_id) REFERENCES sessions(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_turns_session ON turns(session_id);
CREATE INDEX IF NOT EXISTS idx_sessions_elder ON sessions(elder_id, started_at);

CREATE TABLE IF NOT EXISTS telegram_accounts (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    chat_id     INTEGER UNIQUE,
    role        TEXT NOT NULL CHECK(role IN ('elder', 'caregiver')),
    elder_id    TEXT NOT NULL,
    username    TEXT,
    first_name  TEXT,
    phone       TEXT,
    linked_at   TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_tg_elder_role ON telegram_accounts(elder_id, role);
CREATE INDEX IF NOT EXISTS idx_tg_phone ON telegram_accounts(phone);
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class Store:
    def __init__(self, path: str | Path = "data/sessions.db") -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._conn() as c:
            self._migrate_telegram_accounts(c)
            c.executescript(SCHEMA)

    @staticmethod
    def _migrate_telegram_accounts(conn: sqlite3.Connection) -> None:
        """Old schema had chat_id as PK NOT NULL; new one needs it nullable + a phone
        column. If the legacy shape exists, drop and let CREATE rebuild it."""
        row = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='telegram_accounts'"
        ).fetchone()
        if not row:
            return
        cols = {r["name"]: r for r in conn.execute("PRAGMA table_info(telegram_accounts)").fetchall()}
        if "id" not in cols or "phone" not in cols:
            conn.execute("DROP TABLE telegram_accounts")

    @contextmanager
    def _conn(self):
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def create_session(self, elder_id: str) -> str:
        sid = f"sess_{uuid4().hex[:12]}"
        with self._conn() as c:
            c.execute(
                "INSERT INTO sessions (id, elder_id, started_at, status) VALUES (?, ?, ?, ?)",
                (sid, elder_id, _now(), "active"),
            )
        return sid

    def set_context(self, session_id: str, context: dict[str, Any]) -> None:
        with self._conn() as c:
            c.execute(
                "UPDATE sessions SET context_json = ? WHERE id = ?",
                (json.dumps(context, default=str), session_id),
            )

    def set_scenario(self, session_id: str, scenario: dict[str, Any]) -> None:
        with self._conn() as c:
            c.execute(
                "UPDATE sessions SET scenario_json = ? WHERE id = ?",
                (json.dumps(scenario, default=str), session_id),
            )

    def add_turn(
        self,
        session_id: str,
        *,
        phase: str,
        role: str,
        content: str | None = None,
        tool_calls: list[dict] | None = None,
        usage: dict | None = None,
    ) -> None:
        with self._conn() as c:
            c.execute(
                "INSERT INTO turns (session_id, ts, phase, role, content, tool_calls_json, usage_json) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    session_id,
                    _now(),
                    phase,
                    role,
                    content,
                    json.dumps(tool_calls, default=str) if tool_calls else None,
                    json.dumps(usage, default=str) if usage else None,
                ),
            )

    def end_session(self, session_id: str, status: str = "completed", summary: str | None = None) -> None:
        with self._conn() as c:
            c.execute(
                "UPDATE sessions SET ended_at = ?, status = ?, summary = ? WHERE id = ?",
                (_now(), status, summary, session_id),
            )

    def get_session(self, session_id: str) -> dict | None:
        with self._conn() as c:
            row = c.execute("SELECT * FROM sessions WHERE id = ?", (session_id,)).fetchone()
            return dict(row) if row else None

    def get_turns(self, session_id: str) -> list[dict]:
        with self._conn() as c:
            rows = c.execute(
                "SELECT * FROM turns WHERE session_id = ? ORDER BY id ASC",
                (session_id,),
            ).fetchall()
            return [dict(r) for r in rows]

    # ── telegram_accounts ──────────────────────────────────────────────

    def link_telegram(
        self,
        chat_id: int,
        role: str,
        elder_id: str,
        username: str | None = None,
        first_name: str | None = None,
        phone: str | None = None,
    ) -> None:
        """Link or update a real Telegram chat. If a pre-registered family member exists
        for the same (elder_id, phone), upgrade that row with the chat_id."""
        if role not in {"elder", "caregiver"}:
            raise ValueError(f"role must be 'elder' or 'caregiver', got {role!r}")
        with self._conn() as c:
            existing = None
            if phone:
                existing = c.execute(
                    "SELECT id FROM telegram_accounts WHERE elder_id = ? AND phone = ? AND chat_id IS NULL",
                    (elder_id, phone),
                ).fetchone()
            if existing:
                c.execute(
                    "UPDATE telegram_accounts SET chat_id=?, role=?, username=?, "
                    "first_name=?, linked_at=? WHERE id=?",
                    (chat_id, role, username, first_name, _now(), existing["id"]),
                )
            else:
                c.execute(
                    "INSERT INTO telegram_accounts (chat_id, role, elder_id, username, first_name, phone, linked_at) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?) "
                    "ON CONFLICT(chat_id) DO UPDATE SET "
                    "  role=excluded.role, elder_id=excluded.elder_id, "
                    "  username=excluded.username, first_name=excluded.first_name, "
                    "  phone=COALESCE(excluded.phone, telegram_accounts.phone), "
                    "  linked_at=excluded.linked_at",
                    (chat_id, role, elder_id, username, first_name, phone, _now()),
                )

    def register_family_member(
        self,
        elder_id: str,
        phone: str,
        first_name: str | None = None,
        username: str | None = None,
        role: str = "caregiver",
    ) -> int:
        """Pre-register a family member by phone before they've connected via Telegram.
        Returns the row id. Idempotent on (elder_id, phone)."""
        if role not in {"elder", "caregiver"}:
            raise ValueError(f"role must be 'elder' or 'caregiver', got {role!r}")
        with self._conn() as c:
            existing = c.execute(
                "SELECT id FROM telegram_accounts WHERE elder_id = ? AND phone = ?",
                (elder_id, phone),
            ).fetchone()
            if existing:
                c.execute(
                    "UPDATE telegram_accounts SET role=?, first_name=?, username=?, linked_at=? WHERE id=?",
                    (role, first_name, username, _now(), existing["id"]),
                )
                return int(existing["id"])
            cur = c.execute(
                "INSERT INTO telegram_accounts (chat_id, role, elder_id, username, first_name, phone, linked_at) "
                "VALUES (NULL, ?, ?, ?, ?, ?, ?)",
                (role, elder_id, username, first_name, phone, _now()),
            )
            return int(cur.lastrowid)

    def unlink_telegram(self, chat_id: int) -> None:
        with self._conn() as c:
            c.execute("DELETE FROM telegram_accounts WHERE chat_id = ?", (chat_id,))

    def get_telegram_account(self, chat_id: int) -> dict | None:
        with self._conn() as c:
            row = c.execute(
                "SELECT * FROM telegram_accounts WHERE chat_id = ?", (chat_id,)
            ).fetchone()
            return dict(row) if row else None

    def list_family_members(self, elder_id: str) -> list[dict]:
        with self._conn() as c:
            rows = c.execute(
                "SELECT * FROM telegram_accounts WHERE elder_id = ? ORDER BY role, linked_at",
                (elder_id,),
            ).fetchall()
            return [dict(r) for r in rows]

    def get_caregiver_chat_id(self, elder_id: str) -> int | None:
        """Return the chat_id of the most recently linked caregiver for an elder.
        Only returns rows where chat_id is set (i.e. they've actually connected)."""
        with self._conn() as c:
            row = c.execute(
                "SELECT chat_id FROM telegram_accounts "
                "WHERE elder_id = ? AND role = 'caregiver' AND chat_id IS NOT NULL "
                "ORDER BY linked_at DESC LIMIT 1",
                (elder_id,),
            ).fetchone()
            return int(row["chat_id"]) if row else None

    def list_sessions(self, elder_id: str | None = None, limit: int = 50) -> list[dict]:
        with self._conn() as c:
            if elder_id:
                rows = c.execute(
                    "SELECT * FROM sessions WHERE elder_id = ? ORDER BY started_at DESC LIMIT ?",
                    (elder_id, limit),
                ).fetchall()
            else:
                rows = c.execute(
                    "SELECT * FROM sessions ORDER BY started_at DESC LIMIT ?", (limit,)
                ).fetchall()
            return [dict(r) for r in rows]
