"""
PGN Pandonia — Download ozone total column data for a date range.

API: https://api.pandonia-global-network.org/v1
Docs: https://www.pandonia-global-network.org/services/api/
"""

import requests
from datetime import datetime, timedelta
from pathlib import Path

# ── CONFIG ────────────────────────────────────────────────────
SITE = "Sodankyla"
PAN_ID = 309
SPECTROMETER = "1"
LEVEL = "L2"
CODE = "rout2"
DATE_START = "2026-04-20"
DATE_END   = "2026-04-20"

OUT_DIR = Path("./pandora_data")
OUT_DIR.mkdir(parents=True, exist_ok=True)

BASE = "https://api.pandonia-global-network.org/v1"


def date_range(start, end):
    """Yield each date in [start, end]."""
    d = start
    while d <= end:
        yield d
        d += timedelta(days=1)


def main():
    start_dt = datetime.strptime(DATE_START, "%Y-%m-%d")
    end_dt   = datetime.strptime(DATE_END,   "%Y-%m-%d")

    print(f"=== Pandonia Download — {SITE} ===\n")
    print(f"  Period: {DATE_START} -> {DATE_END}\n")

    count = 0
    for date in date_range(start_dt, end_dt):
        day = date.strftime("%Y-%m-%d")
        start = f"{day}T00:00:00"
        end   = f"{day}T23:59:59"

        url = f"{BASE}/files/{SITE}/{PAN_ID}/{SPECTROMETER}/{LEVEL}?start={start}&end={end}&code={CODE}"
        print(f"  [{day}]")
        resp = requests.get(url)
        resp.raise_for_status()
        files = resp.json()

        if not files:
            print(f"      No {CODE} files found")
            continue

        for f in files:
            filename = f["filename"]
            print(f"      {filename} ({f['size']} bytes)")
            dl_url = f"{BASE}/download/{filename}"
            resp = requests.get(dl_url)
            resp.raise_for_status()
            content = resp.text

            local_path = OUT_DIR / f"pandonia_{SITE}_{day}_L2_{CODE}.txt"
            local_path.write_text(content, encoding="utf-8")
            print(f"      Saved -> {local_path.name}")
            count += 1

    print(f"\n  Done: {count} file(s) downloaded")


if __name__ == "__main__":
    main()
