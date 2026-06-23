# Brewer — Ozone data download (EUBREWNET)

## Data source

EUBREWNET web portal: https://eubrewnet.aemet.es/eubrewnet

Sodankyla station ID: 18
Brewer instruments: #037 (MkII), #214

## Prerequisites

- A free account at https://eubrewnet.aemet.es/eubrewnet/default/registration
- Credentials in `.env`: `EUBREWNET_USER`, `EUBREWNET_PASS`
- Dependencies: `requests`, `beautifulsoup4`, `lxml`

## Configuration

Edit the top of `download_brewer.py`:

| Variable | Default | Description |
|---|---|---|
| `BREWER_IDS` | `["037", "214"]` | Brewer serial numbers |
| `PRODUCT` | `"ozone"` | Product type (ozone, uv, aod, so2) |
| `LEVEL` | `"1.5"` | Data level (1.5 = NRT, 2.0 = final) |
| `DATE_START` | `"2026-04-15"` | Start date (YYYY-MM-DD) |
| `DATE_END` | `"2026-04-15"` | End date (YYYY-MM-DD) |

## How to download

```bash
# From the Brewer/ directory
python download_brewer.py

# Or from the project root
python Brewer/download_brewer.py
```

## Output

Files saved to `brewer_data/YYYY/` with original EUBREWNET filenames (`.037`, `.214`, `.txt`, `.csv`).

## File format

- **B-files** (`.037`, `.214`): Brewer raw instrument format, multi-line with metadata and ozone values.
- **Text / CSV**: Tabular data with columns including ozone in DU.
- **Units**: DU (Dobson Units) — no conversion needed.

## Standalone analysis

```bash
python brewer_plot.py
```

Parses downloaded files and prints O3 summary statistics.
