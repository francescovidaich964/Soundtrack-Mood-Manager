# Mood Model Benchmark Results

Comparison of three model configurations across three datasets.
Results collected from notebook runs on 2025-06-07.

## Models

| ID | Model | Notebook | Notes |
|----|-------|----------|-------|
| **A** | Essentia EmoMusic (production) | `01_essentia_benchmark.ipynb` | MusiCNN + EmoMusic head; CPU |
| **B** | Essentia + Valence Correction | `01c_essentia_valence_key_correction.ipynb` | Same backbone, corrected valence column mapping; CPU |
| **C** | music2emo | `02_music2emo_benchmark.ipynb` | MERT + chord/key features; CPU (GPU failed: P100 sm_60 incompatible) |

Arousal results for **A** and **B** are identical — the correction only affects valence.

---

## DEAM (n = 1802 / 1756 for C)

| Dimension | Metric | A — Essentia | B — Corrected | C — music2emo |
|-----------|--------|:------------:|:-------------:|:-------------:|
| **Valence** | MAE | **0.0913** | 0.1006 | 0.1009 |
| | R² | **0.3801** | 0.2555 | 0.2497 |
| | Pearson r | 0.6200 | 0.5381 | **0.6550** |
| | Kendall τ | 0.4593 | 0.3812 | **0.4777** |
| **Arousal** | MAE | **0.0906** | 0.0906 | 0.0919 |
| | R² | **0.4726** | **0.4726** | 0.4603 |
| | Pearson r | 0.6965 | 0.6965 | **0.7586** |
| | Kendall τ | 0.5303 | 0.5303 | **0.5727** |

---

## PMEmo (n = 767)

music2emo had no valid results on PMEmo (ID matching failure on that run).

| Dimension | Metric | A — Essentia | B — Corrected | C — music2emo |
|-----------|--------|:------------:|:-------------:|:-------------:|
| **Valence** | MAE | 0.1238 | **0.1111** | — |
| | R² | 0.1499 | **0.2818** | — |
| | Pearson r | 0.5749 | **0.6258** | — |
| | Kendall τ | 0.4123 | **0.4481** | — |
| **Arousal** | MAE | 0.1076 | 0.1076 | — |
| | R² | 0.4897 | 0.4897 | — |
| | Pearson r | 0.7455 | 0.7455 | — |
| | Kendall τ | 0.5435 | 0.5435 | — |

---

## MERGE (n = 3232 / 3082 for C)

| Dimension | Metric | A — Essentia | B — Corrected | C — music2emo |
|-----------|--------|:------------:|:-------------:|:-------------:|
| **Valence** | MAE | 0.1843 | **0.1783** | 0.1889 |
| | R² | 0.1189 | **0.1487** | 0.0202 |
| | Pearson r | 0.3857 | **0.4218** | 0.3159 |
| | Kendall τ | 0.2584 | **0.2783** | 0.2283 |
| **Arousal** | MAE | **0.1108** | **0.1108** | 0.1156 |
| | R² | **−0.0127** | **−0.0127** | −0.1236 |
| | Pearson r | 0.6246 | 0.6246 | **0.6672** |
| | Kendall τ | 0.4399 | 0.4399 | **0.4655** |

---

## Spot-checks (qualitative)

| Track | Expected V / A | A — Essentia | B — Corrected | C — music2emo |
|-------|---------------|:------------:|:-------------:|:-------------:|
| Don't Stop Me Now (happy/energetic) | 0.90 / 0.95 | 0.57 / 0.59 | 0.62 / 0.59 | — |
| Clair de Lune (happy/calm) | 0.70 / 0.10 | 0.39 / 0.35 | 0.45 / 0.35 | — |
| Killing in the Name (sad/energetic) | 0.30 / 0.95 | 0.64 / 0.70 | 0.58 / 0.70 | — |
| Hurt — Johnny Cash (sad/calm) | 0.10 / 0.15 | 0.42 / 0.38 | 0.48 / 0.38 | — |
| Walking on Sunshine (happy/energetic) | 0.95 / 0.85 | 0.60 / 0.62 | 0.66 / 0.62 | — |

music2emo spot-checks were not run (GPU failure session; CPU rerun pending).

---

## Summary

- **Arousal** is consistently easier to predict than **valence** across all models and datasets — consistent with the MER literature.
- **B (Essentia + Correction)** is the most consistent overall: it matches or beats A on valence for PMEmo and MERGE, and arousal is identical to A. It is worse than A only on DEAM valence (MAE +0.009, R² −0.125).
- **C (music2emo)** achieves the best arousal *ranking* (Pearson r, Kendall τ) on DEAM and MERGE, but its absolute calibration is poor (low R², negative on MERGE arousal). PMEmo results are missing. Requires a re-run with a compatible GPU or on a larger CPU machine.
- **For the DnD use case** (track selection by cursor proximity), ranking quality matters more than absolute calibration. A re-run of music2emo with working inference would be needed before drawing final conclusions.

---

## Runtime

| Model | s / track | Hardware |
|-------|-----------|----------|
| A — Essentia EmoMusic | ~14 s | CPU (Kaggle, DEAM 45 s clips) |
| B — Essentia + Correction | ~13 s | CPU (Kaggle, DEAM 45 s clips) |
| C — music2emo | TBD | TBD |
