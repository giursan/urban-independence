"""Tool registry for live Hong Kong data sources.

How to add a new tool:

    from agent.tools import REGISTRY, tool

    @tool(
        name="get_mtr_status",
        description="Get current operational status of Hong Kong MTR lines.",
        parameters={
            "line": {
                "type": "string",
                "description": "Optional MTR line name (e.g. 'Tsuen Wan'). Omit for all lines.",
            },
        },
        required=[],
    )
    def get_mtr_status(line: str | None = None) -> dict:
        # call the real API here
        ...

The orchestrator picks tools up from REGISTRY automatically.
"""

from __future__ import annotations

import inspect
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

import httpx


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
# STUB TOOLS — replace each return value with a real HK API call.
# The orchestrator works end-to-end against these mocks today.
# ──────────────────────────────────────────────────────────────────────


@tool(
    name="get_weather",
    description=(
        "Get current Hong Kong weather (temperature, humidity, condition, feels-like) "
        "for a specific district. Source: HK Observatory."
    ),
    parameters={
        "district": {
            "type": "string",
            "description": "Hong Kong district, e.g. 'Sham Shui Po', 'Central', 'Causeway Bay'.",
        }
    },
    required=["district"],
)
def get_weather(district: str) -> dict:
    return {
        "district": district,
        "temp_c": 32,
        "feels_like_c": 38,
        "humidity_pct": 84,
        "condition": "sunny with patchy clouds",
        "uv_index": 9,
        "rainfall_mm_last_hour": 0,
        "source": "STUB — wire HK Observatory open data",
    }


@tool(
    name="get_air_quality",
    description="Get current Hong Kong Air Quality Health Index (AQHI) for a district.",
    parameters={
        "district": {"type": "string", "description": "Hong Kong district name."}
    },
    required=["district"],
)
def get_air_quality(district: str) -> dict:
    return {
        "district": district,
        "aqhi": 6,
        "band": "High",
        "main_pollutant": "PM2.5",
        "health_advisory": "People with heart or respiratory illnesses should reduce outdoor physical exertion.",
        "source": "STUB — wire EPD AQHI feed",
    }


# ── MTR Next Train (live) ─────────────────────────────────────────────
# Official HK Open Data "MTR Next Train" feed (data.gov.hk). Station/line
# codes are from github.com/sarkrui/MTR-Next-Train's reference tables.
# Returns upcoming arrivals per direction plus the `isdelay` flag.

_MTR_OFFICIAL = "https://rt.data.gov.hk/v1/transport/mtr/getSchedule.php"

_MTR_LINES = {
    "AEL": "Airport Express",
    "TCL": "Tung Chung Line",
    "TML": "Tuen Ma Line",
    "TKL": "Tseung Kwan O Line",
    "EAL": "East Rail Line",
    "SIL": "South Island Line",
    "TWL": "Tsuen Wan Line",
}

_MTR_STATIONS = {
    "HOK": "Hong Kong", "KOW": "Kowloon", "TSY": "Tsing Yi", "AIR": "Airport",
    "AWE": "AsiaWorld Expo", "OLY": "Olympic", "NAC": "Nam Cheong", "LAK": "Lai King",
    "SUN": "Sunny Bay", "TUC": "Tung Chung", "WKS": "Wu Kai Sha", "MOS": "Ma On Shan",
    "HEO": "Heng On", "TSH": "Tai Shui Hang", "SHM": "Shek Mun", "CIO": "City One",
    "STW": "Sha Tin Wai", "CKT": "Che Kung Temple", "TAW": "Tai Wai", "HIK": "Hin Keng",
    "DIH": "Diamond Hill", "KAT": "Kai Tak", "SUW": "Sung Wong Toi", "TKW": "To Kwa Wan",
    "HOM": "Ho Man Tin", "HUH": "Hung Hom", "ETS": "East Tsim Sha Tsui", "AUS": "Austin",
    "MEF": "Mei Foo", "TWW": "Tsuen Wan West", "KSR": "Kam Sheung Road", "YUL": "Yuen Long",
    "LOP": "Long Ping", "TIS": "Tin Shui Wai", "SIH": "Siu Hong", "TUM": "Tuen Mun",
    "NOP": "North Point", "QUB": "Quarry Bay", "YAT": "Yau Tong", "TIK": "Tiu Keng Leng",
    "TKO": "Tseung Kwan O", "LHP": "LOHAS Park", "HAH": "Hang Hau", "POA": "Po Lam",
    "ADM": "Admiralty", "EXC": "Exhibition Centre", "MKK": "Mong Kok East",
    "KOT": "Kowloon Tong", "SHT": "Sha Tin", "FOT": "Fo Tan", "RAC": "Racecourse",
    "UNI": "University", "TAP": "Tai Po Market", "TWO": "Tai Wo", "FAN": "Fanling",
    "SHS": "Sheung Shui", "LOW": "Lo Wu", "LMC": "Lok Ma Chau", "OCP": "Ocean Park",
    "WCH": "Wong Chuk Hang", "LET": "Lei Tung", "SOH": "South Horizons", "CEN": "Central",
    "TST": "Tsim Sha Tsui", "JOR": "Jordan", "YMT": "Yau Ma Tei", "MOK": "Mong Kok",
    "PRE": "Prince Edward", "SSP": "Sham Shui Po", "CSW": "Cheung Sha Wan",
    "LCK": "Lai Chi Kok", "KWF": "Kwai Fong", "KWH": "Kwai Hing", "TWH": "Tai Wo Hau",
    "TSW": "Tsuen Wan",
}

