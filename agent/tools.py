"""Tool registry for live Hong Kong data.

This file is the single source of truth for what tools the orchestrator sees.
Each tool here is a thin `@tool`-decorated wrapper around a `fetch_*` function
in `agent/sources/`. The wrapper does only:
    - declare name, description, parameters (the API surface Claude sees)
    - delegate to the source module

To add a new tool:
    1. Create `agent/sources/<name>.py` with a pure `fetch_*` function.
    2. Import it below and add an `@tool` block.
    3. Done. The registry picks it up at import time.

Status legend:
    LIVE — wired to a real HK API
    STUB — not wired yet (returns fake but realistic data so the loop runs)
"""

from __future__ import annotations

import inspect
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from .sources import aqhi, calendar, mtr, news, traffic, weather, web


@dataclass
class Tool:
    name: str
    description: str
    parameters: dict[str, dict[str, Any]]
    required: list[str]
    fn: Callable[..., Any]

    def to_anthropic_schema(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": {
                "type": "object",
                "properties": self.parameters,
                "required": self.required,
            },
        }

    def call(self, **kwargs: Any) -> Any:
        sig = inspect.signature(self.fn)
        accepted = {k: v for k, v in kwargs.items() if k in sig.parameters}
        return self.fn(**accepted)


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    def register(self, t: Tool) -> None:
        self._tools[t.name] = t

    def get(self, name: str) -> Tool:
        if name not in self._tools:
            raise KeyError(f"unknown tool: {name}")
        return self._tools[name]

    def all(self) -> list[Tool]:
        return list(self._tools.values())

    def anthropic_schemas(self) -> list[dict[str, Any]]:
        return [t.to_anthropic_schema() for t in self._tools.values()]


REGISTRY = ToolRegistry()


def tool(
    *,
    name: str,
    description: str,
    parameters: dict[str, dict[str, Any]] | None = None,
    required: list[str] | None = None,
):
    def deco(fn: Callable[..., Any]) -> Callable[..., Any]:
        REGISTRY.register(
            Tool(
                name=name,
                description=description,
                parameters=parameters or {},
                required=required or [],
                fn=fn,
            )
        )
        return fn

    return deco


# ──────────────────────────────────────────────────────────────────────
# LIVE — Weather (HK Observatory)
# ──────────────────────────────────────────────────────────────────────

@tool(
    name="get_weather",
    description=(
        "Get the current Hong Kong weather report for a district: temperature, relative "
        "humidity, rainfall in the past hour, UV index, sky condition, and any active warning. "
        "Source: HK Observatory current report (rhrread)."
    ),
    parameters={
        "district": {
            "type": "string",
            "description": "HK district, e.g. 'Sham Shui Po', 'Central', 'Sha Tin', 'Tuen Mun'.",
        }
    },
    required=["district"],
)
def get_weather(district: str) -> dict:
    return weather.fetch_current_weather(district)


@tool(
    name="get_weather_forecast",
    description=(
        "Get the Hong Kong weather forecast: general situation, today/tomorrow outlook, and "
        "day-by-day 9-day forecast (weather, high/low temperature, humidity, wind, chance of rain). "
        "Territory-wide. Source: HK Observatory (flw + fnd)."
    ),
    parameters={
        "days": {
            "type": "integer",
            "description": "How many days of the 9-day forecast to return (1–9). Defaults to 5.",
        }
    },
    required=[],
)
def get_weather_forecast(days: int = 5) -> dict:
    return weather.fetch_weather_forecast(days)


# ──────────────────────────────────────────────────────────────────────
# LIVE — Air quality (HK EPD)
# ──────────────────────────────────────────────────────────────────────

