"""Shared Pydantic models: user profile and the structured wellbeing output."""
from __future__ import annotations

from pydantic import BaseModel, Field

from .persona import DISCLAIMER


class Profile(BaseModel):
    id: str
    display_name: str | None = None
    preferred_name: str | None = None
    locale: str = "en"
    interests: list[str] = Field(default_factory=list)
    life_context: dict = Field(default_factory=dict)

    @property
    def address_name(self) -> str:
        return self.preferred_name or self.display_name or "friend"


class WellbeingSnapshot(BaseModel):
    """Non-clinical, conversation-derived wellbeing indicators for a relative."""

    summary: str = Field(description="A warm 2-4 sentence overview for a caring relative.")
    mood_trend: str = Field(description="How the person's mood seemed to move over the period.")
    emotional_valence: float = Field(ge=-1, le=1, description="-1 low … +1 warm/positive")
    engagement_level: int = Field(ge=1, le=5)
    loneliness_signal: int = Field(ge=1, le=5, description="1 = well-connected, 5 = notably lonely")
    conversational_markers: str = Field(description="Descriptive, non-diagnostic notes on expression.")
    topics_of_interest: list[str] = Field(default_factory=list)
    highlights: list[str] = Field(default_factory=list)
    gentle_followups: list[str] = Field(default_factory=list)
    suggested_topics: list[str] = Field(default_factory=list)
    crisis_flags: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0, le=1, default=0.5)
    disclaimer: str = DISCLAIMER
