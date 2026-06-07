"""Telegram tools registered on the companion agent."""
from __future__ import annotations

from .companion import companion_agent
from .config import settings
from .sources.telegram import send_message


@companion_agent.tool_plain
async def send_telegram_message(text: str, chat_id: str | None = None) -> dict:
    """Send a Telegram message to a trusted caregiver.

    Use only when the person explicitly asks you to message a caregiver, or when
    there is clear immediate safety concern and a configured trusted contact.
    Keep the message concise and factual. If `chat_id` is omitted, the configured
    TELEGRAM_CAREGIVER_CHAT_ID is used.
    """
    target = chat_id or settings.telegram_caregiver_chat_id
    if not target:
        raise RuntimeError("No Telegram recipient configured")
    return await send_message(target, text)
