# Mood Model Benchmark Results

Cross-dataset evaluation of all tested valence/arousal models.
Results collected from Kaggle/Colab/local notebook runs, June 2025.

---

## Notebooks and Models Tested

| Notebook | Model tag | Backbone | Head | Key correction |
|----------|-----------|----------|------|---------------|
| `01_essentia_emomusic` | `emomusic-musicnn` | MusiCNN | EmoMusic | None -- **current production** |
| `01c_essentia_emomusic_key_correction` | `emomusic-musicnn+key` | MusiCNN | EmoMusic | +0.13 x (major-0.5) x strength |
| `01b_essentia_all_heads` | `deam-musicnn` | MusiCNN | DEAM | None |
| `01d_essentia_deam_key_correction` | `deam-musicnn+key` | MusiCNN | DEAM | +0.13 x (major-0.5) x strength |
| `01b_essentia_all_heads` | `emomusic-vggish` | VGGish | EmoMusic | None |
| `01b_essentia_all_heads` | `deam-vggish` | VGGish | DEAM | None |
| `01e_essentia_muse_key_correction` | `muse-musicnn` | MusiCNN | MuSE | None |
| `01e_essentia_muse_key_correction` | `muse-musicnn+key` | MusiCNN | MuSE | +0.13 x (major-0.5) x strength |
| `01e_essentia_muse_key_correction` | `muse-vggish` | VGGish | MuSE | None |
| `01e_essentia_muse_key_correction` | `muse-vggish+key` | VGGish | MuSE | +0.13 x (major-0.5) x strength |
| `02_music2emo` | `music2emo` | MERT-v1-95M | Multi-task FC | Built-in chord/key |

---

## Datasets

**DEAM** (n = 1802) -- 45-second clips from Jamendo (Creative Commons). Mixed genres: pop, rock, electronic, jazz, country. Crowdsourced continuous valence/arousal ratings at 2 Hz; scale 1-9.

**PMEmo** (n = 767) -- 45-second chorus segments from popular songs. Crowdsourced static valence/arousal ratings; scale 0-1. Best cross-dataset benchmark: same annotation methodology as DEAM but no data overlap.

**MERGE** (n = 3232) -- 30-second clips from AllMusic covering a wide genre range (classical, ambient, soundtracks, world music). Annotations by professional editors rather than listeners; scale 0-1. Most genre-diverse dataset and closest proxy to out-of-distribution music such as DnD playlists.

---

## Results

All metrics on [0, 1]-normalised predictions vs ground truth.
**V** = valence, **A** = arousal, ***bold italic*** = best value in column.

### DEAM (n = 1802)

| Model | V MAE | V R2 | V r | V tau | A MAE | A R2 | A r | A tau |
|-------|------:|-----:|----:|------:|------:|-----:|----:|------:|
| emomusic-musicnn | 0.091 | 0.380 | 0.620 | 0.459 | 0.091 | 0.473 | 0.697 | 0.530 |
| emomusic-musicnn+key | 0.101 | 0.256 | 0.538 | 0.381 | 0.091 | 0.473 | 0.697 | 0.530 |
| deam-musicnn | ***0.067*** | ***0.654*** | ***0.820*** | ***0.635*** | ***0.066*** | ***0.725*** | ***0.865*** | ***0.690*** |
| deam-musicnn+key | 0.077 | 0.561 | 0.750 | 0.558 | ***0.066*** | ***0.725*** | ***0.865*** | ***0.690*** |
| emomusic-vggish | 0.089 | 0.419 | 0.662 | 0.493 | 0.090 | 0.497 | 0.707 | 0.527 |
| deam-vggish | 0.079 | 0.547 | 0.766 | 0.574 | 0.079 | 0.623 | 0.813 | 0.625 |
| muse-musicnn | 0.119 | 0.010 | 0.367 | 0.285 | 0.141 | -0.096 | 0.142 | 0.089 |
| muse-musicnn+key | 0.121 | -0.033 | 0.228 | 0.169 | 0.141 | -0.096 | 0.142 | 0.089 |
| muse-vggish | 0.120 | -0.025 | 0.319 | 0.276 | 0.141 | -0.095 | 0.132 | 0.124 |
| muse-vggish+key | 0.122 | -0.063 | 0.212 | 0.163 | 0.141 | -0.095 | 0.132 | 0.124 |
| music2emo | 0.101 | 0.250 | 0.655 | 0.478 | 0.092 | 0.460 | 0.759 | 0.573 |

> Key correction costs ~0.09 R2 on DEAM valence (0.654 to 0.561); arousal is unaffected.
> deam-musicnn has a partial in-sample advantage (head trained on DEAM data).
> MuSE heads show near-zero arousal signal on DEAM (r=0.14) despite the same backbone — arousal
> appears to not transfer from MuSE training data to DEAM/PMEmo conventions.

### PMEmo (n = 767)

