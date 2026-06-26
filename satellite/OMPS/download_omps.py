"""
OMPS (Suomi-NPP / NOAA-21) — Download ozone data for Sodankyla FMI

Products:
  - NMTO3 (Suomi-NPP) : Total column ozone
  - LP-L2-O3-DAILY (NOAA-21) : Ozone profile (limb)

Data sources:
  - NASA AVDC (pre-computed overpass text files, no auth): https://avdc.gsfc.nasa.gov
  - NOAA STAR / NASA Earthdata (full orbit HDF5 via CMR): requires Earthdata Login

Dependencies:
    pip install requests
"""

import os
from datetime import datetime, timedelta
from dotenv import load_dotenv
load_dotenv()
import requests
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.resolve()
OUT_DIR = SCRIPT_DIR / "omps_data"
OUT_DIR.mkdir(parents=True, exist_ok=True)
NOAA21_PROFILE_DIR = OUT_DIR / "noaa21_profile"

LAT_SITE = 67.3668
LON_SITE = 26.6297
DELTA    = 0.5

DATE_START = "2026-04-25"
DATE_END   = "2026-04-26"

EARTHDATA_USER = os.getenv("EARTHDATA_USER", "your_username")
EARTHDATA_PASS = os.getenv("EARTHDATA_PASS", "your_password")
EARTHDATA_TOKEN = os.getenv("EARTHDATA_TOKEN", "")

PRODUCTS = {
    "OMPS_NPP_NMTO3_L2": {
        "desc": "OMPS Suomi-NPP Total Column Ozone L2",
        "concept_id": "C1386443916-GES_DISC",
    },
}

AVDC_BASE = "https://avdc.gsfc.nasa.gov/pub/data/satellite/Suomi_NPP/L2OVP/NMTO3-L2"

AVDC_FILES = {
    "NMTO3_total_column": {
        "url": f"{AVDC_BASE}/suomi_npp_omps_l2ovp_nmto3_v2.1_sodankyla_262.txt",
        "filename": "suomi_npp_omps_l2ovp_nmto3_v2.1_sodankyla_262.txt",
    },
}

NOAA21_AVDC_BASE = "https://avdc.gsfc.nasa.gov/pub/data/satellite/NOAA21/OMPS/L2OVP/LP-L2-O3-DAILY_v1.0/Sodankyla"


def ensure_omps_avdc():
    """Download OMPS AVDC overpass text file (no auth required)."""
    print("  [AVDC] OMPS NMTO3 overpass file from NASA AVDC")
    for key, info in AVDC_FILES.items():
        out_path = OUT_DIR / info["filename"]
        if out_path.exists():
            print(f"    [skip] {info['filename']}")
            continue
        print(f"    [dl]   {info['filename']}")
        with requests.get(info["url"], stream=True, timeout=120) as r:
            r.raise_for_status()
            with open(out_path, "wb") as f:
                for chunk in r.iter_content(chunk_size=65536):
                    f.write(chunk)
    print()


def ensure_noaa21_avdc(start, end):
    """Download NOAA-21 OMPS LP-L2-O3-DAILY profile files per day."""
    print("  [AVDC] NOAA-21 OMPS LP-L2-O3-DAILY profiles from NASA AVDC")
    NOAA21_PROFILE_DIR.mkdir(parents=True, exist_ok=True)
    n = 0
    d = start
    while d <= end:
        ymd = d.strftime("%Y%m%d")
        yyyy = d.strftime("%Y")
        filename = f"noaa21_omps_lp_l2ovp_o3c_v1.0_sodankyla_{ymd}.txt"
        out_path = NOAA21_PROFILE_DIR / filename
        if out_path.exists():
            d += timedelta(days=1)
            continue
        url = f"{NOAA21_AVDC_BASE}/{yyyy}/{filename}"
        try:
            with requests.get(url, stream=True, timeout=60) as r:
                if r.status_code == 404:
                    d += timedelta(days=1)
                    continue
                r.raise_for_status()
                with open(out_path, "wb") as f:
                    for chunk in r.iter_content(chunk_size=65536):
                        f.write(chunk)
                n += 1
        except requests.RequestException:
            pass
        d += timedelta(days=1)
    if n:
        print(f"    [dl] {n} new file(s)")
    print()


def search_cmr(concept_id, start, end, lat, lon, delta):
    url = "https://cmr.earthdata.nasa.gov/search/granules.json"
    params = {
        "collection_concept_id": [concept_id],
        "temporal": f"{start}T00:00:00Z,{end}T23:59:59Z",
        "bounding_box": f"{lon-delta},{lat-delta},{lon+delta},{lat+delta}",
        "page_size": 500,
    }
    headers = {"Authorization": f"Bearer {EARTHDATA_TOKEN}"} if EARTHDATA_TOKEN else {}
    response = requests.get(url, params=params, headers=headers)
    response.raise_for_status()
    granules = response.json().get("feed", {}).get("entry", [])
    return granules


def download_granule(granule, output_dir):
    """Download one OMPS granule."""
    urls = [link["href"] for link in granule.get("links", [])
            if link.get("rel") == "http://esipfed.org/ns/fedsearch/1.1/data#" and
            (link["href"].endswith(".h5") or link["href"].endswith(".nc"))]
    if not urls:
        print(f"  [skip]  no data URL for {granule.get('title', 'unknown')}")
        return None

    url = urls[0]
    filename = url.split("/")[-1]
    out_path = output_dir / filename

    if out_path.exists():
        print(f"  [skip]  {filename}")
        return out_path

    print(f"  [dl]    {filename}")
    headers = {"Authorization": f"Bearer {EARTHDATA_TOKEN}"} if EARTHDATA_TOKEN else {}
    with requests.get(url, headers=headers, stream=True) as r:
        r.raise_for_status()
        total = int(r.headers.get("Content-Length", 0))
        downloaded = 0
        with open(out_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=65536):
                f.write(chunk)
                downloaded += len(chunk)
                if total:
                    print(f"\r          {downloaded/total*100:5.1f}%  "
                          f"({downloaded/1e6:.1f} / {total/1e6:.1f} MB)", end="")
        print()
    return out_path


def main():
    start_dt = datetime.strptime(DATE_START, "%Y-%m-%d").date()
    end_dt   = datetime.strptime(DATE_END,   "%Y-%m-%d").date()

    print("=== OMPS Download — Sodankyla FMI ===\n")
    print(f"  Period: {DATE_START} -> {DATE_END}")
    print(f"  Site:   {LAT_SITE}N  {LON_SITE}E  ±{DELTA}°\n")

    ensure_omps_avdc()
    ensure_noaa21_avdc(start_dt, end_dt)

    for key, info in PRODUCTS.items():
        if not info["concept_id"]:
            print(f"\n--- {info['desc']} ({key}) ---")
            print("  [skip] No concept ID configured")
            continue
        OUT_DIR.mkdir(parents=True, exist_ok=True)
        print(f"\n--- {info['desc']} ({key}) ---")
        granules = search_cmr(info["concept_id"], DATE_START, DATE_END, LAT_SITE, LON_SITE, DELTA)
        print(f"  -> {len(granules)} granule(s) found")
        for g in granules:
            download_granule(g, OUT_DIR)

    print(f"\n=== Done ===")


if __name__ == "__main__":
    main()
