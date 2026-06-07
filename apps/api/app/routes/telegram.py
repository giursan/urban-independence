"""Telegram webhook transport backed by the companion conversation engine."""
from __future__ import annotations

from typing import Any
from uuid import NAMESPACE_URL, uuid5

from fastapi import APIRouter, HTTPException, Request

from ..companion import companion_agent
from ..config import settings
from ..deps import CompanionDeps
from ..memory import MemoryService
from ..persistence import (
    fetch_model_history,
    fetch_profile,
    get_or_create_conversation,
    log_safety_event,
    persist_assistant_message,
    persist_user_message,
)
from ..safety import screen_text
from ..sources.telegram import send_message
from ..supabase_client import user_client

router = APIRouter()

HELP_TEXT = (
    "I'm here. Send me a message and I'll reply here.\n\n"
    "/new starts a fresh conversation.\n"
    "/help shows this message."
)


def _conversation_id(chat_id: str | int) -> str:
    return str(uuid5(NAMESPACE_URL, f"telegram-chat:{chat_id}"))


def _message_from_update(update: dict[str, Any]) -> dict[str, Any] | None:
    return update.get("message") or update.get("edited_message")


def _chat_id(message: dict[str, Any]) -> str:
    return str((message.get("chat") or {}).get("id") or "")


def _text(message: dict[str, Any]) -> str:
    return (message.get("text") or "").strip()


def _sender_name(message: dict[str, Any]) -> str | None:
    sender = message.get("from") or {}
    return sender.get("first_name") or sender.get("username")


def _response_text(text: str) -> str:
    cleaned = " ".join((text or "").split())
    if not cleaned:
        return "I'm here with you. Could you say that another way?"
    return cleaned[:3900]


def _authorized(request: Request) -> bool:
    if not settings.telegram_webhook_secret:
        return True
    return (
        request.headers.get("x-telegram-bot-api-secret-token")
        == settings.telegram_webhook_secret
    )


async def _run_telegram_turn(
    *,
    user_text: str,
    conversation_id: str,
    sender_name: str | None,
) -> str:
    user_id = settings.dev_user_id
    db = user_client("")
    conversation_id = get_or_create_conversation(db, user_id, conversation_id, "telegram")
    history = fetch_model_history(db, conversation_id)
    profile = fetch_profile(db, user_id)

    persist_user_message(db, conversation_id, user_id, user_text)
    assessment = screen_text(user_text)
    if assessment:
        log_safety_event(db, user_id, conversation_id, assessment)

    sender_hint = (
        f"Telegram message from {sender_name}: {user_text}" if sender_name else user_text
    )
    deps = CompanionDeps(
        user_id=user_id,
        profile=profile,
        mode="telegram",
        db=db,
        memory=MemoryService(db, user_id),
        last_user_text=user_text,
        conversation_id=conversation_id,
    )
    result = await companion_agent.run(
        sender_hint,
        deps=deps,
        model=settings.model_str,
        message_history=history,
        conversation_id=conversation_id,
    )
    reply = _response_text(str(result.output))
    persist_assistant_message(db, conversation_id, user_id, reply)
    return reply


@router.post("/telegram/webhook")
async def telegram_webhook(request: Request):
    if not _authorized(request):
        raise HTTPException(403, "Invalid Telegram webhook secret")

    update = await request.json()
    message = _message_from_update(update)
    if not message:
        return {"ok": True, "ignored": True}

    chat_id = _chat_id(message)
    if not chat_id:
        return {"ok": True, "ignored": True}
    text = _text(message)
    if not text:
        return {"ok": True, "ignored": True}

    command = text.split()[0].split("@")[0].lower() if text.startswith("/") else ""
    if command == "/help" or command == "/start":
        await send_message(chat_id, HELP_TEXT)
        return {"ok": True}
    if command == "/new":
        db = user_client("")
        conversation_id = _conversation_id(chat_id)
        (
            db.table("conversations")
            .delete()
            .eq("id", conversation_id)
            .eq("user_id", settings.dev_user_id)
            .execute()
        )
        get_or_create_conversation(db, settings.dev_user_id, conversation_id, "telegram")
        await send_message(chat_id, "Started a fresh conversation. What's on your mind?")
        return {"ok": True, "conversation_id": conversation_id}
    if command:
        await send_message(chat_id, "I don't know that command. Send /help.")
        return {"ok": True}

    reply = await _run_telegram_turn(
        user_text=text,
        conversation_id=_conversation_id(chat_id),
        sender_name=_sender_name(message),
    )
    await send_message(chat_id, reply)
    return {"ok": True}
