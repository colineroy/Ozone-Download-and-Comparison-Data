# GOME-2 — Ozone data download (EUMETSAT)

## Data source

EUMETSAT Data Store
https://data.eumetsat.int

Collection: `EO:EUM:DAT:METOP:NTO` (Near Real-Time Total Column O3)

Platforms: MetOp-B and MetOp-C

## Prerequisites

- A free EUMETSAT account: https://data.eumetsat.int/
- API key and secret from https://data.eumetsat.int/profile/
- Credentials in `.env`: `EUMETSAT_KEY`, `EUMETSAT_SECRET`
- Dependencies: `eumdac` (`pip install eumdac`)

## Configuration

Edit the top of `gome2_download.py`:

| Variable | Default | Description |
|---|---|---|
| `LAT_SITE` | `67.3668` | Station latitude |
| `LON_SITE` | `26.6297` | Station longitude |
| `DATE_START` | `"2026-04-10"` | Start date (YYYY-MM-DD) |
| `DATE_END` | `"2026-04-16"` | End date (YYYY-MM-DD) |
| `COLLECTION_ID` | `"EO:EUM:DAT:METOP:NTO"` | EUMETSAT collection |

## How to download

```bash
# From the GOME2/ directory
python gome2_download.py

# Or from the project root
python GOME2/gome2_download.py
```

## Output

`GOME2/GOME2_data/` — HDF5 files with original EUMETSAT filenames.

## File format

- **Format**: HDF5 (`.HDF5`)
- **Ozone**: already in DU — no conversion needed
- Contains latitude, longitude, time, quality assurance, and O3 fields
- Near Real-Time product (NTO)
