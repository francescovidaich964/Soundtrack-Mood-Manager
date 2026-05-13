# .github/ — GitHub Infrastructure

This document explains how the GitHub-specific components interact: workflows, Pages, secrets, caches, and the branch strategy.

---

## Overview

```
GitHub Repository (source branches)
        │
        │  push / workflow_dispatch
        ▼
GitHub Actions (ubuntu-latest runner)
        │
        │  peaceiris/actions-gh-pages pushes to
        ▼
gh-pages branch  ──→  GitHub Pages serves
        │                   /           (production, from main)
        │                   /preview/   (staging, from any other branch)
        └── also read back by workflows as a data.js cache
```

Two workflows exist. They share the same deployment target (`gh-pages`) but serve different purposes and triggers.

---

## Workflows

### deploy.yml — Deploy Webapp

**Trigger:** Push to any branch when files inside `webapp/` or `deploy.yml` itself change, or manually via `workflow_dispatch`.

**Purpose:** Deploy source file changes (HTML/CSS/JS) to Pages quickly, without running the expensive Essentia sync.

**What it does:**
1. Checks out the source branch
2. Determines deploy target (`main` → root, everything else → `preview/`)
3. Restores `data.js` and `config.js` from `gh-pages` so playlist data is not lost on every deploy
4. For main deploys: saves the existing `preview/` directory from `gh-pages` and re-injects it into the publish dir, since `keep_files: false` would otherwise wipe it
5. Deploys `webapp/` to `gh-pages`

**keep_files behavior:**
- Main deploys: `keep_files: false` — clean deploy, but `preview/` is manually preserved (see above)
- Preview deploys: `keep_files: true` — never wipe production from a feature branch deploy

---

### sync.yml — Sync Playlist

**Trigger:** Manual only (`workflow_dispatch`), with two optional inputs:
- `playlist` — override the playlist ID at runtime without changing secrets
- `force_reanalyze` — re-analyze all tracks even if already cached

**Purpose:** Run the full Python sync pipeline (fetch Spotify metadata → download previews → Essentia analysis → write `data.js`).

**What it does:**
1. Determines deploy target and the correct `GITHUB_PAGES_URL` for the branch
2. Restores `data.js` from `gh-pages` as an analysis cache — tracks already in `data.js` are skipped
3. Caches Essentia `.pb` models and pip packages between runs
4. Runs `sync.py` with Spotify secrets injected as environment variables
5. Deploys the updated `webapp/` (including the new `data.js`) to `gh-pages`

---

## gh-pages branch

`gh-pages` is not a source branch — it contains only build output. It is never checked out for development.

**Structure after a full setup:**

```
gh-pages/
  index.html
  token.html
  data.js              ← production playlist data (written by sync.yml on main)
  js/
    config.js          ← production config (clientId, etc.)
    auth.js
    ...
  css/
    style.css
  preview/             ← staging slot (written by either workflow on non-main branches)
    index.html
    data.js            ← preview playlist data (independent from production)
    js/
      config.js
      ...
```

`gh-pages` is written by both workflows. Conflicts are avoided because:
- `deploy.yml` on main explicitly saves and restores `preview/` before deploying
- `deploy.yml` on feature branches uses `keep_files: true`, leaving the root untouched
- `sync.yml` always uses `keep_files: true`
- Commit messages include `[skip ci]` to prevent deploy loops

---

## GitHub Pages

Configured in **Settings → Pages → Deploy from branch `gh-pages`, folder `/ (root)`**.

GitHub Pages serves the entire `gh-pages` branch as a static site. Since both production and preview live in the same branch (at different paths), only one Pages configuration is needed.

| URL | Source in gh-pages | Updated by |
|-----|--------------------|------------|
| `/<repo>/` | root files | deploy.yml or sync.yml on main |
| `/<repo>/preview/` | `preview/` subdirectory | deploy.yml or sync.yml on any non-main branch |

---

## Secrets

Stored in **Settings → Secrets and variables → Actions**. Injected as environment variables into the runner by `sync.yml`.

| Secret | Used by | Purpose |
|--------|---------|---------|
| `SPOTIFY_CLIENT_ID` | sync.yml → sync.py → spotify_client.py | Identify the Spotify app |
| `SPOTIFY_CLIENT_SECRET` | sync.yml → sync.py → spotify_client.py | Exchange refresh token for access token |
| `SPOTIFY_PLAYLIST_ID` | sync.yml → sync.py | Default playlist to sync |
| `SPOTIFY_REFRESH_TOKEN` | sync.yml → sync.py → spotify_client.py | Authenticate as the playlist owner |

`GITHUB_TOKEN` is provided automatically by GitHub Actions (no setup needed). It is used by `peaceiris/actions-gh-pages` to push commits to the `gh-pages` branch.

Secrets are never logged. The "Check secrets" step in sync.yml only prints `true`/`false` (whether each secret is set), not the values.

---

## Caches

Two independent caches, managed by `actions/cache@v4` in sync.yml:

| Cache | Key | What it stores | Why |
|-------|-----|----------------|-----|
| Essentia models | `essentia-models-msd-musicnn-1-emomusic-msd-musicnn-2` | `models/*.pb` (~3 MB total) | Avoid re-downloading TF model files on every sync run |
| pip packages | `pip-<hash of requirements.txt>` | `~/.cache/pip` | Avoid re-downloading Python dependencies; key rotates when requirements.txt changes |

These caches live in GitHub's cache storage (separate from the repo). They are scoped to the repository and shared across all branches and workflow runs.

---

## Branch strategy

```
main ──────────────────────────────────────────────────── production
  │
  └── feat/xyz ──────────────────── squash merge ──→ main
        │
        push → deploy.yml → /preview/    (webapp changes)
        workflow_dispatch → sync.yml → /preview/    (sync changes)
```

**Day-to-day:**
1. `git checkout -b feat/xyz` from main
2. Push `webapp/` changes — deploy.yml auto-deploys to `/preview/`
3. To test sync changes: Actions → Sync Playlist → Run workflow → select `feat/xyz`
4. Test on `https://<you>.github.io/<repo>/preview/`
5. PR → main, squash merge → production updated, preview remains until overwritten

The preview slot is shared: the last non-main branch to push owns it.

---

## Interaction diagram

```
                    ┌─────────────────────────────────────────────┐
                    │              GitHub Actions runner           │
push/dispatch ────► │                                             │
                    │  1. checkout source branch                  │
                    │  2. git fetch gh-pages (read cache)         │
                    │  3. restore data.js / config.js             │
                    │  4. [sync.yml only] run sync.py             │
                    │     ├─ reads SPOTIFY_* secrets (env vars)   │
                    │     └─ writes webapp/data.js, config.js     │
                    │  5. peaceiris/actions-gh-pages              │
                    │     ├─ uses GITHUB_TOKEN (auto-provided)    │
                    │     └─ pushes webapp/ → gh-pages branch     │
                    └─────────────────────┬───────────────────────┘
                                          │
                                          ▼
                                    gh-pages branch
                                          │
                                          ▼
                                   GitHub Pages CDN
                                          │
                              ┌───────────┴───────────┐
                              ▼                       ▼
                    /  (production)          /preview/ (staging)
```
