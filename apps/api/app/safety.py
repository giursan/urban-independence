"""Lightweight, deterministic crisis screening for incoming user messages.

This is a safety net, not a classifier of record: it errs toward surfacing help.
A positive screen makes the UI show crisis resources and writes a safety_event.
"""
from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass
class CrisisAssessment:
    severity: str  # 'low' | 'medium' | 'high'
    category: str
    excerpt: str


_HIGH = [
    r"\bkill(ing)? myself\b",
    r"\bend(ing)? my life\b",
    r"\bsuicid",
    r"\bwant to die\b",
    r"\bdon'?t want to (live|be here)\b",
    r"\b(hurt|harm) myself\b",
    r"\btake my (own )?life\b",
    r"\bno reason to (live|go on)\b",
]
_ABUSE = [
    r"\b(hit|hits|hurt|hurts|beats) me\b",
    r"\bafraid of (him|her|them)\b",
    r"\bbeing abused\b",
]
_MEDIUM = [
    r"\bhopeless\b",
    r"\bcan'?t go on\b",
    r"\bgiving up\b",
    r"\bworthless\b",
    r"\bno one cares\b",
    r"\bbetter off without me\b",
]


def _excerpt(text: str, n: int = 200) -> str:
    text = text.strip()
    return text if len(text) <= n else text[:n] + "…"


def screen_text(text: str | None) -> CrisisAssessment | None:
    if not text:
        return None
    t = text.lower()
    for pat in _HIGH:
        if re.search(pat, t):
            return CrisisAssessment("high", "self-harm", _excerpt(text))
    for pat in _ABUSE:
        if re.search(pat, t):
            return CrisisAssessment("high", "abuse", _excerpt(text))
    for pat in _MEDIUM:
        if re.search(pat, t):
            return CrisisAssessment("medium", "distress", _excerpt(text))
    return None
