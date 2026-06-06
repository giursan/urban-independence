"""MTR — Next Train + MTR Bus (data.gov.hk real-time feeds)."""

from __future__ import annotations

import httpx

NEXT_TRAIN_URL = "https://rt.data.gov.hk/v1/transport/mtr/getSchedule.php"
MTR_BUS_URL = "https://rt.data.gov.hk/v1/transport/mtr/bus/getSchedule"

MTR_LINES = {
    "AEL": "Airport Express",
    "TCL": "Tung Chung Line",
    "TML": "Tuen Ma Line",
    "TKL": "Tseung Kwan O Line",
    "EAL": "East Rail Line",
    "SIL": "South Island Line",
    "TWL": "Tsuen Wan Line",
    "ISL": "Island Line",
    "KTL": "Kwun Tong Line",
    "DRL": "Disneyland Resort Line",
}

MTR_STATIONS = {
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

_LINE_BY_NAME = {v.lower(): k for k, v in MTR_LINES.items()}
_STATION_BY_NAME = {v.lower(): k for k, v in MTR_STATIONS.items()}
_STATION_BY_NAME["price edward"] = "PRE"


def _resolve(value: str, codes: dict[str, str], by_name: dict[str, str], kind: str) -> str:
    v = value.strip()
    if v.upper() in codes:
        return v.upper()
    if v.lower() in by_name:
        return by_name[v.lower()]
    raise ValueError(f"unknown MTR {kind}: {value!r}")


async def fetch_next_train(line: str, station: str) -> dict:
    line_code = _resolve(line, MTR_LINES, _LINE_BY_NAME, "line")
    sta_code = _resolve(station, MTR_STATIONS, _STATION_BY_NAME, "station")

    async with httpx.AsyncClient(timeout=15.0) as c:
        r = await c.get(NEXT_TRAIN_URL, params={"line": line_code, "sta": sta_code})
        r.raise_for_status()
        body = r.json()
    if body.get("status") != 1:
        raise RuntimeError(f"MTR Next Train feed error: {body.get('message', 'unknown')}")
    block = body["data"][f"{line_code}-{sta_code}"]

    def norm(rows: list[dict]) -> list[dict]:
        return [
            {
                "dest": MTR_STATIONS.get(row.get("dest"), row.get("dest")),
                "time": (row.get("time") or "")[11:16],
                "mins": int(row["ttnt"]) if str(row.get("ttnt", "")).isdigit() else None,
                "platform": row.get("plat"),
            }
            for row in rows
        ]

    schedule = {"UP": norm(block.get("UP", [])), "DOWN": norm(block.get("DOWN", []))}
    all_mins = [t["mins"] for d in schedule.values() for t in d if t["mins"] is not None]

    return {
        "line": MTR_LINES[line_code],
        "line_code": line_code,
        "station": MTR_STATIONS[sta_code],
        "station_code": sta_code,
        "is_delayed": body.get("isdelay") == "Y",
        "next_arrival_min": min(all_mins) if all_mins else None,
        "schedule": schedule,
        "source": "MTR Next Train (data.gov.hk)",
        "source_url": NEXT_TRAIN_URL,
    }


async def fetch_mtr_bus_schedule(route: str, station_id: str, language: str = "en") -> dict:
    payload = {
        "language": language,
        "routeName": route.upper(),
        "stationId": station_id,
    }
    async with httpx.AsyncClient(timeout=15.0) as c:
        r = await c.post(MTR_BUS_URL, json=payload)
        r.raise_for_status()
        data = r.json()

    arrivals: list[dict] = []
    for stop in data.get("busStop") or []:
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
        "source": "MTR Bus (data.gov.hk)",
        "source_url": MTR_BUS_URL,
    }
