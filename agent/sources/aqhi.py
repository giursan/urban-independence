"""HK Environmental Protection Department — Air Quality Health Index (AQHI).

Source: https://data.gov.hk/en-data/dataset/hk-epd-airteam-current-aqhi-of-individual-air-quality-monitoring-stations
Live feed (RSS / XML, updated hourly):
    https://www.aqhi.gov.hk/epd/ddata/html/out/aqhi_ind_rss_Eng.xml

Each <item>'s <description> is a CDATA string of the form:
    "Central - Roadside Stations: 4 Moderate - Sun, 07 Jun 2026 03:30"

AQHI band reference (EPD):
    1–3  Low
    4    Moderate
    5–6  High
    7    Very High
    8–10 Serious
    10+  Serious (extreme)
"""

from __future__ import annotations

import re
import time
import xml.etree.ElementTree as ET

import httpx

FEED_URL = "https://www.aqhi.gov.hk/epd/ddata/html/out/aqhi_ind_rss_Eng.xml"
CACHE_TTL_SECONDS = 300

_DESC_RE = re.compile(
    r"^(?P<station>.+?)\s*-\s*(?P<type>General Stations|Roadside Stations):\s*"
    r"(?P<value>\d+\+?|N\.?A\.?)\s+(?P<band>Very High|High|Moderate|Low|Serious)"
    r"\s*-\s*(?P<ts>.+?)\s*$"
)

HEALTH_ADVISORY_ELDERLY = {
    "Low": "No precaution needed.",
    "Moderate": "Elderly people with heart or respiratory illnesses should reduce outdoor physical exertion.",
    "High": "Elderly people with heart or respiratory illnesses should reduce outdoor activities and physical exertion.",
    "Very High": "Elderly people with heart or respiratory illnesses should avoid outdoor activities and physical exertion.",
    "Serious": "Elderly people with heart or respiratory illnesses should stay indoors and keep windows closed.",
}

_CACHE: dict[str, tuple[float, bytes]] = {}


def _fetch_feed() -> bytes:
    now = time.monotonic()
    cached = _CACHE.get(FEED_URL)
    if cached and (now - cached[0]) < CACHE_TTL_SECONDS:
        return cached[1]
    resp = httpx.get(
        FEED_URL,
        timeout=10.0,
        headers={"User-Agent": "urban-independence/0.1"},
    )
    resp.raise_for_status()
    _CACHE[FEED_URL] = (now, resp.content)
    return resp.content


def _parse_feed(xml_bytes: bytes) -> list[dict]:
    root = ET.fromstring(xml_bytes)
    stations: list[dict] = []
    for item in root.iterfind(".//item"):
        desc = (item.findtext("description") or "").strip()
        m = _DESC_RE.match(desc)
        if not m:
            continue
        raw_value = m["value"]
        try:
            aqhi_numeric: int | str = int(raw_value.rstrip("+"))
        except ValueError:
            aqhi_numeric = raw_value
        band = m["band"]
        stations.append(
            {
                "station": m["station"].strip(),
                "station_type": m["type"],
                "aqhi": aqhi_numeric,
                "aqhi_raw": raw_value,
                "band": band,
                "observed_at": m["ts"].strip(),
                "health_advisory_for_elderly": HEALTH_ADVISORY_ELDERLY.get(band, ""),
            }
        )
    return stations


def fetch_aqhi(district: str) -> dict:
    """Fetch the live AQHI feed and return stations matching `district` (loose substring)."""
    stations = _parse_feed(_fetch_feed())
    needle = district.lower().strip()
    matches = [s for s in stations if needle in s["station"].lower()]
    return {
        "district": district,
        "matched": bool(matches),
        "match_count": len(matches),
        "stations": matches if matches else stations,
        "source": "HK Environmental Protection Department — Air Quality Health Index (RSS, hourly)",
        "source_url": FEED_URL,
        "note": (
            None
            if matches
            else f"No EPD station name contained {district!r}; returning all stations so the model can pick the nearest."
        ),
    }
