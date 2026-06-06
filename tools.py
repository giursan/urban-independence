import json
from pathlib import Path

DATA_DIR = Path(__file__).parent / "data"


def _load(name: str):
    with open(DATA_DIR / name) as f:
        return json.load(f)


TOOL_DEFS = [
    {
        "name": "get_calendar",
        "description": "Get the caller's personal calendar entries within a date range. Use this for anything about their appointments, reminders, or what they have planned.",
        "input_schema": {
            "type": "object",
            "properties": {
                "start_date": {"type": "string", "description": "Start date in YYYY-MM-DD format, inclusive."},
                "end_date": {"type": "string", "description": "End date in YYYY-MM-DD format, inclusive. Use the same date as start_date for a single day."},
            },
            "required": ["start_date", "end_date"],
        },
    },
    {
        "name": "get_city_events",
        "description": "Get public events happening in the city on a specific date. Use this for markets, concerts, marathons, public gatherings.",
        "input_schema": {
            "type": "object",
            "properties": {
                "date": {"type": "string", "description": "Date in YYYY-MM-DD format."},
            },
            "required": ["date"],
        },
    },
    {
        "name": "get_route_advisory",
        "description": "Get warnings about a route on a given date: closures, roadworks, weather, marathons. Use this when the caller asks whether they can or should travel somewhere.",
        "input_schema": {
            "type": "object",
            "properties": {
                "date": {"type": "string", "description": "Date in YYYY-MM-DD format."},
                "from_location": {"type": "string", "description": "Starting location, in plain words (e.g. 'home', 'Marktplatz')."},
                "to_location": {"type": "string", "description": "Destination, in plain words."},
            },
            "required": ["date", "from_location", "to_location"],
        },
    },
    {
        "name": "get_elder_profile",
        "description": "Get the caller's profile: their preferred name, family contacts, birthdays, and notes the family has written for the assistant. Call this once at the start of a conversation if you don't know their name yet.",
        "input_schema": {"type": "object", "properties": {}},
    },
]


def get_calendar(start_date: str, end_date: str):
    entries = _load("calendar.json")
    hits = [e for e in entries if start_date <= e["date"] <= end_date]
    return {"entries": hits, "count": len(hits)}


def get_city_events(date: str):
    entries = _load("events.json")
    hits = [e for e in entries if e["date"] == date]
    return {"events": hits, "count": len(hits)}


def get_route_advisory(date: str, from_location: str, to_location: str):
    entries = _load("advisories.json")
    f = from_location.lower()
    t = to_location.lower()
    hits = []
    for e in entries:
        if e["date"] != date:
            continue
        affected = [a.lower() for a in e["affects"]]
        if "whole city" in affected or any(a in f or a in t or f in a or t in a for a in affected):
            hits.append(e)
    return {"advisories": hits, "count": len(hits)}


def get_elder_profile():
    return _load("profile.json")


DISPATCH = {
    "get_calendar": get_calendar,
    "get_city_events": get_city_events,
    "get_route_advisory": get_route_advisory,
    "get_elder_profile": get_elder_profile,
}


def run_tool(name: str, args: dict):
    fn = DISPATCH[name]
    return fn(**args)
