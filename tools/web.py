"""Web search and scraping tools via Firecrawl.

Registered with the shared REGISTRY in agent.tools via the @tool decorator.
Import this module from agent/tools.py so registration happens at boot.

Env:
    FIRECRAWL_API_KEY (required)
"""

from __future__ import annotations

import os
from typing import Any

import httpx

from agent.tools import tool

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


@tool(
    name="web_search",
    description=(
        "Search the public web for current information (news, advisories, opening hours, "
        "official notices). Use when local HK tools cannot answer."
    ),
    parameters={
        "query": {
            "type": "string",
            "description": "Search query, e.g. 'Hong Kong heat advisory today'.",
        },
        "limit": {
            "type": "integer",
            "description": "Max results to return, 1–10. Defaults to 5.",
        },
    },
    required=["query"],
)
def web_search(query: str, limit: int = 5) -> dict[str, Any]:
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
    return {"query": query, "results": results}


@tool(
    name="web_scrape",
    description=(
        "Fetch and parse a single web page as Markdown. Use to read a specific URL "
        "returned by web_search."
    ),
    parameters={
        "url": {"type": "string", "description": "Full URL to fetch."},
        "formats": {
            "type": "array",
            "description": "Output formats; any of 'markdown', 'html', 'links'. Defaults to ['markdown'].",
            "items": {"type": "string"},
        },
    },
    required=["url"],
)
def web_scrape(url: str, formats: list[str] | None = None) -> dict[str, Any]:
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
    }
