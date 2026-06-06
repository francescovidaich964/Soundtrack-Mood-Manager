"""Dataset download and annotation loading for mood evaluation benchmarks.

Each setup_*() returns (df, id_col, val_col, aro_col) on success,
or (None, None, None, None) if the dataset is not available.

Ground-truth annotation scales:
  DEAM:  1–9  (normalised to [0, 1] inside run_evaluation in spot_checks.py)
  PMEmo: 0–1  (already normalised — no conversion needed)
  MERGE: 0–1  (continuous valence/arousal, already normalised)
"""

from __future__ import annotations

import importlib.util
import zipfile
from pathlib import Path

import pandas as pd
import requests


# ── Helpers ──────────────────────────────────────────────────────────────────

def _download(url: str, dest: Path, label: str = "", timeout: int = 120) -> None:
    """Stream-download url to dest."""
    print(f"Downloading {label or dest.name}...", end=" ", flush=True)
    r = requests.get(url, stream=True, timeout=timeout)
    r.raise_for_status()
    dest.parent.mkdir(parents=True, exist_ok=True)
    with open(dest, "wb") as f:
        for chunk in r.iter_content(65536):
            f.write(chunk)
    print(f"{dest.stat().st_size / 1e6:.1f} MB")


def _extract_zips(directory: Path) -> None:
    """Extract all .zip files found directly under directory."""
    for zip_path in sorted(directory.glob("*.zip")):
        print(f"Extracting {zip_path.name}...")
        with zipfile.ZipFile(zip_path) as z:
            z.extractall(directory)


def _detect_columns(df: pd.DataFrame) -> tuple[str, str | None, str | None]:
    """Return (id_col, val_col, aro_col) by scanning column names."""
    id_col = df.columns[0]
    val_col = next((c for c in df.columns if "valence" in c.lower()), None)
    aro_col = next((c for c in df.columns if "arousal" in c.lower()), None)
    return id_col, val_col, aro_col


# ── DEAM ─────────────────────────────────────────────────────────────────────

# Official download page: https://cvml.unige.ch/databases/DEAM/
_DEAM_URLS = {
    "DEAM_Annotations.zip": "https://cvml.unige.ch/databases/DEAM/DEAM_Annotations.zip",
    "DEAM_audio.zip":       "https://cvml.unige.ch/databases/DEAM/DEAM_audio.zip",
}


def setup_deam(data_dir: Path) -> tuple:
    """Load DEAM annotations; download zips if not already present.

    Zip structure (after extraction):
      DEAM_audio.zip        → MEMD_audio/<song_id>.mp3
      DEAM_Annotations.zip  → annotations/annotations averaged per song/song_level/
                               static_annotations_averaged_songs_1_2000.csv
                               static_annotations_averaged_songs_2000_2058.csv

    Annotation columns: song_id, valence_mean, arousal_mean  (scale 1–9)

    Audio is NOT downloaded automatically — only annotations are fetched.
    Place DEAM_audio.zip in <data_dir>/deam/ and re-run to extract audio.
    """
    deam_dir = Path(data_dir) / "deam"
    deam_dir.mkdir(parents=True, exist_ok=True)

    # Download annotations zip if not present (small, 4.7 MB)
    annot_zip = deam_dir / "DEAM_Annotations.zip"
    if not annot_zip.exists():
        url = _DEAM_URLS["DEAM_Annotations.zip"]
        print(f"Downloading DEAM annotations from {url}")
        try:
            _download(url, annot_zip, "DEAM_Annotations.zip")
        except requests.HTTPError as e:
            print(f"  ⚠  Download failed ({e.response.status_code}).")
            print(f"     Download manually from https://cvml.unige.ch/databases/DEAM/")
            print(f"     Place DEAM_Annotations.zip in {deam_dir}/ and re-run.")

    # Extract any unextracted zips (annotations + audio if present)
    _extract_zips(deam_dir)

    # Merge both static annotation CSVs (songs 1-2000 and 2000-2058)
    annot_csvs = sorted(deam_dir.rglob("static_annotations_averaged_songs_*.csv"))
    if not annot_csvs:
        print("⚠  No DEAM annotation CSVs found.")
        print(f"   Place DEAM_Annotations.zip in {deam_dir}/ and re-run this cell.")
        return None, None, None, None

    parts = []
    for p in annot_csvs:
        df = pd.read_csv(p)
        df.columns = df.columns.str.strip()  # column names have leading spaces in the raw files
        parts.append(df)
    df = pd.concat(parts, ignore_index=True)

    # Use known stable column names; fall back to detection if they differ
    id_col  = "song_id"      if "song_id"      in df.columns else df.columns[0]
    val_col = "valence_mean" if "valence_mean"  in df.columns else next((c for c in df.columns if "valence" in c.lower()), None)
    aro_col = "arousal_mean" if "arousal_mean"  in df.columns else next((c for c in df.columns if "arousal" in c.lower()), None)

    print(f"DEAM: {len(df)} songs  id={id_col!r}  valence={val_col!r}  arousal={aro_col!r}")
    return df, id_col, val_col, aro_col


# ── EmoMusic ─────────────────────────────────────────────────────────────────

