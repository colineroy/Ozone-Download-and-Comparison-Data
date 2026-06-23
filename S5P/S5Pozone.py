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
DATE_START = "2026-04-15"
DATE_END   = "2026-04-15"   # ← start with one week !

# Products to download — comment out either line to skip it
PRODUCTS_TO_DOWNLOAD = [
    "L2__O3____",   # Total column ozone  
    "L2__O3__PR_",   # Ozone profile       
]

# Download folders (created automatically)
DIRS = {
    "L2__O3____": Path("./s5p_data/total_column"),
    "L2__O3__PR_": Path("./s5p_data/profile"),
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

    url = "https://catalogue.dataspace.copernicus.eu/odata/v1/Products"

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
    }

    response = requests.get(url, params=params)
    response.raise_for_status()

    all_products = response.json().get("value", [])

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
    """Download one granule with progress bar. Skip if already present."""
    name       = product["Name"]
    product_id = product["Id"]
    out_path   = output_dir / name

    if out_path.exists():
        print(f"  [skip]  {name}")
        return out_path

    url     = f"https://download.dataspace.copernicus.eu/odata/v1/Products({product_id})/$value"
    headers = {"Authorization": f"Bearer {token}"}

    print(f"  [dl]    {name}")
    with requests.get(url, headers=headers, stream=True) as r:
        r.raise_for_status()
        total      = int(r.headers.get("Content-Length", 0))
        downloaded = 0
        with open(out_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=65536):
                f.write(chunk)
                downloaded += len(chunk)
                if total:
                    pct = downloaded / total * 100
                    print(f"\r          {pct:5.1f}%  "
                          f"({downloaded/1e6:.1f} / {total/1e6:.1f} MB)", end="")
        print()

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
        size_est = n * (100 if "O3____" in ptype else 150)
        print(f"  Estimated download: {n} files x ~{size_est//n} MB = ~{size_est} MB\n")

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