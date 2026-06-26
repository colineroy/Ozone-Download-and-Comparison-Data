"""
Ground-based instrument comparison at Sodankyla.
  SAOZ, Pandora, BTS, Brewer #037/#214, Ozonesonde, FTIR.

Reads all available data, creates daily-aggregated comparison table,
pairwise statistics, and a multi-panel figure.
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
from gs_comparison import (
    ensure_saoz, ensure_pandora,
    read_saoz_raw, read_pandora_raw, read_bts_raw,
    read_brewer_raw, read_ftir_raw, _parse_sonde_header,
    SONDE_DIR, STYLES,
)

# - CONFIG -------------------------------------------------------------------
DOWNLOAD = True   # download SAOZ / Pandora if not cached

# - Read helpers --------------------------------------------------------------

def read_all_sondes():
    sondes = []
    for fpath in sorted(SONDE_DIR.iterdir()):
        if not fpath.is_file():
            continue
        result = _parse_sonde_header(fpath)
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


def daily_mean(points):
    if not points:
        return {}
    daily = {}
    for dt, val in points:
        d = dt.date()
        daily.setdefault(d, []).append(val)
    return {d: (np.mean(vals), np.std(vals), len(vals), min(vals), max(vals))
            for d, vals in daily.items()}


# - Run ----------------------------------------------------------------------

def run():
    print("=" * 65)
    print("Ground Instrument Comparison - Sodankyla")
    print("=" * 65)

    # -- Phase 1: download ----------------------------------------------------
    if DOWNLOAD:
        print("\n-- Phase 1: Download --")
        print("  SAOZ...", end=" ", flush=True)
        ok = ensure_saoz(date(2012, 1, 1), date.today())
        print("OK" if ok else "no data")

        print("  Pandora...", end=" ", flush=True)
        ok = ensure_pandora(date(2026, 1, 1), date.today())
        print("OK" if ok else "no data")

    # -- Phase 2: read --------------------------------------------------------
    print("\n-- Phase 2: Read data --")

    all_data = {}  # name -> list of (dt, o3)

    readers = [
        ("SAOZ",    read_saoz_raw,    False),
        ("Pandora", read_pandora_raw, False),
        ("BTS",     read_bts_raw,     False),
        ("Brewer",  read_brewer_raw,  True),
        ("FTIR",    read_ftir_raw,    False),
    ]

    for name, reader, returns_dict in readers:
        pts = reader(date.min, date.max)
        if returns_dict:
            for sub_key, sub_pts in pts.items():
                if sub_pts:
                    all_data[sub_key] = sub_pts
                    print(f"  {sub_key:12s} -- {len(sub_pts)} points")
        else:
            if not pts:
                print(f"  {name:12s} -- no data")
                continue
            if isinstance(pts[0], tuple) and len(pts[0]) == 3:
                pts = [(dt, val) for dt, val, _ in pts]
            all_data[name] = pts
            print(f"  {name:12s} -- {len(pts)} points")

    # Sondes
    sondes = read_all_sondes()
    if sondes:
        sonde_pts = []
        for s in sondes:
            sonde_pts.append((s["dt"], s["o3"]))
            sonde_pts.append((s["dt"] + timedelta(hours=2), s["o3"]))
        all_data["Sonde"] = sonde_pts
        print(f"  {'Sonde':12s} -- {len(sondes)} profiles")

    # -- Phase 3: daily aggregation -------------------------------------------
    print("\n-- Phase 3: Daily aggregation --")

    daily = {}
    for name, pts in sorted(all_data.items()):
        d = daily_mean(pts)
        daily[name] = d
        if d:
            print(f"  {name:12s} -- {len(d)} days  [{min(d)} -> {max(d)}]")

    # Build a union of all dates
    all_dates = sorted(set().union(*[set(d.keys()) for d in daily.values()]))
    print(f"\n  Total unique days: {len(all_dates)}")

    # -- Phase 4: comparison table --------------------------------------------
    print("\n-- Phase 4: Comparison table --")
    print()

    instruments = sorted(all_data.keys())
    header = f"{'Date':12s}"
    for name in instruments:
        header += f" {name:>12s}"
    print(header)
    print("-" * len(header))

    for d in all_dates:
        row = f"{d!s:12s}"
        has_data = False
        for name in instruments:
            if d in daily.get(name, {}):
                mean_v, std_v, n, _, _ = daily[name][d]
                if n == 1:
                    row += f" {mean_v:>10.1f}  "
                else:
                    row += f" {mean_v:>10.1f}*"
                has_data = True
            else:
                row += f" {'-':>12s}"
        if has_data and sum(1 for name in instruments if d in daily.get(name, {})) >= 2:
            print(row)

    # -- Phase 5: pairwise statistics -----------------------------------------
    print("\n-- Phase 5: Pairwise statistics --")
    print()

    for i, name1 in enumerate(instruments):
        for name2 in instruments[i + 1:]:
            d1 = daily.get(name1, {})
            d2 = daily.get(name2, {})
            common = sorted(set(d1) & set(d2))
            if len(common) < 1:
                continue
            v1 = [d1[d][0] for d in common]
            v2 = [d2[d][0] for d in common]
            diff = np.array(v1) - np.array(v2)
            bias = np.mean(diff)
            rmsd = np.sqrt(np.mean(diff ** 2))
            corr = np.corrcoef(v1, v2)[0, 1] if len(common) >= 3 else float("nan")
            print(f"  {name1:12s} vs {name2:12s}:  N={len(common):3d}  "
                  f"bias={bias:+7.2f}  RMSD={rmsd:6.2f}  R={corr:.3f}")

    # -- Phase 6: plot --------------------------------------------------------
    print("\n-- Phase 6: Plot --")

    n_inst = len(instruments)
    fig, axes = plt.subplots(n_inst, n_inst, figsize=(3 * n_inst, 3 * n_inst))
    fig.suptitle("Ground Instrument Pairwise Comparison - Sodankyla",
                 fontsize=14, fontweight="bold")

    for i, name1 in enumerate(instruments):
        for j, name2 in enumerate(instruments):
            ax = axes[i, j] if n_inst > 1 else axes
            d1 = daily.get(name1, {})
            d2 = daily.get(name2, {})
            common = sorted(set(d1) & set(d2))

            if i == j:
                # Diagonal: histogram of daily values
                vals = [d1[d][0] for d in d1]
                ax.hist(vals, bins=15, color="#888", edgecolor="white", alpha=0.7)
                ax.set_title(name1, fontsize=9)
                continue

            if not common:
                ax.text(0.5, 0.5, "no overlap", ha="center", va="center",
                        transform=ax.transAxes, fontsize=8, color="#999")
                continue

            v1 = [d1[d][0] for d in common]
            v2 = [d2[d][0] for d in common]

            ax.scatter(v1, v2, s=20, c="#1f77b4", edgecolors="white", linewidths=0.3, alpha=0.7)
            lims = [min(ax.get_xlim()[0], ax.get_ylim()[0]),
                    max(ax.get_xlim()[1], ax.get_ylim()[1])]
            ax.plot(lims, lims, "k--", alpha=0.3, linewidth=0.8)
            ax.set_xlim(lims)
            ax.set_ylim(lims)

            diff_vals = np.array(v1) - np.array(v2)
            bias = np.mean(diff_vals)
            rmsd = np.sqrt(np.mean(diff_vals ** 2))
            corr = np.corrcoef(v1, v2)[0, 1] if len(common) >= 3 else float("nan")

            ax.text(0.05, 0.95, f"N={len(common)}\nbias={bias:.1f}\nRMSD={rmsd:.1f}\nR={corr:.2f}",
                    transform=ax.transAxes, fontsize=7, va="top",
                    bbox=dict(boxstyle="round,pad=0.3", facecolor="white", alpha=0.8))

            if j == 0:
                ax.set_ylabel(name2, fontsize=8)
            if i == n_inst - 1:
                ax.set_xlabel(name1, fontsize=8)

    plt.tight_layout()
    out_path = Path("plots/ground_comparison_matrix.png")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(str(out_path), dpi=150)
    print(f"  Matrix plot: {out_path}")
    plt.close()

    # Time series overlay
    fig, ax = plt.subplots(figsize=(12, 5))
    for name in instruments:
        pts = all_data.get(name, [])
        if not pts:
            continue
        style = STYLES.get(name, {"color": "#888", "marker": "o", "label": name})
        dts = [p[0] for p in pts]
        vals = [p[1] for p in pts]
        ax.scatter(dts, vals, s=6, color=style["color"], marker=style.get("marker", "o"),
                   label=style["label"], alpha=0.6, edgecolors="none")
    ax.set_xlabel("Date")
    ax.set_ylabel("Total Ozone (DU)")
    ax.set_title("Ground-based Total Column Ozone - Sodankyla")
    ax.legend(fontsize=8, markerscale=2, ncol=2)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
    fig.autofmt_xdate()
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    out_path2 = Path("plots/ground_comparison_timeseries.png")
    plt.savefig(str(out_path2), dpi=150)
    print(f"  Timeseries:  {out_path2}")
    plt.close()

    print("\nDone.")


if __name__ == "__main__":
    run()
