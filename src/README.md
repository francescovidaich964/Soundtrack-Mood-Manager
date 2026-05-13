# src/ — Backend Modules

These modules are used exclusively by `sync.py` (the Phase 1 sync script that runs on GitHub Actions). They are not loaded by the browser.

---

## Module overview

```
sync.py                        ← orchestrator (calls all modules below)
src/
  spotify_client.py            ← fetch playlist metadata from Spotify Web API
  downloader.py                ← download 30-second preview MP3s
  feature_extractor.py         ← extract valence/energy with Essentia TF models
  data_manager.py              ← read/write webapp/data.js
```

---

## Data flow

```
Spotify Web API
      │
      │  playlist metadata (track IDs, titles, artists, album art)
      ▼
spotify_client.py
      │
      ▼
sync.py  ──── already cached? ──── yes ──→  skip
      │
      │  no
      ▼
downloader.py
  scrapes open.spotify.com/embed/track/{id}
  downloads 30-sec preview MP3 (no auth, no ffmpeg)
      │
      ▼
feature_extractor.py
  MonoLoader (16 kHz mono)
  → TensorflowPredictMusiCNN  → embeddings  (N_frames × 200)
  → TensorflowPredict2D       → predictions (N_frames × 2)
  → mean over frames
  → normalize [1,9] → [0,1]
  → (valence, energy)
      │
      ▼
data_manager.py
  update_track() — incremental write after each track
  write_data_js() — full write at the end
      │
      ▼
webapp/data.js  (consumed by the browser)
```

---

## spotify_client.py

Wraps [Spotipy](https://spotipy.readthedocs.io/) to fetch playlist metadata.

**Auth:** Uses a stored refresh token (from `SPOTIFY_REFRESH_TOKEN` secret) to get a live access token. Falls back to client credentials if no refresh token is provided, but this is restricted for Development Mode Spotify apps.

**Key methods:**
- `get_playlist_name(playlist_id)` — returns the playlist display name
- `get_playlist_tracks(playlist_id)` — returns all tracks as a list of dicts:
  ```python
  {
    "track_id": str,
    "uri": str,            # spotify:track:...
    "title": str,
    "artist": str,
    "album_art_url": str,
    "duration_ms": int,
  }
  ```
  Handles pagination transparently. Skips local files and episodes.

---

## downloader.py

Downloads the 30-second preview MP3 that Spotify embeds on `open.spotify.com/embed/track/{id}`.

**How it works:** The embed page injects a `<script id="__NEXT_DATA__">` tag containing page state as JSON. The preview MP3 URL is at `props.pageProps.state.data.entity.audioPreview.url`. One HTTP request per track, no authentication, no ffmpeg, no external tools.

**Returns `None`** if the track has no preview (common for some markets/tracks). These are recorded as `download_failed: true` in data.js and skipped on future syncs.

---

## feature_extractor.py

Extracts `valence` and `energy` from an audio file using two Essentia TensorFlow models.

**Pipeline:**
1. Load audio as 16 kHz mono
2. `TensorflowPredictMusiCNN` (`msd-musicnn-1.pb`) → embeddings of shape `(N_frames, 200)`
3. `TensorflowPredict2D` (`emomusic-msd-musicnn-2.pb`) → predictions of shape `(N_frames, 2)`
4. Mean over frames → `[valence_mean, arousal_mean]`
5. Normalize from EmoMusic scale `[1, 9]` → `[0.0, 1.0]`

Column 0 = valence (negative ↔ positive), column 1 = arousal (calm ↔ energetic, used as "energy").

**Platform note:** `essentia-tensorflow` has no Windows wheels. This module only runs on Linux/macOS — i.e., in GitHub Actions or WSL2.

**Models** are lazy-loaded on first call and cached for the process lifetime. The `.pb` files are downloaded by the sync workflow and cached between runs via `actions/cache`.

---

## data_manager.py

Reads and writes `webapp/data.js`, which doubles as both a browser asset and a sync cache.

**Format:** A JavaScript file containing `window.TRACK_DATA = {...};`. The JSON is extracted with a regex so no JS parser is needed.