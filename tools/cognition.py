"""Tool wrapper around the quickdiagnosis dementia classifier."""
import sys
from pathlib import Path
from typing import Any

from .registry import tool

# quickdiagnosis lives as a sibling package, not on the path by default
_QD = Path(__file__).resolve().parent.parent / "quickdiagnosis"
if str(_QD) not in sys.path:
    sys.path.insert(0, str(_QD))

from quickdiagnosis import _load  # noqa: E402
from features import extract_chunk_features  # noqa: E402


@tool(
    name="categorise_cognition",
    description=(
        "Classify a speech audio file as dementia vs healthy using a Random "
        "Forest over MFCC + spectral features. Returns the model's per-class "
        "probabilities (averaged over fixed-length chunks), a boolean "
        "dementia_detected flag, and a cognition_score in [0, 1] where 1.0 "
        "means clearly healthy. Trained on celebrity-interview audio, so "
        "results are indicative only and not clinically diagnostic."
    ),
    parameters={
        "audio_path": {
            "type": "string",
            "description": "Absolute path to a wav/mp3/flac/ogg/m4a file of speech.",
        },
    },
    required=["audio_path"],
)
def categorise_cognition(audio_path: str) -> dict[str, Any]:
    import numpy as np

    model, classes, chunk_sec = _load()
    chunks = extract_chunk_features(audio_path, chunk_sec=chunk_sec)
    if not chunks:
        return {"error": f"no usable audio chunks in {audio_path}"}

    probs = model.predict_proba(np.array(chunks)).mean(axis=0)
    class_to_p = {c: float(p) for c, p in zip(classes, probs)}
    dementia_p = class_to_p.get("dementia", 0.0)
    healthy_p = class_to_p.get("healthy", 1.0 - dementia_p)
    dementia_detected = dementia_p > 0.5 and dementia_p == max(class_to_p.values())

    return {
        "audio_path": audio_path,
        "n_chunks": len(chunks),
        "chunk_sec": chunk_sec,
        "probabilities": class_to_p,
        "dementia_detected": bool(dementia_detected),
        "cognition_score": healthy_p,
    }
