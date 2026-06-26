"""
S5P TROPOMI — Download script for Sodankyla FMI
Downloads two products:
  - L2__O3____  : Total Column Ozone  (~100 MB/file)
  - L2__O3_PR   : Ozone vertical Profile (~150 MB/file)

Both are needed for full comparison with Brewer (total column) and
ozonesonde ECC (vertical profile).

Dependencies:
    pip install requests
"""

import os
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from pathlib import Path
from dotenv import load_dotenv
load_dotenv()

# ─────────────────────────────────────────────
# CONFIGURATION — edit this section only
# ─────────────────────────────────────────────

# Sodankyla FMI station coordinates
LAT_SITE = 67.3668
LON_SITE = 26.6297
DELTA    = 0.5        # co-location window in degrees (~50 km)

# Time period
DATE_START = "2026-04-01"
DATE_END   = "2026-04-03"   # ← start with one week !

# Products to download — comment out either line to skip it
PRODUCTS_TO_DOWNLOAD = [
    "L2__O3____",   # Total column ozone  
    "L2__O3__PR_",   # Ozone profile       
]

SCRIPT_DIR = Path(__file__).parent.resolve()
OUT_DIR = SCRIPT_DIR / "s5p_data"

DIRS = {
    "L2__O3____": OUT_DIR / "total_column",
    "L2__O3__PR_": OUT_DIR / "profile",
}
for d in DIRS.values():
    d.mkdir(parents=True, exist_ok=True)

# Copernicus Data Space credentials (from .env)
USERNAME = os.getenv("COPERNICUS_USER")
PASSWORD = os.getenv("COPERNICUS_PASS")


# ─────────────────────────────────────────────
# AUTHENTICATION
# ─────────────────────────────────────────────

def get_access_token(username: str, password: str) -> str:
    """Get OAuth2 token from Copernicus Data Space."""
    url = "https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token"
    response = requests.post(url, data={
        "client_id":  "cdse-public",
        "username":   username,
        "password":   password,
        "grant_type": "password",
    })
    if response.status_code != 200:
        print(f"Auth error {response.status_code}: {response.json()}")
        response.raise_for_status()
    print("  Authentication OK")
    return response.json()["access_token"]


# ─────────────────────────────────────────────
# SEARCH
# ─────────────────────────────────────────────

def search_products(product_type, date_start, date_end, lat, lon, delta):

    base_url = "https://catalogue.dataspace.copernicus.eu/odata/v1/Products"

    params = {
        "$filter": (
            f"Collection/Name eq 'SENTINEL-5P' "
            f"and ContentDate/Start gt {date_start}T00:00:00.000Z "
            f"and ContentDate/Start lt {date_end}T23:59:59.000Z "
            f"and OData.CSC.Intersects(area=geography'SRID=4326;POLYGON(("
            f"{lon-delta} {lat-delta},{lon+delta} {lat-delta},"
            f"{lon+delta} {lat+delta},{lon-delta} {lat+delta},"
            f"{lon-delta} {lat-delta}))')"
        ),
        "$top": 500,
        "$orderby": "ContentDate/Start asc",
    }

    session = requests.Session()
    retries = Retry(total=3, connect=3, backoff_factor=2,
                    status_forcelist=[502, 503, 504])
    session.mount("https://", HTTPAdapter(max_retries=retries))

    # pagination: follow @odata.nextLink until exhausted
    all_products = []
    url = base_url

    while url:
        response = session.get(url, params=params if url == base_url else None, timeout=30)
        response.raise_for_status()
        data = response.json()
        all_products.extend(data.get("value", []))
        url = data.get("@odata.nextLink")   # None on last page

    # actual filtering
    filtered = [
        p for p in all_products
        if product_type in p["Name"]
    ]

    print(f"  -> {len(filtered)} files found for {product_type}")
    return filtered


# ─────────────────────────────────────────────
# DOWNLOAD
# ─────────────────────────────────────────────

