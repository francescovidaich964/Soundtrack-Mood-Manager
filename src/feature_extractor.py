"""
feature_extractor.py — extract valence and energy from an audio file

Pipeline (per Essentia model zoo documentation):
  1. MonoLoader at 16 kHz
  2. TensorflowPredictMusiCNN  → embeddings  (N_frames × 200)
  3. TensorflowPredict2D       → predictions (N_frames × 2)
  4. mean over frames          → [valence_mean, arousal_mean]
  5. normalize (x − 1) / 8    → [0.0, 1.0]

Model output column order (verified against Essentia model zoo docs):
  column 0 = valence   (negative ↔ positive)
  column 1 = arousal   (calm ↔ energetic)  — used as "energy" throughout

Raw prediction range is approximately [1.0, 9.0] (EmoMusic dataset scale).
After normalization the values are clipped to [0.0, 1.0] to guard against
occasional out-of-range predictions at the extremes.

Models are loaded lazily on the first call to avoid slow import-time
initialization and to produce a clear error if the .pb files are missing.
"""

from __future__ import annotations

import math
import warnings
from pathlib import Path

import numpy as np
import pyloudnorm as pyln

_TARGET_LUFS = -14.0


def _measure_and_normalize(
    audio: np.ndarray, sr: int = 16000
) -> tuple[np.ndarray, float | None]:
    """Normalize audio to _TARGET_LUFS; return (normalized_audio, original_lufs).

    Returns (audio, None) if loudness is unmeasurable (silence, too short, etc.).
    """
    meter = pyln.Meter(sr)
    loudness = meter.integrated_loudness(audio)
    if not np.isfinite(loudness) or loudness < -70.0:
        return audio, None
    return pyln.normalize.loudness(audio, loudness, _TARGET_LUFS), float(loudness)


# Lazy-loaded module-level references so the heavy TF import only happens once.
_MonoLoader = None
_TensorflowPredictMusiCNN = None
_TensorflowPredict2D = None

# Loaded model instances (one per process).
_musicnn_model = None
_emomusic_model = None
_models_dir_loaded: Path | None = None


def _load_models(models_dir: Path) -> None:
    """Import Essentia and instantiate both models (idempotent)."""
    global _MonoLoader, _TensorflowPredictMusiCNN, _TensorflowPredict2D
    global _musicnn_model, _emomusic_model, _models_dir_loaded

    if _models_dir_loaded == models_dir:
        return  # already loaded

    try:
        import essentia  # type: ignore[import]
        essentia.log.warningActive = False  # suppress C++ "No network created" warnings
        from essentia.standard import (  # type: ignore[import]
            MonoLoader,
            TensorflowPredict2D,
            TensorflowPredictMusiCNN,
        )
    except ImportError as exc:
        raise ImportError(
            "essentia-tensorflow is not installed.\n"
            "This package has no Windows wheels; it must run on Linux/macOS.\n"
            "Use the GitHub Actions workflow (.github/workflows/sync.yml) or WSL2.\n"
            "Install: pip install essentia-tensorflow\n"
            f"Original error: {exc}"
        ) from exc

    musicnn_pb = models_dir / "msd-musicnn-1.pb"
    emomusic_pb = models_dir / "emomusic-msd-musicnn-2.pb"

    for pb in (musicnn_pb, emomusic_pb):
        if not pb.exists():
            raise FileNotFoundError(
                f"Model file not found: {pb}\n"
                "Download the .pb files as described in models/README.md."
            )

    # Suppress TensorFlow deprecation warnings that Essentia emits.
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        _musicnn_model = TensorflowPredictMusiCNN(
            graphFilename=str(musicnn_pb),
            output="model/dense/BiasAdd",  # verified against Essentia model zoo docs
        )
        _emomusic_model = TensorflowPredict2D(
            graphFilename=str(emomusic_pb),
            output="model/Identity",        # verified against Essentia model zoo docs
        )

    _MonoLoader = MonoLoader
    _TensorflowPredictMusiCNN = TensorflowPredictMusiCNN
    _TensorflowPredict2D = TensorflowPredict2D
    _models_dir_loaded = models_dir


def analyze(audio_path: Path, models_dir: Path) -> tuple[float, float, float | None] | None:
    """Extract (valence, energy, loudness_db) from an audio file.

    Args:
        audio_path: Path to the MP3 (or any format MonoLoader accepts).
        models_dir: Directory containing the .pb model files.

    Returns:
        (valence, energy, loudness_db) where valence/energy are in [0.0, 1.0]
        and loudness_db is the integrated LUFS of the original audio (before
        normalization), or None if unmeasurable. Returns None on any failure.
    """
    try:
        _load_models(models_dir)
    except (ImportError, FileNotFoundError):
        raise  # let the caller log and skip

    try:
        # 1. Load audio as mono at 16 kHz and normalize loudness.
        audio = _MonoLoader(filename=str(audio_path), sampleRate=16000)()
        audio, loudness_db = _measure_and_normalize(audio)

        # 2. MusiCNN embeddings: shape (N_frames, 200)
        embeddings = _musicnn_model(audio)

        if embeddings.shape[0] == 0:
            return None  # audio too short to produce any frames

        # 3. EmoMusic predictions: shape (N_frames, 2)
        #    Column 0 = valence, Column 1 = arousal (energy)
        predictions = _emomusic_model(embeddings)

        if predictions.shape[0] == 0:
            return None

        # 4. Mean over frames → [valence_mean, arousal_mean]
        mean = predictions.mean(axis=0)  # shape (2,)

        # 5. Normalize from EmoMusic scale [1, 9] → [0, 1] and clip.
        valence = float(np.clip((mean[0] - 1.0) / 8.0, 0.0, 1.0))
        energy = float(np.clip((mean[1] - 1.0) / 8.0, 0.0, 1.0))

        # np.clip does not sanitise NaN; guard so callers never store NaN in data.js.
        # (json.dumps writes float('nan') as the bare JS token NaN, which then passes
        # typeof checks but draws at (NaN, NaN) — invisible on the canvas.)
        if not (math.isfinite(valence) and math.isfinite(energy)):
            return None

        return valence, energy, loudness_db

    except Exception:  # noqa: BLE001
        # Corrupted audio, model inference error, etc. — skip the track.
        return None
