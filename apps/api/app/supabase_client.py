"""Supabase client factories.

- `user_client(token)` attaches the caller's JWT so all PostgREST calls run
  under that user's Row Level Security context (the default for user data).
- `service_client()` uses the service-role key and BYPASSES RLS — only for
  trusted server jobs (e.g. the diagnostics cron). Never hand this to a client.
"""
from __future__ import annotations

from supabase import Client, create_client

from .config import settings


def user_client(access_token: str) -> Client:
    # Auth is disabled for testing: with no token, use the service-role client
    # (RLS is off anyway). When real auth returns, a token routes PostgREST
    # through the user's JWT so RLS applies as them.
    if not access_token:
        return service_client()
    client = create_client(settings.supabase_url, settings.supabase_anon_key)
    client.postgrest.auth(access_token)
    return client


def service_client() -> Client:
    return create_client(settings.supabase_url, settings.supabase_service_role_key)
