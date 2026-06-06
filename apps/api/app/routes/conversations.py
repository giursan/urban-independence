"""List conversations and fetch transcripts (used to seed the chat UI on reload)."""
from __future__ import annotations

from fastapi import APIRouter, Depends

from ..auth import AuthedUser, current_user
from ..supabase_client import user_client

router = APIRouter()


@router.get("/conversations")
async def list_conversations(user: AuthedUser = Depends(current_user)):
    db = user_client(user.token)
    res = (
        db.table("conversations")
        .select("*")
        .eq("user_id", user.id)
        .order("started_at", desc=True)
        .limit(50)
        .execute()
    )
    return res.data or []


@router.get("/conversations/{conversation_id}/messages")
async def conversation_messages(conversation_id: str, user: AuthedUser = Depends(current_user)):
    db = user_client(user.token)
    res = (
        db.table("messages")
        .select("id,role,content,created_at")
        .eq("conversation_id", conversation_id)
        .order("created_at")
        .execute()
    )
    return res.data or []
