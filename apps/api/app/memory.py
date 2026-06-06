"""Long-term memory: OpenAI embeddings + pgvector retrieval via the
`match_memories` RPC (RLS-scoped to the calling user)."""
from __future__ import annotations

import json

from openai import AsyncOpenAI
from supabase import Client

from .config import settings


class MemoryService:
    def __init__(self, db: Client, user_id: str) -> None:
        self.db = db
        self.user_id = user_id
        self._oai = AsyncOpenAI(api_key=settings.openai_api_key)

    async def embed(self, text: str) -> list[float]:
        resp = await self._oai.embeddings.create(
            model=settings.openai_embedding_model, input=text
        )
        return resp.data[0].embedding

    async def recall(self, query: str, k: int = 5) -> list[dict]:
        if not query or not query.strip():
            return []
        embedding = await self.embed(query)
        res = self.db.rpc(
            "match_memories",
            {"query_embedding": json.dumps(embedding), "match_count": k},
        ).execute()
        return res.data or []

    async def save(self, content: str, kind: str = "fact", salience: float = 0.6) -> None:
        embedding = await self.embed(content)
        self.db.table("memories").insert(
            {
                "user_id": self.user_id,
                "content": content,
                "kind": kind,
                "salience": salience,
                "embedding": json.dumps(embedding),
            }
        ).execute()
