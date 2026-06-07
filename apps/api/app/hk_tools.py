"""Live Hong Kong tools wired onto the companion agent.

Importing this module registers ~10 tools on `companion_agent` via pydantic-ai's
`@tool_plain` decorator — they take no user context and only read live data
from public HK government / city feeds. The companion uses them naturally
in conversation ("how's the air today?", "is the train running?").

Tool inputs/return shapes are deliberately simple dicts so the model can quote
specific values back to the user ("AQHI is 4 — moderate — in Central").

Env vars (optional per-tool):
    FIRECRAWL_API_KEY        — web_search, web_scrape
    GOOGLE_CALENDAR_API_KEY  — get_calendar_events
    GOOGLE_CALENDAR_ID       — default calendar for get_calendar_events
"""

from __future__ import annotations

import functools
import logging
from collections.abc import Awaitable, Callable
from typing import Any

from .companion import companion_agent
from .sources import aqhi, calendar, mtr, news, traffic, web, weather

logger = logging.getLogger(__name__)


def _live_tool(fn: Callable[..., Awaitable[dict]]) -> Callable[..., Awaitable[dict]]:
    """Keep a live-data tool from ever crashing the agent turn.

    These tools call flaky external feeds and take model-chosen arguments, so
    they can raise: timeouts, HTTP errors, parse errors, or a bad/placeholder
    argument (e.g. line='Any'). An unhandled exception kills the whole agent
    run and surfaces to the caller as an "application error". Instead we log it
    and hand the model a structured error it can recover from — usually by
    telling the person briefly or asking for the missing detail and retrying.

    `functools.wraps` preserves the signature and docstring so pydantic-ai still
    generates the correct tool schema.
    """

    @functools.wraps(fn)
    async def wrapper(*args: Any, **kwargs: Any) -> dict:
        try:
            return await fn(*args, **kwargs)
        except Exception as exc:  # noqa: BLE001 — tools must never crash the turn
            logger.warning("live tool %s failed: %s", fn.__name__, exc)
            return {
                "error": f"The {fn.__name__} tool could not complete: {exc}",
                "hint": (
                    "Tell the person briefly that this information isn't available "
                    "right now. If a value looks wrong or missing (e.g. which MTR "
                    "line or station), ask them for it and try again."
                ),
            }

    return wrapper


@companion_agent.tool_plain
@_live_tool
async def get_weather(district: str = "Hong Kong Observatory") -> dict:
    """Current Hong Kong weather: temperature, humidity, rainfall, UV, condition.

    Use when the person mentions going out, the weather, feeling hot/cold, or
    when planning anything outdoors. `district` accepts an HK district name
    (e.g. "Central", "Sha Tin", "Tuen Mun") — the HKO station nearest that
    place is returned.
    """
    return await weather.fetch_current_weather(district)


@companion_agent.tool_plain
@_live_tool
async def get_weather_forecast(days: int = 5) -> dict:
    """Hong Kong weather forecast for the next 1–9 days.

    Use when the person is planning ahead (visits, outings, errands later in
    the week). Returns daily highs, lows, chance of rain, and the HKO general
    situation including any tropical-cyclone info.
    """
    return await weather.fetch_weather_forecast(days)


@companion_agent.tool_plain
@_live_tool
async def get_air_quality(district: str) -> dict:
    """Live air-quality (AQHI) for a Hong Kong district.

    Important for elderly users with heart or respiratory conditions — the
    response includes plain-language health advisory for older adults. Use
    proactively when air quality could affect a planned activity outdoors.
    `district` is a substring match against EPD station names (e.g. "Central",
    "Causeway Bay", "Sham Shui Po"); if nothing matches we return all stations.
    """
    return await aqhi.fetch_aqhi(district)


@companion_agent.tool_plain
@_live_tool
async def get_traffic_advisory(district: str | None = None) -> dict:
    """Real-time HK Transport Department incident feed: closures, accidents,
    construction, watermain works, special arrangements.

    Use when the person is planning to go somewhere or worried about getting
    stuck. Pass a district / area name to filter; omit for a feed-wide view.
    """
    return await traffic.fetch_traffic_advisories(district)


@companion_agent.tool_plain
@_live_tool
async def get_mtr_status(line: str, station: str) -> dict:
    """Next MTR train arrivals and delay status at a given station on a given line.

    Accepts either MTR line/station codes ("TWL", "CEN") or full names
    ("Tsuen Wan Line", "Central"). Returns next arrival in minutes for each
    direction, plus a delay flag.
    """
    return await mtr.fetch_next_train(line, station)


@companion_agent.tool_plain
@_live_tool
async def get_mtr_bus_schedule(route: str, station_id: str) -> dict:
    """MTR Bus stop ETAs for a given route and stop ID.

    Use when the person depends on the MTR Bus network (mostly New Territories
    feeder routes). `station_id` is the data.gov.hk stop identifier.
    """
    return await mtr.fetch_mtr_bus_schedule(route, station_id)


@companion_agent.tool_plain
@_live_tool
async def get_hkfp_news(limit: int = 5) -> dict:
    """Latest Hong Kong news headlines from Hong Kong Free Press.

    Use when the person asks what's going on, references "the news", or
    when current events would be relevant to a topic they brought up.
    """
    return await news.fetch_hkfp_news(limit)


@companion_agent.tool_plain
@_live_tool
async def web_search(query: str, limit: int = 5) -> dict:
    """General web search (Firecrawl).

    Fallback when no specific HK tool covers the question — e.g. an obscure
    venue's hours, a specific government notice, a news story not on HKFP.
    Returns title / URL / short description per result.
    """
    return await web.search_web(query, limit)


@companion_agent.tool_plain
@_live_tool
async def web_scrape(url: str) -> dict:
    """Fetch and parse a specific web page as markdown (Firecrawl).

    Use after web_search has identified a relevant URL, or when the person
    references a specific page they want you to read.
    """
    return await web.scrape_url(url)


@companion_agent.tool_plain
@_live_tool
async def get_calendar_events(calendar_id: str | None = None, max_results: int = 10) -> dict:
    """Upcoming events from the configured Google Calendar.

    Use when the person asks about their schedule, what's coming up, or
    references an event they think is on the calendar. Uses `calendar_id` when
    provided, otherwise the default GOOGLE_CALENDAR_ID set in the API environment.
    """
    return await calendar.fetch_calendar_events(calendar_id=calendar_id, max_results=max_results)