# name → code (case-insensitive), tolerant of the "Price Edward" typo in the source tables.
_MTR_LINE_BY_NAME = {v.lower(): k for k, v in _MTR_LINES.items()}
_MTR_STATION_BY_NAME = {v.lower(): k for k, v in _MTR_STATIONS.items()}
_MTR_STATION_BY_NAME["price edward"] = "PRE"


def _resolve_mtr_code(value: str, codes: dict[str, str], by_name: dict[str, str], kind: str) -> str:
    """Accept either an official code (e.g. 'TWL') or a human name (e.g. 'Tsuen Wan Line')."""
    v = value.strip()
    if v.upper() in codes:
        return v.upper()
    if v.lower() in by_name:
        return by_name[v.lower()]
    raise ValueError(f"unknown MTR {kind}: {value!r}")


@tool(
    name="get_mtr_status",
    description=(
        "Get live next-train arrivals for a Hong Kong MTR station: upcoming trains in both "
        "directions (destination, scheduled time, minutes away) and whether the line is delayed. "
        "Requires both an MTR line and a station; you may pass official codes (line 'TWL', "
        "station 'CEN') or names (line 'Tsuen Wan Line', station 'Central'). "
        "Source: MTR Next Train API."
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
    line_code = _resolve_mtr_code(line, _MTR_LINES, _MTR_LINE_BY_NAME, "line")
    sta_code = _resolve_mtr_code(station, _MTR_STATIONS, _MTR_STATION_BY_NAME, "station")

    r = httpx.get(_MTR_OFFICIAL, params={"line": line_code, "sta": sta_code}, timeout=15)
    r.raise_for_status()
    body = r.json()
    if body.get("status") != 1:
        raise RuntimeError(f"MTR Next Train feed error: {body.get('message', 'unknown')}")
    block = body["data"][f"{line_code}-{sta_code}"]

    def norm(rows: list[dict]) -> list[dict]:
        return [
            {
                "dest": _MTR_STATIONS.get(row.get("dest"), row.get("dest")),
                "time": (row.get("time") or "")[11:16],
                "mins": int(row["ttnt"]) if str(row.get("ttnt", "")).isdigit() else None,
                "platform": row.get("plat"),
            }
            for row in rows
        ]

    schedule = {"UP": norm(block.get("UP", [])), "DOWN": norm(block.get("DOWN", []))}
    all_mins = [t["mins"] for d in schedule.values() for t in d if t["mins"] is not None]

    return {
        "line": _MTR_LINES[line_code],
        "line_code": line_code,
        "station": _MTR_STATIONS[sta_code],
        "station_code": sta_code,
        "is_delayed": body.get("isdelay") == "Y",
        "next_arrival_min": min(all_mins) if all_mins else None,
        "schedule": schedule,
        "source": "MTR Next Train API (data.gov.hk)",
    }


@tool(
    name="get_bus_status",
    description="Get current Hong Kong bus route status, frequency, and crowding.",
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
    name="get_traffic_advisory",
    description="Get current traffic incidents, road closures, and event-related disruptions in Hong Kong.",
    parameters={
        "district": {"type": "string", "description": "District to check."}
    },
    required=["district"],
)
def get_traffic_advisory(district: str) -> dict:
    return {
        "district": district,
        "incidents": [
            {
                "location": "Nathan Road southbound",
                "type": "accident",
                "severity": "moderate",
                "expected_clear_min": 30,
            }
        ],
        "source": "STUB — wire Transport Department feed",
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
