"""
Brewer — Ozone analysis and visualization for Sodankyla

Reads Brewer files downloaded from EUBREWNET.
Supported formats: .txt, .csv, .dat, .B* (B-files)
"""

from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime

DATA_DIR = Path("./brewer_data")


def parse_brewer_file(file_path):
    """Parse a Brewer file and extract ozone column + time."""
    ext = file_path.suffix.lower()
    name = file_path.name

    # B* files (Brewer raw data) — compact format
    if name.startswith("B") and (ext in [".037", ".214"] or len(name) > 3 and name[1:6].isdigit()):
        return parse_bfile(file_path)

    # CSV / TXT
    try:
        data = np.genfromtxt(file_path, comments=["#", "'", "!"], dtype=None, encoding="latin1")
    except Exception:
        return None

    if data is None or len(data) == 0:
        return None

    return {"file": name, "raw": data}


def parse_bfile(file_path):
    """Attempt to parse a Brewer B-file."""
    try:
        with open(file_path, "r", encoding="latin1") as f:
            lines = f.readlines()
    except Exception:
        return None

    results = {"file": file_path.name}
    o3_values = []

    for line in lines:
        # B-files often have O3 on lines with a specific format
        parts = line.split()
        if len(parts) >= 5:
            try:
                # Ozone column is often at variable positions
                vals = [float(p) for p in parts if p.replace(".", "").replace("-", "").isdigit()]
                if 100 < vals[-1] < 600:  # DU range plausible
                    o3_values.append(vals[-1])
            except (ValueError, IndexError):
                pass

    if o3_values:
        results["o3_mean"] = np.mean(o3_values)
        results["o3_std"] = np.std(o3_values)
        results["n"] = len(o3_values)
    return results if "o3_mean" in results else None


def read_ozone_from_text(file_path):
    """Extract total column ozone from a Brewer text file."""
    try:
        with open(file_path, "r", encoding="latin1") as f:
            lines = f.readlines()
    except Exception:
        return None

    o3 = []
    times = []
    for line in lines:
        if line.startswith("#") or line.startswith("'") or line.strip() == "":
            continue
        parts = line.split()
        try:
            # Look for an ozone column value in the line
            for p in parts:
                try:
                    v = float(p)
                    if 100 < v < 600:  # DU range
                        o3.append(v)
                        break
                except ValueError:
                    pass
        except (ValueError, IndexError):
            continue

    if o3:
        return {"o3_mean": np.mean(o3), "o3_std": np.std(o3), "n": len(o3)}
    return None


def main():
    print("=== Brewer Ozone Analysis — Sodankyla ===\n")

    # Scan all files in brewer_data/
    files = sorted(DATA_DIR.rglob("*"))
    files = [f for f in files if f.is_file() and f.suffix.lower() in [".037", ".214", ".txt", ".csv", ".dat"]]

    print(f"Found {len(files)} Brewer file(s) in {DATA_DIR}\n")

    results = []
    for f in files:
        print(f"  {f.relative_to(DATA_DIR.parent)}...", end=" ")
        r = parse_brewer_file(f)
        if r and "o3_mean" in r:
            results.append(r)
            print(f" O3={r['o3_mean']:.1f} +/- {r['o3_std']:.1f} DU ({r['n']} measurements)")
        elif r:
            print(f" {len(files)} lines read (no O3 detected)")
        else:
            print(" unparsed")

    if not results:
        print("\nNo Brewer data parsed.")
        print("First download files with download_brewer.py")
        return

    o3_vals = [r["o3_mean"] for r in results]
    print(f"\n{'='*50}")
    print(f"  Summary: {len(results)} file(s)")
    print(f"  Mean O3 : {np.mean(o3_vals):.1f} DU")
    print(f"  Min/Max : {np.min(o3_vals):.1f} / {np.max(o3_vals):.1f} DU")


if __name__ == "__main__":
    main()
