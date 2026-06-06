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


def setup_deam(data_dir: Path, download_audio: bool = True) -> tuple:
    """Load DEAM annotations and optionally download audio from the official source.

    Zip structure (after extraction):
      DEAM_audio.zip        → MEMD_audio/<song_id>.mp3   (1802 files, 1.3 GB)
      DEAM_Annotations.zip  → annotations/annotations averaged per song/song_level/
                               static_annotations_averaged_songs_1_2000.csv
                               static_annotations_averaged_songs_2000_2058.csv

    Annotation columns: song_id, valence_mean, arousal_mean  (scale 1–9)
    Official download page: https://cvml.unige.ch/databases/DEAM/
    """
    deam_dir = Path(data_dir) / "deam"
    deam_dir.mkdir(parents=True, exist_ok=True)

    files_to_download = {"DEAM_Annotations.zip"}
    if download_audio:
        files_to_download.add("DEAM_audio.zip")

    for name in files_to_download:
        dest = deam_dir / name
        if dest.exists():
            print(f"  ✓ {name} (cached)")
            continue
        try:
            _download(_DEAM_URLS[name], dest, name)
        except requests.HTTPError as e:
            print(f"  ⚠  Download failed ({e.response.status_code}): {name}")
            print(f"     Get it from https://cvml.unige.ch/databases/DEAM/")
            dest.unlink(missing_ok=True)

    # Extract any downloaded zips that haven't been extracted yet
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
_MERGE_ZENODO    = "13939205"
_MERGE_AUDIO_FILE = "MERGE_Audio_Balanced.zip"   # 1.1 GB, 3232 clips
# Audio is organised into quadrant subdirs: Q1/ Q2/ Q3/ Q4/
# Annotation file bundled inside the zip: merge_audio_balanced_av_values.csv
#   Columns: Song (string ID), Arousal (0-1), Valence (0-1)


def setup_merge(data_dir: Path, download_audio: bool = True) -> tuple:
    """Download MERGE (Balanced) from Zenodo; return (df, id_col, val_col, aro_col).

    MERGE has 3,232 30-second audio clips with continuous valence/arousal (scale 0–1).
    Audio is organised in Q1/Q2/Q3/Q4 subdirectories inside the zip.
    Zenodo record: https://zenodo.org/records/13939205
    """
    merge_dir = Path(data_dir) / "merge"
    merge_dir.mkdir(parents=True, exist_ok=True)

    audio_zip = merge_dir / _MERGE_AUDIO_FILE
    if download_audio and not audio_zip.exists():
        url = f"https://zenodo.org/records/{_MERGE_ZENODO}/files/{_MERGE_AUDIO_FILE}?download=1"
        try:
            _download(url, audio_zip, _MERGE_AUDIO_FILE)
        except requests.HTTPError as e:
            print(f"  ⚠  Download failed ({e.response.status_code}): {_MERGE_AUDIO_FILE}")
            print(f"     Get it from https://zenodo.org/records/{_MERGE_ZENODO}")
            audio_zip.unlink(missing_ok=True)

    if audio_zip.exists():
        _extract_zips(merge_dir)

    # The av_values CSV has the continuous valence/arousal we need
    annot_path = next(iter(sorted(merge_dir.rglob("merge_audio_balanced_av_values.csv"))), None)
    if annot_path is None:
        print("⚠  MERGE annotation CSV not found after extraction.")
        print(f"   Expected merge_audio_balanced_av_values.csv inside {_MERGE_AUDIO_FILE}.")
        return None, None, None, None

    df = pd.read_csv(annot_path)
    df.columns = df.columns.str.strip()
    # Known columns: Song, Arousal, Valence (scale 0-1, already normalised)
    id_col  = "Song"
    val_col = "Valence"
    aro_col = "Arousal"
    print(f"MERGE: {len(df)} rows  id={id_col!r}  valence={val_col!r}  arousal={aro_col!r}")
    return df, id_col, val_col, aro_col
