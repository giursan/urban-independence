"""Smoke tests for the live tools in tools/.

Run from repo root:
    python -m tests.test_live_tools

These hit real network endpoints. Tools requiring API keys are skipped
unless the corresponding env var is set.

Exit code 0 = all enabled checks passed.
"""

from __future__ import annotations

import os
import sys
import traceback
from typing import Any, Callable

# Importing agent.tools triggers `import tools`, which registers everything.
from agent.tools import REGISTRY


def _section(title: str) -> None:
    print(f"\n── {title} " + "─" * (50 - len(title)))


def _check(name: str, fn: Callable[[], Any], required_env: list[str] | None = None) -> bool:
    missing = [k for k in (required_env or []) if not os.environ.get(k)]
    if missing:
        print(f"  SKIP  {name}  (missing env: {', '.join(missing)})")
        return True
    try:
        result = fn()
        head = repr(result)[:200].replace("\n", " ")
        print(f"  PASS  {name}  →  {head}…")
        return True
    except Exception as e:  # noqa: BLE001
        print(f"  FAIL  {name}  →  {type(e).__name__}: {e}")
        traceback.print_exc(limit=2)
        return False


def main() -> int:
    _section("Registry")
    names = [t.name for t in REGISTRY.all()]
    print(f"  {len(names)} tools registered:")
    for n in sorted(names):
        print(f"    - {n}")

    expected = {
        "web_search", "web_scrape",
        "get_hkfp_news", "get_calendar_events",
        "get_next_train", "get_mtr_bus_schedule",
    }
    missing = expected - set(names)
    if missing:
        print(f"  FAIL  missing from registry: {missing}")
        return 1
    print("  PASS  all live tools registered")

    results: list[bool] = []

    _section("No-key live endpoints")
    results.append(_check(
        "get_hkfp_news(limit=3)",
        lambda: REGISTRY.get("get_hkfp_news").call(limit=3),
    ))
    results.append(_check(
        "get_next_train(line='TWL', station='MOK')",
        lambda: REGISTRY.get("get_next_train").call(line="TWL", station="MOK"),
    ))
    results.append(_check(
        "get_mtr_bus_schedule(route='K12', station_id='20015144')",
        lambda: REGISTRY.get("get_mtr_bus_schedule").call(route="K12", station_id="20015144"),
    ))

    _section("Key-gated endpoints")
    results.append(_check(
        "web_search('Hong Kong weather today', limit=3)",
        lambda: REGISTRY.get("web_search").call(query="Hong Kong weather today", limit=3),
        required_env=["FIRECRAWL_API_KEY"],
    ))
    results.append(_check(
        "get_calendar_events(max_results=3)",
        lambda: REGISTRY.get("get_calendar_events").call(max_results=3),
        required_env=["GOOGLE_CALENDAR_API_KEY", "GOOGLE_CALENDAR_ID"],
    ))

    _section("Result")
    ok = all(results)
    print(f"  {'OK' if ok else 'FAILURES'}  — {sum(results)}/{len(results)} checks passed")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
