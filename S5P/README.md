# S5P TROPOMI — Ozone data download (Copernicus)

## Data source

Copernicus Data Space Ecosystem
https://dataspace.copernicus.eu

API: https://catalogue.dataspace.copernicus.eu/odata/v1/Products

## Products

| Product | Description | Size |
|---|---|---|
| `L2__O3____` | Total column ozone | ~100 MB/file |
| `L2__O3__PR_` | Ozone vertical profile | ~150 MB/file |

## Prerequisites

- A free Copernicus Data Space account: https://dataspace.copernicus.eu/
- Credentials in `.env`: `COPERNICUS_USER`, `COPERNICUS_PASS`
- Dependencies: `requests`, `xarray`, `netCDF4`

## Configuration

Edit the top of `S5Pozone.py`:

| Variable | Default | Description |
|---|---|---|
| `LAT_SITE` | `67.3668` | Station latitude |
| `LON_SITE` | `26.6297` | Station longitude |
| `DELTA` | `0.5` | Co-location window (degrees) |
| `DATE_START` | `"2026-04-15"` | Start date (YYYY-MM-DD) |
| `DATE_END` | `"2026-04-15"` | End date (YYYY-MM-DD) |

## How to download

```bash
# From the S5P/ directory
python S5Pozone.py

# Or from the project root
python S5P/S5Pozone.py
```

## Output

| Directory | Contents |
|---|---|
| `s5p_data/total_column/` | Total column NetCDF files (L2__O3____) |
| `s5p_data/profile/` | Profile NetCDF files (L2__O3__PR_) |

## File format

- **Format**: NetCDF4
- **Group**: `PRODUCT`
- **Variable**: `ozone_total_vertical_column` (mol/m²)
- **Dimensions**: `(time, scanline, ground_pixel)`
- **Conversion to DU**: multiply by 2241
- **Filtering**: `qa_value > 0.5`, co-located within ±0.5° of station
