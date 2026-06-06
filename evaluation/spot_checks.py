"""Spot-check tracks, generic evaluation loop, and runtime profiler.

run_evaluation() is the shared entry point for both benchmark notebooks.
It accepts any predictor callable with signature:
  predictor_fn(audio_path: str | Path) -> {"valence": float, "arousal": float} | None
Both values must be in [0, 1].
"""

from __future__ import annotations

import subprocess
import time
import tracemalloc
from pathlib import Path

import numpy as np
import pandas as pd
from tqdm.notebook import tqdm


# ── Spot-check track definitions ─────────────────────────────────────────────

SPOT_CHECKS = [
    {
        "title": "dont_stop_me_now",
        "query": "Queen Don't Stop Me Now official audio",
        "exp_valence": 0.90,
        "exp_arousal": 0.95,
    },
    {
        "title": "clair_de_lune",
        "query": "Debussy Clair de Lune full piano",
        "exp_valence": 0.70,
        "exp_arousal": 0.10,
    },
    {
        "title": "killing_in_the_name",
        "query": "Rage Against The Machine Killing In The Name audio",
        "exp_valence": 0.30,
        "exp_arousal": 0.95,
    },
    {
        "title": "hurt_johnny_cash",
        "query": "Johnny Cash Hurt official audio",
        "exp_valence": 0.10,
        "exp_arousal": 0.15,
    },
    {
        "title": "walking_on_sunshine",
        "query": "Katrina and the Waves Walking on Sunshine official",
        "exp_valence": 0.95,
        "exp_arousal": 0.85,
    },
]


def download_spot_checks(output_dir: Path) -> None:
    """Download SPOT_CHECKS tracks via yt-dlp."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    for track in SPOT_CHECKS:
        dest = output_dir / f"{track['title']}.mp3"
        if dest.exists():
            print(f"  ✓ {track['title']} (cached)")
            continue
        print(f"Downloading {track['title']}...", end=" ", flush=True)
        result = subprocess.run(
            [
                "yt-dlp", "-x", "--audio-format", "mp3", "--audio-quality", "128K",
                "-o", str(output_dir / f"{track['title']}.%(ext)s"),
                "--match-filter", "duration < 600",
                "--no-playlist", "-q",
                f"ytsearch1:{track['query']}",
            ],
            capture_output=True, text=True,
        )
        if dest.exists():
            print(f"done ({dest.stat().st_size / 1e6:.1f} MB)")
        else:
            print(f"FAILED\n  stderr: {result.stderr[:300]}")


# ── Evaluation loop ───────────────────────────────────────────────────────────

def run_evaluation(
    dataset_name: str,
    model_name: str,
    predictor_fn,
    audio_dir,
    df_annot: pd.DataFrame,
    id_col: str,
    val_col: str,
    aro_col: str,
    max_tracks: int | None = None,
) -> pd.DataFrame:
    """Run predictor_fn over all annotated audio files; return a tidy results DataFrame.

    Args:
        dataset_name: Label stored in the 'dataset' column (e.g. 'DEAM').
        model_name:   Label stored in the 'model' column (e.g. 'essentia').
        predictor_fn: Callable(audio_path) → {"valence": float, "arousal": float} | None.
        audio_dir:    Root directory to search for .mp3 files (recursively).
                      Files can be in subdirectories (e.g. MERGE's Q1/Q2/Q3/Q4 layout).
        df_annot:     Annotation DataFrame.
        id_col:       Column with the song identifier (int or string).
        val_col:      Column with ground-truth valence.
        aro_col:      Column with ground-truth arousal.
        max_tracks:   Cap on tracks to evaluate (None = all).

    Returns:
        DataFrame with columns:
          model, dataset, song_id, gt_valence, gt_arousal, valence, arousal
    """
    # Build {stem → path} map with recursive search so nested layouts (e.g. Q1/Q2/Q3/Q4)
    # are handled the same as flat directories.
    audio_map = {p.stem: p for p in sorted(Path(audio_dir).rglob("*.mp3"))}
    if not audio_map:
        print(f"  ⚠  No .mp3 files found under {audio_dir}")
        return pd.DataFrame()

    # Build annotation lookup keyed on string ID for O(1) access
    annot_lookup: dict[str, tuple[float, float]] = {}
    for _, row in df_annot.iterrows():
        key = str(row[id_col]).strip()
        annot_lookup[key] = (float(row[val_col]), float(row[aro_col]))

    items = list(audio_map.items())
    if max_tracks:
        items = items[:max_tracks]

    records = []
    for stem, audio_path in tqdm(items, desc=f"{dataset_name} / {model_name}"):
        if stem not in annot_lookup:
            continue

        gt_v, gt_a = annot_lookup[stem]

        # Normalise [1, 9] → [0, 1] for DEAM and EmoMusic; PMEmo is already [0, 1]
        if gt_v > 1.5 or gt_a > 1.5:
            gt_v = (gt_v - 1.0) / 8.0
            gt_a = (gt_a - 1.0) / 8.0

        pred = predictor_fn(audio_path)
        records.append({
            "model":      model_name,
            "dataset":    dataset_name,
            "song_id":    stem,
            "gt_valence": gt_v,
            "gt_arousal": gt_a,
            "valence":    pred["valence"] if pred else float("nan"),
            "arousal":    pred["arousal"] if pred else float("nan"),
        })

    df = pd.DataFrame(records)
    if not df.empty:
        ok = df["valence"].notna().sum()
        print(f"{dataset_name}: {len(df)} tracks  |  OK: {ok}  |  failed: {len(df) - ok}")
    return df


# ── Profiler ──────────────────────────────────────────────────────────────────

def profile_predictor(predictor_fn, audio_path, n: int = 5) -> dict:
    """Time and memory-profile predictor_fn over n runs.

    Returns {"mean_s": float, "std_s": float, "peak_mb": float}.
    Note: peak_mb measures Python heap allocations only (via tracemalloc).
    GPU memory is not included.
    """
    tracemalloc.start()
    times = []
    for _ in range(n):
        t0 = time.perf_counter()
        predictor_fn(audio_path)
        times.append(time.perf_counter() - t0)
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return {
        "mean_s":  float(np.mean(times)),
        "std_s":   float(np.std(times)),
        "peak_mb": peak / 1e6,
    }