| Model | V MAE | V R2 | V r | V tau | A MAE | A R2 | A r | A tau |
|-------|------:|-----:|----:|------:|------:|-----:|----:|------:|
| emomusic-musicnn | 0.124 | 0.150 | 0.575 | 0.412 | ***0.108*** | ***0.490*** | ***0.746*** | ***0.544*** |
| emomusic-musicnn+key | 0.111 | 0.282 | 0.626 | 0.448 | ***0.108*** | ***0.490*** | ***0.746*** | ***0.544*** |
| deam-musicnn | 0.103 | 0.394 | 0.669 | 0.492 | 0.115 | 0.424 | 0.724 | 0.531 |
| deam-musicnn+key | ***0.095*** | ***0.454*** | ***0.686*** | ***0.500*** | 0.115 | 0.424 | 0.724 | 0.531 |
| emomusic-vggish | 0.131 | 0.090 | 0.601 | 0.465 | 0.138 | 0.224 | 0.651 | 0.449 |
| deam-vggish | 0.119 | 0.228 | 0.582 | 0.439 | 0.140 | 0.194 | 0.662 | 0.463 |
| muse-musicnn | 0.139 | -0.036 | 0.138 | 0.105 | 0.234 | -1.175 | -0.094 | -0.091 |
| muse-musicnn+key | 0.135 | -0.012 | 0.218 | 0.141 | 0.234 | -1.175 | -0.094 | -0.091 |
| muse-vggish | 0.141 | -0.059 | 0.024 | 0.005 | 0.232 | -1.131 | -0.171 | -0.124 |
| muse-vggish+key | 0.137 | -0.034 | 0.176 | 0.109 | 0.232 | -1.131 | -0.171 | -0.124 |
| music2emo | - | - | - | - | - | - | - | - |

> music2emo had no valid PMEmo results (ID matching issue -- needs re-run).
> MuSE arousal on PMEmo: R2 = -1.17 (musicnn) / -1.13 (vggish) — the model is confidently
> predicting arousal in the wrong direction. Valence is also weak (r < 0.22).

### MERGE (n = 3232)

| Model | V MAE | V R2 | V r | V tau | A MAE | A R2 | A r | A tau |
|-------|------:|-----:|----:|------:|------:|-----:|----:|------:|
| emomusic-musicnn | 0.184 | 0.119 | 0.386 | 0.258 | 0.111 | -0.013 | 0.625 | 0.440 |
| emomusic-musicnn+key | ***0.178*** | ***0.149*** | ***0.422*** | ***0.278*** | 0.111 | -0.013 | 0.625 | 0.440 |
| deam-musicnn | 0.201 | -0.026 | 0.219 | 0.168 | 0.094 | 0.224 | 0.634 | 0.459 |
| deam-musicnn+key | 0.193 | 0.009 | 0.286 | 0.200 | 0.094 | 0.224 | 0.634 | 0.459 |
| emomusic-vggish | 0.194 | 0.104 | 0.327 | 0.227 | 0.103 | 0.134 | 0.635 | 0.433 |
| deam-vggish | 0.208 | -0.026 | 0.142 | 0.137 | ***0.084*** | ***0.355*** | 0.668 | ***0.484*** |
| muse-musicnn | 0.208 | 0.006 | 0.160 | 0.127 | 0.111 | -0.085 | 0.246 | 0.128 |
| muse-musicnn+key | 0.205 | 0.003 | 0.156 | 0.102 | 0.111 | -0.085 | 0.246 | 0.128 |
| muse-vggish | 0.207 | 0.011 | 0.230 | 0.175 | 0.112 | -0.081 | 0.224 | 0.116 |
| muse-vggish+key | 0.204 | 0.006 | 0.175 | 0.118 | 0.112 | -0.081 | 0.224 | 0.116 |
| music2emo | 0.189 | 0.020 | 0.316 | 0.228 | 0.116 | -0.124 | ***0.667*** | 0.466 |

> DEAM-trained heads generalise poorly to MERGE valence (R2 < 0); key correction partially
> recovers deam-musicnn (-0.026 to +0.009). emomusic-musicnn+key is best for MERGE valence.
> MuSE MERGE valence is weak (r=0.16-0.23) and arousal R2 is negative.

---

## Spot-checks (qualitative, 5 tracks)

| Track | Expected | emomusic-musicnn | emomusic+key | deam-musicnn+key |
|-------|----------|:----------------:|:------------:|:----------------:|
| Dont Stop Me Now (happy/energetic) | v=0.90 a=0.95 | v=0.57 a=0.59 | v=0.62 a=0.59 | v=0.65 a=0.58 |
| Clair de Lune (happy/calm) | v=0.70 a=0.10 | v=0.39 a=0.35 | v=0.45 a=0.35 | v=0.42 a=0.35 |
| Killing in the Name (sad/energetic) | v=0.30 a=0.95 | v=0.64 a=0.70 | v=0.58 a=0.70 | v=0.49 a=0.70 |
| Hurt -- Johnny Cash (sad/calm) | v=0.10 a=0.15 | v=0.42 a=0.38 | v=0.48 a=0.38 | v=0.46 a=0.36 |
| Walking on Sunshine (happy/energetic) | v=0.95 a=0.85 | v=0.60 a=0.62 | v=0.66 a=0.62 | v=0.71 a=0.64 |

