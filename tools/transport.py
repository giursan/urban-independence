"""Transport tools — MTR Next Train + MTR Bus (data.gov.hk real-time feeds).

Registered with the shared REGISTRY in agent.tools via the @tool decorator.

No API key required — these are public data.gov.hk endpoints.

Refs:
    Next Train: https://opendata.mtr.com.hk/doc/Next_Train_API_Spec_v1.6.pdf
    MTR Bus:    https://opendata.mtr.com.hk/doc/MTR_BUS_API_Spec_v1.13.pdf
"""

from __future__ import annotations

from typing import Any

import httpx

from agent.tools import tool

NEXT_TRAIN_URL = "https://rt.data.gov.hk/v1/transport/mtr/getSchedule.php"
MTR_BUS_URL = "https://rt.data.gov.hk/v1/transport/mtr/bus/getSchedule"


@tool(
    name="get_next_train",
    description=(
        "Get the next MTR train arrivals for a specific line and station, including "
        "direction (UP/DOWN), platform, and minutes to arrival."
    ),
    parameters={
        "line": {
            "type": "string",
            "description": "MTR line code, e.g. 'TWL' (Tsuen Wan), 'ISL' (Island), 'KTL' (Kwun Tong), 'TCL' (Tung Chung), 'TML' (Tuen Ma), 'EAL' (East Rail), 'SIL' (South Island), 'AEL' (Airport Express), 'DRL' (Disneyland Resort).",
        },
        "station": {
            "type": "string",
            "description": "Station code, e.g. 'CEN' (Central), 'ADM' (Admiralty), 'MOK' (Mong Kok), 'SSP' (Sham Shui Po).",
        },
    },
    required=["line", "station"],
)
def get_next_train(line: str, station: str) -> dict[str, Any]:
    params = {"line": line.upper(), "sta": station.upper(), "lang": "EN"}
    with httpx.Client(timeout=15.0) as c:
        r = c.get(NEXT_TRAIN_URL, params=params)
        r.raise_for_status()
        data = r.json()

    if data.get("status") != 1:
        return {
            "line": line,
            "station": station,
            "status": "unavailable",
            "message": data.get("message") or data.get("url"),
            "raw": data,
        }

    key = f"{line.upper()}-{station.upper()}"
    block = (data.get("data") or {}).get(key, {})
    return {
        "line": line.upper(),
        "station": station.upper(),
        "system_time": data.get("sys_time"),
        "current_time": data.get("curr_time"),
        "up": block.get("UP", []),
        "down": block.get("DOWN", []),
    }


@tool(
    name="get_mtr_bus_schedule",
    description=(
        "Get the next MTR Bus arrivals at a given stop on a given route, including "
        "minutes to arrival and bus remarks."
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
def get_mtr_bus_schedule(
    route: str, station_id: str, language: str = "en"
) -> dict[str, Any]:
    payload = {
        "language": language,
        "routeName": route.upper(),
        "stationId": station_id,
    }
    with httpx.Client(timeout=15.0) as c:
        r = c.post(MTR_BUS_URL, json=payload)
        r.raise_for_status()
        data = r.json()

    routes = data.get("busStop") or []
    arrivals: list[dict[str, Any]] = []
    for stop in routes:
        for bus in stop.get("bus", []):
            arrivals.append(
                {
                    "bus_id": bus.get("busId"),
                    "arrival_time_text": bus.get("arrivalTimeText"),
                    "arrival_time_in_second": bus.get("arrivalTimeInSecond"),
                    "departure_time_text": bus.get("departureTimeText"),
                    "remarks": bus.get("busRemark"),
                    "is_delayed": bus.get("isDelayed") == "1",
                }
            )

    return {
        "route": route.upper(),
        "station_id": station_id,
        "status_code": data.get("routeStatusRemarkTitle"),
        "arrivals": arrivals,
    }
