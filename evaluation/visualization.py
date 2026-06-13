"""Visualisation helpers for mood prediction benchmarks.

Expects DataFrames produced by spot_checks.run_evaluation with schema:
  model, dataset, song_id, gt_valence, gt_arousal, valence, arousal
"""

from __future__ import annotations

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from metrics import compute_metrics


def plot_scatter(df: pd.DataFrame, title: str = "") -> None:
    """1×2 scatter grid (valence | arousal) for a single model's results.

    If df contains multiple datasets they are overlaid with different colours.
    Saves a PNG named after title (spaces replaced with underscores).
    """
    if df.empty:
        print(f"No data to plot{f' for {title}' if title else ''}.")
        return

    datasets = df["dataset"].unique() if "dataset" in df.columns else [""]
    colors = plt.cm.tab10(np.linspace(0, 0.9, len(datasets)))

    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    for col_i, dim in enumerate(["valence", "arousal"]):
        ax = axes[col_i]
        gt_col = f"gt_{dim}"
        for ds_name, color in zip(datasets, colors):
            grp = df[df["dataset"] == ds_name] if ds_name else df
            idx = grp[[dim, gt_col]].dropna().index
            ax.scatter(grp.loc[idx, gt_col], grp.loc[idx, dim],
                       alpha=0.35, s=10, label=ds_name or "", color=color, rasterized=True)
        ax.plot([0, 1], [0, 1], "r--", lw=1)
        ax.set_xlabel(f"Ground truth {dim}")
        ax.set_ylabel(f"Predicted {dim}")
        ax.set_title(dim.capitalize())
        ax.set_xlim(-0.05, 1.05)
        ax.set_ylim(-0.05, 1.05)
        m = compute_metrics(df, dim)
        ax.text(0.04, 0.91,
                f"MAE={m['mae']:.3f}  R²={m['r2']:.3f}  n={m['n']}",
                transform=ax.transAxes, fontsize=8)
        if len(datasets) > 1:
            ax.legend(fontsize=7)

    plt.suptitle(title or "Predicted vs Ground-Truth", y=1.01)
    plt.tight_layout()
    fname = f"{(title or 'scatter').lower().replace(' ', '_')}.png"
    plt.savefig(fname, dpi=120, bbox_inches="tight")
    plt.show()
    print(f"Saved: {fname}")


def cross_dataset_comparison(df: pd.DataFrame) -> None:
    """Grouped bar chart: MAE and R² per model × dataset × dimension.

    df must have 'model' and 'dataset' columns (produced by concatenating
    results from multiple run_evaluation calls or multiple notebooks).
    """
    if df.empty or "model" not in df.columns or "dataset" not in df.columns:
        print("cross_dataset_comparison requires 'model' and 'dataset' columns.")
        return

    models = df["model"].unique()
    datasets = df["dataset"].unique()
    colors = plt.cm.tab10(np.linspace(0, 0.9, len(models)))

    rows = []
    for model in models:
        for ds in datasets:
            sub = df[(df["model"] == model) & (df["dataset"] == ds)]
            if sub.empty:
                continue
            for dim in ["valence", "arousal"]:
                m = compute_metrics(sub, dim)
                rows.append({"Model": model, "Dataset": ds, "Dim": dim,
                             "MAE": m["mae"], "R²": m["r2"], "Kendall τ": m["kendall_tau"]})

    summary = pd.DataFrame(rows)
    if summary.empty:
        print("No metrics to compare.")
        return

    print(summary.to_string(index=False, float_format="{:.4f}".format))

    x = np.arange(len(datasets))
    width = 0.8 / len(models)
    offsets = np.linspace(-(len(models) - 1) * width / 2, (len(models) - 1) * width / 2, len(models))
    metric_cfg = [
        ("MAE",       "MAE (lower is better)"),
        ("R²",        "R² (higher is better)"),
        ("Kendall τ", "Kendall τ (higher is better)"),
    ]

    fig, axes = plt.subplots(3, 2, figsize=(14, 15))
    for row_i, (metric_key, metric_label) in enumerate(metric_cfg):
        for col_i, dim in enumerate(["valence", "arousal"]):
            ax = axes[row_i][col_i]
            for i, (model, color) in enumerate(zip(models, colors)):
                heights = [
                    float(summary.loc[
                        (summary["Model"] == model) &
                        (summary["Dataset"] == ds) &
                        (summary["Dim"] == dim), metric_key
                    ].values[0])
                    if len(summary.loc[
                        (summary["Model"] == model) &
                        (summary["Dataset"] == ds) &
                        (summary["Dim"] == dim)
                    ]) else float("nan")
                    for ds in datasets
                ]
                ax.bar(x + offsets[i], heights, width, label=model, color=color, alpha=0.8)
            ax.set_xticks(x)
            ax.set_xticklabels(datasets)
            ax.set_ylabel(metric_label)
            ax.set_title(f"{dim.capitalize()} — {metric_label}")
            ax.legend(fontsize=8)

    plt.suptitle("Cross-Dataset Comparison")
    plt.tight_layout()
    plt.savefig("cross_dataset_comparison.png", dpi=120, bbox_inches="tight")
    plt.show()
    print("Saved: cross_dataset_comparison.png")


