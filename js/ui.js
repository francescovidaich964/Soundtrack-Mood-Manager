/**
 * ui.js — Mood Pad canvas + Player Controls
 *
 * Mood Pad (400×400 canvas):
 *   X axis = valence  (left=0 sad / right=1 happy)
 *   Y axis = energy   (bottom=0 calm / top=1 energetic)
 *   Canvas Y is inverted: pixel_y = (1 - energy) * HEIGHT
 *
 *   - Scatter plot: every analyzed track as a small semi-transparent circle.
 *   - Draggable cursor: shows the current mood point.
 *   - Hover tooltip: shows title + artist of the nearest track.
 *   - Currently playing track highlighted with a larger, brighter ring.
 *
 * Player Controls:
 *   - Track title + artist label
 *   - Progress bar + time label
 *   - Play/Pause toggle, Next button
 *
 * The progress bar is updated on every player_state_changed event.
 * Sub-second smoothness is achieved by interpolating with requestAnimationFrame
 * between events (using Date.now() to estimate elapsed time).
 */

const UI = (() => {
  const CANVAS_SIZE = 400;
  const TRACK_RADIUS = 5;
  const CURSOR_RADIUS = 10;
  const HOVER_RADIUS  = 14;  // hit-test distance in pixels
  const PLAYING_RING  = 10;  // extra ring drawn around the current track

  // Internal state
  let _canvas = null;
  let _ctx    = null;
  let _moodSelector = null;
  let _currentPoint = { x: 0.5, y: 0.5 };

  // Currently playing track ID (for highlight)
  let _playingTrackId = null;

  // Progress tracking
  let _playbackState = null;   // last SDK state snapshot
  let _stateTimestamp = 0;     // Date.now() when _playbackState was recorded
  let _rafId = null;

  // Drag state
  let _dragging = false;

  // Tooltip state
  let _hoveredTrack = null;
  let _mousePos     = { x: 0, y: 0 };

  // Callbacks
  let _onPointChanged  = null;  // (x, y) => void — called while dragging
  let _onPlayPause     = null;  // () => void
  let _onNext          = null;  // () => void

  // ------------------------------------------------------------------
  // Coordinate helpers
  // ------------------------------------------------------------------

  function _toCanvas(valence, energy) {
    return {
      x: valence * CANVAS_SIZE,
      y: (1 - energy) * CANVAS_SIZE,
    };
  }

  function _fromCanvas(cx, cy) {
    return {
      x: Math.max(0, Math.min(1, cx / CANVAS_SIZE)),
      y: Math.max(0, Math.min(1, 1 - cy / CANVAS_SIZE)),
    };
  }

  function _canvasXY(event) {
    const rect = _canvas.getBoundingClientRect();
    const scaleX = CANVAS_SIZE / rect.width;
    const scaleY = CANVAS_SIZE / rect.height;
    return {
      cx: (event.clientX - rect.left) * scaleX,
      cy: (event.clientY - rect.top)  * scaleY,
    };
  }

  // ------------------------------------------------------------------
  // Drawing
  // ------------------------------------------------------------------

  function _draw() {
    if (!_ctx || !_moodSelector) return;
    _ctx.clearRect(0, 0, CANVAS_SIZE, CANVAS_SIZE);

    const tracks = _moodSelector.getTracks();

    // --- Track dots ---
    for (const track of tracks) {
      const { x, y } = _toCanvas(track.valence, track.energy);
      const isPlaying = track.track_id === _playingTrackId;
      const isHovered = _hoveredTrack && track.track_id === _hoveredTrack.track_id;

      if (isPlaying) {
        // Outer ring
        _ctx.beginPath();
        _ctx.arc(x, y, TRACK_RADIUS + PLAYING_RING, 0, Math.PI * 2);
        _ctx.strokeStyle = "rgba(201,168,76,0.6)";
        _ctx.lineWidth = 2;
        _ctx.stroke();
      }

      _ctx.beginPath();
      _ctx.arc(x, y, isHovered ? TRACK_RADIUS + 2 : TRACK_RADIUS, 0, Math.PI * 2);
      _ctx.fillStyle = isPlaying
        ? "rgba(201,168,76,0.9)"
        : isHovered
          ? "rgba(201,168,76,0.7)"
          : "rgba(201,168,76,0.35)";
      _ctx.fill();
    }

    // --- Cursor ---
    const cp = _toCanvas(_currentPoint.x, _currentPoint.y);

    // Outer ring
    _ctx.beginPath();
    _ctx.arc(cp.x, cp.y, CURSOR_RADIUS + 4, 0, Math.PI * 2);
    _ctx.strokeStyle = "rgba(255,255,255,0.3)";
    _ctx.lineWidth = 1;
    _ctx.stroke();

    // Inner circle
    _ctx.beginPath();
    _ctx.arc(cp.x, cp.y, CURSOR_RADIUS, 0, Math.PI * 2);
    _ctx.fillStyle = "rgba(255,255,255,0.85)";
    _ctx.fill();

    // Cross-hair lines
    _ctx.strokeStyle = "rgba(13,13,26,0.8)";
    _ctx.lineWidth = 1.5;
    _ctx.beginPath();
    _ctx.moveTo(cp.x - 5, cp.y);
    _ctx.lineTo(cp.x + 5, cp.y);
    _ctx.moveTo(cp.x, cp.y - 5);
    _ctx.lineTo(cp.x, cp.y + 5);
    _ctx.stroke();

    // --- Axis labels (subtle) ---
    _ctx.fillStyle = "rgba(232,224,208,0.25)";
    _ctx.font = "11px serif";
    _ctx.textAlign = "center";
    _ctx.fillText("happy →",  CANVAS_SIZE - 36, CANVAS_SIZE - 6);
    _ctx.fillText("← sad",    36, CANVAS_SIZE - 6);
    _ctx.save();
    _ctx.translate(10, CANVAS_SIZE / 2);
    _ctx.rotate(-Math.PI / 2);
    _ctx.fillText("energetic ↑", 0, 0);
    _ctx.restore();
  }

  // ------------------------------------------------------------------
  // Tooltip
  // ------------------------------------------------------------------

  function _findNearestTrack(cx, cy) {
    if (!_moodSelector) return null;
    let best = null;
    let bestDist = HOVER_RADIUS * HOVER_RADIUS;

    for (const t of _moodSelector.getTracks()) {
      const pos = _toCanvas(t.valence, t.energy);
      const d2  = (pos.x - cx) ** 2 + (pos.y - cy) ** 2;
      if (d2 < bestDist) {
        bestDist = best ? bestDist : d2; // keep shrinking threshold
        bestDist = d2;
        best = t;
      }
    }
    return best;
  }

  function _updateTooltip() {
    const tooltip = document.getElementById("mood-tooltip");
    if (!tooltip) return;

    if (_hoveredTrack) {
      tooltip.textContent = `${_hoveredTrack.title} — ${_hoveredTrack.artist}`;
      tooltip.style.display = "block";
      // Position tooltip near mouse, clamped to canvas area
      const rect = _canvas.getBoundingClientRect();
      const tx = Math.min(_mousePos.x + 12, rect.right  - rect.left - 10);
      const ty = Math.min(_mousePos.y - 28, rect.bottom - rect.top  - 10);
      tooltip.style.left = `${rect.left + tx}px`;
      tooltip.style.top  = `${rect.top  + ty + window.scrollY}px`;
    } else {
      tooltip.style.display = "none";
    }
  }

  // ------------------------------------------------------------------
  // Progress bar (smooth via rAF)
  // ------------------------------------------------------------------

  function _formatTime(ms) {
    const totalSec = Math.floor(ms / 1000);
    const min = Math.floor(totalSec / 60);
    const sec = totalSec % 60;
    return `${min}:${sec.toString().padStart(2, "0")}`;
  }

  function _updateProgress() {
    const bar      = document.getElementById("progress-bar");
    const timeLabel = document.getElementById("time-label");
    if (!bar || !_playbackState) return;

    let position = _playbackState.position;
    const duration = _playbackState.duration;

    // Interpolate forward if playing (not paused)
    if (!_playbackState.paused && _stateTimestamp) {
      position = Math.min(duration, position + (Date.now() - _stateTimestamp));
    }

    bar.style.width = duration > 0 ? `${(position / duration) * 100}%` : "0%";
    if (timeLabel) {
      timeLabel.textContent = `${_formatTime(position)} / ${_formatTime(duration)}`;
    }
  }

  function _rafLoop() {
    _updateProgress();
    _rafId = requestAnimationFrame(_rafLoop);
  }

  // ------------------------------------------------------------------
  // Event wiring
  // ------------------------------------------------------------------

  function _bindCanvasEvents() {
    _canvas.addEventListener("mousedown", e => {
      _dragging = true;
      const { cx, cy } = _canvasXY(e);
      _currentPoint = _fromCanvas(cx, cy);
      if (_onPointChanged) _onPointChanged(_currentPoint.x, _currentPoint.y);
      _draw();
    });

    _canvas.addEventListener("mousemove", e => {
      const { cx, cy } = _canvasXY(e);
      _mousePos = { x: e.clientX - _canvas.getBoundingClientRect().left, y: e.clientY - _canvas.getBoundingClientRect().top };

      if (_dragging) {
        _currentPoint = _fromCanvas(cx, cy);
        if (_onPointChanged) _onPointChanged(_currentPoint.x, _currentPoint.y);
      }

      _hoveredTrack = _findNearestTrack(cx, cy);
      _updateTooltip();
      _draw();
    });

    window.addEventListener("mouseup", () => {
      _dragging = false;
    });

    _canvas.addEventListener("mouseleave", () => {
      _hoveredTrack = null;
      _updateTooltip();
      _draw();
    });

    // Touch support (for tablets)
    _canvas.addEventListener("touchstart", e => {
      e.preventDefault();
      _dragging = true;
      const { cx, cy } = _canvasXY(e.touches[0]);
      _currentPoint = _fromCanvas(cx, cy);
      if (_onPointChanged) _onPointChanged(_currentPoint.x, _currentPoint.y);
      _draw();
    }, { passive: false });

    _canvas.addEventListener("touchmove", e => {
      e.preventDefault();
      if (!_dragging) return;
      const { cx, cy } = _canvasXY(e.touches[0]);
      _currentPoint = _fromCanvas(cx, cy);
      if (_onPointChanged) _onPointChanged(_currentPoint.x, _currentPoint.y);
      _draw();
    }, { passive: false });

    _canvas.addEventListener("touchend", () => { _dragging = false; });
  }

  // ------------------------------------------------------------------
  // Public API
  // ------------------------------------------------------------------

  /**
   * Initialize the UI.
   * @param {MoodSelector} moodSelector
   * @param {function} onPointChanged  (x, y) => void — cursor moved
   * @param {function} onPlayPause     () => void
   * @param {function} onNext          () => void
   */
  function init(moodSelector, onPointChanged, onPlayPause, onNext) {
    _moodSelector    = moodSelector;
    _onPointChanged  = onPointChanged;
    _onPlayPause     = onPlayPause;
    _onNext          = onNext;

    _canvas = document.getElementById("mood-canvas");
    _ctx    = _canvas.getContext("2d");
    _canvas.width  = CANVAS_SIZE;
    _canvas.height = CANVAS_SIZE;

    _bindCanvasEvents();

    document.getElementById("btn-play-pause")
      ?.addEventListener("click", () => _onPlayPause && _onPlayPause());
    document.getElementById("btn-next")
      ?.addEventListener("click", () => _onNext && _onNext());

    // Hide the "run sync first" overlay if data is available.
    if (window.TRACK_DATA && window.TRACK_DATA.tracks) {
      document.getElementById("no-data-overlay")?.remove();
    }

    _draw();
    _rafId = requestAnimationFrame(_rafLoop);
  }

  /**
   * Called by player.js on every player_state_changed event.
   * Updates the track label, progress bar, and play/pause button.
   */
  function onPlayerStateChanged(state) {
    _playbackState   = state;
    _stateTimestamp  = Date.now();

    const track = state?.track_window?.current_track;
    _playingTrackId  = track?.id || null;

    // Update labels
    const titleEl  = document.getElementById("track-title");
    const artistEl = document.getElementById("track-artist");
    if (titleEl)  titleEl.textContent  = track?.name   || "—";
    if (artistEl) artistEl.textContent = track?.artists?.map(a => a.name).join(", ") || "—";

    // Update play/pause button icon
    const btn = document.getElementById("btn-play-pause");
    if (btn) btn.textContent = state.paused ? "▶" : "⏸";

    _draw();
  }

  /**
   * Show a persistent error overlay (e.g., no Spotify Premium).
   */
  function showError(message) {
    const existing = document.getElementById("error-overlay");
    if (existing) existing.remove();

    const el = document.createElement("div");
    el.id = "error-overlay";
    el.className = "overlay error-overlay";
    el.innerHTML = `<p>${message.replace(/\n/g, "<br>")}</p>`;
    document.body.appendChild(el);
  }

  /** Current cursor position as {x, y} ∈ [0,1]². */
  function getCurrentPoint() {
    return { ..._currentPoint };
  }

  return { init, onPlayerStateChanged, showError, getCurrentPoint };
})();
