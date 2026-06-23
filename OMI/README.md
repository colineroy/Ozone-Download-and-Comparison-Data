# OMI (Aura) - Ozone data download (NASA)

## Data source

NASA GES DISC via CMR (Common Metadata Repository)
https://cmr.earthdata.nasa.gov

Data portal: https://disc.gsfc.nasa.gov/

## Products

| Product | Collection ID | Description |
|---|---|---|
| OMDOAO3 | `C3454342622-GES_DISC` | Total column ozone v004 |
| OMPROFOZ | `C3581239399-GES_DISC` | Ozone vertical profile v004 |

## Prerequisites

- A free NASA Earthdata Login account: https://urs.earthdata.nasa.gov/
- Credentials in `.env`: `EARTHDATA_USER`, `EARTHDATA_PASS` (or `EARTHDATA_TOKEN`)
- Dependencies: `requests`, `h5py`, `python-dateutil`

## Configuration

Edit the top of `download_omi.py`:

| Variable | Default | Description |
|---|---|---|
| `LAT_SITE` | `67.3668` | Station latitude |
| `LON_SITE` | `26.6297` | Station longitude |
| `DELTA` | `0.5` | Co-location window (degrees) |
| `DATE_START` | `"2026-04-15"` | Start date (YYYY-MM-DD) |
| `DATE_END` | `"2026-04-15"` | End date (YYYY-MM-DD) |

## How to download

```bash
# From the OMI/ directory
python download_omi.py

# Or from the project root
python OMI/download_omi.py
```

## Output

| Directory | Contents |
|---|---|
| `omi_data/total_column/` | OMDOAO3 HDF5 files (`.he5` or `.nc`) |
| `omi_data/profile/` | OMPROFOZ HDF5 files |

## File format

- **Format**: HDF-EOS5 (`.he5`) or NetCDF
- **Total column O3**: conversion factor �-0.01 to DU
- An AVDC collocated text file is also read by `gs_comparison.py`
