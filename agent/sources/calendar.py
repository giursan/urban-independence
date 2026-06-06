"""Google Calendar — upcoming events from a public calendar.

Env:
    GOOGLE_CALENDAR_API_KEY  (required)
    GOOGLE_CALENDAR_ID       (optional default; per-call override allowed)
"""

from __future__ import annotations

import os
from datetime import datetime, timezone

import httpx

GCAL_BASE = "https://www.googleapis.com/calendar/v3"


def fetch_calendar_events(
    calendar_id: str | None = None,
    max_results: int = 10,
) -> dict:
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
    return {
        "calendar_id": cal_id,
        "events": events,
        "source": "Google Calendar API v3",
    }