def plot_spot_checks(spot_df: pd.DataFrame, model_tag: str) -> None:
    """Mood-space scatter of spot-check predictions vs expected positions.

    ★ = expected position, ● = predicted position, arrow shows the error.
    Saves <model_tag>_spotchecks.png.
    """
    if spot_df.empty:
        print("No spot-check results to plot.")
        return
    colors = plt.cm.tab10(np.linspace(0, 0.9, len(spot_df)))
    fig, ax = plt.subplots(figsize=(7, 7))
    ax.set_xlim(-0.05, 1.05)
    ax.set_ylim(-0.05, 1.05)
    ax.axhline(0.5, color="#ccc", lw=0.8, ls="--")
    ax.axvline(0.5, color="#ccc", lw=0.8, ls="--")
    ax.text(0.02, 0.98, "sad/energetic",  transform=ax.transAxes, va="top",    fontsize=8, color="#999")
    ax.text(0.98, 0.98, "happy/energetic", transform=ax.transAxes, va="top",    ha="right", fontsize=8, color="#999")
    ax.text(0.02, 0.02, "sad/calm",        transform=ax.transAxes, va="bottom", fontsize=8, color="#999")
    ax.text(0.98, 0.02, "happy/calm",      transform=ax.transAxes, va="bottom", ha="right", fontsize=8, color="#999")
    for i, row in spot_df.iterrows():
        c = colors[i]
        ax.scatter(row["exp_valence"], row["exp_arousal"], marker="*", s=220, color=c, zorder=4)
        if not pd.isna(row["valence"]):
            ax.scatter(row["valence"], row["arousal"], marker="o", s=70,
                       color=c, edgecolors="black", lw=0.5, zorder=4)
            ax.annotate("", xy=(row["valence"], row["arousal"]),
                        xytext=(row["exp_valence"], row["exp_arousal"]),
                        arrowprops=dict(arrowstyle="->", color=c, lw=1.0))
        ax.annotate(row["title"], xy=(row["exp_valence"], row["exp_arousal"]),
                    xytext=(5, 5), textcoords="offset points", fontsize=7, color=c)
    ax.set_xlabel("Valence (sad → happy)")
    ax.set_ylabel("Arousal (calm → energetic)")
    ax.set_title(f"{model_tag} — Spot-checks\n★ = expected  ● = predicted")
    plt.tight_layout()
    fname = f"{model_tag}_spotchecks.png"
    plt.savefig(fname, dpi=120, bbox_inches="tight")
    plt.show()
    print(f"Saved: {fname}")