def setup_emomusic(data_dir: Path) -> tuple:
    """EmoMusic — currently unavailable (official links return 404 as of 2025-06).

    If you have a local copy, place it as:
      <data_dir>/emomusic/clips/          — .mp3 files named by song_id
      <data_dir>/emomusic/annotations.csv — columns: <id>, valence, arousal (scale 1–9)
    """
    emo_dir = Path(data_dir) / "emomusic"
    annot   = emo_dir / "annotations.csv"

    if not annot.exists():
        print("⚠  EmoMusic unavailable — official download links return 404 (as of 2025-06).")
        print("   If you have a local copy, place annotations.csv in data/emomusic/")
        print("   and audio .mp3 files in data/emomusic/clips/")
        return None, None, None, None

    df = pd.read_csv(annot)
    df.columns = df.columns.str.strip()
    id_col, val_col, aro_col = _detect_columns(df)
    print(f"EmoMusic: {len(df)} rows  id={id_col!r}  valence={val_col!r}  arousal={aro_col!r}")
    return df, id_col, val_col, aro_col


# ── PMEmo ─────────────────────────────────────────────────────────────────────

_PMEMO_DRIVE = "https://drive.google.com/drive/folders/1qDk6hZDGVlVXgckjLq9LvXLZ9EgK9gw0"


def setup_pmemo(data_dir: Path) -> tuple:
    """Download PMEmo from Google Drive via gdown; return (df, id_col, val_col, aro_col).

    Annotation scale is 0–1 (already normalised — no conversion applied).
    Audio lives in the chorus/ subfolder inside the extracted zip.
    """
    pmemo_dir = Path(data_dir) / "pmemo"
    pmemo_dir.mkdir(parents=True, exist_ok=True)

    annot = pmemo_dir / "static_annotations.csv"

    if not annot.exists():
        if importlib.util.find_spec("gdown") is None:
            print("gdown not installed — run: pip install gdown -q")
        else:
            import gdown
            print("Downloading PMEmo from Google Drive (may take several minutes)...")
            try:
                gdown.download_folder(
                    _PMEMO_DRIVE, output=str(pmemo_dir), quiet=False, use_cookies=False
                )
            except Exception as e:
                print(f"  gdown failed: {e}")

        # gdown downloads files as-is (including zips) — extract them
        _extract_zips(pmemo_dir)

        candidates = sorted(pmemo_dir.rglob("static_annotations.csv"))
        if candidates:
            annot = candidates[0]

    if not annot.exists():
        print("⚠  PMEmo annotations not found. Mount from Google Drive manually:")
        print("   from google.colab import drive; drive.mount('/content/drive')")
        print("   PMEMO_AUDIO_DIR  = Path('/content/drive/MyDrive/PMEmo2019/chorus')")
        print("   PMEMO_ANNOT_PATH = Path('/content/drive/MyDrive/PMEmo2019/annotations/static_annotations.csv')")
        return None, None, None, None

    df = pd.read_csv(annot)
    df.columns = df.columns.str.strip()
    # PMEmo uses 'musicId' as the track identifier
    id_col = next(
        (c for c in df.columns if "music" in c.lower() or c.lower() == "id"),
        df.columns[0],
    )
    _, val_col, aro_col = _detect_columns(df)
    print(f"PMEmo: {len(df)} rows  id={id_col!r}  valence={val_col!r}  arousal={aro_col!r}")
    return df, id_col, val_col, aro_col


# ── MERGE ─────────────────────────────────────────────────────────────────────

# Zenodo record: https://zenodo.org/records/13939205
_MERGE_ZENODO = "13939205"
_MERGE_AUDIO_FILE  = "MERGE_Audio_Complete.zip"   # 1.2 GB, 3554 clips
_MERGE_ANNOT_FILE  = "MERGE_Audio_Complete.zip"   # annotations are bundled inside


def setup_merge(data_dir: Path) -> tuple:
    """Download MERGE dataset from Zenodo; return (df, id_col, val_col, aro_col).

    MERGE has 3,554 30-second audio clips with continuous valence and arousal
    annotations (scale 0–1) from AllMusic, plus Russell quadrant labels.
    Zenodo record: https://zenodo.org/records/13939205

    Audio is NOT downloaded automatically (1.2 GB).
    Run the download cell below when ready.
    """
    merge_dir = Path(data_dir) / "merge"
    merge_dir.mkdir(parents=True, exist_ok=True)

    # Locate annotation CSV (bundled inside the audio zip after extraction)
    annot_candidates = sorted(merge_dir.rglob("*.csv"))
    # Prefer files that mention 'metadata' or 'annotation' in their name
    scored = sorted(annot_candidates, key=lambda p: (
        "metadata" in p.name.lower() or "annot" in p.name.lower()
    ), reverse=True)

    if not scored:
        print("⚠  MERGE annotations not found.")
        print(f"   Download MERGE_Audio_Complete.zip from https://zenodo.org/records/{_MERGE_ZENODO}")
        print(f"   Place it in {merge_dir}/ and re-run this cell.")
        print()
        print("   To download automatically, run:")
        print(f"   url = 'https://zenodo.org/records/{_MERGE_ZENODO}/files/{_MERGE_AUDIO_FILE}?download=1'")
        print(f"   !wget -q --show-progress -O data/merge/{_MERGE_AUDIO_FILE} {{url}}")
        return None, None, None, None

    df = pd.read_csv(scored[0])
    df.columns = df.columns.str.strip()

    id_col, val_col, aro_col = _detect_columns(df)
    print(f"MERGE: {len(df)} rows  id={id_col!r}  valence={val_col!r}  arousal={aro_col!r}")
    print(f"  (loaded from {scored[0].relative_to(merge_dir)})")
    return df, id_col, val_col, aro_col
