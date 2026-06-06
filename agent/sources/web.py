"""Generic web search + scrape via Firecrawl.

Used as a fallback when no local HK tool answers — e.g. an obscure venue's
opening hours, a specific government notice, or any URL the model needs
to read for context.

Env:
    FIRECRAWL_API_KEY (required)
"""

from __future__ import annotations

import os

import httpx

FIRECRAWL_BASE = "https://api.firecrawl.dev/v1"


def _client() -> httpx.Client:
    key = os.environ.get("FIRECRAWL_API_KEY")
    if not key:
        raise RuntimeError("FIRECRAWL_API_KEY is not set")
    return httpx.Client(
        base_url=FIRECRAWL_BASE,
        headers={"Authorization": f"Bearer {key}"},
        timeout=30.0,
    )


def search_web(query: str, limit: int = 5) -> dict:
    with _client() as c:
        r = c.post("/search", json={"query": query, "limit": max(1, min(limit, 10))})
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


def scrape_url(url: str, formats: list[str] | None = None) -> dict:
    payload = {"url": url, "formats": formats or ["markdown"]}
    with _client() as c:
        r = c.post("/scrape", json=payload)
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
