# DnD Soundtrack Manager

A mood-driven music player for Dungeons & Dragons sessions. Drag a point on a 2D **valence × energy** canvas to set the atmosphere, and the app continuously picks tracks from your Spotify playlist that match the current mood.

```
sad / calm        →        happy / calm
        ┌─────────────────────┐
        │  · ·   ·     ·  ·  │  ← each dot is a track
        │     ·     ·        │
        │  ·    ○ ← cursor   │
        │     ·      ·    ·  │
        └─────────────────────┘
sad / energetic   →   happy / energetic
```

---

## How it works

- **Phase 1 — Sync** (GitHub Actions, Linux): fetches your Spotify playlist, downloads each track with [spotdl](https://github.com/spotDL/spotify-downloader), analyzes it with [Essentia](https://essentia.upf.edu/) TensorFlow models, and writes `webapp/data.js`.
- **Phase 2 — Session** (your browser): reads `data.js`, authenticates via Spotify PKCE, plays music through the Spotify Web Playback SDK — no local server needed.

---

## Setup (one time)

### 1. Fork / clone this repo

```bash
git clone https://github.com/<you>/Soundtrack-Mood-Manager.git
```

### 2. Enable GitHub Pages

Repository **Settings → Pages → Source**: Deploy from branch **`gh-pages`**, folder **`/ (root)`**.

The webapp will be served at `https://<you>.github.io/Soundtrack-Mood-Manager/`.

### 3. Create a Spotify app

1. Go to [developer.spotify.com/dashboard](https://developer.spotify.com/dashboard) and create a new app.
2. In the app settings, add a **Redirect URI**: `https://<you>.github.io/Soundtrack-Mood-Manager/`
   (must match exactly, including the trailing slash).
3. Note your **Client ID** and **Client Secret**.

> **Spotify Premium required** — the Web Playback SDK only works with Premium accounts.

### 4. Add GitHub Secrets

Repository **Settings → Secrets and variables → Actions → New repository secret**:

| Secret name | Where to find it |
|---|---|
| `SPOTIFY_CLIENT_ID` | Spotify app overview page → "Client ID" |
| `SPOTIFY_CLIENT_SECRET` | Spotify app overview page → "Show client secret" |
| `SPOTIFY_PLAYLIST_ID` | Open playlist in Spotify → Share → Copy link → the ID after `/playlist/` |

Example playlist URL: `https://open.spotify.com/playlist/`**`37i9dQZF1DXcBWIGoYBM5M`**

### 5. First sync

Go to **Actions → Sync Playlist → Run workflow**.

The workflow will:
1. Download the Essentia `.pb` model files (cached after the first run).
2. Install Python dependencies.
3. Download each playlist track with spotdl, analyze it with Essentia.
4. Write `webapp/data.js` and `webapp/js/config.js`.
5. Deploy `webapp/` to the `gh-pages` branch.

With a 50-track playlist, the first run takes ~25–30 minutes. Subsequent runs only process new tracks (cached via `data.js`).

---

## Using the webapp

1. Visit `https://<you>.github.io/Soundtrack-Mood-Manager/`
2. Complete the Spotify login prompt.
3. Drag the cursor on the **Mood Pad** to set the atmosphere:
   - **X axis**: valence (left = sad, right = happy)
   - **Y axis**: energy (bottom = calm, top = energetic)
4. Press **▶** to start playing. The app picks a nearby track and auto-advances when each track ends.
5. Press **⏭** to skip to the next track at the current mood.

---

## Updating the playlist

Just trigger **Actions → Sync Playlist → Run workflow** again. Only new tracks are downloaded and analyzed; existing ones are read from the cache in `data.js`.

To force re-analysis of all tracks, check **force_reanalyze** in the workflow inputs.

---

## Local development

If you want to run `sync.py` locally (Linux/macOS/WSL2 required for `essentia-tensorflow`):

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Download the Essentia models
mkdir -p models
curl -L -o models/msd-musicnn-1.pb \
  https://essentia.upf.edu/models/feature-extractors/musicnn/msd-musicnn-1.pb
curl -L -o models/emomusic-msd-musicnn-2.pb \
  https://essentia.upf.edu/models/classification-heads/emomusic/emomusic-msd-musicnn-2.pb

# 3. Copy and fill in config
cp config.json.example config.json
# edit config.json with your client_id, client_secret, playlist_id

# 4. Run sync (--local also starts a static server and opens the browser)
python sync.py --local
```

---

## Troubleshooting

| Problem | Fix |
|---|---|
| "Spotify Premium required" | The Web Playback SDK requires a Premium account. |
| OAuth redirect fails | Check that the Redirect URI in your Spotify app matches the GitHub Pages URL exactly (including trailing `/`). |
| Tracks missing from the canvas | Check the Actions log — some tracks may have `download_failed` or `analysis_failed` if spotdl couldn't find them. |
| Models not found | The workflow auto-downloads them. For local dev, run the `curl` commands in the "Local development" section. |
| Blank canvas after login | Open browser DevTools → Console for errors. Usually a mismatched `redirectUri` in `config.js`. |
