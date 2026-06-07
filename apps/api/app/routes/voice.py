"""Twilio voice webhooks backed by the same companion conversation engine.

Twilio posts speech turns as form-encoded webhooks. We respond with TwiML that
speaks the companion reply and gathers the next spoken turn. Each CallSid maps
to one persisted conversation, so phone calls feed the same memory, safety, and
wellbeing-summary pipeline as web chat.
"""
from __future__ import annotations

from urllib.parse import parse_qs
from uuid import NAMESPACE_URL, uuid5
from xml.sax.saxutils import escape

from fastapi import APIRouter, Request
from fastapi.responses import Response

from ..companion import companion_agent
from ..config import settings
from ..deps import CompanionDeps
from ..memory import MemoryService
from ..persistence import (
    fetch_model_history,
    fetch_profile,
    get_or_create_conversation,
    log_safety_event,
    persist_assistant_message,
    persist_user_message,
)
from ..safety import screen_text
from ..supabase_client import user_client

router = APIRouter()

GATHER_TIMEOUT_SECONDS = 5
SPEECH_LANGUAGE = "en-US"


def _conversation_id(call_sid: str) -> str:
    return str(uuid5(NAMESPACE_URL, f"twilio-call:{call_sid}"))


async def _twilio_form(request: Request) -> dict[str, str]:
    body = (await request.body()).decode("utf-8", errors="replace")
    parsed = parse_qs(body, keep_blank_values=True)
    return {key: values[-1] if values else "" for key, values in parsed.items()}


def _xml_response(body: str) -> Response:
    return Response(content=body, media_type="application/xml")


def _say(text: str) -> str:
    return f"<Say>{escape(text)}</Say>"


def _gather_xml(say_text: str) -> Response:
    body = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        "<Response>"
        f'<Gather input="speech" action="/voice/turn" method="POST" '
        f'speechTimeout="auto" timeout="{GATHER_TIMEOUT_SECONDS}" language="{SPEECH_LANGUAGE}">'
        f"{_say(say_text)}"
        "</Gather>"
        '<Redirect method="POST">/voice/timeout</Redirect>'
        "</Response>"
    )
    return _xml_response(body)


def _hangup_xml(say_text: str) -> Response:
    return _xml_response(
        '<?xml version="1.0" encoding="UTF-8"?>'
        f"<Response>{_say(say_text)}<Hangup /></Response>"
    )


def _wants_to_end(text: str) -> bool:
    lowered = text.lower()
    return any(phrase in lowered for phrase in ("goodbye", "good bye", "bye", "hang up"))


def _voice_text(text: str) -> str:
    cleaned = " ".join((text or "").split())
    return cleaned or "I'm here with you. Could you say that again?"


async def _run_phone_turn(
    *,
    call_sid: str,
    user_text: str,
    persist_user: bool,
) -> tuple[str, str]:
    user_id = settings.dev_user_id
    db = user_client("")
    conversation_id = get_or_create_conversation(
        db,
        user_id,
        _conversation_id(call_sid),
        "phone",
    )
    history = fetch_model_history(db, conversation_id)
    profile = fetch_profile(db, user_id)

    if persist_user:
        persist_user_message(db, conversation_id, user_id, user_text)
        assessment = screen_text(user_text)
        if assessment:
            log_safety_event(db, user_id, conversation_id, assessment)

    deps = CompanionDeps(
        user_id=user_id,
        profile=profile,
        mode="phone",
        db=db,
        memory=MemoryService(db, user_id),
        last_user_text=user_text,
        conversation_id=conversation_id,
    )
    result = await companion_agent.run(
        user_text,
        deps=deps,
        model=settings.model_str,
        message_history=history,
        conversation_id=conversation_id,
    )
    reply = _voice_text(str(result.output))
    persist_assistant_message(db, conversation_id, user_id, reply)
    return conversation_id, reply


@router.post("/voice")
async def voice(request: Request):
    form = await _twilio_form(request)
    call_sid = form.get("CallSid") or "manual-call"
    _, reply = await _run_phone_turn(
        call_sid=call_sid,
        user_text="The person has just called by phone. Greet them briefly and ask how you can help.",
        persist_user=False,
    )
    return _gather_xml(reply)


@router.post("/voice/turn")
async def voice_turn(request: Request):
    form = await _twilio_form(request)
    call_sid = form.get("CallSid") or "manual-call"
    speech = (form.get("SpeechResult") or "").strip()
    if not speech:
        return _gather_xml("I didn't catch that. Could you say it again?")

    user_id = settings.dev_user_id
    db = user_client("")
    conversation_id = get_or_create_conversation(db, user_id, _conversation_id(call_sid), "phone")
    if _wants_to_end(speech):
        persist_user_message(db, conversation_id, user_id, speech)
        goodbye = "Goodbye. Take care."
        persist_assistant_message(db, conversation_id, user_id, goodbye)
        return _hangup_xml(goodbye)

    _, reply = await _run_phone_turn(call_sid=call_sid, user_text=speech, persist_user=True)
    return _gather_xml(reply)


@router.post("/voice/timeout")
async def voice_timeout(request: Request):
    form = await _twilio_form(request)
    call_sid = form.get("CallSid") or "manual-call"
    db = user_client("")
    conversation_id = get_or_create_conversation(
        db,
        settings.dev_user_id,
        _conversation_id(call_sid),
        "phone",
    )
    goodbye = "I didn't hear anything. Goodbye, take care."
    persist_assistant_message(db, conversation_id, settings.dev_user_id, goodbye)
    return _hangup_xml(goodbye)
