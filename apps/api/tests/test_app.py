from fastapi.testclient import TestClient

from app.main import app


def test_health_and_imports():
    # Importing app.main wires every route module; this also smoke-tests
    # the pydantic_ai message imports used for transcript persistence.
    client = TestClient(app)
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json() == {"ok": True}
