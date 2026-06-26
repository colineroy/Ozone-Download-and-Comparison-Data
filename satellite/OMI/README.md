# OMI (Aura) - Ozone data download (NASA)

## Data sources

### 1. NASA GES DISC (full orbit granules via CMR)

NASA GES DISC via CMR (Common Metadata Repository)
https://cmr.earthdata.nasa.gov

Data portal: https://disc.gsfc.nasa.gov/

| Product | Collection ID | Description |
|---|---|---|
| OMDOAO3 | `C3454342622-GES_DISC` | Total column ozone v004 |
| OMPROFOZ | `C3581239399-GES_DISC` | Ozone vertical profile v004 |

### 2. NASA AVDC (pre-computed overpass files, no auth required)

https://avdc.gsfc.nasa.gov/pub/data/satellite/Aura/OMI/V03/L2OVP/

| File | Source |
|---|---|
| `aura_omi_l2ovp_omto3_col4_v8.5_sodankyla_262.txt` | OMTO3 total column |
| `aura_omi_l2ovp_omdoao3_v03_sodankyla_262.txt` | OMDOAO3 DOAS total column |
| `satellite_aura_omi_l2ovp_omo3pr_sodankyla.h5` | OMO3PR ozone profile |

The script downloads AVDC files automatically (no auth needed).

## Prerequisites

- For CMR download: NASA Earthdata Login account: https://urs.earthdata.nasa.gov/
- Credentials in `.env`: `EARTHDATA_USER`, `EARTHDATA_PASS` (or `EARTHDATA_TOKEN`)
- Dependencies: `requests`, `h5py`, `python-dateutil`

## Configuration

Edit the top of `satellite/OMI/download_omi.py`:

| Variable | Default | Description |
|---|---|---|
| `LAT_SITE` | `67.3668` | Station latitude |
| `LON_SITE` | `26.6297` | Station longitude |
| `DELTA` | `0.5` | Co-location window (degrees) |
| `DATE_START` | `"2026-04-15"` | Start date (YYYY-MM-DD) |
| `DATE_END` | `"2026-04-15"` | End date (YYYY-MM-DD) |

## How to download

```bash
# From the project root
python satellite/OMI/download_omi.py
```

## Output

`satellite/OMI/omi_data/` — OMDOAO3/OMPROFOZ HDF5 granules (via CMR) + AVDC overpass text files (via HTTP).

## File format

- **Format**: HDF-EOS5 (`.he5`) or NetCDF
- **Total column O3**: conversion factor ~-0.01 to DU
- AVDC text files are read by `gs_comparison.py` and `gs_profile_comparison.py`
