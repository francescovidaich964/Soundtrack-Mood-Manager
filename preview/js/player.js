/**
 * player.js — Spotify Web Playback SDK setup
 *
 * Creates a "DnD Player" Spotify Connect device in the browser.
 * Handles SDK lifecycle events and drives the auto-advance logic.
 *
 * Important: window.onSpotifyWebPlaybackSDKReady must be defined BEFORE
 * the SDK script tag executes. We define it here (loaded via defer), but
 * index.html loads the SDK script with async so the callback assignment
 * races. To be safe we also use a Promise that the SDK callback resolves.
 *
 * Track-end detection:
 *   player_state_changed fires when a track ends with:
 *     state.paused === true && state.position === 0
 *   We also check that previousPosition > 1000 ms to distinguish a
 *   natural end from the user pausing at the very start of a track.
 */

const Player = (() => {
  let _player = null;
  let _deviceId = null;
  let _previousPosition = 0;
  let _isReady = false;

  // Callbacks registered by other modules.
  let _onTrackChanged = null;  // (state) => void
  let _onTrackEnded = null;    // () => void

  // Promise + resolver so external code can await SDK readiness.
  let _resolveReady;
  const _readyPromise = new Promise(resolve => { _resolveReady = resolve; });

  // ------------------------------------------------------------------
  // SDK callback — must be set on window before the SDK script runs.
  // ------------------------------------------------------------------

  window.onSpotifyWebPlaybackSDKReady = () => {
    _player = new Spotify.Player({
      name: CONFIG.playerName,
      getOAuthToken: async cb => cb(await Auth.getAccessToken()),
      volume: 0.8,
    });

    // ---- Error listeners ----

    _player.addListener("initialization_error", ({ message }) => {
      console.error("SDK init error:", message);
      UI.showError("Spotify player failed to initialize: " + message);
    });

    _player.addListener("authentication_error", ({ message }) => {
      console.error("SDK auth error:", message);
      UI.showError("Spotify authentication error — please refresh the page.");
    });

    _player.addListener("account_error", ({ message }) => {
      console.error("SDK account error:", message);
      UI.showError(
        "Spotify Premium is required to use the Web Playback SDK.\n" + message
      );
    });

    _player.addListener("playback_error", ({ message }) => {
      console.error("SDK playback error:", message);
    });

    // ---- Ready ----

    _player.addListener("ready", async ({ device_id }) => {
      _deviceId = device_id;
      _isReady = true;
      console.log("DnD Player ready, device_id:", device_id);

      // Make this browser the active Spotify Connect device.
      // Don't start playing yet (play=false) — wait for user input.
      try {
        await SpotifyAPI.transferPlayback(device_id, false);
      } catch (err) {
        console.warn("transferPlayback failed:", err);
      }

      _resolveReady(device_id);
    });

    _player.addListener("not_ready", ({ device_id }) => {
      console.warn("DnD Player went offline:", device_id);
      _isReady = false;
    });

    // ---- State changes ----

    _player.addListener("player_state_changed", state => {
      if (!state) return;

      // Detect natural track end:
      //   paused=true, position=0, and we weren't already near position=0
      //   before (guard against user pausing at the very start).
      const naturalEnd =
        state.paused &&
        state.position === 0 &&
        _previousPosition > 1000;

      _previousPosition = state.position;

      if (_onTrackChanged) _onTrackChanged(state);

      if (naturalEnd && _onTrackEnded) {
        _onTrackEnded();
      }
    });

    _player.connect();
  };

  // ------------------------------------------------------------------
  // Public API
  // ------------------------------------------------------------------

  /**
   * Initialize the player module.
   * Registers state-change and track-end callbacks.
   *
   * @param {function} onTrackChanged  Called with the full SDK state object.
   * @param {function} onTrackEnded    Called when a track ends naturally.
   */
  function init(onTrackChanged, onTrackEnded) {
    _onTrackChanged = onTrackChanged;
    _onTrackEnded   = onTrackEnded;
  }

  /** Returns a Promise that resolves to the device_id when the SDK is ready. */
  function waitForReady() {
    return _readyPromise;
  }

  /** The current device_id, or null if not yet ready. */
  function getDeviceId() {
    return _deviceId;
  }

  /** Pause the current track. */
  async function pause() {
    if (_player) await _player.pause();
  }

  /** Resume (unpause) the current track. */
  async function resume() {
    if (_player) await _player.resume();
  }

  /** Returns the current SDK playback state, or null if not ready. */
  async function getCurrentState() {
    if (!_player) return null;
    return _player.getCurrentState();
  }

  /** Toggle pause/resume. Returns true if now playing, false if paused. */
  async function togglePlayPause() {
    if (!_player) return false;
    const state = await _player.getCurrentState();
    if (!state) return false;
    if (state.paused) {
      await _player.resume();
      return true;
    } else {
      await _player.pause();
      return false;
    }
  }

  /**
   * Call before issuing a manual playTrack() request so that the resulting
   * paused→position:0 state change is not misread as a natural track end.
   */
  function resetPositionTracking() {
    _previousPosition = 0;
  }

  return { init, waitForReady, getDeviceId, getCurrentState, pause, resume, togglePlayPause, resetPositionTracking };
})();
