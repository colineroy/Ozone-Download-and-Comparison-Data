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

import requests
from pathlib import Path
from datetime import datetime, timedelta
import csv

# ── CONFIG ────────────────────────────────────────────────────
STATION = "SK"
STATION_NAME = "Sodankyla"

DATE_START = "2025-04-15"
DATE_END   = "2025-04-15"

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


def years_in_range(start, end):
    """Return sorted list of years covered by [start, end]."""
    years = set()
    d = start
    while d <= end:
        years.add(d.year)
        d += timedelta(days=1)
    return sorted(years)


def download_raw(year, station):
    """Download O3_YYYY.STATIONCODE → raw text content."""
    url = f"{BASE_URL}/O3_{year}.{station}"
    print(f"  [dl] {url}")
    resp = requests.get(url, timeout=60)
    resp.raise_for_status()
    return resp.text


def save_raw(content, year, station):
    """Save raw file to disk."""
    out = OUT_DIR / f"O3_{year}.{station}"
    out.write_text(content, encoding="utf-8")
    print(f"  [save] {out}")
    return out


def parse_data(content):
    """Parse SAOZ file → list of dicts.

    Format:
      Line 1: header (Units...)
      Line 2: column names
      Lines 3+: data (Year Month Day DoY O3sr ...)
    """
    lines = content.strip().splitlines()
    data = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        # Skip header lines
        if line.startswith("Units") or line.startswith("Year"):
            continue
        parts = line.split()
        if len(parts) < 12:
            continue
        try:
            year = int(parts[0])
            month = int(parts[1])
            day = int(parts[2])
        except ValueError:
            continue

        def f(val):
            if val in ("NaN", "nan", ""):
                return None
            try:
                return float(val)
            except ValueError:
                return None

        data.append({
            "year": year, "month": month, "day": day, "doy": int(parts[3]),
            "O3sr": f(parts[4]), "O3ss": f(parts[5]),
            "dO3sr": f(parts[6]), "dO3ss": f(parts[7]),
            "NO2sr": f(parts[8]), "NO2ss": f(parts[9]),
            "dNO2sr": f(parts[10]), "dNO2ss": f(parts[11]),
        })
    return data


def filter_by_date(data, start, end):
    """Keep rows whose date falls within [start, end]."""
    filtered = []
    for row in data:
        d = datetime(row["year"], row["month"], row["day"])
        if start <= d <= end:
            row["date"] = d
            filtered.append(row)
    return filtered


def write_csv(rows, path):
    """Write parsed data to CSV."""
    fieldnames = ["year", "month", "day", "doy",
                  "O3sr", "O3ss", "dO3sr", "dO3ss",
                  "NO2sr", "NO2ss", "dNO2sr", "dNO2ss"]
    clean = [{k: r[k] for k in fieldnames} for r in rows]
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(clean)
    print(f"  [csv]  {path}")


def summary(rows, station_name):
    """Print a summary of downloaded data."""
    n = len(rows)
    if n == 0:
        print(f"\n  No data for {station_name} in this period.")
        return

    o3_vals = []
    no2_vals = []
    for r in rows:
        if r["O3sr"] is not None:
            o3_vals.append(r["O3sr"])
        if r["NO2sr"] is not None:
            no2_vals.append(r["NO2sr"])

    print(f"\n  {station_name} — {n} day(s) with data")
    if o3_vals:
        print(f"    O3  (sr) : {min(o3_vals):.1f} – {max(o3_vals):.1f} DU  "
              f"(mean: {sum(o3_vals)/len(o3_vals):.1f})")
    if no2_vals:
        print(f"    NO2 (sr) : {min(no2_vals):.2f} – {max(no2_vals):.2f} "
              f"(mean: {sum(no2_vals)/len(no2_vals):.2f}) ×1e15 mol/cm2")


def main():
    start = datetime.strptime(DATE_START, "%Y-%m-%d")
    end = datetime.strptime(DATE_END, "%Y-%m-%d")
    years = years_in_range(start, end)
    station_name = STATIONS.get(STATION, STATION)

    print(f"=== SAOZ Download — {station_name} ({STATION}) ===\n")
    print(f"  Period: {DATE_START} -> {DATE_END}")
    print(f"  Years:  {', '.join(str(y) for y in years)}\n")

    all_rows = []
    for year in years:
        try:
            content = download_raw(year, STATION)
        except requests.RequestException as e:
            print(f"    [!] {e}")
            continue

        save_raw(content, year, STATION)
        rows = parse_data(content)
        filtered = filter_by_date(rows, start, end)
        all_rows.extend(filtered)

    station_dir = OUT_DIR / STATION
    station_dir.mkdir(parents=True, exist_ok=True)

    # Merged CSV (all years combined)
    if all_rows:
        csv_path = station_dir / f"saoz_{STATION}_{DATE_START}_{DATE_END}.csv"
        write_csv(all_rows, csv_path)

    summary(all_rows, station_name)
    print(f"\n  Done: {len(all_rows)} row(s)")


if __name__ == "__main__":
    main()
