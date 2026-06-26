"""
GS Profile Comparison — Vertical ozone profiles at Sodankyla
  Sonde (ozonesonde), S5P TROPOMI O3_PR, GOME-2 NTO

All profiles interpolated to a common pressure grid.
Units: DU per layer.
"""

import os
import re
from pathlib import Path
from datetime import datetime, date, timedelta
from dotenv import load_dotenv
load_dotenv()

import requests
import numpy as np
from scipy import interpolate
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker

# ── Constants ──
k_B     = 1.380649e-23   # Boltzmann constant (J/K)
DU_FACT = 2.687e20        # molecules/m2 per DU
MOL2DU  = 2241.15         # mol/m2 to DU

# ── Config ──
DATE_START = "2026-04-15"
DATE_END   = "2026-04-15"

SONDE_DIR    = Path("./ground/sondes/sondes_data")
S5P_PR_DIR   = Path("./satellite/S5P/s5p_data/profile")
GOME2_DIR    = Path("./satellite/GOME2/GOME2_data")
AVDC_OMI_H5  = Path("./satellite/OMI/omi_data/satellite_aura_omi_l2ovp_omo3pr_sodankyla.h5")
OUT_PLOT     = "plots/gs_profile_comparison_{}_{}.png"

S5P_LAT    = 67.3668
S5P_LON    = 26.6297
S5P_RADIUS = 0.5
S5P_QA_MIN = 0.5

COPERNICUS_USER = os.getenv("COPERNICUS_USER")
COPERNICUS_PASS = os.getenv("COPERNICUS_PASS")
EUMETSAT_KEY    = os.getenv("EUMETSAT_KEY")
EUMETSAT_SECRET = os.getenv("EUMETSAT_SECRET")
GOME2_COLLECTION = "EO:EUM:DAT:METOP:NTO"

COMMON_PRESSURE = np.array([
    1000, 900, 800, 700, 600, 500, 400, 300, 250,
    200, 150, 100, 70, 50, 30, 20, 10, 7, 5, 3, 2, 1,
    0.5, 0.3, 0.2, 0.1
])

# ── Helpers ──

def date_range(start, end):
    d = start
    while d <= end:
        yield d
        d += timedelta(days=1)

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
    except requests.RequestException as e:
        print(f"    [!] Copernicus auth failed: {e}")
        return None

def _copernicus_search(product_type, start, end, token):
    url = "https://catalogue.dataspace.copernicus.eu/odata/v1/Products"
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
    except requests.RequestException as e:
        print(f"    [!] Copernicus search: {e}")
        return []
    filtered = [p for p in all_products if product_type in p["Name"]]
    print(f"    [search] {len(filtered)} S5P {product_type} files found")
    return filtered

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
            with open(out, "wb") as f:
                for chunk in r.iter_content(chunk_size=65536):
                    f.write(chunk)
    except requests.RequestException as e:
        print(f"    [!] S5P download failed: {e}")
        if out.exists():
            out.unlink()

# ── Phase 1: Download ──

def ensure_s5p_profile(start, end):
    if not COPERNICUS_USER or not COPERNICUS_PASS:
        print("    [!] S5P: Copernicus credentials not configured")
        return False
    S5P_PR_DIR.mkdir(parents=True, exist_ok=True)
    token = _copernicus_auth()
    if token is None:
        return False
    products = _copernicus_search("L2__O3__PR_", start, end, token)
    if not products:
        return False
    cached = sum(1 for p in products if (S5P_PR_DIR / p["Name"]).exists())
    if cached > 0:
        print(f"    [cache] {cached} file(s) already present")
    new = [p for p in products if not (S5P_PR_DIR / p["Name"]).exists()]
    for prod in new:
        _copernicus_download(prod, token, S5P_PR_DIR)
    return True

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
            products = collection.search(dtstart=dt_day, dtend=dt_day, sat=plat)
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


