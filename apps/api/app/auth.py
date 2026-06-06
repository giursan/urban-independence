"""Supabase JWT verification as a FastAPI dependency.

v1 verifies the HS256 access token with the project's JWT secret. For projects
using asymmetric (RS256/ES256) signing keys, swap in JWKS verification here —
the rest of the app only depends on the returned `AuthedUser`.
"""
from __future__ import annotations

from dataclasses import dataclass

import jwt
from fastapi import HTTPException, Request, status

from .config import settings


@dataclass
class AuthedUser:
    id: str
    token: str
    claims: dict


def _bearer(request: Request) -> str:
    header = request.headers.get("authorization", "")
    if not header.lower().startswith("bearer "):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Missing bearer token")
    return header.split(" ", 1)[1].strip()


async def current_user(request: Request) -> AuthedUser:
    token = _bearer(request)
    try:
        claims = jwt.decode(
            token,
            settings.supabase_jwt_secret,
            algorithms=["HS256"],
            audience="authenticated",
        )
    except Exception as exc:  # noqa: BLE001 - surface any decode/verify failure as 401
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, f"Invalid token: {exc}") from exc

    user_id = claims.get("sub")
    if not user_id:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token has no subject")
    return AuthedUser(id=user_id, token=token, claims=claims)
