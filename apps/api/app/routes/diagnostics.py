"""Wellbeing diagnostics: generate and list non-clinical snapshots."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends

from ..auth import AuthedUser, current_user
from ..config import settings
from ..diagnostics import analyze_wellbeing
from ..supabase_client import user_client

router = APIRouter()

LOOKBACK_DAYS = 14


@router.post("/diagnostics/generate")
async def generate(user: AuthedUser = Depends(current_user)):
    db = user_client(user.token)
    now = datetime.now(timezone.utc)
    since = (now - timedelta(days=LOOKBACK_DAYS)).isoformat()

    msgs = (
        db.table("messages")
        .select("role,content,created_at")
        .eq("user_id", user.id)
        .gte("created_at", since)
        .order("created_at")
        .limit(500)
        .execute()
        .data
        or []
    )
    moods = (
        db.table("mood_logs")
        .select("score,label,note,created_at")
        .eq("user_id", user.id)
        .gte("created_at", since)
        .order("created_at")
        .execute()
        .data
        or []
    )

    transcript = "\n".join(f"{m['role']}: {m['content']}" for m in msgs)
    snapshot = await analyze_wellbeing(transcript, moods)

    row = (
        db.table("wellbeing_snapshots")
        .insert(
            {
                "user_id": user.id,
                "period_start": since,
                "period_end": now.isoformat(),
                "payload": snapshot.model_dump(),
                "model_version": settings.openai_model,
                "confidence": snapshot.confidence,
            }
        )
        .execute()
    )
    return {"id": row.data[0]["id"], "snapshot": snapshot.model_dump()}


@router.get("/diagnostics")
async def list_snapshots(user: AuthedUser = Depends(current_user)):
    db = user_client(user.token)
    res = (
        db.table("wellbeing_snapshots")
        .select("*")
        .eq("user_id", user.id)
        .order("created_at", desc=True)
        .execute()
    )
    return res.data or []