def ensure_noaa21(start, end):
    NOAA21_PROFILE_DIR.mkdir(parents=True, exist_ok=True)
    from satellite.OMPS.download_omps import ensure_noaa21_avdc
    ensure_noaa21_avdc(start, end)


# ── Phase 2: Profile readers ──

def read_sonde_profile(fpath):
    lines = fpath.read_text(encoding="latin-1").splitlines()
    # Find data start (after "Sodankyla" marker, first pressure > 500 hPa)
    data_start = None
    for i, line in enumerate(lines):
        if i < 110:
            continue
        parts = line.strip().split()
        if len(parts) >= 7:
            try:
                p0 = float(parts[0])
                o6 = float(parts[6])
                if 500 < p0 < 1100 and 0 < o6 < 200:
                    data_start = i
                    break
            except ValueError:
                continue
    if data_start is None:
        return None
    press = []
    o3_mPa = []
    temp_c = []
    alt  = []
    for line in lines[data_start:]:
        parts = line.strip().split()
        if len(parts) < 7:
            continue
        try:
            p = float(parts[0])
            h = float(parts[2])
            t = float(parts[3])
            o = float(parts[6])
        except (ValueError, IndexError):
            continue
        if p <= 0 or np.isnan(p):
            continue
        press.append(p)
        alt.append(h)
        temp_c.append(t)
        o3_mPa.append(o)
    if len(press) < 5:
        return None
    press = np.array(press)
    alt   = np.array(alt)
    temp_c = np.array(temp_c)
    o3_mPa = np.array(o3_mPa)

    # --- Extract COL1 (total column) from header ---
    col1 = None
    for i, line in enumerate(lines):
        if "Sodankyla" in line:
            if i + 2 < len(lines):
                parts = lines[i + 2].strip().split()
                if len(parts) > 10:
                    try:
                        col1 = float(parts[10])
                    except ValueError:
                        pass
            break

    # Launch datetime
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
    launch_hour = 12.0
    for i, line in enumerate(lines):
        if "Sodankyla" in line:
            if i + 1 < len(lines):
                parts = lines[i + 1].strip().split()
                if len(parts) > 1:
                    try:
                        launch_hour = float(parts[1])
                    except ValueError:
                        pass
            break
    dt_launch = datetime(launch_date.year, launch_date.month, launch_date.day,
                         int(launch_hour), int((launch_hour % 1) * 60))

    # Compute DU per LAYER (between consecutive levels) using ideal gas law
    layer_du = []
    layer_p  = []
    for i in range(len(press) - 1):
        dz = alt[i + 1] - alt[i]
        if dz <= 0:
            continue
        P_avg = (o3_mPa[i] + o3_mPa[i + 1]) / 2 * 1e-3  # Pa
        T_avg = (temp_c[i] + temp_c[i + 1]) / 2 + 273.15  # K
        n_m3 = P_avg / (k_B * T_avg)  # molecules/m³
        col_molec = n_m3 * dz  # molecules/m²
        du = col_molec / DU_FACT
        layer_du.append(du)
        layer_p.append(np.sqrt(press[i] * press[i + 1]))
    layer_du = np.array(layer_du)
    layer_p  = np.array(layer_p)

    # Scale to match COL1 (total column from header)
    computed_total = layer_du.sum()
    if col1 is not None and computed_total > 0:
        scale = col1 / computed_total
        layer_du *= scale

    return {
        "source": f"Sonde {fpath.name}",
        "label": f"Sonde ({launch_date})",
        "datetime": dt_launch,
        "pressure": layer_p,
        "o3_layer": layer_du,
        "color": "#d62728",
        "marker": "^",
    }

