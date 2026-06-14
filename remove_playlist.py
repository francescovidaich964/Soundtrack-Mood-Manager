#!/usr/bin/env python3
"""
remove_playlist.py — Remove a playlist from webapp/data.js.

Removes the playlist entry from 'playlists' and prunes any tracks that are
no longer referenced by any remaining playlist (orphaned tracks).

Usage:
  python remove_playlist.py --playlist <url-or-id>
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO_ROOT))

from src.data_manager import normalize_playlist_id, read_data_js, write_data_js


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Remove a playlist from webapp/data.js and prune orphaned tracks."
    )
    parser.add_argument("--playlist", required=True, metavar="URL_OR_ID",
                        help="Spotify playlist URL or ID to remove")
    args = parser.parse_args()

    try:
        playlist_id = normalize_playlist_id(args.playlist)
    except ValueError as e:
        sys.exit(f"ERROR: {e}")
    data_js_path  = REPO_ROOT / "webapp" / "data.js"

    data = read_data_js(data_js_path)

    if playlist_id not in data["playlists"]:
        print(f"Playlist '{playlist_id}' not found in data.js — nothing to do.")
        sys.exit(0)

    removed_name = data["playlists"][playlist_id]["name"]
    del data["playlists"][playlist_id]
    print(f"Removed playlist: '{removed_name}' ({playlist_id})")

    # Collect all track_ids still referenced by the remaining playlists
    referenced_ids = {
        tid
        for pl in data["playlists"].values()
        for tid in pl["track_ids"]
    }

    # Drop orphaned tracks (not referenced by any remaining playlist)
    orphans = [tid for tid in data["tracks"] if tid not in referenced_ids]
    for tid in orphans:
        del data["tracks"][tid]
    if orphans:
        print(f"Pruned {len(orphans)} orphaned track(s).")

    write_data_js(data_js_path, data)
    print(
        f"data.js updated — {len(data['playlists'])} playlist(s), "
        f"{len(data['tracks'])} track(s) remaining."
    )


if __name__ == "__main__":
    main()
