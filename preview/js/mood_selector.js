/**
 * mood_selector.js — greedy nearest-neighbor selection on the 2D mood plane
 *
 * Tracks are plotted at (valence, energy) ∈ [0,1]².
 * When the DM moves the cursor to (x, y), pickNext() returns the track
 * closest to that point. If the cursor stays still, subsequent calls
 * walk down the sorted list: 1st closest, 2nd closest, 3rd closest, etc.
 *
 * Position-change detection resets the index and re-sorts the list,
 * so a moved cursor always starts again from the globally closest track.
 *
 * When all tracks have been played (index exhausts the sorted list),
 * it wraps back to the closest track (index 0).
 */
class MoodSelector {
  /**
   * @param {Object[]} tracks Array of track objects from window.TRACK_DATA.tracks.
   * Each must have: track_id, valence, energy.
   * Tracks with download_failed or analysis_failed are filtered out.
   */
  constructor(tracks) {
    // Only include tracks that were successfully analyzed.
    this._tracks = tracks.filter(
      t => typeof t.valence === "number" && typeof t.energy === "number"
    );
    this._lastX = null;           // last cursor x (valence)
    this._lastY = null;           // last cursor y (energy)
    this._sortedCandidates = [];  // tracks sorted by distance from last point
    this._playIndex = 0;          // index of next track to play in sorted list
  }

  /**
   * Pick the next track based on proximity to the given point.
   *
   * If the cursor has moved since the last call, re-sort all tracks by
   * Euclidean distance and reset the play index to 0 (closest track).
   * If the cursor is stationary, advance the index to the next closest track.
   *
   * @param {number} x Valence axis ∈ [0,1] (0 = sad, 1 = happy)
   * @param {number} y Energy axis ∈ [0,1] (0 = calm, 1 = energetic)
   * @returns {Object|null} Track object, or null if the playlist is empty.
   */
  pickNext(x, y) {
    if (this._tracks.length === 0) return null;

    const positionChanged = x !== this._lastX || y !== this._lastY;

    if (positionChanged) {
      // Re-sort all tracks by Euclidean distance to the new cursor position.
      this._sortedCandidates = [...this._tracks].sort((a, b) => {
        const da = (a.valence - x) ** 2 + (a.energy - y) ** 2;
        const db = (b.valence - x) ** 2 + (b.energy - y) ** 2;
        return da - db;
      });
      this._playIndex = 0;
      this._lastX = x;
      this._lastY = y;
    }

    // Wrap around if we have exhausted the full sorted list.
    if (this._playIndex >= this._sortedCandidates.length) {
      this._playIndex = 0;
    }

    return this._sortedCandidates[this._playIndex++];
  }

  /** Return all analyzable tracks (used by UI to draw scatter plot). */
  getTracks() {
    return this._tracks;
  }

  /** Total number of analyzable tracks. */
  get count() {
    return this._tracks.length;
  }
}
