"""Wellbeing diagnostics: a structured-output agent over recent transcripts.

Produces a non-clinical `WellbeingSnapshot`. Positioned as wellbeing indicators,
never a medical diagnosis.
"""
from __future__ import annotations

from pydantic_ai import Agent

from .config import settings
from .models import WellbeingSnapshot
from .persona import DIAG_INSTRUCTIONS

diagnostics_agent = Agent(
    output_type=WellbeingSnapshot,
    instructions=DIAG_INSTRUCTIONS,
)


async def analyze_wellbeing(
    transcript: str, moods: list[dict] | None = None, model=None
) -> WellbeingSnapshot:
    mood_lines = [
        f"- {m.get('score')}/10 {m.get('label', '')} {m.get('note', '')}".rstrip()
        for m in (moods or [])
    ]
    mood_str = "\n".join(mood_lines) or "(none recorded)"
    prompt = (
        "Review the following recent conversations and mood notes, then produce the "
        "wellbeing summary.\n\n"
        f"=== CONVERSATIONS ===\n{transcript or '(no conversation in this period)'}\n\n"
        f"=== MOOD NOTES ===\n{mood_str}"
    )
    result = await diagnostics_agent.run(prompt, model=model or settings.model_str)
    return result.output
