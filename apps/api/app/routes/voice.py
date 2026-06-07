"""Twilio voice webhooks backed by the same companion conversation engine.

Twilio posts speech turns as form-encoded webhooks. We respond with TwiML that
speaks the companion reply and gathers the next spoken turn. Each CallSid maps
to one persisted conversation, so phone calls feed the same memory, safety, and
wellbeing-summary pipeline as web chat.

Before any private context is exposed we verify WHO is calling (see identity.py):
a known caller number identifies the user outright; an unknown number is
challenged for first+last name and a security question.
"""
from __future__ import annotations

import re
from urllib.parse import parse_qs
from uuid import NAMESPACE_URL, uuid5
from xml.sax.saxutils import escape

from fastapi import APIRouter, Request
from fastapi.responses import Response

from .. import identity
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

GREETING_PROMPT = (
    "The person has just called by phone. Greet them warmly by name and ask how "
    "you can help."
)
NAME_PROMPT = "Hello. Before we begin, may I have your first and last name, please?"


def _conversation_id(call_sid: str) -> str:
    return str(uuid5(NAMESPACE_URL, f"twilio-call:{call_sid}"))


async def _twilio_form(request: Request) -> dict[str, str]:
    body = (await request.body()).decode("utf-8", errors="replace")
    parsed = parse_qs(body, keep_blank_values=True)
    return {key: values[-1] if values else "" for key, values in parsed.items()}


def _xml_response(body: str) -> Response:
    return Response(content=body, media_type="application/xml")


_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")


def _ssml(text: str) -> str:
    """Render a reply as gentle SSML: a slightly slower, warm pace with a brief
    pause between sentences so the companion sounds unhurried, not monotone."""
    pause = f'<break time="{settings.voice_sentence_pause_ms}ms"/>'
    sentences = [escape(s) for s in _SENTENCE_SPLIT.split((text or "").strip()) if s.strip()]
    body = pause.join(sentences) or escape(text or "")
    return f'<prosody rate="{settings.voice_tts_rate}">{body}</prosody>'


def _say(text: str) -> str:
    return f'<Say voice="{settings.voice_tts_voice}">{_ssml(text)}</Say>'


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
    user_id: str,
    user_text: str,
    persist_user: bool,
) -> tuple[str, str]:
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
    """Call setup. Known caller number → verified and greeted; unknown number →
    challenged for their name."""
    form = await _twilio_form(request)
    call_sid = form.get("CallSid") or "manual-call"
    from_number = form.get("From") or ""

    db = user_client("")
    user_id = identity.find_user_by_phone(db, from_number)
    if user_id:
        identity.upsert_call_session(
            db, call_sid, stage=identity.VERIFIED, verified_user_id=user_id, attempts=0
        )
        _, reply = await _run_phone_turn(
            call_sid=call_sid,
            user_id=user_id,
            user_text=GREETING_PROMPT,
            persist_user=False,
        )
        return _gather_xml(reply)

    identity.upsert_call_session(db, call_sid, stage=identity.AWAIT_NAME, attempts=0)
    return _gather_xml(NAME_PROMPT)


@router.post("/voice/turn")
async def voice_turn(request: Request):
    form = await _twilio_form(request)
    call_sid = form.get("CallSid") or "manual-call"
    from_number = form.get("From") or ""
    speech = (form.get("SpeechResult") or "").strip()
    if not speech:
        # Re-prompt without touching the DB (keeps no-context webhooks cheap).
        return _gather_xml("I didn't catch that. Could you say it again?")

    db = user_client("")
    session = identity.get_call_session(db, call_sid)
    # No session (e.g. server restarted mid-call): restart verification.
    stage = session.get("stage") if session else identity.AWAIT_NAME

    if stage == identity.VERIFIED:
        return await _verified_turn(db, call_sid, session["verified_user_id"], speech)
    if stage == identity.AWAIT_SECURITY_ANSWER:
        return await _security_answer_turn(db, call_sid, session, from_number, speech)
    if stage == identity.FAILED:
        return _hangup_xml("I'm sorry, I wasn't able to verify you. Goodbye.")
    return _name_turn(db, call_sid, session, speech)