@tool(
    name="get_air_quality",
    description=(
        "Get the current Hong Kong Air Quality Health Index (AQHI) for a district or monitoring station, "
        "with a health advisory tailored for elderly users. "
        "AQHI bands: 1–3 Low, 4 Moderate, 5–6 High, 7 Very High, 8–10+ Serious. "
        "Source: HK EPD live RSS feed (updated hourly). "
        "If the district doesn't match an EPD station, all stations are returned so the model can pick the nearest."
    ),
    parameters={
        "district": {
            "type": "string",
            "description": (
                "HK district or monitoring station name "
                "(e.g. 'Sham Shui Po', 'Central', 'Causeway Bay', 'Mong Kok', 'Tsuen Wan', 'Tung Chung'). "
                "Loose substring match against EPD station names."
            ),
        }
    },
    required=["district"],
)
def get_air_quality(district: str) -> dict:
    return aqhi.fetch_aqhi(district)


# ──────────────────────────────────────────────────────────────────────
# LIVE — Roads & traffic (HK Transport Department)
# ──────────────────────────────────────────────────────────────────────

@tool(
    name="get_traffic_advisory",
    description=(
        "Get current Hong Kong road incidents and special traffic arrangements: closures, construction, "
        "watermain works, accidents, lane restrictions, diversions, and event-related disruptions. "
        "Each incident includes the street/location, district, type, status (NEW/UPDATED/CLEARED), "
        "announcement time, and a full description. "
        "Source: HK Transport Department — Special Traffic News v2 (live XML, real-time). "
        "If the district has no incidents tagged, the 15 most recent feed-wide are returned."
    ),
    parameters={
        "district": {
            "type": "string",
            "description": (
                "HK district, street, or landmark name to filter by "
                "(e.g. 'Sham Shui Po', 'Wong Tai Sin', 'Nathan Road', 'Causeway Bay'). "
                "Loose substring match against district, location, and landmark fields. "
                "Omit to get feed-wide situational awareness."
            ),
        }
    },
    required=[],
)
def get_traffic_advisory(district: str | None = None) -> dict:
    return traffic.fetch_traffic_advisories(district)


# ──────────────────────────────────────────────────────────────────────
# LIVE — MTR (Next Train + MTR Bus)
# ──────────────────────────────────────────────────────────────────────

@tool(
    name="get_mtr_status",
    description=(
        "Get live next-train arrivals for a Hong Kong MTR station: upcoming trains in both directions "
        "(destination, scheduled time, minutes away), platform, and whether the line is delayed. "
        "Accepts either official codes (line 'TWL', station 'CEN') or names (line 'Tsuen Wan Line', "
        "station 'Central'). Source: MTR Next Train API (data.gov.hk)."
    ),
    parameters={
        "line": {
            "type": "string",
            "description": "MTR line code or name, e.g. 'TWL' / 'Tsuen Wan Line', 'EAL' / 'East Rail Line'.",
        },
        "station": {
            "type": "string",
            "description": "Station code or name on that line, e.g. 'CEN' / 'Central', 'SSP' / 'Sham Shui Po'.",
        },
    },
    required=["line", "station"],
)
def get_mtr_status(line: str, station: str) -> dict:
    return mtr.fetch_next_train(line, station)


@tool(
    name="get_mtr_bus_schedule",
    description=(
        "Get the next MTR Bus arrivals at a given stop on a given route, with minutes-to-arrival "
        "and remarks. Use only when the user is on an MTR Bus route (separate from KMB / Citybus). "
        "Source: MTR Bus API (data.gov.hk)."
    ),
    parameters={
        "route": {
            "type": "string",
            "description": "MTR Bus route number, e.g. 'K12', 'K65', 'K76'.",
        },
        "station_id": {
            "type": "string",
            "description": "MTR Bus stop id (numeric string), e.g. '20015144'.",
        },
        "language": {
            "type": "string",
            "description": "Response language: 'en' or 'zh'. Defaults to 'en'.",
        },
    },
    required=["route", "station_id"],
)
def get_mtr_bus_schedule(route: str, station_id: str, language: str = "en") -> dict:
    return mtr.fetch_mtr_bus_schedule(route, station_id, language)


# ──────────────────────────────────────────────────────────────────────
# LIVE — Local news (Hong Kong Free Press)
# ──────────────────────────────────────────────────────────────────────

