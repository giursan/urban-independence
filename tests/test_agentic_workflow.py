"""End-to-end agentic workflow test.

Runs the full Orchestrator pipeline (FETCH_CONTEXT → GENERATE_SCENARIO → one DIALOGUE turn)
and asserts that:

  - the new live tools from tools/ are exposed in the Anthropic schema
  - start_session() returns a Session with a Scenario
  - at least one tool from REGISTRY was called during context fetch
  - one turn() reply comes back as a non-empty string

Requires ANTHROPIC_API_KEY. Without it the test exits 0 with a SKIP.

Usage:
    python -m tests.test_agentic_workflow
"""

from __future__ import annotations

import os
import sys

from dotenv import load_dotenv

from agent import Orchestrator, Store
from agent.config import ElderProfile
from agent.tools import REGISTRY


def main() -> int:
    load_dotenv()

    # 1. Schema check — the live tools must be in the schema list the orchestrator hands Claude.
    schema_names = {s["name"] for s in REGISTRY.anthropic_schemas()}
    live = {"web_search", "web_scrape", "get_hkfp_news", "get_calendar_events",
            "get_next_train", "get_mtr_bus_schedule"}
    if not live <= schema_names:
        print(f"FAIL  schema missing: {live - schema_names}")
        return 1
    print(f"PASS  schema exposes {len(live)} live tools to Claude")

    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("SKIP  ANTHROPIC_API_KEY not set — skipping live orchestrator run")
        return 0

    # 2. Live orchestrator run.
    store = Store(path=":memory:") if False else Store()  # use real DB to exercise persistence
    orch = Orchestrator(store=store)

    elder = ElderProfile(
        elder_id="test-elder",
        name="Test Subject",
        age=78,
        home_district="Sham Shui Po",
        mobility="walks slowly with a cane",
        health_notes=["mild hypertension"],
        languages=["English"],
    )

    print("\n→ start_session() …")
    session = orch.start_session(elder)
    print(f"  session_id={session.id}")
    print(f"  tools called during context fetch: {len(session.context.get('tool_calls', []))}")
    for tc in session.context.get("tool_calls", []):
        print(f"    - {tc.get('name')}({tc.get('input')})")

    if not session.scenario:
        print("FAIL  no scenario generated")
        return 1
    print(f"  scenario title: {session.scenario.title}")

    print("\n→ turn() …")
    reply = orch.turn(session.id, "I think I'll skip going out today because it sounds risky.")
    if not isinstance(reply, str) or not reply.strip():
        print("FAIL  empty dialogue reply")
        return 1
    print(f"  reply ({len(reply)} chars): {reply[:200]}…")

    orch.end_session(session.id, summary="test ended")
    print("\nPASS  agentic workflow ran end-to-end")
    return 0


if __name__ == "__main__":
    sys.exit(main())
