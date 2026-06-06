"""Minimal tool registry matching the @tool(name, description, parameters, required) pattern.

Replace with your real framework's decorator if you have one — the metadata
shape mirrors OpenAI / Anthropic tool-use JSON schema.
"""
from typing import Any, Callable

REGISTRY: dict[str, dict[str, Any]] = {}


def tool(
    *,
    name: str,
    description: str,
    parameters: dict[str, dict[str, Any]],
    required: list[str],
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    def decorator(fn: Callable[..., Any]) -> Callable[..., Any]:
        REGISTRY[name] = {
            "name": name,
            "description": description,
            "parameters": {
                "type": "object",
                "properties": parameters,
                "required": required,
            },
            "fn": fn,
        }
        fn.tool_name = name  # type: ignore[attr-defined]
        return fn

    return decorator
