"""Database helpers for conversations, transcript persistence, and safety events.
All calls use the user-scoped Supabase client, so RLS applies as the caller."""
from __future__ import annotations

from typing import Any

from pydantic_ai.messages import (
    ModelRequest,
    ModelResponse,
    TextPart,
    UserPromptPart,
)

from .models import Profile
from .safety import CrisisAssessment


def fetch_profile(db: Any, user_id: str) -> Profile:
    res = db.table("profiles").select("*").eq("id", user_id).limit(1).execute()
    if res.data:
        row = res.data[0]
        return Profile(
            id=user_id,
            display_name=row.get("display_name"),
            preferred_name=row.get("preferred_name"),
            locale=row.get("locale") or "en",
            interests=row.get("interests") or [],
            life_context=row.get("life_context") or {},
        )
    return Profile(id=user_id)


def get_or_create_conversation(db: Any, user_id: str, conversation_id: str | None, mode: str) -> str:
    if conversation_id:
        db.table("conversations").upsert(
            {"id": conversation_id, "user_id": user_id, "mode": mode},
            on_conflict="id",
        ).execute()
        return conversation_id
    res = db.table("conversations").insert({"user_id": user_id, "mode": mode}).execute()
    return res.data[0]["id"]


def _rows_from_messages(messages: list[Any]) -> list[tuple[str, str]]:
    rows: list[tuple[str, str]] = []
    for msg in messages:
        if isinstance(msg, ModelRequest):
            for part in msg.parts:
                if isinstance(part, UserPromptPart) and isinstance(part.content, str):
                    if part.content.strip():
                        rows.append(("user", part.content))
        elif isinstance(msg, ModelResponse):
            text = "".join(p.content for p in msg.parts if isinstance(p, TextPart))
            if text.strip():
                rows.append(("assistant", text))
    return rows


def persist_user_message(db: Any, conversation_id: str, user_id: str, text: str) -> None:
    """Persist the newest user turn.

    The Vercel AI adapter loads incoming messages as history, so the user prompt
    never appears in `result.new_messages()` — we must store it explicitly or the
    transcript ends up one-sided (assistant only)."""
    if not text or not text.strip():
        return
    db.table("messages").insert(
        {
            "conversation_id": conversation_id,
            "user_id": user_id,
            "role": "user",
            "content": text,
        }
    ).execute()


def persist_new_messages(db: Any, conversation_id: str, user_id: str, messages: list[Any]) -> None:
    rows = _rows_from_messages(messages)
    if not rows:
        return
    db.table("messages").insert(
        [
            {
                "conversation_id": conversation_id,
                "user_id": user_id,
                "role": role,
                "content": content,
            }
            for role, content in rows
        ]
    ).execute()


def log_safety_event(
    db: Any, user_id: str, conversation_id: str | None, assessment: CrisisAssessment
) -> None:
    db.table("safety_events").insert(
        {
            "user_id": user_id,
            "conversation_id": conversation_id,
            "severity": assessment.severity,
            "category": assessment.category,
            "excerpt": assessment.excerpt,
        }
    ).execute()
