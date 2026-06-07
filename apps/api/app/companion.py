"""The companion agent: persona + dynamic per-user instructions + tools.

Cross-session continuity comes from the memory tools (pgvector) and the profile,
injected here as dynamic instructions; within-session context comes from the
message list the client sends with each request.
"""
from __future__ import annotations

import json

from pydantic_ai import Agent, RunContext

from .deps import CompanionDeps
from .persona import ADAPTIVE_OVERLAY, BASE_PERSONA, PHONE_OVERLAY  # MODE_OVERLAYS retired — see persona.py

# Model is supplied per-run (see routes/chat.py) so importing this module never
# requires an OpenAI key — which keeps tests and `/health` working offline.
companion_agent = Agent(
    deps_type=CompanionDeps,
    instructions=BASE_PERSONA,
)


@companion_agent.instructions
async def contextual_instructions(ctx: RunContext[CompanionDeps]) -> str:
    deps = ctx.deps
    profile = deps.profile
    # The model now picks posture (companion / reflect / reminiscence / engage)
    # turn-by-turn from cues in the user's message. `deps.mode` no longer drives
    # web-chat behavior, but routes can still use it for transport hints such as
    # phone delivery.
    lines: list[str] = [ADAPTIVE_OVERLAY]
    if deps.mode == "phone":
        lines.append(PHONE_OVERLAY)
    lines.append(f"You are speaking with {profile.address_name}.")
    if profile.interests:
        lines.append(f"Their interests include: {', '.join(profile.interests)}.")
    if profile.life_context:
        lines.append(f"What you know about their life: {json.dumps(profile.life_context)}.")

    memories = await deps.memory.recall(deps.last_user_text) if deps.last_user_text else []
    if memories:
        remembered = "\n".join(f"- {m['content']}" for m in memories)
        lines.append("Things you remember about them:\n" + remembered)
    return "\n\n".join(lines)


@companion_agent.tool
async def save_memory(ctx: RunContext[CompanionDeps], content: str, kind: str = "fact") -> str:
    """Remember a durable fact about the person.

    Use for family/friend names, important dates, strong preferences, and meaningful
    life events — anything that helps you be a consistent friend over time.
    `kind` is one of: fact, preference, event, person.
    """
    await ctx.deps.memory.save(content, kind=kind)
    return "Saved to long-term memory."


@companion_agent.tool
async def recall_memory(ctx: RunContext[CompanionDeps], query: str) -> list[str]:
    """Look up things you've remembered about the person that relate to `query`."""
    found = await ctx.deps.memory.recall(query)
    return [m["content"] for m in found]


@companion_agent.tool
async def log_mood(ctx: RunContext[CompanionDeps], score: int, label: str = "", note: str = "") -> str:
    """Quietly note how the person seems to be feeling (score 1-10) when they share it."""
    ctx.deps.db.table("mood_logs").insert(
        {
            "user_id": ctx.deps.user_id,
            "conversation_id": ctx.deps.conversation_id,
            "score": max(1, min(10, score)),
            "label": label,
            "note": note,
        }
    ).execute()
    return "Noted."
