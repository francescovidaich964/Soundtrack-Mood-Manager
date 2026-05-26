/**
 * spotify_api.js — thin wrapper around the Spotify Web API REST endpoints
 *
 * All methods require a valid device_id (provided by the Web Playback SDK).
 * Tokens are fetched from Auth.getAccessToken() before every request.
 *
 * Error handling:
 *   401 → refresh token → retry once
 *   429 → backoff for Retry-After seconds → retry once
 *   Other errors → throw
 */

const SpotifyAPI = (() => {
  const BASE = "https://api.spotify.com/v1";

  async function _headers() {
    const token = await Auth.getAccessToken();
    return {
      "Authorization": `Bearer ${token}`,
      "Content-Type":  "application/json",
    };
  }

  async function _request(method, path, body, retrying = false) {
    const res = await fetch(BASE + path, {
      method,
      headers: await _headers(),
      body: body ? JSON.stringify(body) : undefined,
    });

    if (res.status === 401 && !retrying) {
      // Token unexpectedly expired — force refresh and retry.
      await Auth.getAccessToken(); // triggers internal refresh via _doRefresh
      return _request(method, path, body, true);
    }

    if (res.status === 429 && !retrying) {
      const retryAfter = parseInt(res.headers.get("Retry-After") || "2", 10);
      await new Promise(r => setTimeout(r, (retryAfter + 1) * 1000));
      return _request(method, path, body, true);
    }

    if (res.status === 403) {
      console.warn(`Spotify API 403 on ${path} — likely Premium required or missing scope`);
      return null;
    }

    if (!res.ok && res.status !== 204) {
      const text = await res.text().catch(() => "(no body)");
      throw new Error(`Spotify API ${res.status} on ${path}: ${text}`);
    }

    // 204 No Content — success with no body
    if (res.status === 204) return null;

    try { return await res.json(); } catch { return null; }
  }

  // ------------------------------------------------------------------
  // Playback endpoints
  // ------------------------------------------------------------------

  /**
   * Start playing a specific track on the given device.
   * @param {string} deviceId  — Web Playback SDK device ID
   * @param {string} trackUri  — spotify:track:xxx
   */
  async function playTrack(deviceId, trackUri) {
    return _request("PUT", `/me/player/play?device_id=${deviceId}`, {
      uris: [trackUri],
    });
  }

  /** Pause playback. */
  async function pause() {
    return _request("PUT", "/me/player/pause");
  }

  /** Resume playback (no track change). */
  async function resume() {
    return _request("PUT", "/me/player/play");
  }

  /** Seek to a position in the current track. */
  async function seekTo(positionMs) {
    return _request("PUT", `/me/player/seek?position_ms=${Math.round(positionMs)}`);
  }

  /**
   * Transfer playback to a specific device and optionally start playing.
   * Call this after the Web Playback SDK emits 'ready' to make the browser
   * the active Spotify Connect device.
   * @param {string} deviceId
   * @param {boolean} [play=false]
   */
  async function transferPlayback(deviceId, play = false) {
    return _request("PUT", "/me/player", {
      device_ids: [deviceId],
      play,
    });
  }

  return { playTrack, pause, resume, seekTo, transferPlayback };
})();
