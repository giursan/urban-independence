"""List, delete, and fetch conversation transcripts."""
from __future__ import annotations

from fastapi import APIRouter, Depends

from ..auth import AuthedUser, current_user
from ..supabase_client import user_client

router = APIRouter()


@router.get("/conversations")
async def list_conversations(user: AuthedUser = Depends(current_user)):
    db = user_client(user.token)
    conversations = (
        db.table("conversations")
        .select("*")
        .eq("user_id", user.id)
        .order("started_at", desc=True)
        .limit(50)
        .execute()
        .data
        or []
    )
    enriched = []
    for conversation in conversations:
        latest = (
            db.table("messages")
            .select("role,content,created_at")
            .eq("conversation_id", conversation["id"])
            .order("created_at", desc=True)
            .limit(1)
            .execute()
            .data
            or []
        )
        latest_message = latest[0] if latest else None
        enriched.append(
            {
                **conversation,
                "last_message": latest_message["content"] if latest_message else None,
                "last_role": latest_message["role"] if latest_message else None,
                "last_message_at": (
                    latest_message["created_at"] if latest_message else conversation.get("started_at")
                ),
            }
        )
    return sorted(enriched, key=lambda c: c.get("last_message_at") or "", reverse=True)


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


@router.delete("/conversations/{conversation_id}")
async def delete_conversation(conversation_id: str, user: AuthedUser = Depends(current_user)):
    db = user_client(user.token)
    (
        db.table("conversations")
        .delete()
        .eq("id", conversation_id)
        .eq("user_id", user.id)
        .execute()
    )
    return {"deleted": True}