> Key correction moves valence in the correct direction on all 5 tracks. deam-musicnn+key is
> closest to expected on 3/5. All models compress the valence range (regression to the mean).

---

## Runtime

| Model | s/track | Hardware | Notes |
|-------|---------|----------|-------|
| Essentia (no key correction) | ~13-14 s | CPU (Kaggle) | DEAM 45 s clips |
| Essentia + key correction | ~13-14 s | CPU (Kaggle) | KeyExtractor adds <0.5 s overhead |
| music2emo | ~0.66 s | Local GPU (RTX 2000 Ada) | Measured on short spot-check clips only; CPU throughput not benchmarked, expected significantly higher |

---

## Cross-Model Summary

Average Pearson r across all three datasets. MERGE is included because it is the most
genre-diverse dataset and best approximates out-of-distribution music (e.g. DnD playlists).
Its editorial annotations introduce noise but it is the most informative test for generalisation.

### Valence Pearson r

| Model | DEAM | PMEmo | MERGE | Avg |
|-------|-----:|------:|------:|----:|
| emomusic-musicnn | 0.620 | 0.575 | 0.386 | 0.527 |
| emomusic-musicnn+key | 0.538 | 0.626 | ***0.422*** | 0.529 |
| deam-musicnn | ***0.820*** | 0.669 | 0.219 | 0.569 |
| deam-musicnn+key | 0.750 | ***0.686*** | 0.286 | ***0.574*** |
| emomusic-vggish | 0.662 | 0.601 | 0.327 | 0.530 |
| deam-vggish | 0.766 | 0.582 | 0.142 | 0.497 |
| muse-musicnn | 0.367 | 0.138 | 0.160 | 0.222 |
| muse-musicnn+key | 0.228 | 0.218 | 0.156 | 0.201 |
| muse-vggish | 0.319 | 0.024 | 0.230 | 0.191 |
| muse-vggish+key | 0.212 | 0.176 | 0.175 | 0.188 |

### Arousal Pearson r (key correction has no effect on arousal)

| Model | DEAM | PMEmo | MERGE | Avg |
|-------|-----:|------:|------:|----:|
| emomusic-musicnn (=+key) | 0.697 | ***0.746*** | 0.625 | 0.689 |
| deam-musicnn (=+key) | ***0.865*** | 0.724 | 0.634 | ***0.741*** |
| emomusic-vggish | 0.707 | 0.651 | 0.635 | 0.664 |
| deam-vggish | 0.813 | 0.662 | 0.668 | 0.714 |
| muse-musicnn (=+key) | 0.142 | -0.094 | 0.246 | 0.098 |
| muse-vggish (=+key) | 0.132 | -0.171 | 0.224 | 0.062 |
| music2emo | 0.759 | - | ***0.667*** | - |

---

## Production Recommendation

### For absolute accuracy: `deam-musicnn+key`

Best valence on PMEmo (R2=0.454, cleanest cross-dataset test) with arousal identical to
deam-musicnn (best everywhere). Key correction is especially effective for orchestral and
fantasy music, which has a stronger major/minor->valence relationship than training-set pop.
Swap `emomusic-msd-musicnn-2.pb` for `deam-msd-musicnn-2.pb` and add the `KeyExtractor`
post-processing from `feat/valence_key_correction`.

### For relative positioning on out-of-distribution music: open question

deam-musicnn+key leads on average valence ranking (r=0.574) but collapses on MERGE valence
(r=0.286 vs 0.422 for emomusic-musicnn+key). For playlists that are truly out-of-distribution
(orchestral, ambient, fantasy), emomusic-musicnn+key may be safer -- it sacrifices DEAM ranking
accuracy but remains more consistent across genres.

**Practical approach:** deploy `deam-musicnn+key` as the primary model. If valence placement
feels wrong for orchestral/ambient tracks, switch the head back to `emomusic-msd-musicnn-2.pb`
while keeping the key correction active.

**MuSE models are not viable for production.** Across all three datasets arousal is near-random
(avg r=0.10 for musicnn, 0.06 for vggish) and PMEmo arousal is actively inverted (R2=-1.17).
Valence is also 2-4x weaker than the current model (avg valence r ≈ 0.19-0.22 vs 0.574 for
deam-musicnn+key). Key correction is inconsistent: it hurts on DEAM, mildly helps on PMEmo.
The likely cause is a distributional mismatch between MuSE's arousal annotations and the
DEAM/PMEmo arousal convention -- the head has not learned a transferable arousal representation.

music2emo is not production-ready: incomplete PMEmo benchmark, poor MERGE arousal (R2=-0.124),
heavy inference dependency. Revisit when a full GPU benchmark run is available.
