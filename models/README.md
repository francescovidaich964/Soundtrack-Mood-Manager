# Essentia Models

This directory must contain two TensorFlow `.pb` model files downloaded from the
[Essentia Model Zoo](https://essentia.upf.edu/models/).

## Required Files

| File | URL |
|------|-----|
| `msd-musicnn-1.pb` | https://essentia.upf.edu/models/feature-extractors/musicnn/msd-musicnn-1.pb |
| `emomusic-msd-musicnn-2.pb` | https://essentia.upf.edu/models/classification-heads/emomusic/emomusic-msd-musicnn-2.pb |

## Download Commands

```bash
mkdir -p models
curl -L -o models/msd-musicnn-1.pb \
  https://essentia.upf.edu/models/feature-extractors/musicnn/msd-musicnn-1.pb

curl -L -o models/emomusic-msd-musicnn-2.pb \
  https://essentia.upf.edu/models/classification-heads/emomusic/emomusic-msd-musicnn-2.pb
```

## Model Details

- **msd-musicnn-1.pb**: MusiCNN feature extractor trained on the Million Song Dataset.
  Input: audio waveform at 16 kHz. Output: 200-dimensional embeddings per frame.

- **emomusic-msd-musicnn-2.pb**: Regression head trained on the EmoMusic dataset.
  Input: MusiCNN embeddings. Output: (valence, arousal) predictions per frame,
  raw range approximately [1.0, 9.0], normalized to [0.0, 1.0] by `(x - 1) / 8`.

Both files are cached by the GitHub Actions workflow — you only need them for local development.
