# Pandonia — Ozone total column data download

Downloads ozone total column data from the Pandonia Global Network
(https://www.pandonia-global-network.org/).

API: https://api.pandonia-global-network.org/v1

## What gets downloaded

`download_pandora.py` queries the PGN API for a given date and
station, then downloads the first matching Level 2 O3 file.

Output file: `pandora_data/pandonia_SITE_DATE_L2_CODE.txt`

The file contains all measurements for that day with full column
metadata (52 columns including ozone in mol/m², quality flags,
SZA, etc.). Ozone total column is **column 39** (mol/m²).

Convert to DU: multiply by 2241.

## Configuration

Edit the top of `download_pandora.py`:

| Variable | Default | Description |
|---|---|---|
| `SITE` | `"Sodankyla"` | Station name |
| `PAN_ID` | `309` | Pandonia station ID |
| `SPECTROMETER` | `"1"` | Spectrometer number |
| `LEVEL` | `"L2"` | Data level |
| `CODE` | `"rout2"` | Product code (see table below) |
| `DATE_START` | `"2026-04-30"` | Start date (YYYY-MM-DD) |
| `DATE_END` | `"2026-04-30"` | End date (YYYY-MM-DD) |
| `BASE` | `"https://api.pandonia-global-network.org/v1"` | API base URL |
| `OUT_DIR` | `Path("./pandora_data")` | Output directory |

### Common codes

| Code   | Product               |
|--------|-----------------------|
| rout2  | Ozone total column    |
| rno2   | NO2 total column      |
| raer   | Aerosol optical depth |

## How to download

```bash
# From the Pandora/ directory
python download_pandora.py

# Or from the project root
python Pandora/download_pandora.py
```

No login required — data is public.