def read_s5p_profiles(start, end):
    import xarray as xr
    profiles = []
    files = sorted(S5P_PR_DIR.glob("S5P_OFFL_L2__O3__PR_*.nc"))
    for nc_file in files:
        try:
            ds = xr.open_dataset(nc_file, group="PRODUCT")
        except Exception:
            continue
        lat = ds["latitude"].values[0]
        lon = ds["longitude"].values[0]
        mask = (
            (np.abs(lat - S5P_LAT) <= S5P_RADIUS) &
            (np.abs(lon - S5P_LON) <= S5P_RADIUS)
        )
        if not mask.any():
            ds.close()
            continue
        scanlines, pixels = np.where(mask)
        # Average over selected pixels
        o3_all = []
        press_mid_all = []
        alt_mid_all = []
        dtimes = []
        for sl, gp in zip(scanlines, pixels):
            prof = ds["ozone_profile"].values[0, sl, gp, :]
            p_lev = ds["pressure"].values[0, sl, gp, :]
            a_lev = ds["altitude"].values[0, sl, gp, :]
            qa = ds["qa_value"].values[0, sl, gp] if "qa_value" in ds else 1.0
            # Layer: between level i and i+1 (i=0 surface, i=32 TOA)
            o3_layers = []
            p_mid = []
            for i in range(len(p_lev) - 1):
                conc_avg = (prof[i] + prof[i + 1]) / 2
                dz = abs(a_lev[i + 1] - a_lev[i])
                col_mol_m2 = conc_avg * dz
                col_du = col_mol_m2 * MOL2DU
                o3_layers.append(col_du)
                p_mid.append(np.sqrt(p_lev[i] * p_lev[i + 1]) * 0.01)
            o3_all.append(np.array(o3_layers))
            press_mid_all.append(np.array(p_mid))
            dtimes.append(ds["delta_time"].values[0, sl])
        ds.close()
        if not o3_all:
            continue
        o3_avg = np.mean(o3_all, axis=0)
        p_avg  = np.mean(press_mid_all, axis=0)
        # Sort by pressure ascending
        order = np.argsort(p_avg)
        p_avg = p_avg[order]
        o3_avg = o3_avg[order]
        dt = dtimes[0]
        if hasattr(dt, "astype"):
            dt = datetime.utcfromtimestamp(dt.astype(np.int64) / 1e9)
        profiles.append({
            "source": nc_file.name,
            "label": f"S5P ({dt.strftime('%H:%M')})",
            "datetime": dt,
            "pressure": p_avg,
            "o3_layer": o3_avg,
            "color": "#17becf",
            "marker": ".",
        })
    return profiles

def read_gome2_profiles(start, end):
    try:
        import h5py
    except ImportError:
        print("    [!] GOME2: h5py not installed")
        return []
    profiles = []
    for fpath in sorted(GOME2_DIR.glob("*.HDF5")):
        if "METOPB" in fpath.name:
            sat_key = "GOME2B"
            sat_color = "#e377c2"
        elif "METOPC" in fpath.name:
            sat_key = "GOME2C"
            sat_color = "#8c564b"
        else:
            continue
        try:
            f = h5py.File(fpath, "r")
        except Exception:
            continue
        # Spatial filter
        lat = f["/GEOLOCATION/LatitudeCentre"][:]
        lon = f["/GEOLOCATION/LongitudeCentre"][:]
        mask = (
            (np.abs(lat - S5P_LAT) <= S5P_RADIUS) &
            (np.abs(lon - S5P_LON) <= S5P_RADIUS)
        )
        if not mask.any():
            f.close()
            continue
        # Quality filter
        qf = f.get("/DETAILED_RESULTS/QualityFlags")
        if qf is not None:
            qf_val = qf[:]
            if qf_val.ndim == 2 and qf_val.shape[1] > 1:
                qf_col = qf_val[:, 1]
            else:
                qf_col = qf_val
            mask = mask & (qf_col == 0)
        if not mask.any():
            f.close()
            continue
        # O3 profile
        o3prof = f["/DETAILED_RESULTS/O3/O3Profile"][:]
        p_lev  = f["/DETAILED_RESULTS/O3/O3ProfilePressure"][:]
        # Time
        tm = f["/GEOLOCATION/Time"][:]
        f.close()
        idx = np.where(mask)[0]
        # Average over selected pixels
        avg_prof = np.mean(o3prof[idx], axis=0)
        # Parse datetime from first pixel
        t0 = tm[idx[0]]
        if isinstance(t0, (np.void, tuple)):
            try:
                dto = datetime(1950, 1, 1) + timedelta(
                    days=int(t0["Day"]), milliseconds=int(t0["MillisecondOfDay"]))
            except Exception:
                continue
        else:
            try:
                dto = datetime(1950, 1, 1) + timedelta(days=float(t0))
            except Exception:
                continue
        if not (start <= dto.date() <= end):
            continue
        profiles.append({
            "source": fpath.name,
            "label": f"{sat_key} ({dto.strftime('%H:%M')})",
            "datetime": dto,
            "pressure": p_lev,
            "o3_layer": avg_prof,
            "color": sat_color,
            "marker": ".",
        })
    return profiles