@tool(
    name="get_hkfp_news",
    description=(
        "Get the most recent Hong Kong Free Press headlines (English-language HK news). "
        "Useful for current public affairs and events that may shape a decision scenario."
    ),
    parameters={
        "limit": {
            "type": "integer",
            "description": "Max items to return, 1–30. Defaults to 10.",
        }
    },
    required=[],
)
def get_hkfp_news(limit: int = 10) -> dict:
    return news.fetch_hkfp_news(limit)


# ──────────────────────────────────────────────────────────────────────
# LIVE — Web fallback (Firecrawl). Requires FIRECRAWL_API_KEY.
# ──────────────────────────────────────────────────────────────────────

@tool(
    name="web_search",
    description=(
        "Search the public web for current information (news, advisories, opening hours, official notices). "
        "Use ONLY when no other HK tool above can answer."
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
def web_search(query: str, limit: int = 5) -> dict:
    return web.search_web(query, limit)


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
def web_scrape(url: str, formats: list[str] | None = None) -> dict:
    return web.scrape_url(url, formats)


# ──────────────────────────────────────────────────────────────────────
# LIVE — Google Calendar (optional, env-gated)
# Requires GOOGLE_CALENDAR_API_KEY and either GOOGLE_CALENDAR_ID or per-call id.
# ──────────────────────────────────────────────────────────────────────

@tool(
    name="get_calendar_events",
    description=(
        "Get upcoming events from a shared (public) Google Calendar — community classes, "
        "clinic appointments, family schedules. Calendar must be public and shared."
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
def get_calendar_events(calendar_id: str | None = None, max_results: int = 10) -> dict:
    return calendar.fetch_calendar_events(calendar_id, max_results)


# ──────────────────────────────────────────────────────────────────────
# STUB — replace each return value with a real HK API call when wired.
# ──────────────────────────────────────────────────────────────────────

@tool(
    name="get_bus_status",
    description="Get current Hong Kong KMB / Citybus route status, frequency, and crowding.",
    parameters={
        "route": {"type": "string", "description": "Bus route number, e.g. '6', '914', '85K'."}
    },
    required=["route"],
)
def get_bus_status(route: str) -> dict:
    return {
        "route": route,
        "operator": "KMB",
        "status": "running",
        "frequency_min": 12,
        "crowding": "moderate",
        "next_arrival_min": 7,
        "air_conditioned": True,
        "source": "STUB — wire KMB/Citybus ETA",
    }


@tool(
    name="get_typhoon_signal",
    description="Get the current Hong Kong typhoon warning signal and rainstorm warnings.",
    parameters={},
    required=[],
)
def get_typhoon_signal() -> dict:
    return {
        "typhoon_signal": None,
        "rainstorm_warning": None,
        "thunderstorm_warning": True,
        "summary": "No typhoon signal in force. Thunderstorm warning issued for Kowloon and the New Territories.",
        "source": "STUB — wire HKO warnings",
    }


@tool(
    name="get_local_events",
    description="Get notable public events, gatherings, and crowd advisories in Hong Kong for today.",
    parameters={
        "district": {"type": "string", "description": "District filter."}
    },
    required=["district"],
)
def get_local_events(district: str) -> dict:
    return {
        "district": district,
        "events": [
            {
                "name": "Senior fitness class",
                "venue": "Sham Shui Po Sports Centre",
                "time": "15:00–16:00",
                "expected_crowd": "small",
            }
        ],
        "source": "STUB — wire LCSD events feed",
    }


@tool(
    name="get_pharmacy_hours",
    description="Find a nearby pharmacy and whether it is open now.",
    parameters={
        "district": {"type": "string", "description": "District to search."}
    },
    required=["district"],
)
def get_pharmacy_hours(district: str) -> dict:
    return {
        "district": district,
        "pharmacy": {
            "name": "Watsons Sham Shui Po",
            "address": "G/F, 123 Cheung Sha Wan Road",
            "open_now": True,
            "closes_at": "22:00",
        },
        "source": "STUB — wire pharmacy directory",
    }
