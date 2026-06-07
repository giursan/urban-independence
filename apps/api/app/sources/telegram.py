"""Telegram Bot API helpers."""
from __future__ import annotations

from typing import Any

import httpx

from ..config import settings

TELEGRAM_API = "https://api.telegram.org"


async def send_message(chat_id: str | int, text: str) -> dict[str, Any]:
    if not settings.telegram_bot_token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is not set")
    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.post(
            f"{TELEGRAM_API}/bot{settings.telegram_bot_token}/sendMessage",
            json={"chat_id": chat_id, "text": text},
        )
        response.raise_for_status()
        data = response.json()
    if not data.get("ok"):
        raise RuntimeError(f"telegram sendMessage failed: {data}")
    message = data.get("result") or {}
    return {
        "ok": True,
        "chat_id": chat_id,
        "message_id": message.get("message_id"),
        "date": message.get("date"),
    }
