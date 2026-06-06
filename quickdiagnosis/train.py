import hashlib
from pathlib import Path

import numpy as np
import joblib
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import GroupKFold, cross_val_score

from features import extract_chunk_features

ROOT = Path(__file__).parent
DATA_DIR = ROOT / "data" / "audio_files"
MODEL_PATH = ROOT / "model" / "rf.joblib"
CACHE_DIR = ROOT / "model" / "features_cache"
AUDIO_EXTS = {".wav", ".mp3", ".flac", ".ogg", ".m4a"}
CHUNK_SEC = 8.0


def _cache_path(audio_path: Path) -> Path:
    stat = audio_path.stat()
    key = f"{audio_path}|{stat.st_size}|{int(stat.st_mtime)}|{CHUNK_SEC}"
    digest = hashlib.sha1(key.encode()).hexdigest()[:16]
    return CACHE_DIR / f"{digest}.npy"


def _chunks_for(audio_path: Path) -> np.ndarray:
    cache = _cache_path(audio_path)
    if cache.exists():
        return np.load(cache)
    arr = np.array(extract_chunk_features(str(audio_path), chunk_sec=CHUNK_SEC))
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    np.save(cache, arr)
    return arr


def load_dataset():
    """Return (X, y, groups, classes). Each row of X is one chunk; groups
    is the speaker folder, so GroupKFold keeps a speaker in one split."""
    X, y, groups = [], [], []
    classes = sorted(d.name for d in DATA_DIR.iterdir() if d.is_dir())
    for label in classes:
        for f in (DATA_DIR / label).rglob("*"):
            if not f.is_file() or f.suffix.lower() not in AUDIO_EXTS:
                continue
            speaker = f.parent.name
            try:
                chunks = _chunks_for(f)
            except Exception as e:
                print(f"skip {f}: {e}")
                continue
            for c in chunks:
                X.append(c)
                y.append(label)
                groups.append(f"{label}/{speaker}")
    return np.array(X), np.array(y), np.array(groups), classes


def load_model():
    """Load the saved bundle: dict with keys `model`, `classes`, `chunk_sec`."""
    return joblib.load(MODEL_PATH)


def main():
    X, y, groups, classes = load_dataset()
    if len(X) == 0:
        raise SystemExit(f"no audio files found under {DATA_DIR}")
    n_speakers = len(set(groups))
    print(f"loaded {len(X)} chunks from {n_speakers} speakers, classes: {classes}")

    clf = RandomForestClassifier(n_estimators=400, random_state=42, n_jobs=-1)

    n_splits = min(5, n_speakers)
    if n_splits >= 2:
        scores = cross_val_score(
            clf, X, y, groups=groups, cv=GroupKFold(n_splits=n_splits), n_jobs=-1
        )
        print(f"GroupKFold cv accuracy: {scores.mean():.3f} +/- {scores.std():.3f}")

    clf.fit(X, y)
    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(
        {"model": clf, "classes": classes, "chunk_sec": CHUNK_SEC}, MODEL_PATH
    )
    print(f"saved model to {MODEL_PATH}")


if __name__ == "__main__":
    main()
