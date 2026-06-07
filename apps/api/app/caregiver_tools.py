from __future__ import annotations

from pydantic_ai import RunContext

from .deps import CompanionDeps
from .companion import companion_agent


@companion_agent.tool
async def lookup_companion_context(
    ctx: RunContext[CompanionDeps],
    query: str,
    category: str | None = None,
    max_results: int = 5,
) -> list[dict]:
    """Look up caregiver-entered background facts about the person.

    Use this when you need dependable context such as relatives, routines,
    preferences, sensitivities, important memories, or conversation topics.
    """
    rows = (
        ctx.deps.db.table("companion_facts")
        .select("title,content,category,tags,importance,updated_at")
        .eq("user_id", ctx.deps.user_id)
        .execute()
        .data
        or []
    )
    needle = query.lower().strip()
    category_needle = category.lower().strip() if category else None

    def score(row: dict) -> tuple[int, int, str]:
        haystacks = [
            str(row.get("title") or "").lower(),
            str(row.get("content") or "").lower(),
            " ".join(row.get("tags") or []).lower(),
        ]
        points = sum(needle in text for text in haystacks if needle)
        if category_needle and str(row.get("category") or "").lower() == category_needle:
            points += 3
        points += int(row.get("importance") or 0)
        return points, int(row.get("importance") or 0), str(row.get("updated_at") or "")

    filtered = [
        row
        for row in rows
        if (not category_needle or str(row.get("category") or "").lower() == category_needle)
        and (
            not needle
            or needle in str(row.get("title") or "").lower()
            or needle in str(row.get("content") or "").lower()
            or needle in " ".join(row.get("tags") or []).lower()
        )
    ]
    ranked = sorted(filtered or rows, key=score, reverse=True)
    return ranked[: max(1, min(max_results, 8))]
