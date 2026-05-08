/**
 * mood_selector.js — nearest-neighbor soft-sampling on the 2D mood plane
 *
 * Tracks are plotted at (valence, energy) ∈ [0,1]².
 * When the DM moves the cursor to (x, y), pickNext() returns a track
 * sampled probabilistically with weight ∝ exp(−d²/σ²), where d is the
 * Euclidean distance from the cursor to each track.
 *
 * This "soft" sampling means:
 *   - Closer tracks are strongly preferred but not guaranteed.
 *   - The same track isn't always repeated when the cursor is stationary.
 *
 * A circular ring buffer of recently-played track IDs prevents immediate
 * repetitions. If the ring buffer would exhaust all candidates (tiny playlist),
 * it is cleared and sampling restarts.
 */

class MoodSelector {
  /**
   * @param {Object[]} tracks  Array of track objects from window.TRACK_DATA.tracks.
   *                           Each must have: track_id, valence, energy.
   *                           Tracks with download_failed or analysis_failed are filtered out.
   */
  constructor(tracks) {
    // Only include tracks that were successfully analyzed.
    this._tracks = tracks.filter(
      t => typeof t.valence === "number" && typeof t.energy === "number"
    );

    this._sigma = CONFIG.sigma;                       // spread parameter
    this._recentSize = CONFIG.recentlyPlayedSize;     // ring buffer size
    this._recentlyPlayed = [];                        // ring buffer
  }

  /**
   * Pick the next track based on proximity to the given point.
   *
   * @param {number} x  Valence axis ∈ [0,1]  (0 = sad, 1 = happy)
   * @param {number} y  Energy axis  ∈ [0,1]  (0 = calm, 1 = energetic)
   * @returns {Object|null} Track object, or null if the playlist is empty.
   */
  pickNext(x, y) {
    if (this._tracks.length === 0) return null;

    let candidates = this._tracks.filter(
      t => !this._recentlyPlayed.includes(t.track_id)
    );

    // If the recently-played buffer has consumed all tracks (tiny playlist),
    // clear it and try again with the full list.
    if (candidates.length === 0) {
      this._recentlyPlayed = [];
      candidates = [...this._tracks];
    }

    // Compute soft-sampling weights: w_i = exp(−d²/σ²)
    const sigma2 = this._sigma * this._sigma;
    const weights = candidates.map(t => {
      const dx = t.valence - x;
      const dy = t.energy  - y;
      const d2 = dx * dx + dy * dy;
      return Math.exp(-d2 / sigma2);
    });

    const totalWeight = weights.reduce((s, w) => s + w, 0);

    // Weighted random sample.
    let rand = Math.random() * totalWeight;
    let chosen = candidates[candidates.length - 1]; // fallback (should not happen)
    for (let i = 0; i < candidates.length; i++) {
      rand -= weights[i];
      if (rand <= 0) {
        chosen = candidates[i];
        break;
      }
    }

    // Push to ring buffer (evict oldest if full).
    this._recentlyPlayed.push(chosen.track_id);
    if (this._recentlyPlayed.length > this._recentSize) {
      this._recentlyPlayed.shift();
    }

    return chosen;
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
