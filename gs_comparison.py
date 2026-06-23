"""
Ground-based + Satellite ozone comparison at Sodankyla:
  SAOZ, Pandora, BTS, Ozonesondes, Brewer, S5P TROPOMI

Auto-download SAOZ/Pandora/S5P data if not cached.
All units -> DU. Axe x = datetime continu (raw measurements).
"""

from pathlib import Path
from datetime import datetime, date, timedelta
import re
import csv

import os
from dotenv import load_dotenv
load_dotenv()

import requests
from requests.exceptions import RequestException

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np


# -- CONFIG -----------------------------------------------------

DATE_START = "2026-04-15"
DATE_END   = "2026-04-15"

DOWNLOAD = {
    "SAOZ":    True,
    "Pandora": True,
    "S5P":     False,  # disabled — 330 MB each, slow
    "GOME2":   False,  # disabled — many files, slow; using cached data
    "Brewer":  False,
}

# Paths
SAOZ_RAW_DIR  = Path("./SAOZ/saoz_data")
SAOZ_CSV_DIR  = SAOZ_RAW_DIR / "SK"
PANDORA_DIR   = Path("./Pandora/pandora_data")
BTS_DIR       = Path("./BTS/BTS_data")
SONDE_DIR     = Path("./sondes")
BREWER_DIR    = Path("./Brewer/brewer_data")
S5P_DIR       = Path("./S5P/s5p_data/total_column")
GOME2_DIR     = Path("./GOME2/GOME2_data")
OMI_OMTO3_FILE  = Path("./OMI/omi_data/aura_omi_l2ovp_omto3_col4_v8.5_sodankyla_262 (1).txt")
OMPS_NMTO3_FILE = Path("./OMPS/omps_data/suomi_npp_omps_l2ovp_nmto3_v2.1_sodankyla_262.txt")

# SAOZ
SAOZ_STATION  = "SK"
SAOZ_BASE_URL = "http://saoz.obs.uvsq.fr/saoz"

# Pandora
PANDORA_SITE    = "Sodankyla"
PANDORA_PAN_ID  = 309
PANDORA_SPECTRO = "1"
PANDORA_LEVEL   = "L2"
PANDORA_CODE    = "rout2"

# S5P TROPOMI
COPERNICUS_USER = os.getenv("COPERNICUS_USER")
COPERNICUS_PASS = os.getenv("COPERNICUS_PASS")
S5P_LAT     = 67.3668
S5P_LON     = 26.6297
S5P_RADIUS  = 0.5
S5P_QA_MIN  = 0.5

# GOME-2 (EUMETSAT Data Store)
EUMETSAT_KEY    = os.getenv("EUMETSAT_KEY")
EUMETSAT_SECRET = os.getenv("EUMETSAT_SECRET")
GOME2_COLLECTION = "EO:EUM:DAT:METOP:NTO"

# Brewer
EUBREWNET_USER = os.getenv("EUBREWNET_USER", "your_username")
EUBREWNET_PASS = os.getenv("EUBREWNET_PASS", "your_password")

# Conversion
MOL2DU = 2241

STYLES = {
    "SAOZ":    {"color": "#1f77b4", "marker": "s", "label": "SAOZ"},
    "Pandora": {"color": "#ff7f0e", "marker": "o", "label": "Pandora"},
    "BTS":     {"color": "#2ca02c", "marker": "^", "label": "BTS"},
    "Sonde":   {"color": "#d62728", "marker": "D", "label": "Ozonesonde"},
    "Brewer037": {"color": "#9467bd", "marker": "v", "label": "Brewer #037"},
    "Brewer214": {"color": "#e6ab02", "marker": "^", "label": "Brewer #214"},
    "S5P":     {"color": "#17becf", "marker": ".", "label": "S5P TROPOMI"},
    "GOME2B":  {"color": "#e377c2", "marker": ".", "label": "GOME-2B (MetOp-B)"},
    "GOME2C":  {"color": "#8c564b", "marker": ".", "label": "GOME-2C (MetOp-C)"},
    "OMI":     {"color": "#a03a3a", "marker": "s", "label": "OMI (OMTO3)"},
    "OMPS":    {"color": "#7b2d8e", "marker": "D", "label": "OMPS (NMTO3)"},
}

# Approximate sunrise/sunset hours for Sodankyla (67°N)
SUNRISE_TABLE = {
    1: (9, 14), 2: (7, 16), 3: (5, 18), 4: (4, 19),
    5: (2, 21), 6: (1, 23), 7: (0, 0),  8: (2, 21),
    9: (4, 19), 10: (6, 17), 11: (8, 14), 12: (10, 12),
}


