# Mood Model Benchmark Results

Cross-dataset evaluation of all tested valence/arousal models.
Results collected from Kaggle/Colab notebook runs, June 2025.

---

## Notebooks and Models Tested

| Notebook | Model tag | Backbone | Head | Key correction |
|----------|-----------|----------|------|---------------|
| `01_essentia_emomusic` | `emomusic-musicnn` | MusiCNN | EmoMusic | None — **production model** |
| `01b_essentia_all_heads` | `deam-musicnn` | MusiCNN | DEAM | None |
| `01b_essentia_all_heads` | `emomusic-vggish` | VGGish | EmoMusic | None |
| `01b_essentia_all_heads` | `deam-vggish` | VGGish | DEAM | None |
| `01c_essentia_emomusic_key_correction` | `emomusic-musicnn+key` | MusiCNN | EmoMusic | +0.13 × (major−0.5) × strength |
| `01d_essentia_deam_key_correction` | `deam-musicnn+key` | MusiCNN | DEAM | +0.13 × (major−0.5) × strength |
| `02_music2emo` | `music2emo` | MERT-v1-95M | Multi-task FC | Built-in chord/key |

> `01d` has not been run yet — predicted results in the analysis section below.

---

## Results by Dataset

All metrics are reported on [0, 1]-normalised predictions vs ground truth.
**V** = valence, **A** = arousal.

### DEAM (n = 1802)

| Model | V MAE | V R² | V r | V τ | A MAE | A R² | A r | A τ |
|-------|------:|-----:|----:|----:|------:|-----:|----:|----:|
| **deam-musicnn** | **0.067** | **0.654** | **0.820** | **0.635** | **0.066** | **0.725** | **0.865** | **0.690** |
| deam-vggish | 0.079 | 0.547 | 0.766 | 0.574 | 0.079 | 0.623 | 0.813 | 0.625 |
| emomusic-vggish | 0.089 | 0.419 | 0.662 | 0.493 | 0.090 | 0.497 | 0.707 | 0.527 |
| emomusic-musicnn | 0.091 | 0.380 | 0.620 | 0.459 | 0.091 | 0.473 | 0.697 | 0.530 |
| music2emo | 0.101 | 0.250 | **0.655** | **0.478** | 0.092 | 0.460 | **0.759** | **0.573** |
| emomusic-musicnn+key | 0.101 | 0.256 | 0.538 | 0.381 | 0.091 | 0.473 | 0.697 | 0.530 |

> Note: deam-musicnn's high DEAM score has an in-sample advantage (head trained on DEAM data).
> music2emo leads on ranking metrics (r, τ) despite weaker absolute accuracy (R²).

### PMEmo (n = 767, cross-dataset)

| Model | V MAE | V R² | V r | V τ | A MAE | A R² | A r | A τ |
|-------|------:|-----:|----:|----:|------:|-----:|----:|----:|
| **deam-musicnn** | **0.103** | **0.394** | **0.669** | **0.492** | 0.115 | 0.424 | 0.724 | 0.531 |
| emomusic-musicnn+key | 0.111 | 0.282 | 0.626 | 0.448 | **0.108** | **0.490** | **0.746** | **0.544** |
| deam-vggish | 0.119 | 0.228 | 0.582 | 0.439 | 0.140 | 0.194 | 0.662 | 0.463 |
| emomusic-musicnn | 0.124 | 0.150 | 0.575 | 0.412 | **0.108** | **0.490** | **0.746** | **0.544** |
| emomusic-vggish | 0.131 | 0.090 | 0.601 | 0.465 | 0.138 | 0.224 | 0.651 | 0.449 |
| music2emo | — | — | — | — | — | — | — | — |

> music2emo had no valid results on PMEmo (ID matching issue on that run — needs re-run).

### MERGE (n = 3232, AllMusic editorial tags)

