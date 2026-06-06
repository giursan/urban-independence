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


@tool(
    name="get_mtr_status",
    description="Get current operational status and delays of Hong Kong MTR lines.",
    parameters={
        "line": {
            "type": "string",
            "description": "Optional MTR line (e.g. 'Tsuen Wan', 'Island', 'Kwun Tong'). Omit for all lines.",
        }
    },
    required=[],
)
def get_mtr_status(line: str | None = None) -> dict:
    lines = [
        {"line": "Tsuen Wan", "status": "delayed", "delay_min": 15, "reason": "signalling fault near Mong Kok"},
        {"line": "Island", "status": "normal", "delay_min": 0},
        {"line": "Kwun Tong", "status": "normal", "delay_min": 0},
        {"line": "Tung Chung", "status": "normal", "delay_min": 0},
    ]
    if line:
        lines = [l for l in lines if l["line"].lower() == line.lower()]
    return {"lines": lines, "source": "STUB — wire MTR Next Train API"}


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


# ──────────────────────────────────────────────────────────────────────
# LIVE TOOLS — registered via @tool in the `tools/` package.
# Import for side effects so REGISTRY is populated at boot.
# ──────────────────────────────────────────────────────────────────────

import tools  # noqa: E402, F401