# -- HELPERS ----------------------------------------------------

def _sunrise_sunset_hour(d):
    return SUNRISE_TABLE.get(d.month, (6, 18))


def date_range(start, end):
    d = start
    while d <= end:
        yield d
        d += timedelta(days=1)


def parse_saoz_raw(content):
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


def write_saoz_csv(rows, path):
    fieldnames = ["year", "month", "day", "doy",
                  "O3sr", "O3ss", "dO3sr", "dO3ss",
                  "NO2sr", "NO2ss", "dNO2sr", "dNO2ss"]
    clean = [{k: r[k] for k in fieldnames} for r in rows]
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(clean)


def _parse_sonde_header(fpath):
    lines = fpath.read_text(encoding="latin-1").splitlines()
    launch_date = None
    if len(lines) >= 7:
        parts = lines[6].strip().split()
        if len(parts) >= 3:
            try:
                launch_date = date(int(parts[0]), int(parts[1]), int(parts[2]))
            except ValueError:
                pass
    if launch_date is None:
        m = re.search(r"(\d{2})(\d{2})(\d{2})\.", fpath.name)
        if m:
            yy, mm, dd = int(m.group(1)), int(m.group(2)), int(m.group(3))
            launch_date = date(2000 + yy, mm, dd)

    launch_hour = None
    col1 = None
    for i, line in enumerate(lines):
        if line.strip() == "Sodankyla":
            if i + 1 < len(lines):
                parts1 = lines[i + 1].strip().split()
                if len(parts1) > 1:
                    try:
                        launch_hour = float(parts1[1])
                    except ValueError:
                        pass
            if i + 2 < len(lines):
                parts2 = lines[i + 2].strip().split()
                if len(parts2) > 10:
                    try:
                        col1 = float(parts2[10])
                    except (ValueError, IndexError):
                        pass
            break
    if launch_date is not None and col1 is not None:
        return launch_date, launch_hour, col1
    return None


# -- PHASE 1: DOWNLOAD ------------------------------------------

def ensure_saoz(start, end):
    years = set()
    d = start
    while d <= end:
        years.add(d.year)
        d += timedelta(days=1)
    SAOZ_RAW_DIR.mkdir(parents=True, exist_ok=True)
    SAOZ_CSV_DIR.mkdir(parents=True, exist_ok=True)

    ok = True
    for year in sorted(years):
        raw_path = SAOZ_RAW_DIR / f"O3_{year}.{SAOZ_STATION}"
        csv_path = SAOZ_CSV_DIR / f"saoz_{SAOZ_STATION}_{year}.csv"

        if csv_path.exists():
            continue

        if not raw_path.exists():
            url = f"{SAOZ_BASE_URL}/O3_{year}.{SAOZ_STATION}"
            try:
                resp = requests.get(url, timeout=60)
                resp.raise_for_status()
                raw_path.write_text(resp.text, encoding="utf-8")
                print(f"    [dl] SAOZ {year} -> {raw_path.name}")
            except RequestException as e:
                print(f"    [!] SAOZ {year}: {e}")
                ok = False
                continue

        content = raw_path.read_text(encoding="utf-8")
        rows = parse_saoz_raw(content)
        if rows:
            write_saoz_csv(rows, csv_path)
            print(f"    [csv] SAOZ {year} -> {csv_path.name} ({len(rows)} rows)")
    return ok


def ensure_pandora(start, end):
    PANDORA_DIR.mkdir(parents=True, exist_ok=True)
    api_base = "https://api.pandonia-global-network.org/v1"
    count = 0
    for dt_day in date_range(start, end):
        day = dt_day.strftime("%Y-%m-%d")
        local_path = PANDORA_DIR / f"pandonia_{PANDORA_SITE}_{day}_L2_{PANDORA_CODE}.txt"
        if local_path.exists():
            continue
        api_start = f"{day}T00:00:00"
        api_end   = f"{day}T23:59:59"
        url = (f"{api_base}/files/{PANDORA_SITE}/{PANDORA_PAN_ID}/{PANDORA_SPECTRO}"
               f"/{PANDORA_LEVEL}?start={api_start}&end={api_end}&code={PANDORA_CODE}")
        try:
            resp = requests.get(url, timeout=30)
            resp.raise_for_status()
            files = resp.json()
        except RequestException as e:
            print(f"    [!] Pandora {day}: {e}")
            continue
        if not files:
            continue
        for f in files:
            dl_url = f"{api_base}/download/{f['filename']}"
            try:
                resp = requests.get(dl_url, timeout=60)
                resp.raise_for_status()
                local_path.write_text(resp.text, encoding="utf-8")
                print(f"    [dl] Pandora {day} -> {local_path.name} ({f['size']} bytes)")
                count += 1
            except RequestException as e:
                print(f"    [!] Pandora {day}: {e}")
    return count > 0


