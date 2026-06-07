"""Authoring endpoints for phone-call identity verification.

Security answers must be hashed server-side (never in the browser, never stored
in the clear), so unlike the profile/companion_facts data the web app writes
straight to Supabase, these go through the API. Used by onboarding (the person)
and the care page (relatives)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from .. import identity
from ..auth import AuthedUser, current_user
from ..models import SecurityQuestion
from ..supabase_client import user_client

router = APIRouter()


class SecurityQuestionIn(BaseModel):
    question: str
    answer: str
    created_by: str = "onboarding"


class PhoneIn(BaseModel):
    phone: str


@router.get("/security-questions", response_model=list[SecurityQuestion])
async def list_security_questions(user: AuthedUser = Depends(current_user)):
    db = user_client(user.token)
    rows = (
        db.table("security_questions")
        .select("id,question,created_by")
        .eq("user_id", user.id)
        .order("created_at")
        .execute()
        .data
        or []
    )
    return rows


@router.post("/security-questions", response_model=SecurityQuestion)
async def add_security_question(body: SecurityQuestionIn, user: AuthedUser = Depends(current_user)):
    question = body.question.strip()
    if not question or not body.answer.strip():
        raise HTTPException(status_code=422, detail="question and answer are required")
    db = user_client(user.token)
    row = (
        db.table("security_questions")
        .insert(
            {
                "user_id": user.id,
                "question": question,
                "answer_hash": identity.hash_answer(body.answer),
                "created_by": body.created_by or "onboarding",
            }
        )
        .execute()
        .data[0]
    )
    return {"id": row["id"], "question": row["question"], "created_by": row["created_by"]}


@router.delete("/security-questions/{question_id}")
async def delete_security_question(question_id: str, user: AuthedUser = Depends(current_user)):
    db = user_client(user.token)
    (
        db.table("security_questions")
        .delete()
        .eq("id", question_id)
        .eq("user_id", user.id)
        .execute()
    )
    return {"deleted": True}


@router.put("/profile/phone")
async def set_profile_phone(body: PhoneIn, user: AuthedUser = Depends(current_user)):
    """Register the user's primary phone number so calls from it are identified
    without a challenge."""
    key = identity.normalize_phone(body.phone)
    if not key:
        raise HTTPException(status_code=422, detail="a valid phone number is required")
    db = user_client(user.token)
    db.table("caller_phone_numbers").upsert(
        {"phone": key, "user_id": user.id, "verified": True},
        on_conflict="phone",
    ).execute()
    return {"phone": key}
