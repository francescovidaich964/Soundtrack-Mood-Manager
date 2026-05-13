"""
spotify_client.py — fetch playlist metadata via Spotify Web API

Spotify's API (post-2024) requires a user token even for user-owned playlists.
The dedicated /playlists/{id}/items endpoint is restricted for Development Mode
apps; we use GET /playlists/{id} instead, which embeds the first track page in
its response and supports standard pagination via sp.next().
"""

from __future__ import annotations

import time

import spotipy
from spotipy.oauth2 import SpotifyClientCredentials, SpotifyOAuth


class SpotifyClient:
    def __init__(
        self,
        client_id: str,
        client_secret: str,
        refresh_token: str | None = None,
    ) -> None:
        if refresh_token:
            # Exchange the stored refresh token for a live access token using
            # Spotipy's own OAuth helper, then pass the token directly so
            # Spotipy doesn't manage auth state internally.
            auth_manager = SpotifyOAuth(
                client_id=client_id,
                client_secret=client_secret,
                redirect_uri="http://localhost:8080",
                scope="playlist-read-private playlist-read-collaborative",
            )
            token_info = auth_manager.refresh_access_token(refresh_token)
            self._sp = spotipy.Spotify(auth=token_info["access_token"])
            me = self._sp.me()
            print(f"  Authenticated as: {me.get('display_name') or me.get('id')}")
        else:
            # Fallback: client_credentials (restricted on newer Spotify apps)
            auth = SpotifyClientCredentials(
                client_id=client_id,
                client_secret=client_secret,
            )
            self._sp = spotipy.Spotify(auth_manager=auth)

    def get_playlist_tracks(self, playlist_id: str) -> list[dict]:
        """Return all tracks in the playlist.

        Uses GET /playlists/{id} to avoid the restricted /items endpoint.
        Handles pagination transparently. Skips local files and episodes.

        Returns a list of dicts: track_id, uri, title, artist, album_art_url, duration_ms
        """
        playlist_id = self._normalize_playlist_id(playlist_id)
        tracks: list[dict] = []

        # GET /playlists/{id} embeds the first track page in its response.
        # Spotify uses 'tracks' or 'items' as the outer key depending on the
        # playlist type; each entry uses 'track' or 'item' for the track data.
        result = self._fetch_with_retry(self._sp.playlist, playlist_id)
        page = result.get("tracks") or result.get("items") or {}

        while page:
            for item in page.get("items", []):
                track = item.get("track") or item.get("item")
                if not track or item.get("is_local") or not track.get("id"):
                    continue
                artist = ", ".join(a["name"] for a in track.get("artists", []))
                images = track.get("album", {}).get("images", [])
                tracks.append({
                    "track_id":      track["id"],
                    "uri":           track["uri"],
                    "title":         track["name"],
                    "artist":        artist,
                    "album_art_url": images[0]["url"] if images else "",
                    "duration_ms":   track.get("duration_ms", 0),
                })

            page = self._fetch_with_retry(self._sp.next, page) if page.get("next") else None

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
        if "open.spotify.com/playlist/" in playlist_id:
            playlist_id = playlist_id.split("open.spotify.com/playlist/")[1]
            playlist_id = playlist_id.split("?")[0]
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
