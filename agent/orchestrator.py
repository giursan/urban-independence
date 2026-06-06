from __future__ import annotations

import json
import os
from collections.abc import Iterator
from dataclasses import dataclass, field
from typing import Any

import anthropic

from .config import AgentConfig, ElderProfile
from .persistence import Store
from .prompts import (
    system_prompt_context,
    system_prompt_dialogue,
    system_prompt_scenario,
)
from .schemas import Phase, Scenario
from .tools import REGISTRY, ToolRegistry


@dataclass
class Session:
    id: str
    elder: ElderProfile
    phase: Phase = Phase.FETCH_CONTEXT
    context: dict[str, Any] = field(default_factory=dict)
    scenario: Scenario | None = None
    messages: list[dict] = field(default_factory=list)


def _scenario_brief(scenario: Scenario) -> str:
    opts = "\n".join(f"  ({o.label}) {o.text}" for o in scenario.options)
    factors = "\n".join(f"  - {f}" for f in scenario.live_factors)
    return (
        f"Title: {scenario.title}\n"
        f"Setting: {scenario.setting}\n"
        f"Goal: {scenario.goal}\n"
        f"Live factors:\n{factors}\n"
        f"Options:\n{opts}\n"
        f"Teaching focus: {scenario.teaching_focus}"
    )


def _scenario_as_user_text(scenario: Scenario) -> str:
    opts = "\n".join(f"  ({o.label}) {o.text}" for o in scenario.options)
    return f"{scenario.setting}\n\n{scenario.goal}\n\n{opts}"