def read_avdc_omi_profiles(start, end):
    try:
        import h5py
    except ImportError:
        print("    [!] AVDC OMI: h5py not installed")
        return []
    if not AVDC_OMI_H5.exists():
        print("    [!] AVDC OMI file not found:", AVDC_OMI_H5)
        return []
    try:
        f = h5py.File(str(AVDC_OMI_H5), "r")
    except Exception as e:
        print(f"    [!] AVDC OMI: {e}")
        return []
    dt_arr = f["DATETIME"][:]
    o3_arr = f["O3.CONCENTRATION_BACKSCATTER.SOLAR"][:]
    pr_arr = f["PRESSURE_BACKSCATTER.SOLAR"][:]
    tc_arr = f["O3.COLUMN_BACKSCATTER.SOLAR"][:]
    f.close()
    profiles = []
    mjd_offset = datetime(2000, 1, 1)
    for i in range(len(dt_arr)):
        overpass_dt = mjd_offset + timedelta(days=float(dt_arr[i]))
        if not (start <= overpass_dt.date() <= end):
            continue
        o3_levels = o3_arr[i]
        p_levels = pr_arr[i]
        valid = (o3_levels > -1e20) & (p_levels > 0)
        if valid.sum() < 2:
            continue
        o3_v = o3_levels[valid]
        p_v  = p_levels[valid]
        order = np.argsort(p_v)
        p_v  = p_v[order]
        o3_v = o3_v[order]
        profiles.append({
            "source": "AVDC OMI OMO3PR",
            "label": f"OMI ({overpass_dt.strftime('%H:%M')})",
            "datetime": overpass_dt,
            "pressure": p_v,
            "o3_layer": o3_v,
            "color": "#ff7f0e",
            "marker": "s",
        })
    print(f"    [avdc] {len(profiles)} OMI profiles found")
    return profiles


NOAA21_PROFILE_DIR = Path("./satellite/OMPS/omps_data/noaa21_profile")