def ensure_s5p(start, end):
    """Download S5P TROPOMI total column O3 for date range if not cached."""
    if COPERNICUS_USER == "your_username" or COPERNICUS_PASS == "your_password":
        print("    [!] S5P: Copernicus credentials not configured")
        return False

    S5P_DIR.mkdir(parents=True, exist_ok=True)
    token = _copernicus_auth()
    if token is None:
        return False

    products = _copernicus_search("L2__O3____", start, end, token)
    if not products:
        return False

    new_files = []
    cached = 0
    for prod in products:
        if (S5P_DIR / prod["Name"]).exists():
            cached += 1
        else:
            new_files.append(prod)

    if cached > 0:
        print(f"    [cache] {cached} file(s) already present")

    if not new_files:
        return True

    total_mb = sum(f.get("ContentLength", 330e6) for f in new_files) / 1e6
    print(f"    [info] {len(new_files)} file(s) to download (~{total_mb:.0f} MB)")

    count = 0
    for prod in new_files:
        _copernicus_download(prod, token, S5P_DIR)
        count += 1
    return count > 0


def _copernicus_auth():
    url = "https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token"
    try:
        resp = requests.post(url, data={
            "client_id": "cdse-public",
            "username": COPERNICUS_USER,
            "password": COPERNICUS_PASS,
            "grant_type": "password",
        }, timeout=30)
        resp.raise_for_status()
        token = resp.json()["access_token"]
        print("    [auth] Copernicus OK")
        return token
    except RequestException as e:
        print(f"    [!] Copernicus auth failed: {e}")
        return None


def _copernicus_search(product_type, start, end, token):
    url = "https://catalogue.dataspace.copernicus.eu/odata/v1/Products"
    boxes = _split_date_range(start, end)

    all_products = []
    s_start, s_end = start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d")
    delta_lon = S5P_RADIUS / max(1, abs(np.cos(np.radians(S5P_LAT))))
    params = {
        "$filter": (
            f"Collection/Name eq 'SENTINEL-5P' "
            f"and ContentDate/Start gt {s_start}T00:00:00.000Z "
            f"and ContentDate/Start lt {s_end}T23:59:59.000Z "
            f"and OData.CSC.Intersects(area=geography'SRID=4326;POLYGON(({S5P_LON - delta_lon} {S5P_LAT - S5P_RADIUS},{S5P_LON + delta_lon} {S5P_LAT - S5P_RADIUS},{S5P_LON + delta_lon} {S5P_LAT + S5P_RADIUS},{S5P_LON - delta_lon} {S5P_LAT + S5P_RADIUS},{S5P_LON - delta_lon} {S5P_LAT - S5P_RADIUS}))')"
        ),
        "$top": 500,
    }
    try:
        resp = requests.get(url, params=params, timeout=60)
        resp.raise_for_status()
        all_products = resp.json().get("value", [])
    except RequestException as e:
        print(f"    [!] Copernicus search: {e}")
        return []

    filtered = [p for p in all_products if product_type in p["Name"]]
    print(f"    [search] {len(filtered)} S5P {product_type} files found")
    return filtered


def _split_date_range(start, end):
    """Split date range into monthly chunks to avoid OData query limits."""
    chunks = []
    d = start
    while d <= end:
        month_end = date(d.year, d.month, 1)
        if d.month == 12:
            month_end = date(d.year + 1, 1, 1) - timedelta(days=1)
        else:
            month_end = date(d.year, d.month + 1, 1) - timedelta(days=1)
        chunk_end = min(month_end, end)
        chunks.append((d, chunk_end))
        d = chunk_end + timedelta(days=1)
    return chunks