class Orchestrator:
    def __init__(
        self,
        store: Store,
        cfg: AgentConfig | None = None,
        registry: ToolRegistry | None = None,
        client: anthropic.Anthropic | None = None,
    ) -> None:
        self.cfg = cfg or AgentConfig()
        self.store = store
        self.registry = registry or REGISTRY
        self.client = client or anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
        self._sessions: dict[str, Session] = {}

    # ── public lifecycle ──────────────────────────────────────────────

    def start_session(self, elder: ElderProfile) -> Session:
        sid = self.store.create_session(elder.elder_id)
        session = Session(id=sid, elder=elder)
        self._sessions[sid] = session
        self._fetch_context(session)
        self._generate_scenario(session)
        session.phase = Phase.DIALOGUE
        return session

    def get_session(self, session_id: str) -> Session:
        if session_id not in self._sessions:
            raise KeyError(f"unknown or expired session: {session_id}")
        return self._sessions[session_id]

    def turn(self, session_id: str, user_text: str) -> str:
        session = self.get_session(session_id)
        if session.phase not in (Phase.DIALOGUE, Phase.CHALLENGE):
            raise RuntimeError(f"session not ready for dialogue, phase={session.phase}")

        session.messages.append({"role": "user", "content": user_text})
        self.store.add_turn(session.id, phase=session.phase.value, role="user", content=user_text)

        reply = self._run_tool_loop(
            system=system_prompt_dialogue(self.cfg, session.elder, _scenario_brief(session.scenario)),
            messages=session.messages,
            session=session,
            max_tokens=self.cfg.max_tokens_dialogue,
        )

        session.messages.append({"role": "assistant", "content": reply["content"]})
        self.store.add_turn(
            session.id,
            phase=session.phase.value,
            role="assistant",
            content=reply["text"],
            usage=reply["usage"],
        )
        return reply["text"]

    def end_session(self, session_id: str, summary: str | None = None) -> None:
        session = self._sessions.get(session_id)
        if session:
            session.phase = Phase.DONE
        self.store.end_session(session_id, status="completed", summary=summary)
        self._sessions.pop(session_id, None)

    # ── phase 1: fetch live HK context ────────────────────────────────

    def _fetch_context(self, session: Session) -> None:
        session.phase = Phase.FETCH_CONTEXT
        sys_prompt = system_prompt_context(self.cfg, session.elder)
        bootstrap_user = (
            f"Build a live snapshot for {session.elder.name} in {session.elder.home_district} right now. "
            "Call the tools you need, then summarise."
        )
        scratch: list[dict] = [{"role": "user", "content": bootstrap_user}]

        result = self._run_tool_loop(
            system=sys_prompt,
            messages=scratch,
            session=session,
            max_tokens=self.cfg.max_tokens_context,
            record_messages=False,
        )

        context_snapshot = {
            "summary": result["text"],
            "tool_calls": result["tool_calls"],
        }
        session.context = context_snapshot
        self.store.set_context(session.id, context_snapshot)
        self.store.add_turn(
            session.id,
            phase=Phase.FETCH_CONTEXT.value,
            role="assistant",
            content=result["text"],
            tool_calls=result["tool_calls"],
            usage=result["usage"],
        )

    # ── phase 2: generate the scenario (structured output) ────────────

    def _generate_scenario(self, session: Session) -> None:
        session.phase = Phase.GENERATE_SCENARIO
        sys_prompt = system_prompt_scenario(self.cfg, session.elder)
        user_msg = (
            "Here is the live snapshot you just gathered:\n\n"
            f"{json.dumps(session.context, indent=2, default=str)}\n\n"
            "Design ONE decision scenario this elder might face right now."
        )

        kwargs = self._base_kwargs(self.cfg.max_tokens_scenario)
        response = self.client.messages.parse(
            system=sys_prompt,
            messages=[{"role": "user", "content": user_msg}],
            output_format=Scenario,
            **kwargs,
        )
        scenario: Scenario = response.parsed_output
        session.scenario = scenario
        self.store.set_scenario(session.id, scenario.model_dump())
        self.store.add_turn(
            session.id,
            phase=Phase.GENERATE_SCENARIO.value,
            role="assistant",
            content=_scenario_as_user_text(scenario),
            usage=_usage_to_dict(response.usage),
        )

    # ── shared tool-use loop ──────────────────────────────────────────

    def _run_tool_loop(
        self,
        *,
        system: str,
        messages: list[dict],
        session: Session,
        max_tokens: int,
        record_messages: bool = True,
    ) -> dict:
        tool_call_log: list[dict] = []
        last_usage: dict = {}

        for _ in range(self.cfg.max_tool_iterations):
            kwargs = self._base_kwargs(max_tokens)
            response = self.client.messages.create(
                system=system,
                tools=self.registry.anthropic_schemas(),
                messages=messages,
                **kwargs,
            )
            last_usage = _usage_to_dict(response.usage)

            if record_messages:
                messages.append({"role": "assistant", "content": response.content})

            if response.stop_reason != "tool_use":
                text = _extract_text(response.content)
                return {
                    "content": response.content,
                    "text": text,
                    "tool_calls": tool_call_log,
                    "usage": last_usage,
                }

            if not record_messages:
                messages.append({"role": "assistant", "content": response.content})

            tool_results: list[dict] = []
            for block in response.content:
                if block.type != "tool_use":
                    continue
                call = {"name": block.name, "input": dict(block.input)}
                try:
                    result = self.registry.get(block.name).call(**block.input)
                    call["result"] = result
                    tool_results.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": json.dumps(result, default=str),
                        }
                    )
                except Exception as e:
                    call["error"] = str(e)
                    tool_results.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": f"error: {e}",
                            "is_error": True,
                        }
                    )
                tool_call_log.append(call)

            messages.append({"role": "user", "content": tool_results})

        raise RuntimeError("tool loop hit max iterations without resolution")

    # ── shared API kwargs ─────────────────────────────────────────────

    def _base_kwargs(self, max_tokens: int) -> dict:
        kwargs: dict[str, Any] = {
            "model": self.cfg.model,
            "max_tokens": max_tokens,
            "output_config": {"effort": self.cfg.effort},
        }
        if self.cfg.thinking:
            kwargs["thinking"] = {"type": "adaptive"}
        return kwargs


def _extract_text(content: list) -> str:
    parts = [b.text for b in content if getattr(b, "type", None) == "text"]
    return "".join(parts).strip()


def _usage_to_dict(usage: Any) -> dict:
    if usage is None:
        return {}
    try:
        return {
            "input_tokens": getattr(usage, "input_tokens", None),
            "output_tokens": getattr(usage, "output_tokens", None),
            "cache_read_input_tokens": getattr(usage, "cache_read_input_tokens", None),
            "cache_creation_input_tokens": getattr(usage, "cache_creation_input_tokens", None),
        }
    except Exception:
        return {}
