"""Test fakes so the agent can run without OpenAI or Supabase."""
from __future__ import annotations

from app.deps import CompanionDeps
from app.models import Profile


class FakeMemory:
    def __init__(self) -> None:
        self.saved: list[tuple[str, str]] = []
        self.canned: list[dict] = []

    async def embed(self, text: str) -> list[float]:
        return [0.0] * 1536

    async def recall(self, query: str, k: int = 5) -> list[dict]:
        return list(self.canned)

    async def save(self, content: str, kind: str = "fact", salience: float = 0.6) -> None:
        self.saved.append((content, kind))


class _Chain:
    def __init__(self, store: dict, name: str) -> None:
        self.store = store
        self.name = name
        self._payload = None

    def insert(self, payload):
        self._payload = payload
        return self

    def upsert(self, payload, on_conflict=None):
        self._payload = payload
        return self

    def update(self, payload):
        self._payload = payload
        return self

    def select(self, *a, **k):
        return self

    def eq(self, *a, **k):
        return self

    def gte(self, *a, **k):
        return self

    def order(self, *a, **k):
        return self

    def limit(self, *a, **k):
        return self

    def execute(self):
        if self._payload is not None:
            self.store.setdefault(self.name, []).append(self._payload)
        return type("Res", (), {"data": []})()


class FakeDB:
    def __init__(self) -> None:
        self.store: dict = {}

    def table(self, name: str) -> _Chain:
        return _Chain(self.store, name)

    def rpc(self, *a, **k) -> _Chain:
        return _Chain(self.store, "rpc")


def make_deps(mode: str = "companion", last_user_text: str = ""):
    memory = FakeMemory()
    deps = CompanionDeps(
        user_id="u1",
        profile=Profile(id="u1", preferred_name="Rose", interests=["gardening"]),
        mode=mode,
        db=FakeDB(),
        memory=memory,
        last_user_text=last_user_text,
        conversation_id="c1",
    )
    return deps, memory
