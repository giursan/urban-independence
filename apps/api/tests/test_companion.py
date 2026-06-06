from pydantic_ai.messages import ModelResponse, TextPart, ToolCallPart
from pydantic_ai.models.function import AgentInfo, FunctionModel

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


async def test_dynamic_instructions_include_mode_profile_and_memory():
    deps, memory = make_deps(mode="reflect", last_user_text="thinking about my late husband")
    memory.canned = [{"content": "Her husband was named Albert"}]
    captured = {}

    def model_fn(messages, info: AgentInfo) -> ModelResponse:
        captured["instr"] = getattr(messages[-1], "instructions", "") or ""
        return ModelResponse(parts=[TextPart(content="Tell me more about him.")])

    await companion_agent.run("hello", deps=deps, model=FunctionModel(model_fn))

    instr = captured["instr"]
    assert "REFLECT" in instr  # mode overlay applied
    assert "Rose" in instr  # profile name
    assert "Albert" in instr  # injected memory
