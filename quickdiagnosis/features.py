from typing import List
import numpy as np
import librosa


def _stats(y: np.ndarray, sr: int) -> np.ndarray:
    mfcc = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=20)
    delta = librosa.feature.delta(mfcc)
    zcr = librosa.feature.zero_crossing_rate(y)
    centroid = librosa.feature.spectral_centroid(y=y, sr=sr)
    rolloff = librosa.feature.spectral_rolloff(y=y, sr=sr)
    rms = librosa.feature.rms(y=y)

    parts = [mfcc, delta, zcr, centroid, rolloff, rms]
    out = []
    for p in parts:
        out.append(p.mean(axis=1))
        out.append(p.std(axis=1))
    return np.concatenate(out)


def extract_features(path: str, sr: int = 16000) -> np.ndarray:
    """Whole-file features (kept for backwards compatibility)."""
    y, _ = librosa.load(path, sr=sr, mono=True)
    if y.size == 0:
        raise ValueError(f"empty audio: {path}")
    return _stats(y, sr)


def extract_chunk_features(
    path: str, sr: int = 16000, chunk_sec: float = 8.0, hop_sec: float = 8.0
) -> List[np.ndarray]:
    """Split audio into fixed windows and extract features per window.

    Returns a list of feature vectors — one per chunk. Tail chunks shorter
    than half the window length are dropped.
    """
    y, _ = librosa.load(path, sr=sr, mono=True)
    if y.size == 0:
        raise ValueError(f"empty audio: {path}")

    win = int(chunk_sec * sr)
    hop = int(hop_sec * sr)
    min_len = win // 2

    feats = []
    for start in range(0, max(1, len(y) - min_len + 1), hop):
        chunk = y[start : start + win]
        if len(chunk) < min_len:
            break
        feats.append(_stats(chunk, sr))
    return feats
