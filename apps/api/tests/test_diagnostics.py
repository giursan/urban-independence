from pydantic_ai.models.test import TestModel

from app.diagnostics import analyze_wellbeing
from app.models import WellbeingSnapshot


async def test_diagnostics_returns_valid_snapshot():
    snapshot = await analyze_wellbeing(
        transcript="user: I felt a bit lonely today\nassistant: I'm here with you.",
        moods=[{"score": 6, "label": "okay", "note": ""}],
        model=TestModel(),
    )
    assert isinstance(snapshot, WellbeingSnapshot)
    assert -1.0 <= snapshot.emotional_valence <= 1.0
    assert 1 <= snapshot.engagement_level <= 5
    assert 1 <= snapshot.loneliness_signal <= 5
    assert 1 <= snapshot.cognitive_concern_level <= 5
    assert isinstance(snapshot.cognitive_flags, list)
    assert snapshot.disclaimer  # non-empty non-clinical disclaimer
