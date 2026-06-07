"""Live smoke test of every key-free HK source module.

Runs each fetch_* coroutine against the real upstream feed and prints a
compact result. Anything that raises is a real bug (async conversion,
upstream drift, parsing). Anything that returns and contains the expected
keys is considered green.

Run with:  uv run python scripts/smoke_hk_sources.py
"""

from __future__ import annotations

import asyncio
import json
import sys
import time
from typing import Awaitable, Callable

from app.sources import aqhi, mtr, news, traffic, weather


def _trunc(obj, n: int = 240) -> str:
    s = json.dumps(obj, default=str)
    return s if len(s) <= n else s[: n - 1] + "…"


async def _run_one(name: str, coro: Awaitable, expect_keys: list[str]) -> tuple[bool, str]:
    t0 = time.perf_counter()
    try:
        result = await coro
        dt = time.perf_counter() - t0
        missing = [k for k in expect_keys if k not in result]
        if missing:
            return False, f"{name:35s} MISSING KEYS {missing} ({dt*1000:.0f}ms) :: {_trunc(result)}"
        return True, f"{name:35s} OK ({dt*1000:.0f}ms) :: {_trunc(result)}"
    except Exception as e:
        dt = time.perf_counter() - t0
        return False, f"{name:35s} RAISED {type(e).__name__}: {e} ({dt*1000:.0f}ms)"


async def main() -> int:
    cases: list[tuple[str, Awaitable, list[str]]] = [
        (
            "weather.fetch_current_weather('Central')",
            weather.fetch_current_weather("Central"),
            ["district", "temp_c", "source", "source_url"],
        ),
        (
            "weather.fetch_weather_forecast(days=3)",
            weather.fetch_weather_forecast(3),
            ["nine_day_forecast", "general_situation", "source_url"],
        ),
        (
            "aqhi.fetch_aqhi('Central')",
            aqhi.fetch_aqhi("Central"),
            ["matched", "stations", "source", "source_url"],
        ),
        (
            "aqhi.fetch_aqhi('Tuen Mun')",
            aqhi.fetch_aqhi("Tuen Mun"),
            ["matched", "stations"],
        ),
        (
            "traffic.fetch_traffic_advisories(None)",
            traffic.fetch_traffic_advisories(None),
            ["matched", "incidents", "feed_total"],
        ),
        (
            "traffic.fetch_traffic_advisories('Wong Tai Sin')",
            traffic.fetch_traffic_advisories("Wong Tai Sin"),
            ["matched", "incidents"],
        ),
        (
            "mtr.fetch_next_train('Tsuen Wan Line','Central')",
            mtr.fetch_next_train("Tsuen Wan Line", "Central"),
            ["line", "station", "schedule", "next_arrival_min"],
        ),
        (
            "mtr.fetch_next_train('EAL','Hung Hom')  # codes",
            mtr.fetch_next_train("EAL", "HUH"),
            ["line", "station", "schedule"],
        ),
        (
            "news.fetch_hkfp_news(limit=3)",
            news.fetch_hkfp_news(3),
            ["items", "source", "source_url"],
        ),
    ]

    results = await asyncio.gather(*(_run_one(n, c, k) for n, c, k in cases))

    print("=" * 80)
    print("HK SOURCE SMOKE TEST")
    print("=" * 80)
    passed = 0
    for ok, line in results:
        print(("✓ " if ok else "✗ ") + line)
        if ok:
            passed += 1
    print("=" * 80)
    print(f"{passed}/{len(results)} passed")
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
