"""
OMI (Aura) — Download ozone data for Sodankyla FMI

Products:
  - OMDOAO3 : Total column ozone (Level 2)
  - OMPROFOZ : Ozone vertical profile (Level 2)

Data source: NASA Earthdata (https://disc.gsfc.nasa.gov/)
Access: Requires NASA Earthdata Login account
  Register at: https://urs.earthdata.nasa.gov/

Dependencies:
    pip install requests python-dateutil
"""

import os
from pathlib import Path
from datetime import datetime, timedelta

from dotenv import load_dotenv
load_dotenv()
import requests

SCRIPT_DIR = Path(__file__).parent.resolve()
OUT_DIR = SCRIPT_DIR / "omi_data"
OUT_DIR.mkdir(parents=True, exist_ok=True)

LAT_SITE = 67.3668
LON_SITE = 26.6297
DELTA    = 0.5

DATE_START = "2026-05-29"
DATE_END   = "2026-05-29"

EARTHDATA_USER = os.getenv("EARTHDATA_USER", "your_username")
EARTHDATA_PASS = os.getenv("EARTHDATA_PASS", "your_password")
EARTHDATA_TOKEN = os.getenv("EARTHDATA_TOKEN", "")

PRODUCTS = {
    "OMDOAO3": {
        "description": "OMI Total Column Ozone",
    },
    "OMPROFOZ": {
        "description": "OMI Ozone Profile",
    },
}


def search_cmr(product, start, end, lat, lon, delta):
    """Search NASA CMR for OMI granules near site."""
    url = "https://cmr.earthdata.nasa.gov/search/granules.json"
    polygon = f"{lon-delta},{lat-delta},{lon+delta},{lat-delta},{lon+delta},{lat+delta},{lon-delta},{lat+delta},{lon-delta},{lat-delta}"

    params = {
        "collection_concept_id": [],  # to be filled per product
        "temporal": f"{start}T00:00:00Z,{end}T23:59:59Z",
        "bounding_box": f"{lon-delta},{lat-delta},{lon+delta},{lat+delta}",
        "page_size": 500,
        "sort_key": "start_date",
    }

    collection_ids = {
        "OMDOAO3": "C3454342622-GES_DISC",     # v004
        "OMPROFOZ": "C3581239399-GES_DISC",    # v004
    }
    params["collection_concept_id"] = [collection_ids.get(product, "")]

    response = requests.get(url, params=params)
    response.raise_for_status()
    granules = response.json().get("feed", {}).get("entry", [])
    print(f"  -> {len(granules)} granule(s) found for {product}")
    return granules


def download_granule(granule, output_dir):
    """Download one OMI granule."""
    urls = [link["href"] for link in granule.get("links", [])
            if link.get("rel") == "http://esipfed.org/ns/fedsearch/1.1/data#"
            and (link["href"].endswith(".nc") or link["href"].endswith(".he5"))]
    if not urls:
        print(f"  [skip]  no .he5 URL for {granule.get('title', 'unknown')}")
        return None

    url = urls[0]
    filename = url.split("/")[-1]
    out_path = output_dir / filename

    if out_path.exists():
        print(f"  [skip]  {filename}")
        return out_path

    print(f"  [dl]    {filename}")
    headers = {"Authorization": f"Bearer {EARTHDATA_TOKEN}"} if EARTHDATA_TOKEN else {}
    with requests.get(url, headers=headers, auth=(EARTHDATA_USER, EARTHDATA_PASS) if not EARTHDATA_TOKEN else None, stream=True) as r:
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


AVDC_BASE = "https://avdc.gsfc.nasa.gov/pub/data/satellite/Aura/OMI/V03/L2OVP"

AVDC_FILES = {
    "OMTO3_total_column": {
        "url": f"{AVDC_BASE}/OMTO3/aura_omi_l2ovp_omto3_col4_v8.5_sodankyla_262.txt",
        "filename": "aura_omi_l2ovp_omto3_col4_v8.5_sodankyla_262.txt",
    },
    "OMDOAO3_total_column": {
        "url": f"{AVDC_BASE}/OMDOAO3/aura_omi_l2ovp_omdoao3_v03_sodankyla_262.txt",
        "filename": "aura_omi_l2ovp_omdoao3_v03_sodankyla_262.txt",
    },
    "OMO3PR_profile": {
        "url": f"{AVDC_BASE}/OMO3PR/satellite_aura_omi_l2ovp_omo3pr_sodankyla.h5",
        "filename": "satellite_aura_omi_l2ovp_omo3pr_sodankyla.h5",
    },
}


def ensure_omi_avdc():
    """Download OMI AVDC overpass text files (no auth required)."""
    print("  [AVDC] OMI overpass files from NASA AVDC")
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


def main():
    print("=== OMI (Aura) Download — Sodankyla FMI ===\n")
    print(f"  Period: {DATE_START} -> {DATE_END}")
    print(f"  Site:   {LAT_SITE}N  {LON_SITE}E  ±{DELTA}°\n")

    ensure_omi_avdc()

    for product, info in PRODUCTS.items():
        print(f"\n--- {info['description']} ({product}) ---")
        granules = search_cmr(product, DATE_START, DATE_END, LAT_SITE, LON_SITE, DELTA)
        for g in granules:
            download_granule(g, OUT_DIR)

    print(f"\n=== Done ===")


if __name__ == "__main__":
    main()
