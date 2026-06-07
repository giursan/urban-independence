"""Auth dependency: verify the Supabase session JWT and resolve the real user.

Supabase issues asymmetric (ES256/RS256) access tokens signed with per-project
keys published at the JWKS endpoint, so we verify against those. A legacy HS256
shared-secret token is still accepted as a fallback. Once decoded, the token is
handed to `user_client(token)` so PostgREST applies Row-Level Security as this user.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import jwt
from fastapi import HTTPException, Request
from jwt import PyJWKClient

from .config import settings

# Lazily fetches and caches the project's signing keys (no network at import).
_JWKS_URL = f"{settings.supabase_url}/auth/v1/.well-known/jwks.json"
_jwk_client = PyJWKClient(
    _JWKS_URL,
    headers={"apikey": settings.supabase_anon_key},
    cache_keys=True,
)


@dataclass
class AuthedUser:
    id: str
    token: str = ""
    claims: dict = field(default_factory=dict)


def _decode(token: str) -> dict:
    alg = (jwt.get_unverified_header(token).get("alg") or "").upper()
    if alg.startswith(("ES", "RS", "PS")):
        signing_key = _jwk_client.get_signing_key_from_jwt(token).key
        return jwt.decode(token, signing_key, algorithms=[alg], audience="authenticated")
    # Legacy symmetric tokens (older projects).
    return jwt.decode(
        token, settings.supabase_jwt_secret, algorithms=["HS256"], audience="authenticated"
    )


async def current_user(request: Request) -> AuthedUser:
    header = request.headers.get("Authorization", "")
    if not header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")
    token = header[len("Bearer ") :].strip()
    try:
        claims = _decode(token)
    except Exception as exc:  # invalid signature, expired, wrong audience, etc.
        raise HTTPException(status_code=401, detail="Invalid or expired token") from exc
    sub = claims.get("sub")
    if not sub:
        raise HTTPException(status_code=401, detail="Token missing subject")
    return AuthedUser(id=sub, token=token, claims=claims)