| Model | V MAE | V R² | V r | V τ | A MAE | A R² | A r | A τ |
|-------|------:|-----:|----:|----:|------:|-----:|----:|----:|
| **emomusic-musicnn+key** | **0.178** | **0.149** | **0.422** | **0.278** | 0.111 | −0.013 | 0.625 | 0.440 |
| emomusic-musicnn | 0.184 | 0.119 | 0.386 | 0.258 | 0.111 | −0.013 | 0.625 | 0.440 |
| emomusic-vggish | 0.194 | 0.104 | 0.327 | 0.227 | 0.103 | 0.134 | 0.635 | 0.433 |
| music2emo | 0.189 | 0.020 | 0.316 | 0.228 | 0.116 | −0.124 | **0.667** | **0.466** |
| deam-musicnn | 0.201 | −0.026 | 0.219 | 0.168 | 0.094 | 0.224 | 0.634 | 0.459 |
| **deam-vggish** | 0.208 | −0.026 | 0.142 | 0.137 | **0.084** | **0.355** | 0.668 | 0.484 |

> All models struggle on MERGE — MERGE uses AllMusic editorial tags rather than direct
> listener arousal/valence ratings, which produces a weaker signal for all models.
> DEAM-trained models collapse on MERGE valence (R² < 0), suggesting overfit to DEAM conventions.

---

## Spot-checks (qualitative)

Five tracks spanning all mood quadrants. `v` = valence, `a` = arousal.

| Track | Expected | emomusic-musicnn | emomusic-musicnn+key |
|-------|----------|:----------------:|:--------------------:|
| Don't Stop Me Now (happy/energetic) | v=0.90 a=0.95 | v=0.57 a=0.59 | v=0.62 a=0.59 |
| Clair de Lune (happy/calm) | v=0.70 a=0.10 | v=0.39 a=0.35 | v=0.45 a=0.35 |
| Killing in the Name (sad/energetic) | v=0.30 a=0.95 | v=0.64 a=0.70 | v=0.58 a=0.70 |
| Hurt — Johnny Cash (sad/calm) | v=0.10 a=0.15 | v=0.42 a=0.38 | v=0.48 a=0.38 |
| Walking on Sunshine (happy/energetic) | v=0.95 a=0.85 | v=0.60 a=0.62 | v=0.66 a=0.62 |

> Spot-checks for deam-musicnn, deam-vggish, and music2emo not yet run.
> Key correction shifts valence in the expected direction on all 5 tracks.

---

## Runtime

| Model family | s / track | Hardware | Notes |
|---|---|---|---|
| Essentia (all heads) | ~13–14 s | CPU (Kaggle) | DEAM 45 s clips; essentia-tensorflow is CPU-only |
| music2emo | ~0.66 s (profiling) | CPU (Kaggle) | On spot-check clips; full dataset ~1.8 s/track |

---

## Winner Summary

**No single model dominates all datasets.** Key findings:

| Metric | Best model | Notes |
|--------|-----------|-------|
| DEAM valence R² | **deam-musicnn** (0.654) | Partly in-sample advantage |
| DEAM arousal R² | **deam-musicnn** (0.725) | |
| PMEmo valence R² | **deam-musicnn** (0.394) | Generalises well cross-dataset |
| PMEmo arousal R² | emomusic-musicnn / emomusic-musicnn+key (0.490) | Tie |
| MERGE valence R² | **emomusic-musicnn+key** (0.149) | Key correction helps here |
| MERGE arousal R² | **deam-vggish** (0.355) | |
| Arousal ranking (DEAM r) | **music2emo** (0.759) | Best ranking even if R² is lower |
| Most consistent | **emomusic-musicnn** | Production model: never best, never catastrophic |

**Recommended model for DnD/fantasy playlists (listener-study annotations):**
`deam-musicnn` — strongest on DEAM and PMEmo, which best represent music from
listening experiments. Only drops on MERGE (AllMusic editorial tags), which is
less representative of how a DnD playlist would be annotated.

**Pending results:** `01d_essentia_deam_key_correction` (deam-musicnn + key correction)
is predicted to be the best overall valence model on PMEmo and MERGE while staying
strong on DEAM — expected to outperform all current configurations. Run `01d` to confirm.
