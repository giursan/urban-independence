"""Social / community context — HKFP news + public Google Calendar.

Registered with the shared REGISTRY in agent.tools via the @tool decorator.

Env:
    GOOGLE_CALENDAR_API_KEY  (for get_calendar_events; calendar must be public)
    GOOGLE_CALENDAR_ID       (optional default calendar id; per-call override allowed)
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any
from xml.etree import ElementTree as ET

import httpx

from agent.tools import tool

HKFP_FEED_URL = "https://hongkongfp.com/feed/"
GCAL_BASE = "https://www.googleapis.com/calendar/v3"


@tool(
    name="get_hkfp_news",
    description="Get the most recent Hong Kong Free Press headlines (English-language HK news).",
    parameters={
        "limit": {
            "type": "integer",
            "description": "Max number of items to return, 1–30. Defaults to 10.",
        }
    },
    required=[],
)
def get_hkfp_news(limit: int = 10) -> dict[str, Any]:
    limit = max(1, min(limit, 30))
    with httpx.Client(timeout=15.0, headers={"User-Agent": "urban-independence/1.0"}) as c:
        r = c.get(HKFP_FEED_URL)
        r.raise_for_status()
        root = ET.fromstring(r.text)

    items: list[dict[str, Any]] = []
    for item in root.iter("item"):
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        pub = (item.findtext("pubDate") or "").strip()
        desc = (item.findtext("description") or "").strip()
        try:
            published_iso = parsedate_to_datetime(pub).isoformat() if pub else None
        except (TypeError, ValueError):
            published_iso = None
        items.append(
            {"title": title, "link": link, "published": published_iso, "summary": desc}
        )
        if len(items) >= limit:
            break

    return {"source": "Hong Kong Free Press", "feed_url": HKFP_FEED_URL, "items": items}


@tool(
    name="get_calendar_events",
    description=(
        "Get upcoming events from a shared (public) Google Calendar — community classes, "
        "clinic appointments, family schedules."
    ),
    parameters={
        "calendar_id": {
            "type": "string",
            "description": "Calendar id, e.g. 'abc123@group.calendar.google.com'. If omitted, uses GOOGLE_CALENDAR_ID env.",
        },
        "max_results": {
            "type": "integer",
            "description": "Max events to return, 1–50. Defaults to 10.",
        },
    },
    required=[],
)
def get_calendar_events(
    calendar_id: str | None = None, max_results: int = 10
) -> dict[str, Any]:
    cal_id = calendar_id or os.environ.get("GOOGLE_CALENDAR_ID")
    if not cal_id:
        raise RuntimeError("calendar_id not provided and GOOGLE_CALENDAR_ID not set")
    api_key = os.environ.get("GOOGLE_CALENDAR_API_KEY")
    if not api_key:
        raise RuntimeError("GOOGLE_CALENDAR_API_KEY is not set")

    now_iso = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    params = {
        "key": api_key,
        "timeMin": now_iso,
        "maxResults": max(1, min(max_results, 50)),
        "singleEvents": "true",
        "orderBy": "startTime",
    }
    url = f"{GCAL_BASE}/calendars/{cal_id}/events"
    with httpx.Client(timeout=15.0) as c:
        r = c.get(url, params=params)
        r.raise_for_status()
        data = r.json()

    events = [
        {
            "id": e.get("id"),
            "summary": e.get("summary"),
            "location": e.get("location"),
            "description": e.get("description"),
            "start": (e.get("start") or {}).get("dateTime") or (e.get("start") or {}).get("date"),
            "end": (e.get("end") or {}).get("dateTime") or (e.get("end") or {}).get("date"),
            "html_link": e.get("htmlLink"),
        }
        for e in data.get("items", [])
    ]
    return {"calendar_id": cal_id, "events": events}