def _copernicus_download(product, token, out_dir):
    name = product["Name"]
    pid  = product["Id"]
    out  = out_dir / name
    if not out_dir.exists():
        out_dir.mkdir(parents=True, exist_ok=True)

    url = f"https://download.dataspace.copernicus.eu/odata/v1/Products({pid})/$value"
    headers = {"Authorization": f"Bearer {token}"}

    print(f"    [dl] {name}")
    try:
        with requests.get(url, headers=headers, stream=True, timeout=600) as r:
            r.raise_for_status()
            total = int(r.headers.get("Content-Length", 0))
            downloaded = 0
            with open(out, "wb") as f:
                for chunk in r.iter_content(chunk_size=65536):
                    f.write(chunk)
                    downloaded += len(chunk)
                    if total:
                        pct = downloaded / total * 100
                        print(f"\r          {pct:5.1f}%  "
                              f"({downloaded/1e6:.1f}/{total/1e6:.1f} MB)", end="")
            print()
    except RequestException as e:
        print(f"    [!] S5P download failed: {e}")
        if out.exists():
            out.unlink()


def ensure_gome2(start, end):
    if not EUMETSAT_KEY or not EUMETSAT_SECRET:
        print("    [!] GOME2: EUMETSAT credentials not configured")
        return False

    try:
        import eumdac
    except ImportError:
        print("    [!] GOME2: eumdac not installed (pip install eumdac)")
        return False

    GOME2_DIR.mkdir(parents=True, exist_ok=True)
    token = eumdac.AccessToken((EUMETSAT_KEY, EUMETSAT_SECRET))
    datastore = eumdac.DataStore(token)
    collection = datastore.get_collection(GOME2_COLLECTION)

    count = 0
    for dt_day in date_range(start, end):
        for plat in ("Metop-B", "Metop-C"):
            products = collection.search(
                dtstart=dt_day,
                dtend=dt_day,
                sat=plat,
            )
            for prod in products:
                hdf5 = [e for e in prod.entries if e.endswith(".HDF5")]
                if not hdf5:
                    continue
                fname = hdf5[0]
                out_path = GOME2_DIR / fname
                if out_path.exists():
                    continue
                try:
                    with prod.open(entry=fname) as fsrc:
                        with open(out_path, "wb") as fdst:
                            while True:
                                chunk = fsrc.read(65536)
                                if not chunk:
                                    break
                                fdst.write(chunk)
                    count += 1
                    print(f"    [dl] GOME2 {plat} {dt_day} -> {fname}")
                except Exception as e:
                    print(f"    [!] GOME2 {fname}: {e}")
    return count > 0


def ensure_brewer(start, end):
    from bs4 import BeautifulSoup

    if EUBREWNET_USER == "your_username" or EUBREWNET_PASS == "your_password":
        print("    [!] Brewer: credentials not configured "
              "(edit EUBREWNET_USER/PASS in CONFIG)")
        return False

    BREWER_DIR.mkdir(parents=True, exist_ok=True)
    base = "https://eubrewnet.aemet.es/eubrewnet"
    station_id = 18
    brewer_ids = ["037", "214"]

    session = requests.Session()
    session.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                                          "AppleWebKit/537.36"})

    login_url = f"{base}/default/user/login"
    try:
        resp = session.get(login_url, timeout=30)
        resp.raise_for_status()
    except RequestException as e:
        print(f"    [!] Brewer login page: {e}")
        return False

    soup = BeautifulSoup(resp.text, "lxml")
    fk = soup.find("input", {"name": "_formkey"})
    if not fk:
        print("    [!] Brewer: CSRF token not found")
        return False

    data = {
        "username": EUBREWNET_USER, "password": EUBREWNET_PASS,
        "remember_me": "on", "_next": f"{base}/default/index",
        "_formkey": fk["value"], "_formname": "login",
    }
    try:
        resp = session.post(login_url, data=data, timeout=30)
        resp.raise_for_status()
    except RequestException as e:
        print(f"    [!] Brewer login: {e}")
        return False

    if "Log in" in resp.text and "Invalid" in resp.text:
        print("    [!] Brewer: login failed (check credentials)")
        return False

    count = 0
    for dt_day in date_range(start, end):
        page_url = (f"{base}/station/view/{station_id}"
                    f"/{dt_day.year}/{dt_day.month:02d}/{dt_day.day:02d}"
                    f"?level=1.5&product=ozone")
        try:
            resp = session.get(page_url, timeout=30)
            resp.raise_for_status()
        except RequestException as e:
            continue

        soup = BeautifulSoup(resp.text, "lxml")
        links = []
        for a in soup.find_all("a", href=True):
            h = a["href"]
            if any(h.endswith(f".{bid}") for bid in brewer_ids) or h.endswith(".txt") or h.endswith(".csv"):
                links.append(h)
            if "/default/download/" in h:
                links.append(h)
        links = list(set(links))

        day_str = dt_day.strftime("%Y-%m-%d")
        for link in links:
            if link.startswith("/"):
                link = f"{base}{link}"
            elif not link.startswith("http"):
                link = f"{base}/{link}"
            fname = link.split("/")[-1].split("?")[0]
            if not fname:
                fname = f"brewer_{dt_day.strftime('%Y%m%d')}.dat"
            out = BREWER_DIR / fname
            if out.exists():
                continue
            try:
                resp = session.get(link, stream=True, timeout=60)
                resp.raise_for_status()
                with open(out, "wb") as f:
                    for chunk in resp.iter_content(65536):
                        f.write(chunk)
                print(f"    [dl] Brewer {day_str} -> {fname}")
                count += 1
            except RequestException:
                pass

    return count > 0


