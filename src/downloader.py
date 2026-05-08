"""
downloader.py — download a Spotify track as MP3 using spotdl

spotdl names output files using its own template (e.g. "Artist - Title.mp3"),
not by track ID. To make the output reliably discoverable we create a
per-track subdirectory and glob for any .mp3 file inside it after the run.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def download(track_id: str, temp_base: Path) -> Path | None:
    """Download a Spotify track to a local MP3 file.

    Creates `temp_base/{track_id}/` as an isolated working directory so the
    output file is unambiguous regardless of the spotdl naming template.

    Args:
        track_id: Bare Spotify track ID (not the full URI or URL).
        temp_base: Parent directory for per-track subdirs.

    Returns:
        Path to the downloaded .mp3 file, or None if download failed.
    """
    track_dir = temp_base / track_id
    track_dir.mkdir(parents=True, exist_ok=True)

    url = f"https://open.spotify.com/track/{track_id}"

    cmd = [
        sys.executable, "-m", "spotdl",
        url,
        "--output", str(track_dir / "{title}"),
        "--format", "mp3",
        "--log-level", "WARNING",   # suppress spotdl's verbose output
    ]

    try:
        subprocess.run(
            cmd,
            timeout=90,
            check=True,
            capture_output=True,
        )
    except subprocess.CalledProcessError:
        # Track unavailable, no YouTube match, region restriction, etc.
        return None
    except subprocess.TimeoutExpired:
        return None

    mp3_files = list(track_dir.glob("*.mp3"))
    if not mp3_files:
        # spotdl exited successfully but produced nothing (rare edge case).
        return None

    return mp3_files[0]


def cleanup(track_dir: Path) -> None:
    """Remove a per-track temp directory and its contents."""
    if not track_dir.exists():
        return
    for f in track_dir.iterdir():
        f.unlink(missing_ok=True)
    track_dir.rmdir()
