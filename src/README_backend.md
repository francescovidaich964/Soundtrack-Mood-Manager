# src/ — Backend Modules

These modules are used exclusively by `sync.py` (the Phase 1 sync script that runs on GitHub Actions). They are not loaded by the browser.

---

## Module overview

```
sync.py                        ← orchestrator (calls all modules below)
src/
  spotify_client.py            ← fetch playlist metadata from Spotify Web API
  downloader.py                ← download 30-second preview MP3s
  feature_extractor.py         ← extract valence/energy with music2emo
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
  music2emo.predict(audio_path)
  → valence, arousal in [1, 9]
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

Extracts `valence` and `energy` from an audio file using [amaai-lab/music2emo](https://huggingface.co/amaai-lab/music2emo).

**Pipeline:**
1. `music2emo.Music2Emo().predict(audio_path)` → `{"valence": float, "arousal": float, ...}` in range [1, 9]
2. Normalize from EmoMusic scale `[1, 9]` → `[0.0, 1.0]` via `(x - 1) / 8`

valence = negative ↔ positive, arousal = calm ↔ energetic (used as "energy").

**Platform:** Works on Linux, macOS, and Windows (torch + transformers).

**Model** is lazy-loaded on first call and cached for the process lifetime. Weights are downloaded automatically from HuggingFace to `~/.cache/huggingface/` and cached between workflow runs via `actions/cache`.

---

## data_manager.py

Reads and writes `webapp/data.js`, which doubles as both a browser asset and a sync cache.

**Format:** A JavaScript file containing `window.TRACK_DATA = {...};`. The JSON is extracted with a regex so no JS parser is needed.