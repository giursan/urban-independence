"""Streaming chat endpoint.

The frontend talks to this with the Vercel AI SDK `useChat` hook. Pydantic AI's
`VercelAIAdapter` handles the AI-SDK data-stream protocol (sdk_version=6); we
inject per-user `deps`, run a safety screen on the newest message, and persist
the transcript via `on_complete`.
"""
from __future__ import annotations

import json

from fastapi import APIRouter, Depends, Request
from pydantic_ai.ui.vercel_ai import VercelAIAdapter

from ..auth import AuthedUser, current_user
from ..companion import companion_agent
from ..config import settings
from ..deps import CompanionDeps
from ..memory import MemoryService
from ..persistence import (
    fetch_profile,
    get_or_create_conversation,
    log_safety_event,
    persist_new_messages,
    persist_user_message,
)
from ..safety import screen_text
from ..supabase_client import user_client

router = APIRouter()


def _last_user_text(messages: list[dict]) -> str:
    """Extract the newest user message text from AI SDK UIMessages."""
    for msg in reversed(messages or []):
        if msg.get("role") != "user":
            continue
        parts = msg.get("parts")
        if isinstance(parts, list):
            texts = [p.get("text", "") for p in parts if isinstance(p, dict) and p.get("type") == "text"]
            if any(texts):
                return " ".join(t for t in texts if t).strip()
        if isinstance(msg.get("content"), str):
            return msg["content"].strip()
    return ""


@router.post("/chat")
async def chat(request: Request, user: AuthedUser = Depends(current_user)):
    raw = await request.body()
    try:
        body = json.loads(raw)
    except json.JSONDecodeError:
        body = {}

    messages = body.get("messages", [])
    conversation_id = body.get("conversation_id") or body.get("id")
    mode = body.get("mode", "companion")
    last_user = _last_user_text(messages)

    db = user_client(user.token)
    profile = fetch_profile(db, user.id)
    conversation_id = get_or_create_conversation(db, user.id, conversation_id, mode)

    # Persist the user's turn now: the adapter loads it as history, so it won't
    # appear in result.new_messages() (which carries only the assistant reply).
    persist_user_message(db, conversation_id, user.id, last_user)

    # Best-effort crisis screen on the newest user message.
    assessment = screen_text(last_user)
    if assessment:
        log_safety_event(db, user.id, conversation_id, assessment)

    deps = CompanionDeps(
        user_id=user.id,
        profile=profile,
        mode=mode,
        db=db,
        memory=MemoryService(db, user.id),
        last_user_text=last_user,
        conversation_id=conversation_id,
    )

    async def on_complete(result) -> None:
        persist_new_messages(db, conversation_id, user.id, result.new_messages())

    return await VercelAIAdapter.dispatch_request(
        request,
        agent=companion_agent,
        deps=deps,
        conversation_id=conversation_id,
        sdk_version=6,
        model=settings.model_str,
        on_complete=on_complete,
    )
