"""
spotify_client.py — fetch playlist metadata via Spotify Web API

Uses the client_credentials flow (no user login required) because we only
need to read public playlist metadata, not act on behalf of a user.
"""

from __future__ import annotations

import time

import spotipy
from spotipy.oauth2 import SpotifyClientCredentials


class SpotifyClient:
    def __init__(self, client_id: str, client_secret: str) -> None:
        auth = SpotifyClientCredentials(
            client_id=client_id,
            client_secret=client_secret,
        )
        self._sp = spotipy.Spotify(auth_manager=auth)

    def get_playlist_tracks(self, playlist_id: str) -> list[dict]:
        """Return all tracks in the playlist.

        Handles Spotify's pagination transparently (playlists > 100 tracks).
        Skips local files and episodes (non-track items).

        Returns a list of dicts with keys:
            track_id, uri, title, artist, album_art_url, duration_ms
        """
        # Normalize: accept full URL, URI, or bare ID
        playlist_id = self._normalize_playlist_id(playlist_id)

        tracks: list[dict] = []
        offset = 0
        limit = 100

        while True:
            page = self._fetch_with_retry(
                self._sp.playlist_tracks,
                playlist_id,
                limit=limit,
                offset=offset,
                fields="items(track(id,uri,name,artists,album(images),duration_ms,is_local)),next",
            )

            for item in page.get("items", []):
                track = item.get("track")
                if not track or track.get("is_local"):
                    continue
                if not track.get("id"):
                    # Episodes or unresolvable tracks have no ID.
                    continue

                artist = ", ".join(a["name"] for a in track.get("artists", []))
                images = track.get("album", {}).get("images", [])
                album_art = images[0]["url"] if images else ""

                tracks.append(
                    {
                        "track_id": track["id"],
                        "uri": track["uri"],
                        "title": track["name"],
                        "artist": artist,
                        "album_art_url": album_art,
                        "duration_ms": track.get("duration_ms", 0),
                    }
                )

            if page.get("next") is None:
                break
            offset += limit

        return tracks

    def get_playlist_name(self, playlist_id: str) -> str:
        """Return the playlist's display name."""
        playlist_id = self._normalize_playlist_id(playlist_id)
        info = self._fetch_with_retry(self._sp.playlist, playlist_id, fields="name")
        return info.get("name", "")

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _normalize_playlist_id(playlist_id: str) -> str:
        """Accept a full URL, URI, or bare ID and return the bare ID."""
        # https://open.spotify.com/playlist/37i9dQZF1DX...?si=...
        if "open.spotify.com/playlist/" in playlist_id:
            playlist_id = playlist_id.split("open.spotify.com/playlist/")[1]
            playlist_id = playlist_id.split("?")[0]
        # spotify:playlist:37i9dQZF1DX...
        elif playlist_id.startswith("spotify:playlist:"):
            playlist_id = playlist_id.split(":")[-1]
        return playlist_id.strip()

    def _fetch_with_retry(self, fn, *args, max_retries: int = 5, **kwargs):
        """Call a Spotipy method and retry on 429 / transient errors."""
        for attempt in range(max_retries):
            try:
                return fn(*args, **kwargs)
            except spotipy.SpotifyException as exc:
                if exc.http_status == 429:
                    retry_after = int(exc.headers.get("Retry-After", 2)) if exc.headers else 2
                    time.sleep(retry_after + 1)
                elif exc.http_status and exc.http_status >= 500:
                    time.sleep(2 ** attempt)
                else:
                    raise
        raise RuntimeError(f"Spotify API call failed after {max_retries} retries")
