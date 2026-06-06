"""Local CLI demo. Runs the full pipeline against the stub tools.

    python demo_cli.py
"""

import os
import sys

from dotenv import load_dotenv

from agent import Orchestrator, Store
from agent.config import ElderProfile


def main() -> None:
    load_dotenv()
    if not os.environ.get("ANTHROPIC_API_KEY"):
        sys.exit("ANTHROPIC_API_KEY not set. Copy .env.example to .env and fill it in.")

    store = Store()
    orch = Orchestrator(store=store)

    elder = ElderProfile(
        elder_id="demo-elder-1",
        name="Mrs Wong",
        age=78,
        home_district="Sham Shui Po",
        mobility="walks slowly with a cane, gets winded on stairs",
        health_notes=["mild hypertension", "doesn't drink enough water on hot days"],
        languages=["Cantonese", "English"],
    )

    print(f"Starting session for {elder.name}…")
    session = orch.start_session(elder)

    print(f"\n[Session {session.id}]")
    print("\n── Live snapshot ─────────────────────────")
    print(session.context["summary"])
    print(f"({len(session.context['tool_calls'])} tools called)")

    s = session.scenario
    print("\n── Scenario ──────────────────────────────")
    print(f"Title: {s.title}")
    print(f"\n{s.setting}\n")
    print(f"Goal: {s.goal}\n")
    print("Live factors:")
    for f in s.live_factors:
        print(f"  - {f}")
    print("\nOptions:")
    for o in s.options:
        print(f"  ({o.label}) {o.text}")
    print(f"\n[teaching focus: {s.teaching_focus}]")
    print("──────────────────────────────────────────\n")

    try:
        while True:
            user = input(f"{elder.name} > ").strip()
            if not user:
                continue
            if user.lower() in {"quit", "exit", "bye", "goodbye"}:
                break
            reply = orch.turn(session.id, user)
            print(f"\nCoach > {reply}\n")
    except (KeyboardInterrupt, EOFError):
        print()

    orch.end_session(session.id, summary="ended via CLI")
    print(f"Session {session.id} saved to {store.path}.")


if __name__ == "__main__":
    main()