def read_noaa21_profiles(start, end):
    profiles = []
    for fpath in sorted(NOAA21_PROFILE_DIR.glob("*.txt")):
        text = fpath.read_text()
        lines = text.splitlines()
        if len(lines) < 10:
            continue
        # Parse header
        dt_match = re.search(r"Date = (\d{8}),\s+sec\.\s*\(UT\)\s*=\s*(\d+)", text)
        dist_match = re.search(r"Distance to the station =\s*([\d.]+)\s*km", text)
        sza_match = re.search(r"SZA\s*=\s*([\d.]+)\s*deg", text)
        qual_match = re.search(r"SwathLevelQualityFlags\s*=\s*(\d+)", text)
        if not dt_match:
            continue
        ymd, ut_sec = dt_match.group(1), int(dt_match.group(2))
        try:
            overpass_dt = datetime.strptime(ymd, "%Y%m%d") + timedelta(seconds=ut_sec)
        except ValueError:
            continue
        if not (start <= overpass_dt.date() <= end):
            continue
        distance = float(dist_match.group(1)) if dist_match else 999
        sza = float(sza_match.group(1)) if sza_match else 999
        qf = int(qual_match.group(1)) if qual_match else 0
        if distance > 200 or sza > 88 or qf != 0:
            continue
        # Find data start line
        data_start = None
        for i, line in enumerate(lines):
            if line.strip().startswith("Height(km)"):
                data_start = i + 1
                break
        if data_start is None:
            continue
        heights, pressures, vmrs = [], [], []
        for line in lines[data_start:]:
            parts = line.split()
            if len(parts) < 6:
                continue
            try:
                h = float(parts[0])
                p = float(parts[1])
                vmr = float(parts[5])
            except ValueError:
                continue
            if vmr < 0:
                continue
            heights.append(h)
            pressures.append(p)
            vmrs.append(vmr)
        if len(heights) < 2:
            continue
        # Convert VMR (ppmv) to DU per layer
        o3_layers = []
        p_mid = []
        for i in range(len(heights) - 1):
            dp = abs(pressures[i] - pressures[i + 1])
            vmr_avg = (vmrs[i] + vmrs[i + 1]) / 2
            du = 0.789 * vmr_avg * dp
            o3_layers.append(du)
            p_mid.append(np.sqrt(pressures[i] * pressures[i + 1]))
        if not o3_layers:
            continue
        o3_layers = np.array(o3_layers)
        p_mid = np.array(p_mid)
        order = np.argsort(p_mid)
        profiles.append({
            "source": fpath.name,
            "label": f"NOAA21 ({overpass_dt.strftime('%H:%M')})",
            "datetime": overpass_dt,
            "pressure": p_mid[order],
            "o3_layer": o3_layers[order],
            "color": "#2ca02c",
            "marker": "v",
        })
    return profiles


# ── Phase 3: Interpolation ──

def interpolate_profile(pressure, o3_layer, target_pressure):
    pressure = np.asarray(pressure, dtype=float)
    o3_layer = np.asarray(o3_layer, dtype=float)
    valid = (pressure > 0) & np.isfinite(o3_layer)
    if valid.sum() < 2:
        return None
    p = pressure[valid]
    o = o3_layer[valid]
    sort_idx = np.argsort(p)
    p = p[sort_idx]
    o = o[sort_idx]
    # Cumulative from TOA
    cum_o3 = np.zeros(len(p))
    for i in range(len(p) - 2, -1, -1):
        cum_o3[i] = cum_o3[i + 1] + o[i]
    f_cum = interpolate.interp1d(
        np.log(p), cum_o3, kind="linear",
        bounds_error=False, fill_value=(cum_o3[0], cum_o3[-1]))
    target = np.asarray(target_pressure, dtype=float)
    cum_interp = f_cum(np.log(target))
    # Layers between consecutive target levels
    o3_interp = np.zeros(len(target) - 1)
    mid_press = np.zeros(len(target) - 1)
    for i in range(len(target) - 1):
        if (np.isfinite(cum_interp[i]) and np.isfinite(cum_interp[i + 1])
                and cum_interp[i + 1] >= cum_interp[i]):
            o3_interp[i] = cum_interp[i + 1] - cum_interp[i]
        else:
            o3_interp[i] = 0.0
        mid_press[i] = np.sqrt(target[i] * target[i + 1])
    return o3_interp, mid_press

# ── Phase 4: Plot ──

