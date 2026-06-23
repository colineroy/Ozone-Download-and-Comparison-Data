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
SZA, etc.).

## Configuration

Edit the top of `download_pandora.py`:

```python
SITE = "Sodankyla"
PAN_ID = 309
SPECTROMETER = "1"
LEVEL = "L2"
CODE = "rout2"          # rout2 = ozone total column
DATE_START = "2026-04-15"
DATE_END   = "2026-04-15"
```

### Common codes

| Code   | Product               |
|--------|-----------------------|
| rout2  | Ozone total column    |
| rno2   | NO2 total column      |
| raer   | Aerosol optical depth |

## Run

```bash
python download_pandora.py
```

No login required — data is public.
