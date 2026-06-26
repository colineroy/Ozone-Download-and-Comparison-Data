# GOME-2 - Ozone data download

Two complementary data sources for total column O3 at Sodankyla:

| Source | Period | Format | Auth |
|---|---|---|---|
| NRT (EUMETSAT Data Store) | Last ~60 days | HDF5 (`.HDF5`) | EUMETSAT API key |
| Archive (NASA AVDC) | 2007-present | Text files (`.txt`) | None (HTTP) |

## Source 1: NRT (EUMETSAT Data Store)

Collection: `EO:EUM:DAT:METOP:NTO` — Near Real-Time Total Column O3

### Prerequisites
- Free account: https://data.eumetsat.int/
- API keys: https://api.eumetsat.int/api-key/
- `.env`: `EUMETSAT_KEY`, `EUMETSAT_SECRET`
- `pip install eumdac`

### Configuration

Edit the top of `satellite/GOME2/gome2_download.py`:

| Variable | Default | Description |
|---|---|---|
| `LAT` | `67.37` | Station latitude |
| `LON` | `26.63` | Station longitude |
| `DELTA` | `0.5` | Bounding box half-width (degrees) |
| `DATE_START` | `"2026-06-13"` | Start date (YYYY-MM-DD) |
| `DATE_END` | `"2026-06-14"` | End date (YYYY-MM-DD) |
| `COLLECTION_ID` | `"EO:EUM:DAT:METOP:NTO"` | EUMETSAT collection |

### Output

`satellite/GOME2/GOME2_data/` — HDF5 files with original filenames.
Ozone in DU (no conversion needed).

---

## Source 2: Archive (NASA AVDC)

Pre-computed overpass text files collocated at Sodankyla (67.367N, 26.630E).

### URL

```
https://avdc.gsfc.nasa.gov/pub/data/satellite/MetOp/GOME2/V03/L2OVP/
```

### Files

| Satellite | File | Period |
|---|---|---|
| MetOp-A (GOME-2A) | `GOME2A/gome2a_l2ovp_sodankyla.txt` | 2007-01 — 2021 |
| MetOp-B (GOME-2B) | `GOME2B/gome2b_l2ovp_sodankyla.txt` | 2013-01 — 2019-02 |
| MetOp-C (GOME-2C) | `GOME2C/gome2c_l2ovp_sodankyla.txt` | 2019-01 — present |

### Columns (space-separated)

| Column | Description | Units |
|---|---|---|
| `Datetime` | ISO timestamp `YYYYMMDDTHHMMSSmmmZ` | - |
| `DOY` | Day of year | - |
| `Day` | Days since 1950-01-01 | - |
| `Orbit` | Orbit number | - |
| `Scan` | Pixel index within scan | - |
| `Lat.` | Pixel center latitude | deg |
| `Lon.` | Pixel center longitude | deg |
| `Dist.` | Distance from station | km |
| `SZA` | Solar zenith angle | deg |
| `Cld.Fr.` | OCRA cloud fraction | - |
| `Cld.Pr.` | OCRA cloud pressure | mbar |
| `VCD_O3` | Total column O3 | **DU** |
| `VCD_BrO` / `VCD_H2O` / ... | Other trace gases | various |

Fill values: `-1.0000e+00` for O3, other gases similar.

### Download (auto)

`gome2_download.py` downloads all 3 files automatically into `satellite/GOME2/GOME2_avdc/`.
No credentials needed.

---

## How to run

```bash
# From project root - downloads both NRT HDF5 + AVDC archive
python satellite/GOME2/gome2_download.py
```

### Notes

**Why do AVDC points form a "band" while NRT HDF5 points are cleaner?**

NRT HDF5 points (`read_gome2_raw`) are quality-filtered (`qa_col == 0`) and use a small spatial bbox (+-0.5 deg, ~22 x 55 km). Only the best-quality pixels pass through, producing tighter vertical scatter.

AVDC text files (`read_gome2_avdc_raw`) include **all** valid pixels within a **100 km** radius -- up to 15-20 pixels per overpass (the 24 GOME-2 swath pixels over 2-3 scan lines). No quality filter is applied (clouds, swath edges, high SZA all pass through). This produces a wider dispersion ("band") in the comparison plot.

## Reader in gs_comparison.py

Both sources are read and merged points under the same satellite keys:

| Key in STYLES | Source(s) |
|---|---|
| `GOME2A` | AVDC text file |
| `GOME2B` | AVDC text file + NRT HDF5 (if available) |
| `GOME2C` | AVDC text file + NRT HDF5 (if available) |
