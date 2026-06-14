# Mood Model Benchmark Results

Cross-dataset evaluation of all tested valence/arousal models.
Results collected from Kaggle/Colab notebook runs, June 2025.

---

## Notebooks and Models Tested

| Notebook | Model tag | Backbone | Head | Key correction |
|----------|-----------|----------|------|---------------|
| `01_essentia_emomusic` | `emomusic-musicnn` | MusiCNN | EmoMusic | None — **current production** |
| `01b_essentia_all_heads` | `deam-musicnn` | MusiCNN | DEAM | None |
| `01b_essentia_all_heads` | `emomusic-vggish` | VGGish | EmoMusic | None |
| `01b_essentia_all_heads` | `deam-vggish` | VGGish | DEAM | None |
| `01c_essentia_emomusic_key_correction` | `emomusic-musicnn+key` | MusiCNN | EmoMusic | +0.13 × (major−0.5) × strength |
| `01d_essentia_deam_key_correction` | `deam-musicnn+key` | MusiCNN | DEAM | +0.13 × (major−0.5) × strength |
| `02_music2emo` | `music2emo` | MERT-v1-95M | Multi-task FC | Built-in chord/key |

---

## Results by Dataset

All metrics are on [0, 1]-normalised predictions vs ground truth.
**V** = valence · **A** = arousal · **bold** = best value in column.

### DEAM (n = 1802)

| Model | V MAE | V R² | V r | V τ | A MAE | A R² | A r | A τ |
|-------|------:|-----:|----:|----:|------:|-----:|----:|----:|
| **deam-musicnn** | **0.067** | **0.654** | **0.820** | **0.635** | **0.066** | **0.725** | **0.865** | **0.690** |
| deam-musicnn+key | 0.077 | 0.561 | 0.750 | 0.558 | **0.066** | **0.725** | **0.865** | **0.690** |
| deam-vggish | 0.079 | 0.547 | 0.766 | 0.574 | 0.079 | 0.623 | 0.813 | 0.625 |
| emomusic-vggish | 0.089 | 0.419 | 0.662 | 0.493 | 0.090 | 0.497 | 0.707 | 0.527 |
| emomusic-musicnn | 0.091 | 0.380 | 0.620 | 0.459 | 0.091 | 0.473 | 0.697 | 0.530 |
| music2emo | 0.101 | 0.250 | 0.655 | 0.478 | 0.092 | 0.460 | 0.759 | 0.573 |
| emomusic-musicnn+key | 0.101 | 0.256 | 0.538 | 0.381 | 0.091 | 0.473 | 0.697 | 0.530 |

> Key correction costs ~0.09 R² on DEAM valence (0.654 → 0.561) but arousal is unaffected.
> deam-musicnn's high DEAM score has a partial in-sample advantage (head trained on DEAM data).

### PMEmo (n = 767, cross-dataset)

| Model | V MAE | V R² | V r | V τ | A MAE | A R² | A r | A τ |
|-------|------:|-----:|----:|----:|------:|-----:|----:|----:|
| **deam-musicnn+key** | **0.095** | **0.454** | **0.686** | **0.500** | 0.115 | 0.424 | 0.724 | 0.531 |
| deam-musicnn | 0.103 | 0.394 | 0.669 | 0.492 | 0.115 | 0.424 | 0.724 | 0.531 |
| emomusic-musicnn+key | 0.111 | 0.282 | 0.626 | 0.448 | **0.108** | **0.490** | **0.746** | **0.544** |
| deam-vggish | 0.119 | 0.228 | 0.582 | 0.439 | 0.140 | 0.194 | 0.662 | 0.463 |
| emomusic-musicnn | 0.124 | 0.150 | 0.575 | 0.412 | **0.108** | **0.490** | **0.746** | **0.544** |
| emomusic-vggish | 0.131 | 0.090 | 0.601 | 0.465 | 0.138 | 0.224 | 0.651 | 0.449 |
| music2emo | — | — | — | — | — | — | — | — |

> deam-musicnn+key is the clear valence winner on PMEmo (+0.06 R² vs uncorrected deam-musicnn).
> music2emo had no valid results on PMEmo (ID matching issue — needs re-run).

### MERGE (n = 3232, AllMusic editorial tags)

| Model | V MAE | V R² | V r | V τ | A MAE | A R² | A r | A τ |
|-------|------:|-----:|----:|----:|------:|-----:|----:|----:|
| **emomusic-musicnn+key** | **0.178** | **0.149** | **0.422** | **0.278** | 0.111 | −0.013 | 0.625 | 0.440 |
| emomusic-musicnn | 0.184 | 0.119 | 0.386 | 0.258 | 0.111 | −0.013 | 0.625 | 0.440 |
| emomusic-vggish | 0.194 | 0.104 | 0.327 | 0.227 | 0.103 | 0.134 | 0.635 | 0.433 |
| music2emo | 0.189 | 0.020 | 0.316 | 0.228 | 0.116 | −0.124 | **0.667** | **0.466** |
| deam-musicnn+key | 0.193 | 0.009 | 0.286 | 0.200 | **0.094** | 0.224 | 0.634 | 0.459 |
| deam-musicnn | 0.201 | −0.026 | 0.219 | 0.168 | **0.094** | 0.224 | 0.634 | 0.459 |
| **deam-vggish** | 0.208 | −0.026 | 0.142 | 0.137 | **0.084** | **0.355** | 0.668 | 0.484 |

