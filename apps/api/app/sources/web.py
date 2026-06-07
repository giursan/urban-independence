"""Generic web search + scrape via Firecrawl.

Env:
    FIRECRAWL_API_KEY (required)
"""

from __future__ import annotations

import os

import httpx

FIRECRAWL_BASE = "https://api.firecrawl.dev/v1"


def _client() -> httpx.AsyncClient:
    key = os.environ.get("FIRECRAWL_API_KEY")
    if not key:
        raise RuntimeError("FIRECRAWL_API_KEY is not set")
    return httpx.AsyncClient(
        base_url=FIRECRAWL_BASE,
        headers={"Authorization": f"Bearer {key}"},
        timeout=30.0,
    )


async def search_web(query: str, limit: int = 5) -> dict:
    async with _client() as c:
        r = await c.post("/search", json={"query": query, "limit": max(1, min(limit, 10))})
        r.raise_for_status()
        data = r.json()
    results = [
        {
            "title": item.get("title"),
            "url": item.get("url"),
            "description": item.get("description"),
        }
        for item in (data.get("data") or [])
    ]
    return {"query": query, "results": results, "source": "Firecrawl /search"}


async def scrape_url(url: str, formats: list[str] | None = None) -> dict:
    payload = {"url": url, "formats": formats or ["markdown"]}
    async with _client() as c:
        r = await c.post("/scrape", json=payload)
        r.raise_for_status()
        data = r.json()
    body = data.get("data") or {}
    return {
        "url": url,
        "markdown": body.get("markdown"),
        "html": body.get("html"),
        "links": body.get("links"),
        "metadata": body.get("metadata"),
        "source": "Firecrawl /scrape",
    }
