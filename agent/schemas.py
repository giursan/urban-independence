from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


class Phase(str, Enum):
    FETCH_CONTEXT = "fetch_context"
    GENERATE_SCENARIO = "generate_scenario"
    DIALOGUE = "dialogue"
    CHALLENGE = "challenge"
    DEBRIEF = "debrief"
    DONE = "done"


class ScenarioOption(BaseModel):
    label: Literal["a", "b", "c", "d"]
    text: str = Field(description="One sentence describing the option from the elder's perspective.")
    surface_appeal: str = Field(description="Why this option looks attractive at first glance.")
    hidden_risk: str = Field(description="The non-obvious factor that makes this option risky given the live context.")


class Scenario(BaseModel):
    """A concrete real-time decision situation for the elder, grounded in live Hong Kong data."""

    title: str = Field(description="Short title (max 8 words).")
    setting: str = Field(description="One paragraph: the situation, where they are, what just happened. Use the elder's home district.")
    goal: str = Field(description="What the elder needs to decide or accomplish.")
    live_factors: list[str] = Field(
        description="Bullet list of the specific live data points that matter for this decision (e.g. '32°C and 85% humidity', 'Tsuen Wan line 15-min delay'). Each item must reference a real value from the fetched context.",
        min_length=2,
        max_length=6,
    )
    options: list[ScenarioOption] = Field(min_length=2, max_length=4)
    teaching_focus: str = Field(description="The decision-making skill this scenario is designed to train (e.g. 'weighing comfort vs. cost when fatigued', 'reading transit disruptions').")


class Critique(BaseModel):
    """A single Socratic challenge the agent will pose."""

    focus_factor: str = Field(description="The specific live factor or assumption being probed.")
    question: str = Field(description="One open question, no leading. Warm, not adversarial.")
    follow_up_if_unclear: str = Field(description="A gentler rephrasing if the elder seems confused.")


class TurnRecord(BaseModel):
    role: Literal["user", "assistant", "system", "tool"]
    phase: Phase
    content: str
    tool_calls: list[dict] = Field(default_factory=list)
