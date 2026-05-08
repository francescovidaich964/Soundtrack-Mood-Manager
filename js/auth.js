/**
 * auth.js — Spotify OAuth2 PKCE flow
 *
 * PKCE (Proof Key for Code Exchange) lets the webapp authenticate with Spotify
 * without ever exposing a client_secret. Only the client_id is needed.
 *
 * Flow summary:
 *   1. Generate a random code_verifier and derive code_challenge from it.
 *   2. Store code_verifier in sessionStorage and redirect to Spotify's auth page.
 *   3. Spotify redirects back to redirectUri with ?code=... in the URL.
 *   4. Exchange the code + code_verifier for an access_token + refresh_token.
 *   5. Store tokens in sessionStorage with an expiry timestamp.
 *   6. Schedule an automatic refresh 60 s before the token expires.
 *
 * Public API:
 *   Auth.init()                — call once on page load; handles the callback
 *                                and may redirect to Spotify if no token exists
 *   Auth.getAccessToken()      — returns a Promise<string> with a valid token
 *                                (refreshes synchronously if near-expiry)
 */

const Auth = (() => {
  const STORAGE_KEYS = {
    accessToken:  "smm_access_token",
    refreshToken: "smm_refresh_token",
    expiresAt:    "smm_expires_at",
    codeVerifier: "smm_code_verifier",
  };

  // ------------------------------------------------------------------
  // PKCE helpers
  // ------------------------------------------------------------------

  function _randomBytes(length) {
    return crypto.getRandomValues(new Uint8Array(length));
  }

  function _base64url(buffer) {
    return btoa(String.fromCharCode(...new Uint8Array(buffer)))
      .replace(/\+/g, "-")
      .replace(/\//g, "_")
      .replace(/=/g, "");
  }

  async function _sha256(plain) {
    const encoder = new TextEncoder();
    return crypto.subtle.digest("SHA-256", encoder.encode(plain));
  }

  function _generateCodeVerifier() {
    // 43 characters — minimum allowed length per RFC 7636.
    const bytes = _randomBytes(32); // 32 bytes → 43-char base64url
    return _base64url(bytes);
  }

  async function _codeChallenge(verifier) {
    const digest = await _sha256(verifier);
    return _base64url(digest);
  }

  // ------------------------------------------------------------------
  // Token storage helpers
  // ------------------------------------------------------------------

  function _saveTokens(accessToken, refreshToken, expiresIn) {
    const expiresAt = Date.now() + expiresIn * 1000;
    sessionStorage.setItem(STORAGE_KEYS.accessToken,  accessToken);
    sessionStorage.setItem(STORAGE_KEYS.refreshToken, refreshToken);
    sessionStorage.setItem(STORAGE_KEYS.expiresAt,    String(expiresAt));
  }

  function _getStoredToken() {
    return {
      accessToken:  sessionStorage.getItem(STORAGE_KEYS.accessToken),
      refreshToken: sessionStorage.getItem(STORAGE_KEYS.refreshToken),
      expiresAt:    Number(sessionStorage.getItem(STORAGE_KEYS.expiresAt) || 0),
    };
  }

  function _isTokenValid(expiresAt) {
    // Consider valid if more than 60 s remain.
    return expiresAt > Date.now() + 60_000;
  }

  // ------------------------------------------------------------------
  // Spotify token endpoint
  // ------------------------------------------------------------------

  async function _exchangeCodeForTokens(code, codeVerifier) {
    const body = new URLSearchParams({
      grant_type:    "authorization_code",
      code,
      redirect_uri:  CONFIG.redirectUri,
      client_id:     CONFIG.clientId,
      code_verifier: codeVerifier,
    });

    const res = await fetch("https://accounts.spotify.com/api/token", {
      method:  "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body,
    });

    if (!res.ok) {
      const text = await res.text();
      throw new Error(`Token exchange failed (${res.status}): ${text}`);
    }

    return res.json();
  }

  async function _refreshAccessToken(refreshToken) {
    const body = new URLSearchParams({
      grant_type:    "refresh_token",
      refresh_token: refreshToken,
      client_id:     CONFIG.clientId,
    });

    const res = await fetch("https://accounts.spotify.com/api/token", {
      method:  "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body,
    });

    if (!res.ok) {
      const text = await res.text();
      throw new Error(`Token refresh failed (${res.status}): ${text}`);
    }

    return res.json();
  }

  // ------------------------------------------------------------------
  // Auto-refresh scheduler
  // ------------------------------------------------------------------

  let _refreshTimer = null;

  function _scheduleRefresh(expiresAt, refreshToken) {
    if (_refreshTimer) clearTimeout(_refreshTimer);

    const msUntilRefresh = expiresAt - Date.now() - 60_000;
    if (msUntilRefresh <= 0) {
      _doRefresh(refreshToken);
      return;
    }

    _refreshTimer = setTimeout(() => _doRefresh(refreshToken), msUntilRefresh);
  }

  async function _doRefresh(refreshToken) {
    try {
      const data = await _refreshAccessToken(refreshToken);
      const newRefresh = data.refresh_token || refreshToken; // some responses omit it
      _saveTokens(data.access_token, newRefresh, data.expires_in);
      _scheduleRefresh(
        Number(sessionStorage.getItem(STORAGE_KEYS.expiresAt)),
        newRefresh,
      );
    } catch (err) {
      console.error("Token refresh failed:", err);
      // Force re-login on next getAccessToken() call.
      sessionStorage.clear();
    }
  }

  // ------------------------------------------------------------------
  // Authorization redirect
  // ------------------------------------------------------------------

  async function _redirectToSpotify() {
    const verifier = _generateCodeVerifier();
    sessionStorage.setItem(STORAGE_KEYS.codeVerifier, verifier);

    const challenge = await _codeChallenge(verifier);

    const params = new URLSearchParams({
      response_type:         "code",
      client_id:             CONFIG.clientId,
      scope:                 CONFIG.scopes,
      redirect_uri:          CONFIG.redirectUri,
      code_challenge_method: "S256",
      code_challenge:        challenge,
    });

    window.location.href =
      "https://accounts.spotify.com/authorize?" + params.toString();
  }

  // ------------------------------------------------------------------
  // Public API
  // ------------------------------------------------------------------

  /**
   * Initialize the auth module. Must be called once on page load.
   *
   * - If the URL contains ?code=..., handle the PKCE callback.
   * - If a valid token is in sessionStorage, schedule its refresh.
   * - Otherwise, redirect to Spotify's login page.
   *
   * Returns a Promise that resolves when auth is ready, or redirects.
   */
  async function init() {
    const urlParams = new URLSearchParams(window.location.search);
    const code = urlParams.get("code");

    if (code) {
      // We're back from Spotify's auth page — complete the exchange.
      const verifier = sessionStorage.getItem(STORAGE_KEYS.codeVerifier);
      if (!verifier) {
        console.error("code_verifier missing from sessionStorage — restarting auth");
        await _redirectToSpotify();
        return;
      }

      // Clean up the ?code=... from the URL bar (cosmetic + security).
      history.replaceState(null, "", window.location.pathname);

      const data = await _exchangeCodeForTokens(code, verifier);
      sessionStorage.removeItem(STORAGE_KEYS.codeVerifier);
      _saveTokens(data.access_token, data.refresh_token, data.expires_in);
      _scheduleRefresh(
        Number(sessionStorage.getItem(STORAGE_KEYS.expiresAt)),
        data.refresh_token,
      );
      return;
    }

    // Check existing token.
    const { accessToken, refreshToken, expiresAt } = _getStoredToken();

    if (accessToken && _isTokenValid(expiresAt)) {
      _scheduleRefresh(expiresAt, refreshToken);
      return; // already authenticated
    }

    if (refreshToken) {
      // Token exists but is about to expire — refresh immediately.
      await _doRefresh(refreshToken);
      return;
    }

    // No token at all — redirect to Spotify login.
    await _redirectToSpotify();
  }

  /**
   * Return a valid access token.
   * If the token is within 10 s of expiry, refreshes it first.
   */
  async function getAccessToken() {
    const { accessToken, refreshToken, expiresAt } = _getStoredToken();

    if (!accessToken) {
      throw new Error("Not authenticated. Call Auth.init() first.");
    }

    if (expiresAt <= Date.now() + 10_000) {
      // Token expired or about to expire — synchronous refresh.
      await _doRefresh(refreshToken);
      return sessionStorage.getItem(STORAGE_KEYS.accessToken);
    }

    return accessToken;
  }

  return { init, getAccessToken };
})();
