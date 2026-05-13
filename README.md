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

> **Spotify Premium required** — the Web Playback SDK only works with Premium accounts.

---

## Setup

Follow these steps in order. Each step is done once.

---

### Step 1 — Fork / clone this repo

```bash
git clone https://github.com/<you>/Soundtrack-Mood-Manager.git
cd Soundtrack-Mood-Manager
```

---

### Step 2 — Create a Spotify app

1. Go to [developer.spotify.com/dashboard](https://developer.spotify.com/dashboard) and click **Create app**.
2. Fill in any name and description.
3. Under **APIs used**, enable **Web API** and **Web Playback SDK**.
4. Add two **Redirect URIs** (Settings → Edit):
   - `https://<you>.github.io/Soundtrack-Mood-Manager/` ← for the live webapp
   - `https://<you>.github.io/Soundtrack-Mood-Manager/token.html` ← for the one-time token setup script
5. Save. Note your **Client ID** and **Client Secret** from the app overview page.

---

### Step 3 — Get a Spotify refresh token (one-time, on your local machine)

Spotify's API requires a user login token even for public playlists (post-2024 policy).
This step generates a long-lived refresh token that GitHub Actions will use automatically from then on.

**First, push this repo to GitHub** so that `webapp/token.html` is deployed to GitHub Pages (the deploy workflow runs automatically on every push — wait ~30 seconds for it to finish).

Then, on any machine (Windows / macOS / Linux) — no extra installs needed:

```bash
# Copy the example config and fill in your credentials
copy config.json.example config.json      # Windows
# cp config.json.example config.json      # macOS / Linux

# Edit config.json and fill in:
#   client_id, client_secret  — from your Spotify app (Step 2)
#   github_pages_url          — e.g. https://<you>.github.io/Soundtrack-Mood-Manager

python get_refresh_token.py
```

The script will:
1. Remind you to add `https://<you>.github.io/Soundtrack-Mood-Manager/token.html` as a Redirect URI in your Spotify app (if not done yet).
2. Open your browser to the Spotify login page.
3. After login, your browser lands on a page titled **"DnD Soundtrack — Token Setup"** that displays a URL.
4. You copy that URL and paste it back into the terminal.
5. The script prints your **refresh token**.

Copy that token — you'll need it in the next step.

> `config.json` is gitignored and never committed. It is only used by this local script.

---

### Step 4 — Add GitHub Secrets

Repository **Settings → Secrets and variables → Actions → New repository secret**.

Add all four secrets:

| Secret name | Where to find it |
|---|---|
| `SPOTIFY_CLIENT_ID` | Spotify app overview page → "Client ID" |
| `SPOTIFY_CLIENT_SECRET` | Spotify app overview page → "Show client secret" |
| `SPOTIFY_PLAYLIST_ID` | Open playlist in Spotify → Share → Copy link → the ID after `/playlist/` |
| `SPOTIFY_REFRESH_TOKEN` | Printed by `get_refresh_token.py` in Step 3 |

**Finding your playlist ID:**
The URL `https://open.spotify.com/playlist/`**`37i9dQZF1DXcBWIGoYBM5M`** → the ID is the bold part.

> The playlist must be **public** on Spotify.

---

### Step 5 — Enable GitHub Pages

Repository **Settings → Pages → Source**: Deploy from branch **`gh-pages`**, folder **`/ (root)`**.

The webapp will be served at `https://<you>.github.io/Soundtrack-Mood-Manager/`.

> The `gh-pages` branch is created automatically on the first sync run. You can enable Pages before or after that.

---

### Step 6 — Run the first sync

Go to **Actions → Sync Playlist → Run workflow → Run workflow**.

The workflow will:
1. Download the Essentia `.pb` model files (~3 MB + ~80 KB, cached after the first run).
2. Install Python dependencies.
3. Download each playlist track with spotdl and analyze it with Essentia.
4. Write `webapp/data.js` and `webapp/js/config.js`.
5. Deploy `webapp/` to the `gh-pages` branch → GitHub Pages updates automatically.

With a 50-track playlist, the first run takes **~25–30 minutes**. Subsequent runs only process new tracks (already-analyzed tracks are cached in `data.js`).

---

## Using the webapp

1. Visit `https://<you>.github.io/Soundtrack-Mood-Manager/`
2. Complete the Spotify login prompt (once per browser session).
3. Drag the cursor on the **Mood Pad** to set the atmosphere:
   - **X axis**: valence (left = sad / right = happy)
   - **Y axis**: energy (bottom = calm / top = energetic)
4. Press **▶** to start playing. The app picks a nearby track and auto-advances when each track ends.
5. Press **⏭** to skip to the next track at the current mood.

---

## Updating the playlist

Trigger **Actions → Sync Playlist → Run workflow** again. Only new tracks are downloaded and analyzed; existing ones are skipped.

To force re-analysis of every track (e.g. after switching playlists), check **force_reanalyze** in the workflow inputs.

---

## Local development

Running `sync.py` locally requires Linux, macOS, or WSL2 (`essentia-tensorflow` has no Windows wheels).

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Download the Essentia models
mkdir -p models
curl -L -o models/msd-musicnn-1.pb \
  https://essentia.upf.edu/models/feature-extractors/musicnn/msd-musicnn-1.pb
curl -L -o models/emomusic-msd-musicnn-2.pb \
  https://essentia.upf.edu/models/classification-heads/emomusic/emomusic-msd-musicnn-2.pb

# 3. Fill in config.json (client_id, client_secret, playlist_id, refresh_token)
cp config.json.example config.json

# 4. Run sync (--local starts a static server and opens the browser)
python sync.py --local
```

---

## Troubleshooting

| Problem | Fix |
|---|---|
| Sync fails with 401 | `SPOTIFY_REFRESH_TOKEN` secret is missing or expired. Re-run `get_refresh_token.py` and update the secret. |
| "Spotify Premium required" | The Web Playback SDK requires a Premium account. |
| OAuth redirect fails after login | Check that both Redirect URIs in your Spotify app are added exactly as shown in Step 2, including the trailing `/`. |
| Tracks missing from the canvas | Check the Actions log — tracks with `download_failed` or `analysis_failed` were skipped by spotdl or Essentia. |
| Blank canvas after login | Open browser DevTools → Console for errors. Usually a mismatched `redirectUri` in `config.js` — re-run the Sync workflow. |
| `gh-pages` branch not found | Run the Sync workflow at least once. It creates the branch on first deploy. |
