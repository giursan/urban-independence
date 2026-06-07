from fastapi.testclient import TestClient

from app.main import app
from app.routes.voice import _conversation_id


def test_twilio_blank_turn_returns_gather_twiml():
    client = TestClient(app)
    res = client.post(
        "/voice/turn",
        content="CallSid=CA123&SpeechResult=",
        headers={"content-type": "application/x-www-form-urlencoded"},
    )

    assert res.status_code == 200
    assert res.headers["content-type"].startswith("application/xml")
    assert "<Gather" in res.text
    assert 'action="/voice/turn"' in res.text
    assert "I didn't catch that" in res.text


def test_call_sid_maps_to_stable_uuid_conversation_id():
    assert _conversation_id("CA123") == _conversation_id("CA123")
    assert _conversation_id("CA123") != _conversation_id("CA456")
