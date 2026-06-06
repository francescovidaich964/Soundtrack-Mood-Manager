"""Evaluation metrics for mood prediction benchmarks.

Expected DataFrame schema (produced by spot_checks.run_evaluation):
  model       — string label, e.g. 'essentia' or 'music2emo'
  dataset     — string label, e.g. 'DEAM'
  song_id     — int
  gt_valence  — float [0, 1]
  gt_arousal  — float [0, 1]
  valence     — float [0, 1] or NaN (model prediction)
  arousal     — float [0, 1] or NaN (model prediction)
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.stats import pearsonr


def compute_metrics(df: pd.DataFrame, dim: str) -> dict:
    """MAE, R², and Pearson r for one dimension (valence or arousal).

    Args:
        df:  DataFrame with columns ``dim`` (prediction) and ``gt_<dim>`` (ground truth).
        dim: 'valence' or 'arousal'.

    Returns:
        Dict with keys n, mae, r2, pearson_r.
    """
    gt_col = f"gt_{dim}"
    valid = df[[dim, gt_col]].dropna()
    if len(valid) < 2:
        return {"n": len(valid), "mae": float("nan"), "r2": float("nan"), "pearson_r": float("nan")}

    y_true = valid[gt_col].values
    y_pred = valid[dim].values
    mae = float(np.mean(np.abs(y_pred - y_true)))
    r, _ = pearsonr(y_pred, y_true)
    ss_tot = float(np.sum((y_true - np.mean(y_true)) ** 2))
    r2 = float(1 - np.sum((y_true - y_pred) ** 2) / ss_tot) if ss_tot > 0 else float("nan")
    return {"n": len(valid), "mae": mae, "r2": r2, "pearson_r": float(r)}


def print_metrics(df: pd.DataFrame, title: str = "") -> None:
    """Print a formatted metrics table for all datasets in df.

    Groups by 'dataset' column when present; otherwise treats df as a single group.
    """
    if df.empty:
        print(f"No results{f' for {title}' if title else ''}.")
        return

    if title:
        print(f"\n── {title} ──")

    groups = (
        [(name, grp) for name, grp in df.groupby("dataset")]
        if "dataset" in df.columns
        else [("", df)]
    )

    for ds_name, grp in groups:
        if ds_name:
            print(f"  {ds_name}:")
        rows = []
        for dim in ["valence", "arousal"]:
            if dim not in grp.columns or f"gt_{dim}" not in grp.columns:
                continue
            m = compute_metrics(grp, dim)
            rows.append({
                "Dim":       dim,
                "n":         m["n"],
                "MAE":       f"{m['mae']:.4f}",
                "R²":        f"{m['r2']:.4f}",
                "Pearson r": f"{m['pearson_r']:.4f}",
            })
        if rows:
            indent = "    " if ds_name else "  "
            table = pd.DataFrame(rows).to_string(index=False)
            for line in table.split("\n"):
                print(indent + line)
