"""Hong Kong news — Hong Kong Free Press RSS feed."""

from __future__ import annotations

from email.utils import parsedate_to_datetime
from xml.etree import ElementTree as ET

import httpx

HKFP_FEED_URL = "https://hongkongfp.com/feed/"


def fetch_hkfp_news(limit: int = 10) -> dict:
    limit = max(1, min(limit, 30))
    with httpx.Client(
        timeout=15.0,
        headers={"User-Agent": "urban-independence/0.1"},
    ) as c:
        r = c.get(HKFP_FEED_URL)
        r.raise_for_status()
        root = ET.fromstring(r.text)

    items: list[dict] = []
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

    return {
        "source": "Hong Kong Free Press",
        "source_url": HKFP_FEED_URL,
        "items": items,
    }
