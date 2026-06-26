"""
Sonde vs Brewer total column ozone comparison at Sodankyla.

Reads all available ozonesonde and Brewer measurements,
pairs them by date, and produces a comparison table + plots.
"""

import sys
from pathlib import Path
from datetime import datetime, date, timedelta
import re

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

sys.path.insert(0, str(Path(__file__).parent))
from gs_comparison import SONDE_DIR, BREWER_DIR


# -- parse helpers (same logic as gs_comparison._parse_sonde_header) --

def parse_sonde_file(fpath):
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


def read_all_sondes():
    sondes = []
    for fpath in sorted(SONDE_DIR.iterdir()):
        if not fpath.is_file():
            continue
        result = parse_sonde_file(fpath)
        if result is None:
            continue
        launch_date, launch_hour, col1 = result
        if launch_hour is None:
            launch_hour = 12.0
        h = int(launch_hour)
        m = int((launch_hour - h) * 60)
        dt = datetime(launch_date.year, launch_date.month, launch_date.day, h, m)
        sondes.append({"date": launch_date, "dt": dt, "o3": col1, "file": fpath.name})
    return sondes


def read_all_brewers():
    import csv
    brewers = {"Brewer037": [], "Brewer214": []}
    for csv_path in sorted(BREWER_DIR.glob("*.csv")):
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
                date_key = dt.date()
                o37 = (row.get("OZONE #37 (DU)", "") or "").strip()
                o214 = (row.get("OZONE #214 (DU)", "") or "").strip()
                if o37:
                    try:
                        brewers["Brewer037"].append({"dt": dt, "date": date_key, "o3": float(o37)})
                    except ValueError:
                        pass
                if o214:
                    try:
                        brewers["Brewer214"].append({"dt": dt, "date": date_key, "o3": float(o214)})
                    except ValueError:
                        pass
    return brewers


def nearest_in_time(target_dt, points, max_minutes=120):
    best = None
    best_delta = None
    for p in points:
        delta = abs((p["dt"] - target_dt).total_seconds()) / 60
        if delta <= max_minutes:
            if best is None or delta < best_delta:
                best = p
                best_delta = delta
    return best