# -- PHASE 2: READERS -------------------------------------------

def read_saoz_raw(start, end):
    points = []
    for csv_file in sorted(SAOZ_CSV_DIR.glob("*.csv")):
        with open(csv_file, newline="") as f:
            for row in csv.DictReader(f):
                try:
                    y, m, d = int(row["year"]), int(row["month"]), int(row["day"])
                except (ValueError, KeyError):
                    continue
                dt = date(y, m, d)
                if dt < start or dt > end:
                    continue
                sr_h, ss_h = _sunrise_sunset_hour(dt)
                o3sr = float(row["O3sr"]) if row.get("O3sr") else None
                o3ss = float(row["O3ss"]) if row.get("O3ss") else None
                if o3sr is not None and sr_h is not None:
                    ts = datetime(y, m, d, int(sr_h), 0)
                    points.append((ts, o3sr, "sr"))
                if o3ss is not None and ss_h is not None:
                    ts = datetime(y, m, d, int(ss_h), 0)
                    points.append((ts, o3ss, "ss"))
    return points


def read_pandora_raw(start, end):
    points = []
    for txt_file in sorted(PANDORA_DIR.glob("pandonia_*.txt")):
        lines = txt_file.read_text().splitlines()
        for line in lines[75:]:
            line = line.strip()
            if not line:
                continue
            parts = line.split()
            if len(parts) < 39:
                continue
            try:
                dt = datetime.strptime(parts[0][:15], "%Y%m%dT%H%M%S")
            except ValueError:
                continue
            if dt.date() < start or dt.date() > end:
                continue
            o3_mol = float(parts[38])
            if o3_mol < 0:
                continue
            points.append((dt, o3_mol * MOL2DU))
    return points


def read_bts_raw(start, end):
    points = []
    for csv_file in sorted(BTS_DIR.glob("*.csv")):
        if csv_file.suffix != ".csv":
            continue
        lines = csv_file.read_text().splitlines()
        header_idx = None
        for i, line in enumerate(lines):
            if "Ozone (DU)" in line:
                header_idx = i
                break
        if header_idx is None:
            continue
        for line in lines[header_idx + 1:]:
            line = line.strip()
            if not line:
                continue
            parts = line.split(",")
            if len(parts) < 3:
                continue
            try:
                ts = parts[0].replace("Z", "+00:00")
                dt = datetime.fromisoformat(ts)
                o3_du = float(parts[2])
            except (ValueError, IndexError):
                continue
            if dt.date() < start or dt.date() > end:
                continue
            points.append((dt, o3_du))
    return points


def read_sonde_raw(start, end):
    for fpath in sorted(SONDE_DIR.glob("*")):
        if not fpath.is_file():
            continue
        result = _parse_sonde_header(fpath)
        if result is None:
            continue
        launch_date, launch_hour, col1 = result
        if launch_date < start or launch_date > end:
            continue
        if launch_hour is None:
            launch_hour = 12.0
        h = int(launch_hour)
        m = int((launch_hour - h) * 60)
        dt0 = datetime(launch_date.year, launch_date.month, launch_date.day, h, m)
        dt1 = dt0 + timedelta(hours=2)
        return [(dt0, col1), (dt1, col1)]
    return []


def read_brewer_raw(start, end):
    """Read Brewer #037 and #214 total column O3 from FMI CSV."""
    import csv
    csv_path = Path("./Brewer/st-lpnn-7501fmisid-101932-csv-1782203564.csv")
    if not csv_path.exists():
        print(f"    [!] Brewer CSV not found: {csv_path}")
        return {}
    points = {"Brewer037": [], "Brewer214": []}
    with open(str(csv_path), "r", encoding="latin-1") as f:
        reader = csv.DictReader(f, delimiter=";")
        for row in reader:
            d = (row.get("OBSDATE_UTC", "") or "").strip()
            t = (row.get("OBSTIME_UTC", "") or "").strip()
            if not d or not t:
                continue
            try:
                dt = datetime.strptime(f"{d} {t}", "%d.%m.%Y %H:%M")
            except ValueError:
                continue
            if dt.date() < start or dt.date() > end:
                continue
            o37 = (row.get("OZONE #37 (DU)", "") or "").strip()
            o214 = (row.get("OZONE #214 (DU)", "") or "").strip()
            if o37:
                try:
                    points["Brewer037"].append((dt, float(o37)))
                except ValueError:
                    pass
            if o214:
                try:
                    points["Brewer214"].append((dt, float(o214)))
                except ValueError:
                    pass
    return points


