"""HK Transport Department — Special Traffic News v2.

Road incidents, closures, construction, accidents, watermain works, and
special arrangements published in real time by the Transport Department.

Source: https://data.gov.hk/en-data/dataset/hk-td-tis_19-special-traffic-news-v2
Live feed (XML, real-time):
    https://www.td.gov.hk/en/special_news/trafficnews.xml
"""

from __future__ import annotations

import time
import xml.etree.ElementTree as ET

import httpx

FEED_URL = "https://www.td.gov.hk/en/special_news/trafficnews.xml"
CACHE_TTL_SECONDS = 120
MAX_RETURNED = 15

_FIELDS = (
    "INCIDENT_NUMBER",
    "INCIDENT_HEADING_EN",
    "INCIDENT_DETAIL_EN",
    "LOCATION_EN",
    "DISTRICT_EN",
    "DIRECTION_EN",
    "NEAR_LANDMARK_EN",
    "BETWEEN_LANDMARK_EN",
    "ANNOUNCEMENT_DATE",
    "INCIDENT_STATUS_EN",
    "CONTENT_EN",
    "LATITUDE",
    "LONGITUDE",
)

_CACHE: dict[str, tuple[float, bytes]] = {}


async def _fetch_feed() -> bytes:
    now = time.monotonic()
    cached = _CACHE.get(FEED_URL)
    if cached and (now - cached[0]) < CACHE_TTL_SECONDS:
        return cached[1]
    async with httpx.AsyncClient(
        timeout=10.0,
        headers={"User-Agent": "urban-independence/0.1"},
    ) as c:
        resp = await c.get(FEED_URL)
        resp.raise_for_status()
    _CACHE[FEED_URL] = (now, resp.content)
    return resp.content


def _norm(text: str | None) -> str:
    return (text or "").strip()


def _parse_feed(xml_bytes: bytes) -> list[dict]:
    root = ET.fromstring(xml_bytes)
    items: list[dict] = []
    for msg in root.iterfind(".//message"):
        record = {f.lower(): _norm(msg.findtext(f)) for f in _FIELDS}
        record["incident_type"] = record.pop("incident_heading_en")
        record["detail"] = record.pop("incident_detail_en")
        record["location"] = record.pop("location_en")
        record["district"] = record.pop("district_en")
        record["direction"] = record.pop("direction_en")
        record["near_landmark"] = record.pop("near_landmark_en")
        record["between_landmark"] = record.pop("between_landmark_en")
        record["announced_at"] = record.pop("announcement_date")
        record["status"] = record.pop("incident_status_en")
        record["content"] = record.pop("content_en")
        items.append(record)
    return items


def _matches(record: dict, needle: str) -> bool:
    haystacks = (
        record["district"],
        record["location"],
        record["near_landmark"],
        record["between_landmark"],
    )
    return any(needle in (h or "").lower() for h in haystacks)


async def fetch_traffic_advisories(district: str | None = None) -> dict:
    items = _parse_feed(await _fetch_feed())
    total = len(items)

    if district:
        needle = district.lower().strip()
        matched = [i for i in items if _matches(i, needle)]
    else:
        matched = items

    matched_truncated = matched[:MAX_RETURNED]

    if district and not matched:
        fallback = items[:MAX_RETURNED]
        return {
            "district": district,
            "matched": False,
            "match_count": 0,
            "feed_total": total,
            "incidents": fallback,
            "note": (
                f"No incidents tagged to {district!r}; returning {len(fallback)} most "
                "recent feed-wide so the model can judge regional relevance."
            ),
            "source": "HK Transport Department — Special Traffic News v2 (XML, real-time)",
            "source_url": FEED_URL,
        }

    return {
        "district": district,
        "matched": bool(matched),
        "match_count": len(matched),
        "returned_count": len(matched_truncated),
        "feed_total": total,
        "incidents": matched_truncated,
        "truncated": len(matched) > MAX_RETURNED,
        "source": "HK Transport Department — Special Traffic News v2 (XML, real-time)",
        "source_url": FEED_URL,
    }
