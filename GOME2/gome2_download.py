"""
GOME-2 (MetOp-B + MetOp-C) — Download script for Sodankyla FMI
Downloads Near Real-Time Total Column products from EUMETSAT Data Store.

Collection: EO:EUM:DAT:METOP:NTO
Products: O3, NO2, NO2Tropo, SO2 total columns (HDF5 format)
Ozone already in DU (Dobson Units).

Dependencies:
    pip install eumdac
"""

import os
from pathlib import Path
from datetime import datetime, date
from dotenv import load_dotenv
load_dotenv()
import eumdac

# ─────────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────────

LAT_SITE = 67.3668
LON_SITE = 26.6297

DATE_START = "2026-04-10"
DATE_END   = "2026-04-16"

COLLECTION_ID = "EO:EUM:DAT:METOP:NTO"

# EUMETSAT Data Store credentials (from .env)
CONSUMER_KEY    = os.getenv("EUMETSAT_KEY")
CONSUMER_SECRET = os.getenv("EUMETSAT_SECRET")

OUT_DIR = Path("./GOME2/GOME2_data")
OUT_DIR.mkdir(parents=True, exist_ok=True)


# ─────────────────────────────────────────────
# DOWNLOAD
# ─────────────────────────────────────────────

def download_for_day(collection, day: date, platform: str):
    day_str = day.strftime("%Y-%m-%d")
    print(f"  [{platform}] {day_str}...", end=" ")

    products = collection.search(
        dtstart=day,
        dtend=day,
        platform=platform,
    )

    count = 0
    for prod in products:
        fname = prod.properties["Name"]
        if not fname.endswith(".HDF5"):
            continue
        out_path = OUT_DIR / fname
        if out_path.exists():
            continue

        try:
            with prod.open() as fsrc:
                with open(out_path, "wb") as fdst:
                    while True:
                        chunk = fsrc.read(65536)
                        if not chunk:
                            break
                        fdst.write(chunk)
            count += 1
            print(f"dl {fname}", end="; ")
        except Exception as e:
            print(f"ERR {fname}: {e}", end="; ")

    if count == 0:
        print("(no new files)")
    else:
        print()


def main():
    print("=== GOME-2 Download — Sodankyla FMI ===\n")
    print(f"  Collection: {COLLECTION_ID}")
    print(f"  Period    : {DATE_START} -> {DATE_END}\n")

    start = datetime.strptime(DATE_START, "%Y-%m-%d").date()
    end   = datetime.strptime(DATE_END,   "%Y-%m-%d").date()

    if not CONSUMER_KEY or not CONSUMER_SECRET:
        print("[!] Set CONSUMER_KEY and CONSUMER_SECRET in the script")
        return

    print("[1] Authenticating...")
    token = eumdac.AccessToken(CONSUMER_KEY, CONSUMER_SECRET)
    datastore = eumdac.DataStore(token)
    collection = datastore.get_collection(COLLECTION_ID)
    print("  OK\n")

    platforms = ["MetOp-B", "MetOp-C"]
    d = start
    while d <= end:
        for plat in platforms:
            download_for_day(collection, d, plat)
        d += timedelta(days=1)

    print(f"\nDone — files saved to {OUT_DIR}")


if __name__ == "__main__":
    from datetime import timedelta
    main()
