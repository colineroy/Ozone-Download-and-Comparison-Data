"""
Brewer — EUBREWNET API download (if access granted)
=====================================================
Requires special API permissions from EUBREWNET admins.
See: https://eubrewnet.aemet.es/dokuwiki/doku.php?id=codes:dbaccess

If you don't have API access yet, download manually from:
  https://hav.fmi.fi/hav/asema/?fmisid=101932&page=obs
  → place CSV in Brewer/brewer_data/

Credentials in .env:
  EUBREWNET_USER=your_email
  EUBREWNET_PASS=your_password
"""

import os, csv
from pathlib import Path
from datetime import datetime
import requests
from dotenv import load_dotenv
load_dotenv()

# ── CONFIG ──────────────────────────────────────────────────────
DATE_START = "2026-04-01"
DATE_END   = "2026-04-30"
BREWER_IDS = [37, 214]
OUT_DIR    = Path("./Brewer/brewer_data")
OUT_DIR.mkdir(parents=True, exist_ok=True)

USER = os.getenv("EUBREWNET_USER", "")
PASS = os.getenv("EUBREWNET_PASS", "")

# Both GET and PROCESS paths — one of them should work depending on permissions
API_PATHS = [
    "https://eubrewnet.aemet.es/eubrewnet/data/get/O3L1_5",
    "https://eubrewnet.aemet.es/eubrewnet/data/process/O3L1_5",
]


def download_brewer(brewer_id: int) -> Path | None:
    """Try GET then PROCESS endpoint for one Brewer."""
    params = {
        "brewerid": brewer_id,
        "date":     DATE_START,
        "enddate":  DATE_END,
        "format":   "csv",
    }
    for url in API_PATHS:
        try:
            r = requests.get(url, params=params,
                             auth=(USER, PASS), timeout=30)
        except requests.RequestException as e:
            print(f"  [!] {e}")
            continue

        if r.status_code == 200 and len(r.content) > 100 \
                and b"html" not in r.content[:50].lower():
            out = OUT_DIR / f"eubrewnet_brewer{brewer_id:03d}_{DATE_START}_{DATE_END}.csv"
            out.write_bytes(r.content)
            lines = r.text.strip().splitlines()
            print(f"  ✓ #{brewer_id} → {out.name}  ({len(lines)-1} rows)")
            return out

        if r.status_code == 403 or "permission" in r.text.lower():
            print(f"  ✗ #{brewer_id}: no API permission — request access from eubrewnet@aemet.es")
            return None   # no point retrying other path

        # else: 404 or wrong path → try next
    return None


def to_fmi_csv(src: Path, brewer_id: int):
    """
    Convert EUBREWNET CSV (gmt, o3, ...) to the FMI format expected by
    gs_comparison.py (OBSDATE_UTC, OBSTIME_UTC, OZONE #NN (DU), ...).
    """
    lines = src.read_text().splitlines()
    if not lines:
        return

    reader = csv.DictReader(lines)
    fieldnames = reader.fieldnames or []

    # Find the o3 column (varies: 'o3', 'O3', 'ozone')
    o3_col = next((f for f in fieldnames if f.lower() == "o3"), None)
    gmt_col = next((f for f in fieldnames if "gmt" in f.lower()), None)

    if not o3_col or not gmt_col:
        print(f"  [!] Could not find o3/gmt columns in {src.name}. Columns: {fieldnames}")
        return

    out = OUT_DIR / f"st-lpnn-7501fmisid-101932-eubrewnet-{brewer_id:03d}-{DATE_START}.csv"
    col = f"OZONE #{brewer_id} (DU)"

    with open(out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["FMISID","LPNN","OBSDATE_UTC","OBSTIME_UTC", col],
                           delimiter=";")
        w.writeheader()
        for row in csv.DictReader(lines):
            try:
                dt = datetime.strptime(row[gmt_col][:16], "%Y-%m-%dT%H:%M")
                o3 = float(row[o3_col])
            except (ValueError, KeyError):
                continue
            w.writerow({
                "FMISID":       "101932",
                "LPNN":         "7501",
                "OBSDATE_UTC":  dt.strftime("%d.%m.%Y"),
                "OBSTIME_UTC":  dt.strftime("%H:%M"),
                col:            f"{o3:.1f}",
            })

    print(f"  → converted to FMI format: {out.name}")
    src.unlink()   # remove intermediate file


def main():
    print("=== Brewer EUBREWNET download ===")
    print(f"  Period : {DATE_START} → {DATE_END}")
    print(f"  Brewers: {', '.join(f'#{b}' for b in BREWER_IDS)}\n")

    if not USER:
        print("  No credentials in .env — skipping API download.")
        print("  Manual download: https://hav.fmi.fi/hav/asema/?fmisid=101932&page=obs")
        return

    for bid in BREWER_IDS:
        src = download_brewer(bid)
        if src:
            to_fmi_csv(src, bid)

    print("\nDone.")


if __name__ == "__main__":
    main()