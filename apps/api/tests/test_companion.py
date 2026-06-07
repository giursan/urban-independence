from pydantic_ai.messages import ModelResponse, TextPart, ToolCallPart
from pydantic_ai.models.function import AgentInfo, FunctionModel

import app.caregiver_tools  # noqa: F401
from app.companion import companion_agent
from conftest import make_deps


async def test_companion_saves_memory_via_tool():
    deps, memory = make_deps(last_user_text="Let me tell you about my family")
    calls = {"n": 0}

    def model_fn(messages, info: AgentInfo) -> ModelResponse:
        calls["n"] += 1
        if calls["n"] == 1:
            return ModelResponse(
                parts=[
                    ToolCallPart(
                        tool_name="save_memory",
                        args={"content": "Granddaughter Mia is a nurse", "kind": "person"},
                    )
                ]
            )
        return ModelResponse(parts=[TextPart(content="That's lovely, Rose.")])

    result = await companion_agent.run(
        "Tell you about my family", deps=deps, model=FunctionModel(model_fn)
    )

    assert "lovely" in result.output.lower()
    assert any("Mia" in content for content, _ in memory.saved)


async def test_dynamic_instructions_include_adaptive_overlay_profile_and_memory():
    deps, memory = make_deps(last_user_text="thinking about my late husband")
    memory.canned = [{"content": "Her husband was named Albert"}]
    captured = {}

    def model_fn(messages, info: AgentInfo) -> ModelResponse:
        captured["instr"] = getattr(messages[-1], "instructions", "") or ""
        return ModelResponse(parts=[TextPart(content="Tell me more about him.")])

    await companion_agent.run("hello", deps=deps, model=FunctionModel(model_fn))

    instr = captured["instr"]
    # Adaptive overlay teaches the model to pick posture per message instead of
    # being locked into a discrete mode; check for its hallmark cues.
    assert "adapt" in instr.lower()
    assert "Socratic" in instr  # the decision/uncertainty branch is part of the overlay
    assert "Rose" in instr  # profile name
    assert "Albert" in instr  # injected memory


async def test_companion_can_lookup_caregiver_context_via_tool():
    deps, _ = make_deps(last_user_text="Tell me about Mia")
    deps.db.store["companion_facts"] = [
        {
            "user_id": "u1",
            "category": "family",
            "title": "Daughter Mia",
            "content": "Mia is Rose's daughter and calls most Sundays.",
            "tags": ["mia", "daughter", "family"],
            "importance": 5,
            "updated_at": "2026-06-07T10:00:00+00:00",
        }
    ]
    seen = {}

    def model_fn(messages, info: AgentInfo) -> ModelResponse:
        for m in messages:
            for p in getattr(m, "parts", []) or []:
                if type(p).__name__ == "ToolReturnPart" and p.tool_name == "lookup_companion_context":
                    seen["rows"] = p.content
        if "rows" not in seen:
            return ModelResponse(
                parts=[
                    ToolCallPart(
                        tool_name="lookup_companion_context",
                        args={"query": "Mia", "category": "family"},
                    )
                ]
            )
        return ModelResponse(parts=[TextPart(content=seen["rows"][0]["content"])])

    result = await companion_agent.run("Who is Mia?", deps=deps, model=FunctionModel(model_fn))

    assert "daughter" in result.output.lower()
