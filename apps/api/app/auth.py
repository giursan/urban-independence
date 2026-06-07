"""Auth dependency - DISABLED for direct testing.

Authentication has been removed so the app runs without sign-in: every request
is treated as the fixed dev user (settings.dev_user_id). To restore real auth,
verify the Supabase JWT here and return the decoded subject as AuthedUser.id.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from fastapi import Request

from .config import settings


@dataclass
class AuthedUser:
    id: str
    token: str = ""
    claims: dict = field(default_factory=dict)


async def current_user(request: Request) -> AuthedUser:
    # No token verification: act as the single dev user. An empty token makes
    # user_client() fall back to the service-role client.
    return AuthedUser(id=settings.dev_user_id, token="", claims={})
