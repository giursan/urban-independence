"""Phone-call identity verification.

Resolves which user is calling and gates access to their private profile/memory:

  * a known caller number identifies the user outright;
  * an unknown number is challenged for first+last name and a security question.

Speech-to-text output is noisy, so spoken names and answers are aggressively
normalized before comparison. Security answers are stored only as salted hashes.
"""
from __future__ import annotations

import hashlib
import hmac
import re
import unicodedata
from datetime import datetime, timezone
from typing import Any

from .config import settings

# Verification stages held in call_sessions.stage.
AWAIT_NAME = "AWAIT_NAME"
AWAIT_SECURITY_ANSWER = "AWAIT_SECURITY_ANSWER"
VERIFIED = "VERIFIED"
FAILED = "FAILED"

# Failed attempts at a single stage before we give up and hang up.
MAX_ATTEMPTS = 3

_ARTICLES = {"the", "a", "an"}


def normalize(text: str) -> str:
    """Lowercase, strip accents/punctuation, drop articles, collapse whitespace.

    Applied to both spoken names and spoken answers so noisy transcription
    ("The Blue!" vs "blue") still compares equal."""
    text = unicodedata.normalize("NFKD", text or "")
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = re.sub(r"[^a-z0-9\s]", " ", text.lower())
    tokens = [t for t in text.split() if t and t not in _ARTICLES]
    return " ".join(tokens)


def normalize_phone(phone: str) -> str:
    """Reduce a phone number to digits only, so '+1 (555) 555-0100' and
    '15555550100' resolve to the same caller."""
    return re.sub(r"\D", "", phone or "")


def hash_answer(answer: str) -> str:
    return hashlib.sha256(
        (normalize(answer) + settings.identity_secret).encode("utf-8")
    ).hexdigest()


def verify_answer(answer: str, answer_hash: str) -> bool:
    return hmac.compare_digest(hash_answer(answer), answer_hash or "")


# --- Caller / profile resolution ------------------------------------------

def find_user_by_phone(db: Any, phone: str) -> str | None:
    key = normalize_phone(phone)
    if not key:
        return None
    rows = (
        db.table("caller_phone_numbers")
        .select("user_id")
        .eq("phone", key)
        .limit(1)
        .execute()
        .data
        or []
    )
    return rows[0]["user_id"] if rows else None


def find_user_by_name(db: Any, spoken_name: str) -> str | None:
    """Resolve a spoken name to a single profile, or None if no/ambiguous match.

    A profile matches when its normalized name equals the spoken name, or when
    all of the profile's name tokens appear in what was spoken (so "Margaret
    Lee" matches "Margaret Lee speaking"). Returns None unless exactly one
    profile matches, to avoid handing the wrong person someone else's account."""
    spoken = normalize(spoken_name)
    if not spoken:
        return None
    spoken_tokens = set(spoken.split())
    rows = (
        db.table("profiles")
        .select("id,display_name,preferred_name")
        .execute()
        .data
        or []
    )
    matches: list[str] = []
    for row in rows:
        for field in ("display_name", "preferred_name"):
            cand = normalize(row.get(field) or "")
            if not cand:
                continue
            cand_tokens = set(cand.split())
            if cand == spoken or (cand_tokens and cand_tokens <= spoken_tokens):
                matches.append(row["id"])
                break
    unique = list(dict.fromkeys(matches))
    return unique[0] if len(unique) == 1 else None


def fetch_security_question(db: Any, user_id: str) -> dict | None:
    rows = (
        db.table("security_questions")
        .select("id,question,answer_hash")
        .eq("user_id", user_id)
        .order("created_at")
        .limit(1)
        .execute()
        .data
        or []
    )
    return rows[0] if rows else None


def remember_caller_number(db: Any, user_id: str, phone: str) -> None:
    """Bind a freshly verified number to the user so future calls skip the
    challenge."""
    key = normalize_phone(phone)
    if not key:
        return
    db.table("caller_phone_numbers").upsert(
        {"phone": key, "user_id": user_id, "verified": True},
        on_conflict="phone",
    ).execute()


# --- Per-call verification state -------------------------------------------

def get_call_session(db: Any, call_sid: str) -> dict | None:
    rows = (
        db.table("call_sessions")
        .select("*")
        .eq("call_sid", call_sid)
        .limit(1)
        .execute()
        .data
        or []
    )
    return rows[0] if rows else None


def upsert_call_session(db: Any, call_sid: str, **fields: Any) -> dict:
    payload = {
        "call_sid": call_sid,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        **fields,
    }
    db.table("call_sessions").upsert(payload, on_conflict="call_sid").execute()
    return payload


def log_identity_failure(db: Any, user_id: str, excerpt: str) -> None:
    """Record a failed verification against the candidate user (so a relative can
    see suspicious call attempts). Reuses the safety_events sink."""
    db.table("safety_events").insert(
        {
            "user_id": user_id,
            "conversation_id": None,
            "severity": "low",
            "category": "identity_verification_failed",
            "excerpt": excerpt[:200],
        }
    ).execute()
