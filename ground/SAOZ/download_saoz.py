"""
SAOZ — Download O3 + NO2 data for Sodankyla (or any other station)

Site: http://saoz.obs.uvsq.fr/ReseauSAOZ-UK.html
Data: http://saoz.obs.uvsq.fr/saoz/O3_YYYY.STATIONCODE

Available station codes:
  SK=Sodankyla, NY=Ny-Alesund, SC=Scoresby-Sund, EU=Eureka,
  SS=Kangerlussuaq, OH=OHP, RE=Reunion, KR=Kerguelen,
  RG=Rio Gallegos, DD=Dumont d'Urville, DO=Dome C/Concordia,
  PA=Paris, GU=Guyancourt

Raw file contains both O3 and NO2 columns:
  Year Month Day DoY O3sr O3ss dO3sr dO3ss NO2sr NO2ss dNO2sr dNO2ss
"""

import csv
import requests
from pathlib import Path

# ── CONFIG ────────────────────────────────────────────────────
STATION = "SK"
STATION_NAME = "Sodankyla"

YEAR = 2021

OUT_DIR = Path("./saoz_data")
OUT_DIR.mkdir(parents=True, exist_ok=True)

BASE_URL = "http://saoz.obs.uvsq.fr/saoz"

# Station code -> display name
STATIONS = {
    "SK": "Sodankyla", "NY": "Ny-Alesund", "SC": "Scoresby-Sund",
    "EU": "Eureka", "SS": "Kangerlussuaq", "OH": "OHP",
    "RE": "Reunion", "KR": "Kerguelen", "RG": "Rio Gallegos",
    "DD": "Dumont d'Urville", "DO": "Dome C", "PA": "Paris",
    "GU": "Guyancourt",
}


def download_raw(year, station):
    url = f"{BASE_URL}/O3_{year}.{station}"
    print(f"  [dl] {url}")
    resp = requests.get(url, timeout=60)
    resp.raise_for_status()
    return resp.text


def save_raw(content, year, station):
    out = OUT_DIR / f"O3_{year}.{station}"
    out.write_text(content, encoding="utf-8")
    print(f"  [save] {out}")
    return out


def parse_raw(content):
    rows = []
    for line in content.strip().splitlines():
        line = line.strip()
        if not line or line.startswith("Units") or line.startswith("Year"):
            continue
        parts = line.split()
        if len(parts) < 12:
            continue
        try:
            year, month, day = int(parts[0]), int(parts[1]), int(parts[2])
        except ValueError:
            continue

        def f(v):
            if v in ("NaN", "nan", ""):
                return None
            try:
                return float(v)
            except ValueError:
                return None

        rows.append({
            "year": year, "month": month, "day": day, "doy": int(parts[3]),
            "O3sr": f(parts[4]), "O3ss": f(parts[5]),
            "dO3sr": f(parts[6]), "dO3ss": f(parts[7]),
            "NO2sr": f(parts[8]), "NO2ss": f(parts[9]),
            "dNO2sr": f(parts[10]), "dNO2ss": f(parts[11]),
        })
    return rows


def write_csv(rows, path):
    fieldnames = ["year", "month", "day", "doy",
                  "O3sr", "O3ss", "dO3sr", "dO3ss",
                  "NO2sr", "NO2ss", "dNO2sr", "dNO2ss"]
    clean = [{k: r[k] for k in fieldnames} for r in rows]
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(clean)
    print(f"  [csv]  {path} ({len(rows)} rows)")


def main():
    station_name = STATIONS.get(STATION, STATION)
    print(f"=== SAOZ Download — {station_name} ({STATION}) ===\n")
    print(f"  Year: {YEAR}\n")

    try:
        content = download_raw(YEAR, STATION)
    except requests.RequestException as e:
        print(f"  [!] {e}")
        return

    save_raw(content, YEAR, STATION)

    rows = parse_raw(content)
    if rows:
        csv_dir = OUT_DIR / "csvSAOZ"
        csv_path = csv_dir / f"saoz_{STATION}_{YEAR}.csv"
        write_csv(rows, csv_path)

    print(f"\n  Done: {len(rows)} day(s)")


if __name__ == "__main__":
    main()
