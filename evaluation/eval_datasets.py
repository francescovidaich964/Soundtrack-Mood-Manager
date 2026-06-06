"""Dataset download and annotation loading for mood evaluation benchmarks.

Each setup_*() returns (df, id_col, val_col, aro_col) on success,
or (None, None, None, None) if the dataset is not available.

Ground-truth annotation scales:
  DEAM:     1–9  (normalised to [0, 1] inside run_evaluation in spot_checks.py)
  EmoMusic: 1–9  (same)
  PMEmo:    0–1  (already normalised — no conversion needed)
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


def _best_annot_csv(root: Path) -> Path | None:
    """Return the annotation CSV most likely to be the static per-song annotations."""
    csvs = list(root.rglob("*.csv"))
    if not csvs:
        return None
    keywords = ("static", "averaged", "song")

    def score(p: Path) -> int:
        n = p.name.lower()
        return sum(k in n for k in keywords)

    return sorted(csvs, key=score, reverse=True)[0]


def _detect_columns(df: pd.DataFrame) -> tuple[str, str | None, str | None]:
    """Return (id_col, val_col, aro_col) by scanning column names."""
    id_col = df.columns[0]
    val_col = next((c for c in df.columns if "valence" in c.lower()), None)
    aro_col = next((c for c in df.columns if "arousal" in c.lower()), None)
    return id_col, val_col, aro_col


# ── DEAM ─────────────────────────────────────────────────────────────────────

_DEAM_ZENODO = "11400122"


def setup_deam(data_dir: Path) -> tuple:
    """Download DEAM annotations from Zenodo; return (df, id_col, val_col, aro_col).

    Audio (~4 GB) is NOT downloaded automatically.
    Place .mp3 files (named by song_id) in <data_dir>/deam/audio/ to enable evaluation.
    """
    deam_dir = Path(data_dir) / "deam"
    deam_dir.mkdir(parents=True, exist_ok=True)

    resp = requests.get(f"https://zenodo.org/api/records/{_DEAM_ZENODO}")
    if resp.status_code != 200 or not resp.text.strip():
        print(f"⚠  Zenodo API returned {resp.status_code} (possibly rate-limited or down).")
        print(f"   Download annotations manually from https://zenodo.org/records/{_DEAM_ZENODO}")
        print(f"   Then place them in {deam_dir}/ and re-run this cell.")
        return None, None, None, None
    meta = resp.json()
    print(f"DEAM — {meta.get('metadata', {}).get('title', 'Zenodo record')}")

    for f in meta.get("files", []):
        name, size_mb = f["key"], f["size"] / 1e6
        dest = deam_dir / name
        if dest.exists():
            print(f"  ✓ {name} (cached)")
            continue
        if size_mb > 20:
            print(f"  [skipped — {size_mb:.0f} MB] {name}")
            continue
        url = f"https://zenodo.org/records/{_DEAM_ZENODO}/files/{name}?download=1"
        try:
            _download(url, dest, name)
        except requests.HTTPError as e:
            print(f"\n  ⚠  Download failed ({e.response.status_code}): {name}")
            print(f"     Download manually: {url}")
            dest.unlink(missing_ok=True)  # remove partial file
            continue
        if name.endswith(".zip"):
            with zipfile.ZipFile(dest) as z:
                z.extractall(deam_dir)

    csv_path = _best_annot_csv(deam_dir)
    if csv_path is None:
        print(f"⚠  No annotation CSVs found. Download DEAM_Annotations.zip manually:")
        print(f"   https://zenodo.org/records/{_DEAM_ZENODO}")
        print(f"   Extract into {deam_dir}/ and re-run this cell.")
        return None, None, None, None

    df = pd.read_csv(csv_path)
    id_col, val_col, aro_col = _detect_columns(df)
    print(f"  loaded {csv_path.name}  ({len(df)} rows)  "
          f"id={id_col!r}  valence={val_col!r}  arousal={aro_col!r}")
    return df, id_col, val_col, aro_col


# ── EmoMusic ─────────────────────────────────────────────────────────────────

def setup_emomusic(data_dir: Path) -> tuple:
    """Load EmoMusic annotations if present; print access instructions otherwise.

    EmoMusic requires a form request at https://cvml.unige.ch/databases/emoMusic/
    Expected layout after extraction:
      <data_dir>/emomusic/clips/          — .mp3 files named by song_id
      <data_dir>/emomusic/annotations.csv — columns: <id>, valence, arousal (scale 1–9)
    """
    emo_dir = Path(data_dir) / "emomusic"
    annot = emo_dir / "annotations.csv"

    if not annot.exists():
        print("⚠  EmoMusic not found. To enable:")
        print("   1. Request at https://cvml.unige.ch/databases/emoMusic/")
        print("   2. Extract audio to  <data_dir>/emomusic/clips/  (files: <id>.mp3)")
        print("   3. Place annotations: <data_dir>/emomusic/annotations.csv")
        print("      Expected columns: <song_id>, valence, arousal  (scale 1–9)")
        return None, None, None, None

    df = pd.read_csv(annot)
    id_col, val_col, aro_col = _detect_columns(df)
    print(f"EmoMusic: {len(df)} rows  id={id_col!r}  valence={val_col!r}  arousal={aro_col!r}")
    return df, id_col, val_col, aro_col


# ── PMEmo ─────────────────────────────────────────────────────────────────────

_PMEMO_DRIVE = "https://drive.google.com/drive/folders/1qDk6hZDGVlVXgckjLq9LvXLZ9EgK9gw0"


def setup_pmemo(data_dir: Path) -> tuple:
    """Download PMEmo from Google Drive via gdown; return (df, id_col, val_col, aro_col).

    Annotation scale is 0–1 (already normalised — no conversion applied).
    Audio lives in the 'chorus' subfolder.
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
    # PMEmo uses 'musicId' as the track identifier
    id_col = next(
        (c for c in df.columns if "music" in c.lower() or c.lower() == "id"),
        df.columns[0],
    )
    _, val_col, aro_col = _detect_columns(df)
    print(f"PMEmo: {len(df)} rows  id={id_col!r}  valence={val_col!r}  arousal={aro_col!r}")
    return df, id_col, val_col, aro_col
