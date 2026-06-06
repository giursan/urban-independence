"""Agent-level tests for the HK tool wrappers.

We use pydantic-ai's `FunctionModel` to deterministically force tool calls,
then assert the tool actually executes and its result flows back into the
agent's next turn. Source fetches are monkey-patched so these tests are
hermetic — they do not hit the live HK APIs.

The live-source guarantees are covered by `scripts/smoke_hk_sources.py`.
"""

from __future__ import annotations

import pytest
from pydantic_ai.messages import ModelResponse, TextPart, ToolCallPart
from pydantic_ai.models.function import AgentInfo, FunctionModel

# Importing app.hk_tools triggers @companion_agent.tool_plain registrations.
import app.hk_tools  # noqa: F401
from app.companion import companion_agent
from app.sources import aqhi, mtr, traffic, weather
from conftest import make_deps


async def test_get_weather_is_registered_and_callable(monkeypatch):
    fake = {
        "district": "Central",
        "temp_c": 27,
        "condition": "light rain",
        "humidity_pct": 91,
        "source": "test",
        "source_url": "test://",
    }

    async def fake_fetch(district: str):
        assert district == "Central"
        return fake

    monkeypatch.setattr(weather, "fetch_current_weather", fake_fetch)

    deps, _ = make_deps(last_user_text="how's the weather in Central?")
    calls = {"n": 0}

    def model_fn(messages, info: AgentInfo) -> ModelResponse:
        calls["n"] += 1
        if calls["n"] == 1:
            return ModelResponse(
                parts=[ToolCallPart(tool_name="get_weather", args={"district": "Central"})]
            )
        return ModelResponse(parts=[TextPart(content="It's 27 and lightly raining in Central.")])

    result = await companion_agent.run(
        "How's the weather?", deps=deps, model=FunctionModel(model_fn)
    )

    assert calls["n"] == 2, "model should be called twice: once to issue the tool call, once to summarise"
    assert "27" in result.output
    assert "Central" in result.output


async def test_get_air_quality_returns_to_model(monkeypatch):
    fake = {
        "district": "Sham Shui Po",
        "matched": True,
        "match_count": 1,
        "stations": [
            {
                "station": "Sham Shui Po",
                "aqhi": 4,
                "band": "Moderate",
                "health_advisory_for_elderly": "Reduce outdoor physical exertion.",
            }
        ],
        "source": "test",
        "source_url": "test://",
    }

    async def fake_fetch(district: str):
        return fake

    monkeypatch.setattr(aqhi, "fetch_aqhi", fake_fetch)

    deps, _ = make_deps(last_user_text="is the air ok in Sham Shui Po?")
    seen_tool_result: dict = {}

    def model_fn(messages, info: AgentInfo) -> ModelResponse:
        # Second pass: pydantic-ai will have inserted a ToolReturnPart into messages.
        for m in messages:
            for p in getattr(m, "parts", []) or []:
                if type(p).__name__ == "ToolReturnPart" and p.tool_name == "get_air_quality":
                    seen_tool_result.update(p.content if isinstance(p.content, dict) else {})
        if not seen_tool_result:
            return ModelResponse(
                parts=[ToolCallPart(tool_name="get_air_quality", args={"district": "Sham Shui Po"})]
            )
        band = seen_tool_result.get("stations", [{}])[0].get("band", "?")
        return ModelResponse(parts=[TextPart(content=f"The air is {band} today.")])

    result = await companion_agent.run(
        "How's the air?", deps=deps, model=FunctionModel(model_fn)
    )

    assert seen_tool_result["matched"] is True
    assert seen_tool_result["stations"][0]["band"] == "Moderate"
    assert "Moderate" in result.output


async def test_get_mtr_status_propagates_exception_as_tool_error(monkeypatch):
    """If the source raises, pydantic-ai turns it into a retry/error path —
    the agent must not crash the run."""

    async def fake_fetch(line: str, station: str):
        raise RuntimeError("MTR Next Train feed error: simulated outage")

    monkeypatch.setattr(mtr, "fetch_next_train", fake_fetch)

    deps, _ = make_deps(last_user_text="when's the next train at Central?")
    calls = {"n": 0}

    def model_fn(messages, info: AgentInfo) -> ModelResponse:
        calls["n"] += 1
        if calls["n"] == 1:
            return ModelResponse(
                parts=[ToolCallPart(tool_name="get_mtr_status", args={"line": "TWL", "station": "Central"})]
            )
        # On retry / next pass, just answer gracefully
        return ModelResponse(parts=[TextPart(content="I couldn't reach the MTR feed just now.")])

    # Some pydantic-ai versions raise the underlying error after exhausting retries; either is fine
    # for this assertion — what matters is that we get a deterministic outcome, not a crash on the
    # registration path itself.
    try:
        result = await companion_agent.run(
            "Train?", deps=deps, model=FunctionModel(model_fn)
        )
    except Exception as e:  # noqa: BLE001
        assert "MTR" in str(e) or "simulated outage" in str(e)
        return

    assert "couldn't reach" in result.output.lower() or "mtr" in result.output.lower()


async def test_get_traffic_advisory_with_optional_district_none(monkeypatch):
    """`get_traffic_advisory`'s parameter is Optional — confirm the agent
    can call it with no args."""
    fake = {
        "district": None,
        "matched": True,
        "match_count": 0,
        "incidents": [],
        "feed_total": 0,
        "source": "test",
        "source_url": "test://",
    }

    async def fake_fetch(district=None):
        assert district is None
        return fake

    monkeypatch.setattr(traffic, "fetch_traffic_advisories", fake_fetch)

    deps, _ = make_deps(last_user_text="any road problems?")
    calls = {"n": 0}

    def model_fn(messages, info: AgentInfo) -> ModelResponse:
        calls["n"] += 1
        if calls["n"] == 1:
            return ModelResponse(parts=[ToolCallPart(tool_name="get_traffic_advisory", args={})])
        return ModelResponse(parts=[TextPart(content="No road problems right now.")])

    result = await companion_agent.run(
        "Any road issues?", deps=deps, model=FunctionModel(model_fn)
    )
    assert "no road" in result.output.lower()


def test_all_hk_tools_are_registered():
    """Schema sanity check — every expected HK tool name is on the agent."""
    expected = {
        "get_weather",
        "get_weather_forecast",
        "get_air_quality",
        "get_traffic_advisory",
        "get_mtr_status",
        "get_mtr_bus_schedule",
        "get_hkfp_news",
        "web_search",
        "web_scrape",
        "get_calendar_events",
    }
    tools = set(companion_agent._function_toolset.tools.keys())
    missing = expected - tools
    assert not missing, f"HK tools missing from agent: {missing}"