def run():
    print("=" * 60)
    print("Sonde vs Brewer comparison - Sodankyla")
    print("=" * 60)

    print("\n-- Reading sondes --")
    sondes = read_all_sondes()
    if not sondes:
        print("  No sonde data found.")
        return
    for s in sondes:
        print(f"  {s['date']}  {s['file']:20s}  COL1={s['o3']:.1f} DU")

    print("\n-- Reading Brewer --")
    brewers = read_all_brewers()
    for key in ("Brewer037", "Brewer214"):
        print(f"  {key}: {len(brewers[key])} measurements on {len({b['date'] for b in brewers[key]})} days")

    print("\n-- Pairing --")
    rows = []
    for s in sondes:
        sd = s["date"]
        b037 = brewers["Brewer037"]
        b214 = brewers["Brewer214"]

        day037 = [p for p in b037 if p["date"] == sd]
        day214 = [p for p in b214 if p["date"] == sd]

        near037 = nearest_in_time(s["dt"], b037)
        near214 = nearest_in_time(s["dt"], b214)

        row = {
            "date": sd,
            "file": s["file"],
            "sonde_o3": s["o3"],
            "sonde_dt": s["dt"],
        }

        def stats(pts):
            vals = [p["o3"] for p in pts]
            if not vals:
                return None, None, 0, None, None
            return np.mean(vals), np.std(vals), len(vals), min(vals), max(vals)

        for key, day_pts in [("037", day037), ("214", day214)]:
            mean_v, std_v, n, min_v, max_v = stats(day_pts)
            row[f"brew{key}_n"] = n
            row[f"brew{key}_mean"] = mean_v
            row[f"brew{key}_std"] = std_v
            row[f"brew{key}_min"] = min_v
            row[f"brew{key}_max"] = max_v

        rows.append(row)

    # Print table
    print()
    header = f"{'Date':12s} {'Sonde':>7s} {'Br037_n':>6s} {'Br037_mean':>10s} {'Br037_std':>8s} {'Br214_n':>6s} {'Br214_mean':>10s} {'Br214_std':>8s} {'Delta037':>8s} {'Delta214':>8s}"
    print(header)
    print("-" * len(header))
    for r in rows:
        f_mean = lambda v: f"{v:10.1f}" if v is not None else "      N/A"
        f_std  = lambda v: f"{v:8.3f}" if v is not None else "   N/A"
        f_n    = lambda v: f"{v:6d}"   if v is not None and v > 0 else "     0"
        delta037 = r["sonde_o3"] - r["brew037_mean"] if r["brew037_mean"] is not None else None
        delta214 = r["sonde_o3"] - r["brew214_mean"] if r["brew214_mean"] is not None else None
        d037 = f"{delta037:+.1f}" if delta037 is not None else "   N/A"
        d214 = f"{delta214:+.1f}" if delta214 is not None else "   N/A"
        print(f"{r['date']!s:12s} {r['sonde_o3']:7.1f} {f_n(r['brew037_n'])} {f_mean(r['brew037_mean'])} {f_std(r['brew037_std'])} {f_n(r['brew214_n'])} {f_mean(r['brew214_mean'])} {f_std(r['brew214_std'])} {d037:>8s} {d214:>8s}")

    # Summary stats
    valid = [r for r in rows if r["brew037_mean"] is not None]
    if valid:
        biases_037 = [r["sonde_o3"] - r["brew037_mean"] for r in valid]
        biases_214 = [r for r in valid if r["brew214_mean"] is not None]
        biases_214 = [r["sonde_o3"] - r["brew214_mean"] for r in valid if r["brew214_mean"] is not None]

        print(f"\n-- Summary (sonde vs Brewer #037) --")
        b = np.array(biases_037)
        print(f"  N={len(b)}, Mean bias={np.mean(b):+.2f} DU, RMSD={np.sqrt(np.mean(b**2)):.2f} DU")
        print(f"  Min bias={np.min(b):+.2f}, Max bias={np.max(b):+.2f}")

        if biases_214:
            print(f"\n-- Summary (sonde vs Brewer #214) --")
            b2 = np.array(biases_214)
            print(f"  N={len(b2)}, Mean bias={np.mean(b2):+.2f} DU, RMSD={np.sqrt(np.mean(b2**2)):.2f} DU")

    # Plot
    print("\n-- Plotting --")
    fig, axes = plt.subplots(1, 2, figsize=(14, 5.5))

    # Left: scatter with 1:1
    ax = axes[0]
    for label, key in [("#037", "brew037_mean"), ("#214", "brew214_mean")]:
        pts = [(r["sonde_o3"], r[key]) for r in valid if r[key] is not None]
        if not pts:
            continue
        x = [p[0] for p in pts]
        y = [p[1] for p in pts]
        ax.scatter(x, y, label=f"Brewer {label}", s=60, edgecolors="k", linewidths=0.5)
    lims = [min(ax.get_xlim()[0], ax.get_ylim()[0]), max(ax.get_xlim()[1], ax.get_ylim()[1])]
    ax.plot(lims, lims, "k--", alpha=0.4, label="1:1")
    ax.set_xlabel("Sonde O3 (DU)")
    ax.set_ylabel("Brewer O3 (DU)")
    ax.set_title("Sonde vs Brewer — Total Column O3")
    ax.legend()
    ax.grid(True, alpha=0.3)
    ax.set_aspect("equal")

    # Right: bar plot of differences
    ax = axes[1]
    dates_fmt = [r["date"] for r in valid]
    x_idx = np.arange(len(valid))
    width = 0.35
    diffs_037 = [r["sonde_o3"] - r["brew037_mean"] for r in valid if r["brew037_mean"] is not None]
    diffs_214 = [r["sonde_o3"] - r["brew214_mean"] for r in valid if r["brew214_mean"] is not None]
    if diffs_037:
        ax.bar(x_idx - width/2, diffs_037, width, label="Sonde - Brewer #037", color="#9467bd")
    if diffs_214:
        ax.bar(x_idx + width/2, diffs_214, width, label="Sonde - Brewer #214", color="#e6ab02")
    ax.axhline(0, color="k", linewidth=0.8)
    ax.set_xticks(x_idx)
    ax.set_xticklabels([d.strftime("%Y-%m-%d") for d in dates_fmt])
    ax.set_ylabel("Difference (DU)")
    ax.set_title("Sonde minus Brewer")
    ax.legend()
    ax.grid(True, alpha=0.3, axis="y")

    plt.tight_layout()
    out = Path("plots/sonde_brewer_comparison.png")
    out.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(str(out), dpi=150)
    print(f"  Plot saved: {out}")
    plt.close()


if __name__ == "__main__":
    run()
