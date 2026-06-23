"""
OMPS (Suomi-NPP / NOAA-20) — Download ozone data for Sodankyla FMI

Products:
  - NPEMVO3 (Suomi-NPP) : Ozone total column / profile
  - NMVO3  (NOAA-20)   : Ozone total column / profile

Data source: NOAA STAR / NASA Earthdata
Access: Requires NASA Earthdata Login account
  Register at: https://urs.earthdata.nasa.gov/

Dependencies:
    pip install requests
"""

import os
from dotenv import load_dotenv
load_dotenv()
import requests
from pathlib import Path

LAT_SITE = 67.3668
LON_SITE = 26.6297
DELTA    = 0.5

DATE_START = "2026-04-15"
DATE_END   = "2026-04-15"

EARTHDATA_USER = os.getenv("EARTHDATA_USER", "your_username")
EARTHDATA_PASS = os.getenv("EARTHDATA_PASS", "your_password")
EARTHDATA_TOKEN = os.getenv("EARTHDATA_TOKEN", "")

PRODUCTS = {
    "OMPS_NPP_NMTO3_L2": {
        "dir": Path("./OMPS/omps_data/snpp_total_column"),
        "desc": "OMPS Suomi-NPP Total Column Ozone L2",
        "concept_id": "C1386443916-GES_DISC",
    },
    # NOAA-20 total column O3 not found on GES DISC CMR.
    # Check NOAA STAR or CLASS for N20 OMPS O3 data.
    # "NMVO3": {
    #     "dir": Path("./omps_data/noaa20_total_column"),
    #     "desc": "OMPS NOAA-20 Total Column Ozone",
    #     "concept_id": "",
    # },
}

for d in PRODUCTS.values():
    d["dir"].mkdir(parents=True, exist_ok=True)


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
    print("=== OMPS Download — Sodankyla FMI ===\n")
    print(f"  Period: {DATE_START} -> {DATE_END}")
    print(f"  Site:   {LAT_SITE}N  {LON_SITE}E  ±{DELTA}°\n")

    for key, info in PRODUCTS.items():
        if not info["concept_id"]:
            print(f"\n--- {info['desc']} ({key}) ---")
            print("  [skip] No concept ID configured")
            continue
        info["dir"].mkdir(parents=True, exist_ok=True)
        print(f"\n--- {info['desc']} ({key}) ---")
        granules = search_cmr(info["concept_id"], DATE_START, DATE_END, LAT_SITE, LON_SITE, DELTA)
        print(f"  -> {len(granules)} granule(s) found")
        for g in granules:
            download_granule(g, info["dir"])

    print(f"\n=== Done ===")


if __name__ == "__main__":
    main()