def read_omi_total_column(start, end):
    """Read OMI OMTO3 total column from AVDC collocated text file."""
    if not OMI_OMTO3_FILE.exists():
        print(f"    [!] OMI file not found: {OMI_OMTO3_FILE}")
        return []
    lines = OMI_OMTO3_FILE.read_text().splitlines()
    # Data starts at line 30 (0-indexed 29)
    points = []
    for line in lines[29:]:
        line = line.strip()
        if not line:
            continue
        parts = line.split()
        if len(parts) < 12:
            continue
        try:
            dt_str = parts[0][:15]
            dt = datetime.strptime(dt_str, "%Y%m%dT%H%M%S")
            o3_du = float(parts[11])
        except (ValueError, IndexError):
            continue
        if dt.date() < start or dt.date() > end:
            continue
        if o3_du < 0:
            continue
        points.append((dt, o3_du))
    return points


def read_omps_total_column(start, end):
    """Read OMPS NMTO3 total column from AVDC collocated text file."""
    if not OMPS_NMTO3_FILE.exists():
        print(f"    [!] OMPS file not found: {OMPS_NMTO3_FILE}")
        return []
    lines = OMPS_NMTO3_FILE.read_text().splitlines()
    points = []
    for line in lines[27:]:
        line = line.strip()
        if not line:
            continue
        parts = line.split()
        if len(parts) < 12:
            continue
        try:
            dt_str = parts[0][:15]
            dt = datetime.strptime(dt_str, "%Y%m%dT%H%M%S")
            o3_du = float(parts[11])
        except (ValueError, IndexError):
            continue
        if dt.date() < start or dt.date() > end:
            continue
        if o3_du < 0:
            continue
        points.append((dt, o3_du))
    return points


def _find_gome2_paths(f):
    paths = {}
    def visitor(name, obj):
        if hasattr(obj, "shape") and hasattr(obj, "dtype"):
            low = name.lower()
            if "lat" in low and paths.get("lat") is None:
                paths["lat"] = name
            if "lon" in low and paths.get("lon") is None:
                paths["lon"] = name
            if "o3" in low and "total" in low and paths.get("o3") is None:
                paths["o3"] = name
            if "quality" in low and paths.get("qa") is None:
                paths["qa"] = name
            if "time" in low and paths.get("time") is None:
                paths["time"] = name
    f.visititems(visitor)
    return paths


def read_gome2_raw(start, end):
    try:
        import h5py
    except ImportError:
        print("    [!] GOME2: h5py not installed (pip install h5py)")
        return {}

    points = {"GOME2B": [], "GOME2C": []}

    for fpath in sorted(GOME2_DIR.glob("*.HDF5")):
        if "METOPB" in fpath.name:
            sat_key = "GOME2B"
        elif "METOPC" in fpath.name:
            sat_key = "GOME2C"
        else:
            continue

        try:
            f = h5py.File(fpath, "r")
        except Exception:
            continue

        p = _find_gome2_paths(f)
        missing = [k for k in ("lat", "lon", "o3", "qa", "time") if p.get(k) is None]
        if missing:
            print(f"    [!] GOME2 {fpath.name}: missing paths {missing} — skipping")
            # Print available paths to help debug
            for key in f.keys():
                print(f"        group: /{key}")
            f.close()
            continue

        lat = f[p["lat"]][:]
        lon = f[p["lon"]][:]
        o3  = f[p["o3"]][:]
        qa  = f[p["qa"]][:]
        tm  = f[p["time"]][:]
        f.close()

        if qa.ndim == 2 and qa.shape[1] > 1:
            qa_col = qa[:, 1]
        else:
            qa_col = qa

        mask = (
            (np.abs(lat - S5P_LAT) <= S5P_RADIUS) &
            (np.abs(lon - S5P_LON) <= S5P_RADIUS) &
            (qa_col == 0) &
            ~np.isnan(o3)
        )

        if not mask.any():
            continue

        o3_valid = o3[mask]
        tm_valid = tm[mask]

        for i in range(len(o3_valid)):
            t = tm_valid[i]
            if isinstance(t, (np.void, tuple)):
                try:
                    dt = datetime(1950, 1, 1) + timedelta(days=int(t["Day"]), milliseconds=int(t["MillisecondOfDay"]))
                except Exception:
                    continue
            else:
                try:
                    dt = datetime(1950, 1, 1) + timedelta(days=float(t))
                except Exception:
                    try:
                        dt = datetime.utcfromtimestamp(float(t))
                    except Exception:
                        continue
            if start <= dt.date() <= end:
                points[sat_key].append((dt, float(o3_valid[i])))

    return points