def download_product(product: dict, token: str, output_dir: Path) -> Path:
    """Download one granule with resume via Range requests + auto token refresh.
    Writes to a .part file; renames on success. Skip if final file exists.
    """
    name       = product["Name"]
    product_id = product["Id"]
    out_path   = output_dir / name
    part_path  = out_path.with_name(out_path.name + ".part")

    if out_path.exists():
        print(f"  [skip]  {name}")
        return out_path

    url     = f"https://download.dataspace.copernicus.eu/odata/v1/Products({product_id})/$value"
    headers = {"Authorization": f"Bearer {token}"}

    for attempt in range(2):
        resume = part_path.stat().st_size if part_path.exists() else 0

        if resume:
            headers["Range"] = f"bytes={resume}-"
            mode = "ab"
            print(f"  [resume] {name}  ({resume/1e6:.1f} MB already done)")
        else:
            headers.pop("Range", None)
            mode = "wb"
            print(f"  [dl]    {name}")

        session = requests.Session()
        retries = Retry(total=5, backoff_factor=2, status_forcelist=[502, 503, 504])
        session.mount("https://", HTTPAdapter(max_retries=retries))

        try:
            with session.get(url, headers=headers, stream=True, timeout=300) as r:
                if resume and r.status_code == 206:
                    total_size = int(r.headers.get("Content-Length", 0)) + resume
                else:
                    if resume:
                        mode = "wb"
                        resume = 0
                        print(f"  [dl]    {name}  (no Range support, starting over)")
                    total_size = int(r.headers.get("Content-Length", 0))

                if r.status_code == 401 and attempt == 0:
                    print(f"  [auth]  Token expired, refreshing...")
                    token = get_access_token(USERNAME, PASSWORD)
                    headers["Authorization"] = f"Bearer {token}"
                    continue

                r.raise_for_status()

                downloaded = resume
                with open(part_path, mode) as f:
                    for chunk in r.iter_content(chunk_size=65536):
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total_size:
                            pct = downloaded / total_size * 100
                            print(f"\r          {pct:5.1f}%  "
                                  f"({downloaded/1e6:.1f} / {total_size/1e6:.1f} MB)", end="")
                print()
            break  # success
        except requests.exceptions.HTTPError as e:
            if e.response is not None and e.response.status_code == 401 and attempt == 0:
                print(f"  [auth]  Token expired, refreshing...")
                token = get_access_token(USERNAME, PASSWORD)
                headers["Authorization"] = f"Bearer {token}"
                continue
            raise

    part_path.rename(out_path)
    return out_path


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────

def main():
    print("=== S5P TROPOMI Download — Sodankyla FMI ===\n")
    print(f"  Period   : {DATE_START} -> {DATE_END}")
    print(f"  Site     : lat={LAT_SITE}N  lon={LON_SITE}E  window=±{DELTA}°\n")

    # Authenticate once
    print("[1] Authenticating...")
    token = get_access_token(USERNAME, PASSWORD)

    total_files = 0

    for product_type in PRODUCTS_TO_DOWNLOAD:

        ptype = product_type.strip()
        print(f"\n[2] Searching for {ptype} ({'Total Column' if 'O3____' in ptype else 'Ozone Profile'})...")
        products = search_products(product_type, DATE_START, DATE_END,
                                   LAT_SITE, LON_SITE, DELTA)

        if not products:
            print(f"  No files found for {ptype} — check dates or product availability")
            continue

        n        = len(products)
        unit_mb  = 340 if "O3____" in ptype else 150
        print(f"  Estimated download: {n} files x ~{unit_mb} MB = ~{n * unit_mb} MB\n")

        out_dir = DIRS[product_type]
        print(f"  Saving to: {out_dir}\n")

        for i, prod in enumerate(products):
            print(f"  [{i+1:3d}/{n}]", end=" ")
            download_product(prod, token, out_dir)
            total_files += 1

    print(f"\n=== Done — {total_files} files downloaded (or already present) ===")
    print(f"  Total column files : {DIRS['L2__O3____']}")
    print(f"  Profile files      : {DIRS['L2__O3__PR_']}")
    print(f"\nNext steps:")
    print(f"  - Run s5p_ozone_profile.py  to plot the ozone profile (L2__O3_PR)")
    print(f"  - Run s5p_ozone_sodankyla.py to extract total column time series (L2__O3____)")


if __name__ == "__main__":
    main()