from dataclasses import dataclass, field


@dataclass(frozen=True)
class AgentConfig:
    model: str = "claude-opus-4-7"
    effort: str = "high"
    thinking: bool = True
    max_tokens_context: int = 4096
    max_tokens_dialogue: int = 2048
    max_tokens_scenario: int = 2048
    max_tool_iterations: int = 8
    city: str = "Hong Kong"
    locale: str = "en"
    cache_system_prompt: bool = True


@dataclass(frozen=True)
class ElderProfile:
    elder_id: str
    name: str = "Friend"
    age: int | None = None
    home_district: str = "Sham Shui Po"
    mobility: str = "walks independently with a cane"
    health_notes: list[str] = field(default_factory=list)
    languages: list[str] = field(default_factory=lambda: ["English", "Cantonese"])
