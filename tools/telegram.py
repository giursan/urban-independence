"""Telegram messaging tool — lets the agent notify a caregiver / family chat.

Resolution order for the recipient chat_id:
    1. explicit `chat_id` argument
    2. caregiver linked to `elder_id` in the telegram_accounts table
    3. TELEGRAM_CAREGIVER_CHAT_ID env var

Env:
    TELEGRAM_BOT_TOKEN          (required)
    TELEGRAM_CAREGIVER_CHAT_ID  (optional fallback)
    SESSIONS_DB_PATH            (optional override for the SQLite store)
"""

from __future__ import annotations

import os
from typing import Any

import httpx

from agent.tools import tool

TELEGRAM_API = "https://api.telegram.org"


def _api(method: str, payload: dict[str, Any]) -> dict[str, Any]:
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is not set")
    with httpx.Client(timeout=15.0) as c:
        r = c.post(f"{TELEGRAM_API}/bot{token}/{method}", json=payload)
        r.raise_for_status()
        data = r.json()
    if not data.get("ok"):
        raise RuntimeError(f"telegram {method} failed: {data}")
    return data


def _resolve_caregiver(elder_id: str) -> int | None:
    """Look up the caregiver chat_id for an elder in the SQLite store."""
    from agent.persistence import Store  # local import — avoids cycle at module load
    db_path = os.environ.get("SESSIONS_DB_PATH", "data/sessions.db")
    try:
        return Store(path=db_path).get_caregiver_chat_id(elder_id)
    except Exception:
        return None


@tool(
    name="send_telegram_message",
    description=(
        "Send a Telegram message to a caregiver. Use this to alert a trusted contact "
        "when the elder needs help, is taking a risky action, or has decided on a plan "
        "they want to share. Prefer passing `elder_id` so the caregiver is resolved "
        "from the database."
    ),
    parameters={
        "text": {
            "type": "string",
            "description": "Message body. Keep concise; plain text is fine.",
        },
        "elder_id": {
            "type": "string",
            "description": (
                "Elder identifier; the linked caregiver's chat_id will be looked up from "
                "the telegram_accounts table."
            ),
        },
        "chat_id": {
            "type": "string",
            "description": (
                "Explicit Telegram chat id. Overrides elder_id lookup. Use only if you "
                "already know the caregiver's chat_id."
            ),
        },
    },
    required=["text"],
)
def send_telegram_message(
    text: str, elder_id: str | None = None, chat_id: str | None = None
) -> dict[str, Any]:
    target: str | int | None = chat_id
    if not target and elder_id:
        target = _resolve_caregiver(elder_id)
    if not target:
        target = os.environ.get("TELEGRAM_CAREGIVER_CHAT_ID")
    if not target:
        raise RuntimeError(
            "No recipient: pass chat_id, an elder_id with a linked caregiver, or set "
            "TELEGRAM_CAREGIVER_CHAT_ID."
        )
    data = _api("sendMessage", {"chat_id": target, "text": text})
    msg = data.get("result", {})
    return {
        "chat_id": target,
        "message_id": msg.get("message_id"),
        "date": msg.get("date"),
        "ok": True,
    }
