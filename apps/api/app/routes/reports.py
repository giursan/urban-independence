"""Reports and consented, expiring share links for relatives."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from ..auth import AuthedUser, current_user
from ..supabase_client import service_client, user_client

router = APIRouter()


class ShareIn(BaseModel):
    recipient_label: str | None = None
    expires_in_days: int = 30


@router.post("/reports/from-snapshot/{snapshot_id}")
async def create_report(snapshot_id: str, user: AuthedUser = Depends(current_user)):
    db = user_client(user.token)
    snap = (
        db.table("wellbeing_snapshots").select("id").eq("id", snapshot_id).limit(1).execute().data
    )
    if not snap:
        raise HTTPException(404, "Snapshot not found")
    row = (
        db.table("reports")
        .insert({"user_id": user.id, "snapshot_id": snapshot_id})
        .execute()
    )
    return {"id": row.data[0]["id"]}


@router.post("/reports/{report_id}/share")
async def share_report(report_id: str, body: ShareIn, user: AuthedUser = Depends(current_user)):
    db = user_client(user.token)
    rep = db.table("reports").select("id").eq("id", report_id).limit(1).execute().data
    if not rep:
        raise HTTPException(404, "Report not found")
    expires = (datetime.now(timezone.utc) + timedelta(days=body.expires_in_days)).isoformat()
    row = (
        db.table("report_shares")
        .insert(
            {
                "report_id": report_id,
                "user_id": user.id,
                "recipient_label": body.recipient_label,
                "expires_at": expires,
            }
        )
        .execute()
    )
    return {"token": row.data[0]["token"], "expires_at": expires}


@router.post("/shares/{token}/revoke")
async def revoke_share(token: str, user: AuthedUser = Depends(current_user)):
    db = user_client(user.token)
    db.table("report_shares").update({"revoked": True}).eq("token", token).eq(
        "user_id", user.id
    ).execute()
    return {"revoked": True}


@router.get("/shares/{token}")
async def public_share(token: str):
    """Public, unauthenticated resolution of a share token via SECURITY DEFINER RPC."""
    db = service_client()
    res = db.rpc("resolve_shared_report", {"share_token": token}).execute()
    if not res.data:
        raise HTTPException(404, "This shared report is unavailable or has expired.")
    return res.data[0]
