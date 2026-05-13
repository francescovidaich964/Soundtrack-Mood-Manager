"""
Local connectivity test for Spotify auth + playlist fetch.
Run with the venv active: python test_spotify.py

Requires config.json with client_id, client_secret, playlist_id, refresh_token.
"""
import json
import sys

sys.path.insert(0, ".")

with open("config.json") as f:
    config = json.load(f)

from src.spotify_client import SpotifyClient

client = SpotifyClient(
    config["client_id"],
    config["client_secret"],
    refresh_token=config.get("refresh_token"),
)

name = client.get_playlist_name(config["playlist_id"])
print(f"Playlist: {name}")

tracks = client.get_playlist_tracks(config["playlist_id"])
print(f"Tracks:   {len(tracks)}")

print("\n--- Spotify preview download test ---")
from src.downloader import download
from pathlib import Path

previews_dir = Path(__file__).parent / "previews"
previews_dir.mkdir(exist_ok=True)

for t in tracks[:5]:
    out = previews_dir / f"{t['track_id']}.mp3"
    if out.exists():
        print(f"  [cached] {t['title']} — {t['artist']}")
        continue
    result = download(t["track_id"], t["title"], t["artist"], previews_dir / "tmp")
    if result:
        result.rename(out)
        print(f"  [ok] {t['title']} — {t['artist']} ({out.stat().st_size // 1024} KB)")
    else:
        print(f"  [no preview] {t['title']} — {t['artist']}")
