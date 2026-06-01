"""
feature_extractor.py — extract valence and energy from an audio file

Uses amaai-lab/music2emo, a transformer-based model that predicts valence
and arousal on the EmoMusic scale [1.0, 9.0], normalized to [0.0, 1.0]
via (x - 1) / 8.

The model is downloaded automatically from HuggingFace on first use and
cached in ~/.cache/huggingface/. Works on Linux, macOS, and Windows.
"""

from __future__ import annotations

import math
from pathlib import Path

from music2emo import Music2Emo

_model: Music2Emo | None = None


def _get_model() -> Music2Emo:
    global _model
    if _model is None:
        _model = Music2Emo()
    return _model


def analyze(audio_path: Path) -> tuple[float, float, list[str]] | None:
    """Extract (valence, energy, mood_tags) from an audio file.

    Returns:
        (valence, energy, mood_tags) where valence and energy are in [0.0, 1.0]
        and mood_tags is a list of MTG-Jamendo label strings, or None on failure.
    """
    try:
        result = _get_model().predict(str(audio_path))
        valence = float(max(0.0, min(1.0, (result["valence"] - 1.0) / 8.0)))
        energy = float(max(0.0, min(1.0, (result["arousal"] - 1.0) / 8.0)))
        mood_tags: list[str] = result.get("predicted_moods", [])

        if not (math.isfinite(valence) and math.isfinite(energy)):
            return None

        return valence, energy, mood_tags
    except Exception as e:
        print(f"[feature_extractor] ERROR on {audio_path}: {e}")
        return None