def read_s5p_raw(start, end):
    try:
        import xarray as xr
    except ImportError:
        print("    [!] S5P: xarray not installed (pip install xarray netCDF4)")
        return []

    files = sorted(S5P_DIR.glob("S5P_OFFL_L2__O3____*.nc"))
    if not files:
        return []

    points = []
    reference_date = datetime(2010, 1, 1)

    for nc_file in files:
        try:
            ds = xr.open_dataset(nc_file, group="PRODUCT")
        except Exception:
            continue

        lat = ds["latitude"].values[0]
        lon = ds["longitude"].values[0]
        o3  = ds["ozone_total_vertical_column"].values[0]
        qa  = ds["qa_value"].values[0]
        dtime = ds["delta_time"].values[0]
        ds.close()

        mask = (
            (np.abs(lat - S5P_LAT) <= S5P_RADIUS) &
            (np.abs(lon - S5P_LON) <= S5P_RADIUS) &
            (qa >= S5P_QA_MIN) &
            ~np.isnan(o3)
        )

        if not mask.any():
            continue

        o3_valid = o3[mask] * MOL2DU
        time_valid = dtime[mask]

        for i in range(len(o3_valid)):
            ts_ns = time_valid[i].astype(np.int64)
            py_dt = datetime.utcfromtimestamp(ts_ns / 1e9)
            if start <= py_dt.date() <= end:
                points.append((py_dt, float(o3_valid[i])))

    return points


# -- PHASE 3: PLOT ----------------------------------------------

def plot_comparison(all_points, out_path):
    fig, ax = plt.subplots(figsize=(14, 6))

    for name, points in all_points.items():
        if not points:
            continue
        s = STYLES.get(name, {"color": "gray", "marker": "o", "label": name})

        if name == "Sonde" and len(points) >= 2:
            ax.plot([points[0][0], points[1][0]], [points[0][1], points[1][1]],
                    color=s["color"], linestyle="--", linewidth=2,
                    marker="|", markersize=10, label=s["label"])
            ax.annotate(f"{points[0][0].hour:02d}:{points[0][0].minute:02d}",
                        points[0], textcoords="offset points",
                        xytext=(0, -12), fontsize=7, color=s["color"],
                        ha="center")
            continue

        if name == "SAOZ":
            times = [p[0] for p in points]
            vals  = [p[1] for p in points]
            labels = [p[2] for p in points]
            for t, v, lbl in zip(times, vals, labels):
                ax.scatter(t, v, color=s["color"], marker=s["marker"],
                           s=100, zorder=5,
                           label=s["label"] if not ax.get_legend_handles_labels()[1].count(s["label"]) else "")
                ax.annotate(lbl.upper(), (t, v), textcoords="offset points",
                            xytext=(5, 5), fontsize=8, fontweight="bold",
                            color=s["color"])
            continue

        times = [p[0] for p in points]
        vals  = [p[1] for p in points]
        ax.scatter(times, vals, color=s["color"], marker=s["marker"],
                   s=12, alpha=0.5, label=s["label"], zorder=3)

    ax.set_ylabel("O3 total column (DU)")
    ax.set_title(f"Sodankyla -- Ground + Satellite Ozone Comparison "
                 f"({start_str} -> {end_str})")
    ax.legend()
    ax.grid(True, alpha=0.3)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %d\n%H:%M"))
    fig.autofmt_xdate()
    plt.tight_layout()
    plt.savefig(out_path, dpi=150)
    print(f"\n  Plot saved -> {out_path}")


# -- MAIN -------------------------------------------------------

