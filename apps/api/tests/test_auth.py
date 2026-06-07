"""JWT auth dependency: decoding and the 401 path for protected routes."""
from __future__ import annotations

import jwt
import pytest
from fastapi.testclient import TestClient
from starlette.requests import Request

from app.auth import _decode, current_user
from app.config import settings
from app.main import app


def test_decode_accepts_valid_hs256_token():
    token = jwt.encode(
        {"sub": "user-123", "aud": "authenticated"},
        settings.supabase_jwt_secret,
        algorithm="HS256",
    )
    assert _decode(token)["sub"] == "user-123"


def test_protected_route_rejects_missing_or_bad_token():
    client = TestClient(app)
    assert client.get("/conversations").status_code == 401
    assert (
        client.get("/conversations", headers={"Authorization": "Bearer not-a-jwt"}).status_code
        == 401
    )


@pytest.mark.asyncio
async def test_ios_demo_token_maps_to_dev_user(monkeypatch):
    monkeypatch.setattr(settings, "ios_demo_token", "demo-secret")
    monkeypatch.setattr(settings, "dev_user_id", "demo-user")
    request = Request(
        {
            "type": "http",
            "method": "POST",
            "path": "/chat",
            "headers": [(b"x-aporia-demo-token", b"demo-secret")],
        }
    )

    user = await current_user(request)

    assert user.id == "demo-user"
    assert user.token == ""
    assert user.claims["demo"] is True
