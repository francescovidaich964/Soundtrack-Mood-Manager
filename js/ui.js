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
 *   - Zoom: scroll wheel / trackpad pinch to zoom in (up to 8×); cannot zoom out past default.
 *   - Pan: drag pans when zoomed; drag moves cursor when at default zoom.
 *   - Click/tap (no significant drag): places cursor at that point.
 *   - Minimap: shown in top-left corner when zoomed in.
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
  const CANVAS_SIZE    = 400;
  const TRACK_RADIUS   = 5;
  const CURSOR_RADIUS  = 10;
  const HOVER_RADIUS   = 14;   // hit-test distance in pixels (screen space)
  const PLAYING_RING   = 10;   // extra ring drawn around the current track
  const MAX_SCALE      = 8;    // maximum zoom multiplier
  const MINIMAP_SIZE   = 80;   // minimap side length in canvas pixels
  const MINIMAP_MARGIN = 8;    // minimap distance from canvas edge
  const PAN_THRESHOLD  = 4;    // pixels of movement before drag = pan (not click)

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

  // Viewport state
  let _viewScale  = 1.0;
  let _viewOffset = { x: 0, y: 0 };  // top-left world canvas pixel of viewport

  // Pan/click disambiguation
  // _panStart.cx/cy updated each mousemove frame for per-frame deltas (avoids edge dead zone)
  // isClick stays true until PAN_THRESHOLD is crossed
  let _panStart = null;  // { cx, cy, isClick }
  let _panMoved = false;

  // Touch gesture state
  let _touchState = null;

  // Tooltip state
  let _hoveredTrack = null;
  let _mousePos     = { x: 0, y: 0 };

  // Key-correction toggle
  let _applyKeyCorrection = true;

  // Callbacks
  let _onPointChanged  = null;  // (x, y) => void — called while dragging
  let _onPlayPause     = null;  // () => void
  let _onNext          = null;  // () => void
  let _onSeek          = null;  // (positionMs) => void

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
  // Viewport helpers
  // ------------------------------------------------------------------

  function _screenToWorld(scx, scy) {
    return {
      cx: scx / _viewScale + _viewOffset.x,
      cy: scy / _viewScale + _viewOffset.y,
    };
  }

  function _worldToScreen(wx, wy) {
    return {
      sx: (wx - _viewOffset.x) * _viewScale,
      sy: (wy - _viewOffset.y) * _viewScale,
    };
  }

  function _clampViewport() {
    const maxOff = CANVAS_SIZE * (1 - 1 / _viewScale);
    _viewOffset.x = Math.max(0, Math.min(maxOff, _viewOffset.x));
    _viewOffset.y = Math.max(0, Math.min(maxOff, _viewOffset.y));
  }

  function _applyZoom(factor, scx, scy) {
    const newScale = Math.max(1, Math.min(MAX_SCALE, _viewScale * factor));
    if (newScale === _viewScale) return;
    // Keep the world point under (scx, scy) fixed on screen
    const worldX = scx / _viewScale + _viewOffset.x;
    const worldY = scy / _viewScale + _viewOffset.y;
    _viewScale = newScale;
    _viewOffset.x = worldX - scx / _viewScale;
    _viewOffset.y = worldY - scy / _viewScale;
    _clampViewport();
  }

  // ------------------------------------------------------------------
  // Drawing
  // ------------------------------------------------------------------

  function _draw() {
    if (!_ctx || !_moodSelector) return;
    _ctx.clearRect(0, 0, CANVAS_SIZE, CANVAS_SIZE);

    // Clip to canvas bounds so tracks near edges don't bleed outside
    _ctx.save();
    _ctx.beginPath();
    _ctx.rect(0, 0, CANVAS_SIZE, CANVAS_SIZE);
    _ctx.clip();

    const tracks = _moodSelector.getTracks();

    // --- Track dots (drawn in screen space so size is constant regardless of zoom) ---
    for (const track of tracks) {
      const { x, y } = _toCanvas(effectiveValence(track, _applyKeyCorrection), track.energy);
      const { sx, sy } = _worldToScreen(x, y);
      const isPlaying = track.track_id === _playingTrackId;
      const isHovered = _hoveredTrack && track.track_id === _hoveredTrack.track_id;

      if (isPlaying) {
        // Outer ring
        _ctx.beginPath();
        _ctx.arc(sx, sy, TRACK_RADIUS + PLAYING_RING, 0, Math.PI * 2);
        _ctx.strokeStyle = "rgba(201,168,76,0.6)";
        _ctx.lineWidth = 2;
        _ctx.stroke();
      }

      _ctx.beginPath();
      _ctx.arc(sx, sy, isHovered ? TRACK_RADIUS + 2 : TRACK_RADIUS, 0, Math.PI * 2);
      _ctx.fillStyle = isPlaying
        ? "rgba(201,168,76,0.9)"
        : isHovered
          ? "rgba(201,168,76,0.7)"
          : "rgba(201,168,76,0.35)";
      _ctx.fill();
    }

    // --- Cursor (screen space, fixed size) ---
    const { x: cpwx, y: cpwy } = _toCanvas(_currentPoint.x, _currentPoint.y);
    const { sx: cpx, sy: cpy } = _worldToScreen(cpwx, cpwy);

    // Outer ring
    _ctx.beginPath();
    _ctx.arc(cpx, cpy, CURSOR_RADIUS + 4, 0, Math.PI * 2);
    _ctx.strokeStyle = "rgba(255,255,255,0.3)";
    _ctx.lineWidth = 1;
    _ctx.stroke();

    // Inner circle
    _ctx.beginPath();
    _ctx.arc(cpx, cpy, CURSOR_RADIUS, 0, Math.PI * 2);
    _ctx.fillStyle = "rgba(255,255,255,0.85)";
    _ctx.fill();

    // Cross-hair lines
    _ctx.strokeStyle = "rgba(13,13,26,0.8)";
    _ctx.lineWidth = 1.5;
    _ctx.beginPath();
    _ctx.moveTo(cpx - 5, cpy);
    _ctx.lineTo(cpx + 5, cpy);
    _ctx.moveTo(cpx, cpy - 5);
    _ctx.lineTo(cpx, cpy + 5);
    _ctx.stroke();

    _ctx.restore();

    // --- Axis labels (fixed screen positions, not affected by zoom) ---
    _ctx.fillStyle = "rgba(232,224,208,0.25)";
    _ctx.font = "11px serif";
    _ctx.textAlign = "center";
    _ctx.fillText("happy →",  CANVAS_SIZE - 36, CANVAS_SIZE - 6);
    _ctx.fillText("← sad",    36, CANVAS_SIZE - 6);
    _ctx.save();
    _ctx.translate(10, CANVAS_SIZE / 2);
    _ctx.rotate(-Math.PI / 2);
    _ctx.fillText("← calm",       -(CANVAS_SIZE / 2 - 36), 0);
    _ctx.fillText("energetic →",    CANVAS_SIZE / 2 - 36,  0);
    _ctx.restore();

    // --- Minimap (only when zoomed in) ---
    _drawMinimap();
  }

  function _drawMinimap() {
    if (_viewScale <= 1) return;

    const M  = MINIMAP_SIZE;
    const mg = MINIMAP_MARGIN;
    const mx = mg;
    const my = mg;

    // Background
    _ctx.fillStyle = "rgba(13,13,26,0.75)";
    _ctx.fillRect(mx, my, M, M);
    _ctx.strokeStyle = "rgba(232,224,208,0.25)";
    _ctx.lineWidth = 1;
    _ctx.strokeRect(mx, my, M, M);

    // Track dots
    for (const t of _moodSelector.getTracks()) {
      _ctx.beginPath();
      _ctx.arc(mx + effectiveValence(t, _applyKeyCorrection) * M, my + (1 - t.energy) * M, 1.5, 0, Math.PI * 2);
      _ctx.fillStyle = t.track_id === _playingTrackId
        ? "rgba(201,168,76,0.9)"
        : "rgba(201,168,76,0.35)";
      _ctx.fill();
    }

    // Cursor dot
    _ctx.beginPath();
    _ctx.arc(
      mx + _currentPoint.x * M,
      my + (1 - _currentPoint.y) * M,
      2.5, 0, Math.PI * 2
    );
    _ctx.fillStyle = "rgba(255,255,255,0.85)";
    _ctx.fill();

    // Viewport indicator rectangle
    _ctx.strokeStyle = "rgba(255,255,255,0.55)";
    _ctx.lineWidth = 1;
    _ctx.strokeRect(
      mx + (_viewOffset.x / CANVAS_SIZE) * M,
      my + (_viewOffset.y / CANVAS_SIZE) * M,
      M / _viewScale,
      M / _viewScale
    );
  }

  // ------------------------------------------------------------------
  // Tooltip
  // ------------------------------------------------------------------

  function _findNearestTrack(wcx, wcy) {
    if (!_moodSelector) return null;
    // Threshold is in world canvas pixels; scale so it feels constant on screen
    const threshold = (HOVER_RADIUS / _viewScale) ** 2;
    let best = null;
    let bestDist = threshold;

    for (const t of _moodSelector.getTracks()) {
      const pos = _toCanvas(effectiveValence(t, _applyKeyCorrection), t.energy);
      const d2  = (pos.x - wcx) ** 2 + (pos.y - wcy) ** 2;
      if (d2 < bestDist) {
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
    // --- Wheel zoom (scroll wheel + trackpad two-finger scroll) ---
    _canvas.addEventListener("wheel", e => {
      e.preventDefault();
      const { cx, cy } = _canvasXY(e);
      _applyZoom(e.deltaY < 0 ? 1.2 : 1 / 1.2, cx, cy);
      _draw();
    }, { passive: false });

    // --- Mouse ---
    _canvas.addEventListener("mousedown", e => {
      const { cx, cy } = _canvasXY(e);
      _panStart = { cx, cy, isClick: true };
      _panMoved = false;
    });

    _canvas.addEventListener("mousemove", e => {
      const { cx, cy } = _canvasXY(e);
      _mousePos = {
        x: e.clientX - _canvas.getBoundingClientRect().left,
        y: e.clientY - _canvas.getBoundingClientRect().top,
      };

      if (_panStart) {
        const ddx = cx - _panStart.cx;
        const ddy = cy - _panStart.cy;
        if (Math.abs(ddx) > PAN_THRESHOLD || Math.abs(ddy) > PAN_THRESHOLD) {
          _panMoved = true;
          _panStart.isClick = false;
        }
        if (_panMoved) {
          if (_viewScale > 1) {
            // Zoomed: drag pans the viewport
            _viewOffset.x -= ddx / _viewScale;
            _viewOffset.y -= ddy / _viewScale;
            _clampViewport();
          } else {
            // Not zoomed: drag moves the cursor (existing behaviour)
            const { cx: wcx, cy: wcy } = _screenToWorld(cx, cy);
            _currentPoint = _fromCanvas(wcx, wcy);
            if (_onPointChanged) _onPointChanged(_currentPoint.x, _currentPoint.y);
          }
        }
        // Update each frame so next delta is computed from current position
        // (avoids dead zone when pushing against a clamped viewport edge)
        _panStart.cx = cx;
        _panStart.cy = cy;
      }

      const { cx: wcx, cy: wcy } = _screenToWorld(cx, cy);
      _hoveredTrack = _findNearestTrack(wcx, wcy);
      _updateTooltip();
      _draw();
    });

    window.addEventListener("mouseup", () => {
      if (_panStart?.isClick) {
        // Pure click (no drag) → place cursor at that position
        const { cx: wcx, cy: wcy } = _screenToWorld(_panStart.cx, _panStart.cy);
        _currentPoint = _fromCanvas(wcx, wcy);
        if (_onPointChanged) _onPointChanged(_currentPoint.x, _currentPoint.y);
        _draw();
      }
      _panStart = null;
      _panMoved = false;
    });

    _canvas.addEventListener("mouseleave", () => {
      _hoveredTrack = null;
      _updateTooltip();
      _draw();
    });

    // --- Touch ---
    _canvas.addEventListener("touchstart", e => {
      e.preventDefault();
      if (e.touches.length === 1) {
        const { cx, cy } = _canvasXY(e.touches[0]);
        _touchState = {
          type: "single",
          cx, cy,        // updated each touchmove frame for per-frame deltas
          isClick: true,
          moved: false,
        };
      } else if (e.touches.length === 2) {
        const t1 = _canvasXY(e.touches[0]);
        const t2 = _canvasXY(e.touches[1]);
        _touchState = {
          type: "pinch",
          startDist:   Math.hypot(t2.cx - t1.cx, t2.cy - t1.cy),
          startScale:  _viewScale,
          startOffsetX: _viewOffset.x,
          startOffsetY: _viewOffset.y,
          midX: (t1.cx + t2.cx) / 2,
          midY: (t1.cy + t2.cy) / 2,
        };
      }
    }, { passive: false });

    _canvas.addEventListener("touchmove", e => {
      e.preventDefault();
      if (!_touchState) return;

      if (_touchState.type === "single" && e.touches.length === 1) {
        const { cx, cy } = _canvasXY(e.touches[0]);
        const ddx = cx - _touchState.cx;
        const ddy = cy - _touchState.cy;
        if (Math.abs(ddx) > PAN_THRESHOLD || Math.abs(ddy) > PAN_THRESHOLD) {
          _touchState.moved = true;
          _touchState.isClick = false;
        }
        if (_touchState.moved) {
          if (_viewScale > 1) {
            _viewOffset.x -= ddx / _viewScale;
            _viewOffset.y -= ddy / _viewScale;
            _clampViewport();
          } else {
            const { cx: wcx, cy: wcy } = _screenToWorld(cx, cy);
            _currentPoint = _fromCanvas(wcx, wcy);
            if (_onPointChanged) _onPointChanged(_currentPoint.x, _currentPoint.y);
          }
          _draw();
        }
        _touchState.cx = cx;
        _touchState.cy = cy;
      } else if (_touchState.type === "pinch" && e.touches.length === 2) {
        const t1 = _canvasXY(e.touches[0]);
        const t2 = _canvasXY(e.touches[1]);
        const dist = Math.hypot(t2.cx - t1.cx, t2.cy - t1.cy);
        const newScale = Math.max(1, Math.min(MAX_SCALE,
          _touchState.startScale * dist / _touchState.startDist));
        // Keep the world point under the initial pinch midpoint fixed
        const worldMidX = _touchState.midX / _touchState.startScale + _touchState.startOffsetX;
        const worldMidY = _touchState.midY / _touchState.startScale + _touchState.startOffsetY;
        _viewScale = newScale;
        _viewOffset.x = worldMidX - _touchState.midX / _viewScale;
        _viewOffset.y = worldMidY - _touchState.midY / _viewScale;
        _clampViewport();
        _draw();
      }
    }, { passive: false });

    _canvas.addEventListener("touchend", e => {
      if (_touchState?.isClick) {
        // Tap without drag → place cursor
        const { cx, cy } = _canvasXY(e.changedTouches[0]);
        const { cx: wcx, cy: wcy } = _screenToWorld(cx, cy);
        _currentPoint = _fromCanvas(wcx, wcy);
        if (_onPointChanged) _onPointChanged(_currentPoint.x, _currentPoint.y);
        _draw();
      }
      _touchState = null;
    });
  }

  function _bindProgressBarEvents() {
    const container = document.querySelector(".progress-container");
    if (!container) return;
    container.style.cursor = "pointer";
    container.addEventListener("click", e => {
      if (!_playbackState || !_playbackState.duration) return;
      const rect = container.getBoundingClientRect();
      const fraction = Math.max(0, Math.min(1, (e.clientX - rect.left) / rect.width));
      const positionMs = fraction * _playbackState.duration;
      if (_onSeek) _onSeek(positionMs);
    });
  }

  // ------------------------------------------------------------------
  // Public API
  // ------------------------------------------------------------------

  /**
   * Initialize the UI.
   * @param {function} onPointChanged  (x, y) => void — cursor moved
   * @param {function} onPlayPause     () => void
   * @param {function} onNext          () => void
   * @param {function} onSeek          (positionMs) => void
   */
  function init(onPointChanged, onPlayPause, onNext, onSeek) {
    _onPointChanged  = onPointChanged;
    _onPlayPause     = onPlayPause;
    _onNext          = onNext;
    _onSeek          = onSeek;

    _canvas = document.getElementById("mood-canvas");
    _ctx    = _canvas.getContext("2d");
    _canvas.width  = CANVAS_SIZE;
    _canvas.height = CANVAS_SIZE;

    _bindCanvasEvents();
    _bindProgressBarEvents();

    document.getElementById("btn-play-pause")
      ?.addEventListener("click", () => _onPlayPause && _onPlayPause());
    document.getElementById("btn-next")
      ?.addEventListener("click", () => _onNext && _onNext());

    const chkKeyCorrection = document.getElementById("chk-key-correction");
    if (chkKeyCorrection) {
      chkKeyCorrection.addEventListener("change", () => {
        _applyKeyCorrection = chkKeyCorrection.checked;
        if (_moodSelector) _moodSelector.setKeyCorrection(_applyKeyCorrection);
        _draw();
      });
    }

    // Hide the "run sync first" overlay if at least one playlist is available.
    if (window.TRACK_DATA?.playlists && Object.keys(window.TRACK_DATA.playlists).length > 0) {
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
    // Prefer linked_from.id: Spotify may relink a requested track to a
    // different version; linked_from carries the original ID stored in data.js.
    _playingTrackId  = track?.linked_from?.id || track?.id || null;

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

  /**
   * Replace the active MoodSelector and redraw the canvas.
   * Called when the user switches playlists.
   * @param {MoodSelector} newSelector
   */
  function setTracks(newSelector) {
    _moodSelector = newSelector;
    _moodSelector.setKeyCorrection(_applyKeyCorrection);
    _draw();
  }

  return { init, onPlayerStateChanged, showError, getCurrentPoint, setTracks };
})();
