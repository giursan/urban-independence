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
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class Store:
    def __init__(self, path: str | Path = "data/sessions.db") -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._conn() as c:
            c.executescript(SCHEMA)

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