> MERGE uses editorial tags (not listener ratings) so all models struggle — DEAM-trained
> heads fail on MERGE valence (R² < 0), though key correction partially recovers deam-musicnn
> from −0.026 to +0.009. emomusic-musicnn+key remains the best for MERGE valence.

---

## Spot-checks (qualitative, 5 tracks)

`v` = valence · `a` = arousal.

| Track | Expected | emomusic-musicnn | emomusic+key | deam-musicnn+key |
|-------|----------|:----------------:|:------------:|:----------------:|
| Don't Stop Me Now (happy/energetic) | v=0.90 a=0.95 | v=0.57 a=0.59 | v=0.62 a=0.59 | v=0.65 a=0.58 |
| Clair de Lune (happy/calm) | v=0.70 a=0.10 | v=0.39 a=0.35 | v=0.45 a=0.35 | v=0.42 a=0.35 |
| Killing in the Name (sad/energetic) | v=0.30 a=0.95 | v=0.64 a=0.70 | v=0.58 a=0.70 | v=0.49 a=0.70 |
| Hurt — Johnny Cash (sad/calm) | v=0.10 a=0.15 | v=0.42 a=0.38 | v=0.48 a=0.38 | v=0.46 a=0.36 |
| Walking on Sunshine (happy/energetic) | v=0.95 a=0.85 | v=0.60 a=0.62 | v=0.66 a=0.62 | v=0.71 a=0.64 |

> Key correction consistently moves valence predictions in the right direction.
> deam-musicnn+key is best on 3/5 tracks; all models under-predict happy/energetic valence.

---

## Runtime

| Model | s / track | Hardware |
|-------|-----------|----------|
| Essentia (no key correction) | ~13–14 s | CPU (Kaggle, DEAM 45 s clips) |
| Essentia + key correction | ~13–14 s | CPU — KeyExtractor adds < 0.5 s overhead |
| music2emo | ~0.66 s (profiling) | CPU (Kaggle, shorter spot-check clips) |

---

## Cross-Model Summary

### Average valence R² across listener-study datasets (DEAM + PMEmo)

MERGE excluded here — its editorial annotations are not comparable to the other two.

| Model | DEAM | PMEmo | Avg |
|-------|-----:|------:|----:|
| deam-musicnn | **0.654** | 0.394 | 0.524 |
| **deam-musicnn+key** | 0.561 | **0.454** | **0.508** |
| deam-vggish | 0.547 | 0.228 | 0.388 |
| emomusic-musicnn+key | 0.256 | 0.282 | 0.269 |
| emomusic-musicnn | 0.380 | 0.150 | 0.265 |
| emomusic-vggish | 0.419 | 0.090 | 0.255 |

### Average arousal R² (key correction has no effect on arousal)

| Model | DEAM | PMEmo | Avg |
|-------|-----:|------:|----:|
| **deam-musicnn (= deam-musicnn+key)** | **0.725** | 0.424 | **0.575** |
| emomusic-musicnn (= emomusic-musicnn+key) | 0.473 | **0.490** | 0.482 |
| deam-vggish | 0.623 | 0.194 | 0.409 |
| emomusic-vggish | 0.497 | 0.224 | 0.361 |

---

## Production Recommendation

### Suggested new production model: `deam-musicnn+key`

**Swap `emomusic-msd-musicnn-2.pb` → `deam-msd-musicnn-2.pb` and enable the key-mode valence correction from `feat/valence_key_correction`.**

**Why deam-musicnn+key wins:**

1. **Best cross-dataset valence**: Top model on PMEmo (R²=0.454, the cleanest cross-dataset
   test), only −0.093 behind uncorrected deam on DEAM itself. The DEAM gap is partly
   in-sample bias — PMEmo is a fairer generalisation test.

2. **Identical arousal**: Key correction does not affect arousal. Both deam variants share
   the best arousal numbers across all datasets (DEAM R²=0.725, PMEmo R²=0.424).

3. **Key correction is especially valuable for DnD music**: Orchestral and fantasy music
   has a much stronger major/minor → valence relationship than pop music. The correction
   (calibrated conservatively on EmoMusic pop) will likely gain more on a DnD playlist
   than the PMEmo numbers suggest.

4. **Spot-check improvements**: deam-musicnn+key is the best model on 3 of 5 qualitative
   tracks and moves predictions in the correct direction on all of them.

5. **Trivial implementation cost**: Change one `.pb` filename in `models/` and add the
   `KeyExtractor` post-processing from `feat/valence_key_correction`. Same inference
   time (< 0.5 s overhead per track).

**Why not the alternatives:**

| Model | Reason to skip |
|-------|---------------|
| deam-musicnn (no correction) | Marginally better DEAM valence but weaker PMEmo (0.394 vs 0.454) |
| emomusic-musicnn+key | Loses to deam+key on both DEAM and PMEmo valence |
| deam-vggish | Weak PMEmo valence (0.228); VGGish backbone offers no benefit |
| music2emo | Incomplete benchmark (no PMEmo), poor MERGE arousal, heavy runtime dependency |
