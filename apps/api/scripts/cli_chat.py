"""Terminal chat with the companion agent — no FastAPI, no Supabase, no auth.

Use this to see the HK tools in action end-to-end. Fake deps stand in for
the real DB / memory layer (same fakes the tests use), so we never touch
Supabase. The model is real — by default OpenAI, swappable to Anthropic via
$COMPANION_MODEL.

Run:
    # OpenAI (default — needs OPENAI_API_KEY in env / .env)
    PYTHONPATH=. uv run python scripts/cli_chat.py

    # Anthropic
    COMPANION_MODEL=anthropic:claude-sonnet-4-6 PYTHONPATH=. uv run python scripts/cli_chat.py

Type a message and hit enter. Type 'quit' or Ctrl-D to exit.
The tool calls each turn are printed for visibility.
"""

from __future__ import annotations

import asyncio
import os
import sys

from dotenv import load_dotenv

# Load .env from project root (where ANTHROPIC_API_KEY etc. live).
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", "..", "..", ".env"))
load_dotenv()  # also apps/api/.env if present

# Import after dotenv so any API keys are visible.
import app.hk_tools  # noqa: F401, E402  — registers HK tools
from app.companion import companion_agent  # noqa: E402

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tests"))
from conftest import make_deps  # type: ignore  # noqa: E402


def _print_tool_calls(messages) -> None:
    """Walk the agent's message history and print any tool calls + results."""
    for m in messages:
        for p in getattr(m, "parts", []) or []:
            tname = type(p).__name__
            if tname == "ToolCallPart":
                args = getattr(p, "args", {}) or {}
                print(f"  ↳ {p.tool_name}({args})")
            elif tname == "ToolReturnPart":
                content = getattr(p, "content", "")
                preview = str(content)
                if len(preview) > 220:
                    preview = preview[:220] + "…"
                print(f"    ↩ {p.tool_name} → {preview}")


async def main() -> int:
    model = os.environ.get("COMPANION_MODEL", "openai:gpt-4o")
    print(f"Companion ready — model: {model}")
    print("(fake DB + memory; HK tools live)")
    print("Type 'quit' to exit.\n")

    deps, _ = make_deps(mode="companion")
    history: list = []

    while True:
        try:
            user_text = input("you ▸ ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not user_text:
            continue
        if user_text.lower() in {"quit", "exit", ":q"}:
            break

        deps.last_user_text = user_text

        try:
            result = await companion_agent.run(
                user_text,
                deps=deps,
                model=model,
                message_history=history,
            )
        except Exception as e:  # noqa: BLE001
            print(f"  [agent error: {type(e).__name__}: {e}]\n")
            continue

        # Show tool activity for this turn
        new_msgs = result.new_messages()
        _print_tool_calls(new_msgs)
        history = result.all_messages()

        print(f"\ncompanion ▸ {result.output}\n")

    print("bye.")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
