# OMPS (Suomi-NPP / NOAA-21) - Ozone data download (NASA)

## Data sources

### 1. NASA AVDC (pre-computed overpass files, no auth required)

#### Suomi-NPP NMTO3 (total column)

https://avdc.gsfc.nasa.gov/pub/data/satellite/Suomi_NPP/L2OVP/NMTO3-L2/

| File | Source |
|---|---|
| `suomi_npp_omps_l2ovp_nmto3_v2.1_sodankyla_262.txt` | NMTO3 total column overpass |

#### NOAA-21 LP-L2-O3-DAILY (ozone profile)

https://avdc.gsfc.nasa.gov/pub/data/satellite/NOAA21/OMPS/L2OVP/LP-L2-O3-DAILY_v1.0/

One text file per day, stored under `noaa21_profile/`:

The script downloads this file automatically (no auth needed).

### 2. NASA GES DISC (full orbit HDF5 via CMR)

https://cmr.earthdata.nasa.gov

| Product | Collection ID | Description |
|---|---|---|
| NMTO3 | `C1386443916-GES_DISC` | Suomi-NPP total column ozone L2 |

## Prerequisites

- For CMR download: NASA Earthdata Login account: https://urs.earthdata.nasa.gov/
- Credentials in `.env`: `EARTHDATA_USER`, `EARTHDATA_PASS` (or `EARTHDATA_TOKEN`)
- Dependencies: `requests`, `h5py`

## Configuration

Edit the top of `satellite/OMPS/download_omps.py`:

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
python satellite/OMPS/download_omps.py
```

## Output

- `satellite/OMPS/omps_data/` — NMTO3 HDF5 granules (via CMR) + NMTO3 AVDC overpass text file (via HTTP).
- `satellite/OMPS/omps_data/noaa21_profile/` — NOAA-21 LP-L2-O3-DAILY daily profile text files (via AVDC HTTP). Read by `comparaison/gs_profile_comparison.py`.

## File format

- **NMTO3**: HDF5 (`.h5`) — total column, units as provided by GES DISC; AVDC text file read by `comparaison/gs_comparison.py`
- **NOAA-21 LP-L2-O3-DAILY**: Text (`.txt`) — daily limb profile, O3 VMR (ppmv) on 60 levels (0.5–60.5 km), converted to DU/layer by `comparaison/gs_profile_comparison.py`
- NOAA-20 OMPS data is not currently configured (check NOAA STAR or CLASS)
