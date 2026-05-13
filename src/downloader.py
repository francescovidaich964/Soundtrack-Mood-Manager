"""
downloader.py — fetch a 30-second Spotify preview MP3

Spotify's embed player (open.spotify.com/embed/track/{id}) is publicly
accessible with no authentication. It injects full page data as JSON in a
<script id="__NEXT_DATA__"> tag, which contains a direct MP3 preview URL.

Advantages over yt-dlp/spotdl:
- No ffmpeg needed
- No YouTube bot detection issues
- No Spotify API calls during download
- One HTTP request per track
- Works on any platform, no external tools
"""

from __future__ import annotations

import json
import re
import time
import urllib.request
from pathlib import Path


def get_preview_url(track_id: str) -> str | None:
    """Extract the 30-second preview MP3 URL from Spotify's embed page."""
    url = f"https://open.spotify.com/embed/track/{track_id}"
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0"},
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            html = resp.read().decode("utf-8")
    except Exception:
        return None

    match = re.search(r'<script id="__NEXT_DATA__[^>]*>([^<]+)</script>', html)
    if not match:
        return None

    try:
        data = json.loads(match.group(1))
        entity = data["props"]["pageProps"]["state"]["data"]["entity"]
        if entity is None:
            return None
        audio_preview = entity.get("audioPreview", {})
        if audio_preview is None:
            return None
        return audio_preview.get("url")
    except (KeyError, json.JSONDecodeError):
        return None


def download(track_id: str, title: str, artist: str, temp_base: Path) -> Path | None:
    """Download a 30-second Spotify preview MP3.

    Args:
        track_id:  Spotify track ID.
        title:     Track title (used only for logging, not for the request).
        artist:    Artist name (used only for logging, not for the request).
        temp_base: Parent directory for per-track subdirs.

    Returns:
        Path to the downloaded .mp3 file, or None if no preview is available.
    """
    track_dir = temp_base / track_id
    track_dir.mkdir(parents=True, exist_ok=True)

    preview_url = get_preview_url(track_id)
    if not preview_url:
        return None

    out_path = track_dir / "preview.mp3"
    try:
        req = urllib.request.Request(
            preview_url,
            headers={"User-Agent": "Mozilla/5.0"},
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            out_path.write_bytes(resp.read())
    except Exception:
        return None

    return out_path


def cleanup(track_dir: Path) -> None:
    """Remove a per-track temp directory and its contents."""
    if not track_dir.exists():
        return
    for f in track_dir.iterdir():
        f.unlink(missing_ok=True)
    track_dir.rmdir()
