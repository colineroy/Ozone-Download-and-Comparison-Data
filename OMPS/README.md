# OMPS (Suomi-NPP) - Ozone data download (NASA)

## Data source

NASA GES DISC via CMR (Common Metadata Repository)
https://cmr.earthdata.nasa.gov

Data portal: https://disc.gsfc.nasa.gov/

## Products

| Product | Collection ID | Description |
|---|---|---|
| NMTO3 | `C1386443916-GES_DISC` | Suomi-NPP total column ozone L2 |

## Prerequisites

- A free NASA Earthdata Login account: https://urs.earthdata.nasa.gov/
- Credentials in `.env`: `EARTHDATA_USER`, `EARTHDATA_PASS` (or `EARTHDATA_TOKEN`)
- Dependencies: `requests`, `h5py`

## Configuration

Edit the top of `download_omps.py`:

| Variable | Default | Description |
|---|---|---|
| `LAT_SITE` | `67.3668` | Station latitude |
| `LON_SITE` | `26.6297` | Station longitude |
| `DELTA` | `0.5` | Co-location window (degrees) |
| `DATE_START` | `"2026-04-15"` | Start date (YYYY-MM-DD) |
| `DATE_END` | `"2026-04-15"` | End date (YYYY-MM-DD) |

## How to download

```bash
# From the OMPS/ directory
python download_omps.py

# Or from the project root
python OMPS/download_omps.py
```

## Output

`omps_data/snpp_total_column/` - HDF5 files (`.h5`).

## File format

- **Format**: HDF5 (`.h5`)
- **Ozone**: total column, units as provided by GES DISC
- An AVDC collocated text file is also read by `gs_comparison.py`
- NOAA-20 OMPS data is not currently configured (check NOAA STAR or CLASS)
