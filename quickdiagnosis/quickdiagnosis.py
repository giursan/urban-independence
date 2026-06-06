from pathlib import Path
from typing import Tuple
from functools import lru_cache

import numpy as np
import joblib

from features import extract_chunk_features

MODEL_PATH = Path(__file__).parent / "model" / "rf.joblib"


@lru_cache(maxsize=1)
def _load():
    bundle = joblib.load(MODEL_PATH)
    return bundle["model"], bundle["classes"], bundle.get("chunk_sec", 8.0)


def categorise_cognition(wav_path: str) -> Tuple[bool, float]:
    """Takes a wav of speech and returns (dementia_detected, cognition_score).

    cognition_score is the model's probability that the speaker is healthy
    (1.0 = clearly healthy, 0.0 = clearly impaired), averaged over fixed-
    length chunks of the audio. See https://luzs.gitlab.io/adress/#testlabels.
    """
    model, classes, chunk_sec = _load()
    chunks = extract_chunk_features(wav_path, chunk_sec=chunk_sec)
    if not chunks:
        raise ValueError(f"no usable audio chunks in {wav_path}")

    probs = model.predict_proba(np.array(chunks)).mean(axis=0)
    class_to_p = dict(zip(classes, probs))

    dementia_p = class_to_p.get("dementia", 0.0)
    healthy_p = class_to_p.get("healthy", 1.0 - dementia_p)
    dementia_detected = dementia_p > 0.5 and dementia_p == max(class_to_p.values())
    return bool(dementia_detected), float(healthy_p)
