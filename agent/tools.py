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


# ── HK Observatory weather (live) ─────────────────────────────────────
# Official HKO Open Data "Weather Information" API (data.weather.gov.hk).
# One endpoint, selected by `dataType`. All territory-wide; the current
# report (rhrread) breaks temperature/rainfall down by station/district.

_HKO_WEATHER = "https://data.weather.gov.hk/weatherAPI/opendata/weather.php"

# HKO weather-icon code → human description (current-condition icons).
_HKO_ICONS = {
    50: "sunny", 51: "sunny periods", 52: "sunny intervals",
    53: "sunny periods with a few showers", 54: "sunny intervals with showers",
    60: "cloudy", 61: "overcast", 62: "light rain", 63: "rain", 64: "heavy rain",
    65: "thunderstorms", 70: "fine", 71: "fine", 72: "fine", 73: "fine",
    74: "fine", 75: "fine", 76: "mainly cloudy", 77: "mainly fine",
    80: "windy", 81: "dry", 82: "humid", 83: "fog", 84: "mist", 85: "haze",
    90: "hot", 91: "warm", 92: "cool", 93: "cold",
}


def _hko_get(data_type: str, lang: str = "en") -> dict:
    r = httpx.get(_HKO_WEATHER, params={"dataType": data_type, "lang": lang}, timeout=15)
    r.raise_for_status()
    return r.json()


def _match_place(district: str, rows: list[dict], default: str | None = None) -> dict | None:
    """Best-effort match of a requested district to an HKO place reading."""
    d = district.strip().lower()
    for row in rows:
        place = str(row.get("place", "")).lower()
        if place == d or d in place or place in d:
            return row
    if default:
        for row in rows:
            if str(row.get("place", "")).lower() == default.lower():
                return row
    return None


@tool(
    name="get_weather",
    description=(
        "Get the current Hong Kong weather report for a district: temperature, relative "
        "humidity, rainfall in the past hour, UV index, and sky condition. Source: HK Observatory."
    ),
    parameters={
        "district": {
            "type": "string",
            "description": "Hong Kong district, e.g. 'Sham Shui Po', 'Central', 'Sha Tin', 'Tuen Mun'.",
        }
    },
    required=["district"],
)
def get_weather(district: str) -> dict:
    d = _hko_get("rhrread")

    temp_rows = d.get("temperature", {}).get("data", [])
    temp = _match_place(district, temp_rows, default="Hong Kong Observatory")
    rain_rows = d.get("rainfall", {}).get("data", [])
    rain = _match_place(district, rain_rows)

    hum_rows = d.get("humidity", {}).get("data", [])
    humidity_pct = hum_rows[0].get("value") if hum_rows else None

    uv = d.get("uvindex")
    uv_index = None
    if isinstance(uv, dict) and uv.get("data"):
        uv_index = uv["data"][0].get("value")

    icons = d.get("icon") or []
    condition = _HKO_ICONS.get(icons[0]) if icons else None

    return {
        "district": district,
        "temp_c": temp.get("value") if temp else None,
        "temp_station": temp.get("place") if temp else None,
        "humidity_pct": humidity_pct,
        "rainfall_mm_last_hour": (rain.get("max") if rain else None),
        "uv_index": uv_index,
        "condition": condition,
        "warning_message": d.get("warningMessage") or None,
        "update_time": d.get("temperature", {}).get("recordTime") or d.get("updateTime"),
        "source": "HK Observatory current weather report (rhrread)",
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
    description=(
        "Get all Hong Kong weather warnings currently in force: typhoon (tropical cyclone) "
        "signal, rainstorm warning, thunderstorm warning, plus any hot/cold/monsoon/landslip/"
        "flooding warnings and special weather tips. Source: HK Observatory."
    ),
    parameters={},
    required=[],
)
def get_typhoon_signal() -> dict:
    warns = _hko_get("warnsum")  # {} when nothing is in force

    def info(key: str) -> dict | None:
        w = warns.get(key)
        if not isinstance(w, dict):
            return None
        return {
            "name": w.get("name"),
            "code": w.get("code"),
            "action": w.get("actionCode"),
            "issued": w.get("issueTime"),
        }

    tc = info("WTCSGNL")
    rain = info("WRAIN")
    ts = info("WTS")
    others = [
        i for k in ("WHOT", "WCOLD", "WMSGNL", "WFROST", "WFIRE", "WL", "WFNTSA", "WTMW")
        if (i := info(k))
    ]

    tips_raw = _hko_get("swt").get("swt", [])
    tips = [t.get("desc") for t in tips_raw if t.get("desc")]

    active = [w["name"] for w in (tc, rain, ts, *others) if w]
    summary = (
        "Weather warnings in force: " + "; ".join(active)
        if active
        else "No weather warnings in force."
    )

    return {
        "typhoon_signal": tc["code"] if tc else None,
        "typhoon_signal_name": tc["name"] if tc else None,
        "rainstorm_warning": rain["code"] if rain else None,
        "thunderstorm_warning": ts is not None,
        "other_warnings": others,
        "special_weather_tips": tips,
        "summary": summary,
        "source": "HK Observatory weather warning summary (warnsum) + special weather tips (swt)",
    }


@tool(
    name="get_weather_forecast",
    description=(
        "Get the Hong Kong weather forecast: the general situation, today/tomorrow's local "
        "forecast and outlook, and the day-by-day 9-day forecast (weather, high/low temperature, "
        "humidity, wind, chance of rain). Territory-wide. Source: HK Observatory."
    ),
    parameters={
        "days": {
            "type": "integer",
            "description": "How many days of the 9-day forecast to return (1-9). Defaults to 5.",
        }
    },
    required=[],
)
def get_weather_forecast(days: int = 5) -> dict:
    days = max(1, min(days, 9))
    flw = _hko_get("flw")
    fnd = _hko_get("fnd")

    daily = []
    for f in fnd.get("weatherForecast", [])[:days]:
        date = f.get("forecastDate", "")
        daily.append(
            {
                "date": f"{date[:4]}-{date[4:6]}-{date[6:]}" if len(date) == 8 else date,
                "week": f.get("week"),
                "weather": f.get("forecastWeather"),
                "max_temp_c": f.get("forecastMaxtemp", {}).get("value"),
                "min_temp_c": f.get("forecastMintemp", {}).get("value"),
                "max_humidity_pct": f.get("forecastMaxrh", {}).get("value"),
                "min_humidity_pct": f.get("forecastMinrh", {}).get("value"),
                "wind": f.get("forecastWind"),
                "chance_of_rain": f.get("PSR"),
            }
        )

    return {
        "general_situation": flw.get("generalSituation"),
        "tropical_cyclone_info": flw.get("tcInfo") or None,
        "today": {
            "period": flw.get("forecastPeriod"),
            "description": flw.get("forecastDesc"),
            "outlook": flw.get("outlook"),
        },
        "nine_day_forecast": daily,
        "update_time": flw.get("updateTime"),
        "source": "HK Observatory local weather forecast (flw) + 9-day forecast (fnd)",
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
