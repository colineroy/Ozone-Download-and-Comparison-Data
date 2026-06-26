"""
GOME-2 (Metop-A, -B, -C) - Download O3 data for Sodankyla

Sources:
  1) NRT HDF5 via eumdac (EUMETSAT Data Store, last ~60 days)
  2) Archive text files via NASA AVDC (2007-present, no login required)

Credentials for NRT: .env at project root -> EUMETSAT_KEY, EUMETSAT_SECRET
Licence: accept NTO at
  https://user.eumetsat.int/resources/eumetsat-data-catalogue?q=EO:EUM:DAT:METOP:NTO
"""

import os, re
from pathlib import Path
from datetime import datetime, timedelta

import requests
import eumdac
import eumdac.collection
from dotenv import load_dotenv

SCRIPT_DIR = Path(__file__).parent.resolve()
load_dotenv(SCRIPT_DIR.parent.parent / ".env")

# -- CONFIG -----------------------------------------------------------------
EUMETSAT_KEY    = os.getenv("EUMETSAT_KEY",    "your_key")
EUMETSAT_SECRET = os.getenv("EUMETSAT_SECRET", "your_secret")

DATE_START = "2022-06-13"
DATE_END   = "2023-06-14"

LAT   = 67.37
LON   = 26.63
DELTA = 0.5

COLLECTION_ID = "EO:EUM:DAT:METOP:NTO"
OUT_DIR = SCRIPT_DIR / "GOME2_data"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# -- AVDC (NASA archive) ----------------------------------------------------
AVDC_BASE_URL = "https://avdc.gsfc.nasa.gov/pub/data/satellite/MetOp/GOME2/V03/L2OVP"
AVDC_DIR = SCRIPT_DIR / "GOME2_avdc"

AVDC_FILES = {
    "GOME2A": "GOME2A/gome2a_l2ovp_sodankyla.txt",
    "GOME2B": "GOME2B/gome2b_l2ovp_sodankyla.txt",
    "GOME2C": "GOME2C/gome2c_l2ovp_sodankyla.txt",
}


# -- BBOX PATCH -------------------------------------------------------------

def apply_bbox_patch():
    """Fix eumdac bug: converts bbox tuple to '(W, S, E, N)' with spaces."""
    original_get = requests.Session.get

    def patched_get(self, url, **kwargs):
        params = kwargs.get("params", {})
        if isinstance(params, dict) and "bbox" in params:
            raw = params["bbox"]
            if isinstance(raw, (tuple, list)) and len(raw) == 4:
                params["bbox"] = ",".join(f"{v:.4f}" for v in raw)
            elif isinstance(raw, str):
                params["bbox"] = re.sub(r"[() ]", "", raw)
            kwargs["params"] = params
        return original_get(self, url, **kwargs)

    requests.Session.get = patched_get
    print("  [patch] bbox fix applied")


# -- AUTH -------------------------------------------------------------------

def connect():
    token = eumdac.AccessToken(credentials=(EUMETSAT_KEY, EUMETSAT_SECRET))
    print(f"  Token expires: {token.expiration}")
    return eumdac.DataStore(token)


# -- SEARCH -----------------------------------------------------------------

def search_products(datastore, start: datetime, end: datetime) -> list:
    collection = datastore.get_collection(COLLECTION_ID)
    bbox = (LON - DELTA, LAT - DELTA, LON + DELTA, LAT + DELTA)
    print(f"  bbox: {bbox}")
    products = list(collection.search(dtstart=start, dtend=end, bbox=bbox))
    print(f"  Found {len(products)} product(s)")
    return products


# -- DOWNLOAD ---------------------------------------------------------------

def download_product(product, out_dir: Path) -> Path | None:
    try:
        entries = list(product.entries)
    except Exception as e:
        print(f"  [!] Could not list entries: {e}")
        return None

    hdf5_entries = [e for e in entries if e.upper().endswith(".HDF5")]
    if not hdf5_entries:
        print(f"  [skip] No HDF5 - entries: {entries[:5]}")
        return None

    fname    = hdf5_entries[0]
    out_path = out_dir / fname

    if out_path.exists():
        print(f"  [cache] {fname[:60]}")
        return out_path

    print(f"  [dl]   {fname[:60]}")
    try:
        with product.open(entry=fname) as src, open(out_path, "wb") as dst:
            done = 0
            while True:
                chunk = src.read(131072)
                if not chunk:
                    break
                dst.write(chunk)
                done += len(chunk)
                print(f"\r         {done/1e6:.1f} MB", end="", flush=True)
        print(f"\r  OK {fname[:55]}  ({out_path.stat().st_size/1e6:.1f} MB)")
        return out_path
    except Exception as e:
        print(f"\n  FAIL {e}")
        if out_path.exists():
            out_path.unlink()
        return None


# -- AVDC DOWNLOAD ----------------------------------------------------------

def ensure_avdc():
    """Download AVDC overpass text files if not cached."""
    AVDC_DIR.mkdir(parents=True, exist_ok=True)
    count = 0
    for sat, relpath in AVDC_FILES.items():
        fname = Path(relpath).name
        out_path = AVDC_DIR / fname
        if out_path.exists():
            print(f"  [cache] {fname}")
            continue
        url = f"{AVDC_BASE_URL}/{relpath}"
        print(f"  [dl]   {fname} ({sat})")
        try:
            r = requests.get(url, timeout=300)
            r.raise_for_status()
            out_path.write_bytes(r.content)
            size_mb = len(r.content) / 1e6
            print(f"          {size_mb:.1f} MB")
            count += 1
        except Exception as e:
            print(f"  FAIL {fname}: {e}")
    return count


# -- MAIN -------------------------------------------------------------------

def main_nrt():
    """Download NRT HDF5 files via eumdac."""
    print("-- NRT (EUMETSAT Data Store) --")
    if EUMETSAT_KEY == "your_key":
        print("  [!] Set EUMETSAT_KEY and EUMETSAT_SECRET in .env")
        return

    apply_bbox_patch()

    start = datetime.strptime(DATE_START, "%Y-%m-%d")
    end   = datetime.strptime(DATE_END,   "%Y-%m-%d")

    print("  Connect...")
    try:
        datastore = connect()
    except Exception as e:
        print(f"  FAIL {e}")
        return

    print(f"  Search {COLLECTION_ID}...")
    try:
        products = search_products(datastore, start, end)
    except Exception as e:
        print(f"  FAIL {e}")
        return

    if not products:
        print("  No NRT products found.")
        return

    print(f"  Download {len(products)} file(s)...")
    for prod in products:
        download_product(prod, OUT_DIR)

    cached = [p for p in sorted(OUT_DIR.glob("*.HDF5"))]
    print(f"  HDF5 files on disk: {len(cached)}")


def main():
    print("=" * 60)
    print("  GOME-2 Download - Sodankyla")
    print("=" * 60)
    print(f"\n  Period : {DATE_START}  ->  {DATE_END}")
    print(f"  Site   : {LAT}N  {LON}E  +/-{DELTA} deg\n")

    main_nrt()

    print(f"\n-- AVDC (NASA archive) --")
    ensure_avdc()

    print(f"\n{'='*60}\n  Done.")


if __name__ == "__main__":
    main()