def plot_profiles(all_profiles, start, end):
    fig, axes = plt.subplots(1, 3, figsize=(14, 8))
    fig.suptitle(f"Sodankyla — Vertical O3 Profiles ({start} to {end})",
                 fontsize=13, fontweight="bold")
    panels = [
        (axes[0], "Full profile", 1000, 0.1),
        (axes[1], "Troposphere", 1000, 100),
        (axes[2], "Stratosphere", 100, 0.1),
    ]
    prof_list = list(all_profiles.values())
    for idx, (ax, title, p_top, p_bot) in enumerate(panels):
        ax.set_title(title, fontsize=10)
        ax.set_xlabel("O₃ (DU / layer)")
        ax.set_yscale("log")
        ax.invert_yaxis()
        ax.set_ylim(p_top, p_bot)
        ax.grid(True, alpha=0.3)
        used = []
        for prof in prof_list:
            label = prof.get("label", "")
            if label in used:
                label = ""
            else:
                used.append(label)
            res = interpolate_profile(prof["pressure"], prof["o3_layer"], COMMON_PRESSURE)
            if res is None:
                continue
            o3_int, p_int = res
            ax.plot(o3_int, p_int, color=prof.get("color", "gray"),
                    marker=prof.get("marker", "."),
                    markersize=4, linewidth=1.2, label=label, alpha=0.8)
        if idx == 0:
            ax.legend(fontsize=7, loc="upper left")
    axes[0].set_ylabel("Pressure (hPa)")
    plt.tight_layout(rect=[0, 0, 1, 0.95])
    fname = OUT_PLOT.format(start, end)
    fig.savefig(fname, dpi=150)
    print(f"\n  Plot saved -> {fname}")
    plt.close(fig)

# ── Main ──

def main():
    start = datetime.strptime(DATE_START, "%Y-%m-%d").date()
    end   = datetime.strptime(DATE_END,   "%Y-%m-%d").date()
    print(f"=== Sodankyla -- Vertical Ozone Profile Comparison ===")
    print(f"  Period: {start} -> {end}\n")
    print("-- Phase 1: Check cache / Download --")
    print("  S5P (profiles)...")
    ensure_s5p_profile(start, end)
    print("  GOME2...")
    ensure_gome2(start, end)
    print("  NOAA21...")
    ensure_noaa21(start, end)
    print()
    print("-- Phase 2: Read profiles --")
    all_profiles = {}
    # Sonde
    for fpath in sorted(SONDE_DIR.glob("*")):
        if not fpath.is_file():
            continue
        if not re.search(r"so\d{6}", fpath.name):
            continue
        prof = read_sonde_profile(fpath)
        if prof is None:
            continue
        if prof["datetime"].date() < start or prof["datetime"].date() > end:
            continue
        key = prof["source"]
        all_profiles[key] = prof
        n = len(prof["pressure"])
        print(f"  Sonde      -- {n:4d} levels, "
              f"O3: {prof['o3_layer'].sum():.1f} DU")
    # S5P
    s5p_profs = read_s5p_profiles(start, end)
    for prof in s5p_profs:
        total = prof["o3_layer"].sum()
        if np.isnan(total):
            print(f"  S5P        --   skip (all NaN)  ({prof['label']})")
            continue
        key = prof["source"]
        all_profiles[key] = prof
        print(f"  S5P        -- {len(prof['pressure']):4d} levels, "
              f"O3: {total:.1f} DU  ({prof['label']})")
    # GOME2
    gome2_profs = read_gome2_profiles(start, end)
    for prof in gome2_profs:
        key = prof["source"]
        all_profiles[key] = prof
        print(f"  {prof['label'].split()[0]:10s} -- {len(prof['pressure']):4d} levels, "
              f"O3: {prof['o3_layer'].sum():.1f} DU  ({prof['label']})")
    # AVDC OMI (only covers up to 2021-02-28)
    omi_profs = read_avdc_omi_profiles(start, end)
    for prof in omi_profs:
        key = prof["source"]
        all_profiles[key] = prof
        print(f"  OMI        -- {len(prof['pressure']):4d} levels, "
              f"O3: {prof['o3_layer'].sum():.1f} DU  ({prof['label']})")
    # NOAA-21 OMPS LP
    noaa21_profs = read_noaa21_profiles(start, end)
    for prof in noaa21_profs:
        key = prof["source"]
        all_profiles[key] = prof
        print(f"  NOAA21     -- {len(prof['pressure']):4d} levels, "
              f"O3: {prof['o3_layer'].sum():.1f} DU  ({prof['label']})")
    if not all_profiles:
        print("  No profiles found.")
        return
    print()
    print("-- Phase 3: Interpolate & Plot --")
    plot_profiles(all_profiles, start, end)

if __name__ == "__main__":
    main()
