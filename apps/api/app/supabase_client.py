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
    client = create_client(settings.supabase_url, settings.supabase_anon_key)
    # Route PostgREST requests through the user's JWT so RLS applies as them.
    client.postgrest.auth(access_token)
    return client


def service_client() -> Client:
    return create_client(settings.supabase_url, settings.supabase_service_role_key)