async def _verified_turn(db, call_sid: str, user_id: str, speech: str) -> Response:
    conversation_id = get_or_create_conversation(
        db, user_id, _conversation_id(call_sid), "phone"
    )
    if _wants_to_end(speech):
        persist_user_message(db, conversation_id, user_id, speech)
        goodbye = "Goodbye. Take care."
        persist_assistant_message(db, conversation_id, user_id, goodbye)
        return _hangup_xml(goodbye)

    _, reply = await _run_phone_turn(
        call_sid=call_sid, user_id=user_id, user_text=speech, persist_user=True
    )
    return _gather_xml(reply)


def _name_turn(db, call_sid: str, session: dict | None, spoken_name: str) -> Response:
    """AWAIT_NAME: resolve the spoken name to a profile, then ask its security
    question."""
    user_id = identity.find_user_by_name(db, spoken_name)
    if not user_id:
        return _retry_or_fail(
            db,
            call_sid,
            session,
            user_id=None,
            stage=identity.AWAIT_NAME,
            retry_prompt="I couldn't find that name. Please say your first and last name.",
            fail_detail=f"unmatched name: {spoken_name}",
        )

    question = identity.fetch_security_question(db, user_id)
    if not question:
        # Known person, but no challenge configured — we cannot safely verify.
        identity.upsert_call_session(db, call_sid, stage=identity.FAILED)
        identity.log_identity_failure(db, user_id, "no security question configured")
        return _hangup_xml(
            "I'm sorry, I can't verify you over the phone right now. Please call "
            "from your registered phone number. Goodbye."
        )

    identity.upsert_call_session(
        db,
        call_sid,
        stage=identity.AWAIT_SECURITY_ANSWER,
        candidate_user_id=user_id,
        attempts=0,
    )
    return _gather_xml(f"Thank you. {question['question']}")


async def _security_answer_turn(
    db, call_sid: str, session: dict, from_number: str, answer: str
) -> Response:
    candidate_user_id = session.get("candidate_user_id")
    question = identity.fetch_security_question(db, candidate_user_id) if candidate_user_id else None
    if not question:
        identity.upsert_call_session(db, call_sid, stage=identity.FAILED)
        return _hangup_xml("I'm sorry, I wasn't able to verify you. Goodbye.")

    if identity.verify_answer(answer, question["answer_hash"]):
        identity.upsert_call_session(
            db,
            call_sid,
            stage=identity.VERIFIED,
            verified_user_id=candidate_user_id,
            attempts=0,
        )
        identity.remember_caller_number(db, candidate_user_id, from_number)
        _, reply = await _run_phone_turn(
            call_sid=call_sid,
            user_id=candidate_user_id,
            user_text=GREETING_PROMPT,
            persist_user=False,
        )
        return _gather_xml(reply)

    return _retry_or_fail(
        db,
        call_sid,
        session,
        user_id=candidate_user_id,
        stage=identity.AWAIT_SECURITY_ANSWER,
        retry_prompt=f"That's not what I have on file. {question['question']}",
        fail_detail="wrong security answer",
    )


def _retry_or_fail(
    db,
    call_sid: str,
    session: dict | None,
    *,
    user_id: str | None,
    stage: str,
    retry_prompt: str,
    fail_detail: str,
) -> Response:
    """Bump the attempt counter; re-prompt until MAX_ATTEMPTS, then hang up."""
    attempts = (session.get("attempts", 0) if session else 0) + 1
    if attempts >= identity.MAX_ATTEMPTS:
        identity.upsert_call_session(db, call_sid, stage=identity.FAILED, attempts=attempts)
        if user_id:
            identity.log_identity_failure(db, user_id, fail_detail)
        return _hangup_xml(
            "I'm sorry, I wasn't able to verify who you are. Goodbye, take care."
        )
    identity.upsert_call_session(db, call_sid, stage=stage, attempts=attempts)
    return _gather_xml(retry_prompt)


@router.post("/voice/timeout")
async def voice_timeout(request: Request):
    form = await _twilio_form(request)
    call_sid = form.get("CallSid") or "manual-call"
    db = user_client("")
    session = identity.get_call_session(db, call_sid)
    verified_user_id = session.get("verified_user_id") if session else None
    goodbye = "I didn't hear anything. Goodbye, take care."
    if verified_user_id:
        conversation_id = get_or_create_conversation(
            db, verified_user_id, _conversation_id(call_sid), "phone"
        )
        persist_assistant_message(db, conversation_id, verified_user_id, goodbye)
    return _hangup_xml(goodbye)
