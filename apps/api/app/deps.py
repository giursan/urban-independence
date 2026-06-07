"""Per-request dependencies injected into the companion agent."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .memory import MemoryService
from .models import Profile


@dataclass
class CompanionDeps:
    user_id: str
    profile: Profile
    mode: str
    db: Any  # supabase Client (user-scoped) — Any to keep the agent test-friendly
    memory: MemoryService
    last_user_text: str = ""
    conversation_id: str | None = None