def main():
    global start_str, end_str
    start_dt = datetime.strptime(DATE_START, "%Y-%m-%d")
    end_dt   = datetime.strptime(DATE_END,   "%Y-%m-%d")
    start_date = start_dt.date()
    end_date   = end_dt.date()
    start_str = DATE_START
    end_str   = DATE_END

    out_path = Path(f"plots/gs_comparison_{DATE_START}_{DATE_END}.png")

    print("=== Sodankyla -- Ground + Satellite Ozone Comparison ===\n")
    print(f"  Period: {DATE_START} -> {DATE_END}\n")

    # -- Phase 1: Check cache / Download --
    print("-- Phase 1: Check cache / Download --")

    dl_info = {}

    for name, enabled in DOWNLOAD.items():
        if not enabled:
            dl_info[name] = f"download disabled (DOWNLOAD['{name}'] = False)"
            continue

        if name == "SAOZ":
            print("  SAOZ...")
            ensure_saoz(start_date, end_date)
            dl_info["SAOZ"] = None
        elif name == "Pandora":
            print("  Pandora...")
            ensure_pandora(start_date, end_date)
            dl_info["Pandora"] = None
        elif name == "S5P":
            print("  S5P...")
            ensure_s5p(start_date, end_date)
            dl_info["S5P"] = None
        elif name == "GOME2":
            print("  GOME2...")
            ensure_gome2(start_date, end_date)
            dl_info["GOME2"] = None
        elif name == "Brewer":
            print("  Brewer...")
            ensure_brewer(start_date, end_date)
            dl_info["Brewer"] = None

    dl_info.setdefault("BTS",    "no download source (local files only)")
    dl_info.setdefault("Sonde",  "no download source (local files only)")
    dl_info.setdefault("S5P",    "download disabled (DOWNLOAD['S5P'] = False)")
    dl_info.setdefault("GOME2",  "download disabled (DOWNLOAD['GOME2'] = False)")
    dl_info.setdefault("Brewer", "download disabled (DOWNLOAD['Brewer'] = False)")
    dl_info.setdefault("OMPS",  "no download source (local AVDC file)")

    print()

    # -- Phase 2: Read data --
    print("-- Phase 2: Read data --")

    readers = [
        ("SAOZ",    read_saoz_raw),
        ("Pandora", read_pandora_raw),
        ("BTS",     read_bts_raw),
        ("Sonde",   read_sonde_raw),
        ("S5P",     read_s5p_raw),
        ("GOME2",   read_gome2_raw),
        ("Brewer",  read_brewer_raw),
        ("OMI",     read_omi_total_column),
        ("OMPS",    read_omps_total_column),
    ]

    all_points = {}
    has_data = False
    for name, reader in readers:
        points = reader(start_date, end_date)
        if name == "GOME2":
            all_points.update(points)
            for sat_key, pts in points.items():
                n = len(pts)
                msg = dl_info.get("GOME2")
                if msg:
                    print(f"  {sat_key:10s} -- {n:4d} point(s) -- {msg}")
                elif n == 0:
                    print(f"  {sat_key:10s} -- no data in period")
                else:
                    has_data = True
                    vals = [p[1] for p in pts]
                    print(f"  {sat_key:10s} -- {n:4d} point(s), O3: {np.mean(vals):.1f} "
                          f"[{np.min(vals):.1f} - {np.max(vals):.1f}] DU")
            continue

        if name == "Brewer":
            all_points.update(points)
            for br_key, pts in points.items():
                n = len(pts)
                if n == 0:
                    print(f"  {br_key:10s} -- no data in period")
                else:
                    has_data = True
                    vals = [p[1] for p in pts]
                    print(f"  {br_key:10s} -- {n:4d} point(s), O3: {np.mean(vals):.1f} "
                          f"[{np.min(vals):.1f} - {np.max(vals):.1f}] DU")
            continue

        all_points[name] = points
        n = len(points)
        msg = dl_info.get(name)
        if msg:
            print(f"  {name:10s} -- {n:4d} point(s) -- {msg}")
        elif n == 0:
            print(f"  {name:10s} -- no data in period")
        else:
            has_data = True
            if name == "Sonde":
                o3 = points[0][1]
                print(f"  {name:10s} -- {n:4d} point(s), O3: {o3:.1f} DU "
                      f"(launch {points[0][0].hour:02d}:{points[0][0].minute:02d})")
            else:
                vals = [p[1] for p in points]
                print(f"  {name:10s} -- {n:4d} point(s), O3: {np.mean(vals):.1f} "
                      f"[{np.min(vals):.1f} - {np.max(vals):.1f}] DU")

    if not has_data:
        print("\n  No data available in this period.")
        return

    print()

    # -- Phase 3: Plot --
    print("-- Phase 3: Plot --")
    plot_comparison(all_points, out_path)


if __name__ == "__main__":
    main()
