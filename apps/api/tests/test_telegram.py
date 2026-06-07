from fastapi.testclient import TestClient

from app.companion import companion_agent
from app.config import settings
from app.main import app
from app.routes.telegram import _conversation_id


def test_telegram_ignores_non_message_update():
    client = TestClient(app)
    res = client.post("/telegram/webhook", json={"update_id": 1, "my_chat_member": {}})

    assert res.status_code == 200
    assert res.json() == {"ok": True, "ignored": True}


def test_telegram_webhook_secret_rejects_invalid_header(monkeypatch):
    monkeypatch.setattr(settings, "telegram_webhook_secret", "secret")
    client = TestClient(app)
    res = client.post("/telegram/webhook", json={"update_id": 1})

    assert res.status_code == 403


def test_telegram_chat_maps_to_stable_uuid_conversation_id():
    assert _conversation_id("123") == _conversation_id("123")
    assert _conversation_id("123") != _conversation_id("456")


def test_send_telegram_message_tool_is_registered():
    tools = set(companion_agent._function_toolset.tools.keys())
    assert "send_telegram_message" in tools
