"""
feature_extractor.py — extract valence and energy from an audio file

Uses amaai-lab/music2emo, a transformer-based model that predicts valence
and arousal on the EmoMusic scale [1.0, 9.0], normalized to [0.0, 1.0]
via (x - 1) / 8.

The full music2emo repository (code + weights + inference data) is downloaded
automatically from HuggingFace on first use via snapshot_download and cached
in ~/.cache/huggingface/. Works on Linux, macOS, and Windows.
"""

from __future__ import annotations

import functools
import math
import os
import sys
from pathlib import Path

import numpy as np
import soundfile as sf
import torch
import torchaudio
from huggingface_hub import snapshot_download

# music2emo.py imports gradio at the top level for its HuggingFace Space UI,
# but gradio is never called during inference. Stub it out so we don't need
# to install the full package.
import sys as _sys
if "gradio" not in _sys.modules:
    from unittest.mock import MagicMock as _MagicMock
    _sys.modules["gradio"] = _MagicMock()

# torchaudio >= 2.9 dropped its own audio backends and routes torchaudio.load()
# exclusively through torchcodec, which requires FFmpeg shared DLLs that are
# not guaranteed to be on the Windows DLL search path.  Patch torchaudio.load
# with a soundfile implementation (libsndfile 1.1+ supports MP3 natively) so
# music2emo's torchaudio.load() calls work without torchcodec installed.
def _sf_load(
    uri,
    frame_offset: int = 0,
    num_frames: int = -1,
    normalize: bool = True,
    channels_first: bool = True,
    format=None,
    buffer_size: int = 4096,
    backend=None,
):
    start = frame_offset
    stop = None if num_frames < 0 else (frame_offset + num_frames)
    data, sr = sf.read(str(uri), dtype="float32", always_2d=True, start=start, stop=stop)
    # soundfile returns [samples, channels]; torchaudio returns [channels, samples]
    arr = data.T if channels_first else data
    return torch.from_numpy(np.ascontiguousarray(arr)), sr

torchaudio.load = _sf_load

# music2emo's predict() calls torch.load(model_file) without map_location, which
# crashes on CPU-only machines. Patch torch.load to default map_location to "cpu".
_orig_torch_load = torch.load

@functools.wraps(_orig_torch_load)
def _cpu_torch_load(f, map_location=None, weights_only=False, **kwargs):
    return _orig_torch_load(f, map_location=map_location or "cpu", weights_only=weights_only, **kwargs)

torch.load = _cpu_torch_load

_music2emo_path: str | None = None
_model = None


def _get_music2emo_path() -> str:
    global _music2emo_path
    if _music2emo_path is None:
        _music2emo_path = snapshot_download("amaai-lab/music2emo")
    return _music2emo_path


def _get_model():
    global _model
    if _model is None:
        path = _get_music2emo_path()
        if path not in sys.path:
            sys.path.insert(0, path)
        from music2emo import Music2emo  # noqa: PLC0415
        _model = Music2emo()
    return _model


def analyze(audio_path: Path) -> tuple[float, float, list[str]] | None:
    """Extract (valence, energy, mood_tags) from an audio file.

    Returns:
        (valence, energy, mood_tags) where valence and energy are in [0.0, 1.0]
        and mood_tags is a list of MTG-Jamendo label strings, or None on failure.
    """
    try:
        music2emo_path = _get_music2emo_path()

        # music2emo uses hardcoded relative paths (./inference/data/, ./saved_models/)
        # that only resolve correctly from inside the snapshot directory — this applies
        # to both Music2emo.__init__ (loads the checkpoint) and predict() (loads config
        # and chord data). We chdir there for the entire operation and restore afterward.
        # The audio path must be made absolute first so it survives the chdir.
        audio_abs = str(audio_path.resolve())
        old_cwd = os.getcwd()
        os.chdir(music2emo_path)
        try:
            result = _get_model().predict(audio_abs, threshold=0.7)
        finally:
            os.chdir(old_cwd)

        valence = float(max(0.0, min(1.0, (result["valence"] - 1.0) / 8.0)))
        energy = float(max(0.0, min(1.0, (result["arousal"] - 1.0) / 8.0)))
        mood_tags: list[str] = result.get("predicted_moods", [])

        if not (math.isfinite(valence) and math.isfinite(energy)):
            return None

        return valence, energy, mood_tags
    except Exception as e:
        print(f"[feature_extractor] ERROR on {audio_path}: {e}")
        return None
