# Ozone Instrument Comparison — Sodankylä, Finland

Multi-instrument comparison of total column ozone and vertical ozone profiles at the Sodankylä FMI station (67.37°N, 26.63°E), part of the NDACC network.

## Scripts

| Script | Purpose |
|---|---|
| `gs_comparison.py` | Total column O3 comparison — ground + satellite instruments |
| `gs_profile_comparison.py` | Vertical ozone profile comparison — sonde, S5P PR, GOME-2 NTO, OMI OMO3PR |
| `gs_comparison_gui.py` | Dash web GUI wrapping `gs_comparison` readers (port 8050) |

## Supported Instruments

| Instrument | Type | Source | Auto-download | Units |
|---|---|---|---|---|
| SAOZ | Ground | `http://saoz.obs.uvsq.fr/saoz/O3_YYYY.SK` | Yes (HTTP) | DU |
| Pandora | Ground | PGN REST API (`api.pandonia-global-network.org`) | Yes (REST) | mol/m² → ×2241 → DU |
| Brewer #037 / #214 | Ground | EUBREWNET (`eubrewnet.aemet.es`) | Via `download_brewer.py` | DU |
| BTS | Ground | Local CSV files in `BTS/BTS_data/` | No (manual) | DU |
| Ozonesonde (ECC) | Ground | SHARP-format files in `sondes/` | No (manual) | DU (COL1) |
| S5P TROPOMI | Satellite | Copernicus Data Space OData API | Yes (OAuth2) | mol/m² → ×2241 → DU |
| GOME-2B / GOME-2C | Satellite | EUMETSAT Data Store (`eumdac`) | Yes (OAuth) | DU |
| OMI (Aura) | Satellite | NASA Earthdata CMR API / AVDC | Yes | DU (×0.01) |
| OMPS (Suomi-NPP) | Satellite | NASA Earthdata CMR API / AVDC | Yes | DU |

## Instrument Documentation

Each instrument folder contains technical documentation and instrument-specific README files:

| Document | Location | Description |
|---|---|---|
| Instrument Reference | `instruments.md` | Full instrument table with status, format, unit conversion |
| SAOZ README | `SAOZ/README.md` | SAOZ download config, station codes, data format |
| Pandora README | `Pandora/README.md` | Pandora download config, product codes, API details |
| SAOZ Technical Doc | `SAOZ/SAOZ_Technical_Documentation.pdf` | SAOZ instrument technical manual |
| Pandora Technical Doc | `Pandora/Pandora_Technical_Documentation.docx` | Pandora instrument technical manual |
| Brewer Technical Doc | `Brewer/Brewer_Technical_Documentation.docx` | Brewer instrument technical manual |
| BTS Technical Doc | `BTS/BTS_Technical_Documentation.docx` | BTS instrument technical manual |

## Quick Start

```bash
# Total column comparison (ground + satellite)
python gs_comparison.py

# Vertical profile comparison
python gs_profile_comparison.py

# Web GUI (Dash)
python gs_comparison_gui.py
# Open http://127.0.0.1:8050
```

### Credentials

Create a `.env` file (see `.env` template) with:

```
COPERNICUS_USER=your_email
COPERNICUS_PASS=your_password
EUMETSAT_KEY=your_key
EUMETSAT_SECRET=your_secret
EUBREWNET_USER=your_username
EUBREWNET_PASS=your_password
EARTHDATA_USER=your_username
EARTHDATA_PASS=your_password
```

## Configuration

Edit the `CONFIG` section at the top of each script.

### `gs_comparison.py`

| Variable | Default | Description |
|---|---|---|
| `DATE_START` | `"2026-04-10"` | Period start (YYYY-MM-DD) |
| `DATE_END` | `"2026-04-16"` | Period end (YYYY-MM-DD) |
| `DOWNLOAD["SAOZ"]` | `True` | Download SAOZ if not cached |
| `DOWNLOAD["Pandora"]` | `True` | Download Pandora if not cached |
| `DOWNLOAD["S5P"]` | `True` | Download S5P (requires Copernicus credentials) |
| `DOWNLOAD["GOME2"]` | `True` | Download GOME-2 (requires EUMETSAT credentials) |
| `S5P_RADIUS` | `0.5` | Spatial co-location window (degrees) |
| `S5P_QA_MIN` | `0.5` | Quality assurance threshold |

### `gs_profile_comparison.py`

| Variable | Default | Description |
|---|---|---|
| `DATE_START` | `"2026-04-15"` | Period start |
| `DATE_END` | `"2026-04-15"` | Period end |
| `SONDE_DIR` | `./sondes` | Ozonesonde data directory |
| `S5P_PR_DIR` | `./S5P/s5p_data/profile` | S5P profile NetCDF directory |
| `GOME2_DIR` | `./GOME2/GOME2_data` | GOME-2 HDF5 directory |
| `AVDC_OMI_H5` | `./OMI/omi_data/npp_omo3pr_sodankyla.h5` | AVDC OMI profile HDF5 |

### `gs_comparison_gui.py`

No configuration file needed. Date range is selected interactively in the web interface.

## Standalone Downloaders

Each instrument with auto-download has a dedicated script. Edit `DATE_START` and `DATE_END` at the top of the script, then run it directly to download data for a specific period without running the full comparison pipeline.

| Instrument | Script | Command | Config Variables |
|---|---|---|---|
| SAOZ | `SAOZ/download_saoz.py` | `python SAOZ/download_saoz.py` | `STATION`, `DATE_START`, `DATE_END` |
| Pandora | `Pandora/download_pandora.py` | `python Pandora/download_pandora.py` | `PAN_ID`, `DATE_START`, `DATE_END` |
| S5P TROPOMI | `S5P/S5Pozone.py` | `python S5P/S5Pozone.py` | `DATE_START`, `DATE_END`, Copernicus credentials |
| GOME-2 | `GOME2/gome2_download.py` | `python GOME2/gome2_download.py` | `DATE_START`, `DATE_END`, EUMETSAT credentials |
| Brewer | `Brewer/download_brewer.py` | `python Brewer/download_brewer.py` | `BREWER_IDS`, `DATE_START`, `DATE_END`, EUBREWNET credentials |
| OMI | `OMI/download_omi.py` | `python OMI/download_omi.py` | `DATE_START`, `DATE_END`, Earthdata credentials |
| OMPS | `OMPS/download_omps.py` | `python OMPS/download_omps.py` | `DATE_START`, `DATE_END`, Earthdata credentials |

Credentials are read from the `.env` file (see [Credentials](#credentials)).

BTS and ozonesonde data must be placed manually — there is no download script.

## Pipeline

All comparison scripts follow a 3-phase pattern:

1. **Phase 1 — Download/cache**: Check local cache; download missing files from APIs.
2. **Phase 2 — Read**: Parse raw measurement points (no daily averaging).
3. **Phase 3 — Plot**: Generate comparison plots in `plots/`.

Output filenames include the date range: `gs_comparison_YYYY-MM-DD_YYYY-MM-DD.png`.

## Directory Layout

```
.
+-- gs_comparison.py              # Total column comparison (main)
+-- gs_comparison_gui.py          # Dash web GUI
+-- gs_profile_comparison.py      # Vertical profile comparison
+-- instruments.md                # Instrument reference table
+-- .env                          # Credentials (gitignored)
+-- .gitignore
+-- SAOZ/
|   +-- download_saoz.py
|   +-- saoz_data/                # Raw + parsed SAOZ data
|   +-- SAOZ_Technical_Documentation.pdf
+-- Pandora/
|   +-- download_pandora.py
|   +-- pandora_data/             # Pandonia L2 text files
+-- Brewer/
|   +-- download_brewer.py
|   +-- brewer_plot.py            # Standalone Brewer analysis
+-- BTS/
|   +-- BTS_data/                 # Local BTS CSV files
|   +-- BTS_OZON_Sodanklya.zip
+-- sondes/
|   +-- parluku2.m                # MATLAB SHARP parser
|   +-- SondeInfo.m               # MATLAB metadata extractor
|   +-- table.m                   # MATLAB inventory generator
|   +-- so*.q*                    # Ozonesonde data (SHARP format)
+-- S5P/
|   +-- S5Pozone.py               # TROPOMI downloader
|   +-- s5p_data/total_column/    # S5P total column NetCDF
|   +-- s5p_data/profile/         # S5P profile NetCDF
+-- GOME2/
|   +-- gome2_download.py
|   +-- GOME2_data/               # GOME-2 HDF5 files
+-- OMI/
|   +-- download_omi.py
|   +-- omi_data/total_column/    # OMI OMDOAO3 NetCDF
+-- OMPS/
|   +-- download_omps.py
|   +-- omps_data/snpp_total_column/  # OMPS NMTO3 HDF5
+-- FTIR/                         # Placeholder for future FTIR data
+-- plots/                        # Generated comparison plots
```

## Dependencies

```bash
pip install requests numpy matplotlib scipy h5py python-dotenv
pip install xarray netCDF4
pip install beautifulsoup4 lxml     # Brewer downloader
pip install eumdac                   # GOME-2 downloader
pip install dash plotly              # GUI
```

A `requirements.txt` is recommended:

```
requests>=2.31
numpy>=1.24
matplotlib>=3.7
scipy>=1.10
h5py>=3.8
python-dotenv>=1.0
xarray>=2023.6
netCDF4>=1.6
beautifulsoup4>=4.12
lxml>=4.9
eumdac>=2.2
dash>=2.14
plotly>=5.15
```

## Instrument Notes

### SAOZ
- Data from `http://saoz.obs.uvsq.fr/saoz/O3_YYYY.SK` (sunrise + sunset columns).
- Raw format: `Year Month Day DOY O3sr O3ss dO3sr dO3ss NO2sr NO2ss dNO2sr dNO2ss`
- Sunrise/sunset hours estimated from a 67°N latitude table.
- See `SAOZ/SAOZ_Technical_Documentation.pdf` and `SAOZ/README.md` for details.
- Standalone download: edit `STATION`, `DATE_START`, `DATE_END` in `SAOZ/download_saoz.py`, then run `python SAOZ/download_saoz.py`.

### Pandora
- L2 files from PGN API, column 39 = total column O3 (mol/m²).
- Conversion: 1 mol/m² = 2241 DU.
- See `Pandora/Pandora_Technical_Documentation.docx` and `Pandora/README.md` for details.
- Standalone download: edit `PAN_ID`, `DATE_START`, `DATE_END` in `Pandora/download_pandora.py`, then run `python Pandora/download_pandora.py`.

### Brewer
- Data from EUBREWNET (Brewer #037 MkII, #214).
- Also includes FMI CSV file with Brewer #037 and #214 columns.
- See `Brewer/Brewer_Technical_Documentation.docx` for details.
- Standalone download: edit `BREWER_IDS`, `DATE_START`, `DATE_END` in `Brewer/download_brewer.py`, then run `python Brewer/download_brewer.py`.
- Run `python Brewer/brewer_plot.py` for standalone analysis of downloaded Brewer files.

### BTS
- CSV format: `Time (ISO 8601, GMT), Airmass, Ozone (DU), ...`
- Place files manually in `BTS/BTS_data/`.
- See `BTS/BTS_Technical_Documentation.docx` for details.

### Ozonesonde (ECC)
- SHARP ASCII format, trigger line matching `Sodankyla`.
- Total column from `COL1` field.
- Ascension ~2h window starting at ~08:30 UTC.
- MATLAB parsers available in `sondes/` for raw SHARP data.

### S5P TROPOMI
- NetCDF4, group `PRODUCT`, variable `ozone_total_vertical_column` (mol/m²).
- Dimensions: `(time, scanline, ground_pixel)`.
- Filtered by `qa_value > 0.5` and co-located within `±0.5°`.
- Files ~100 MB (total column) to ~150 MB (profile) each.
- Standalone download: edit `DATE_START`, `DATE_END` in `S5P/S5Pozone.py`, then run `python S5P/S5Pozone.py`.

### GOME-2
- HDF5 files from EUMETSAT Data Store (MetOp-B + MetOp-C).
- Collection `EO:EUM:DAT:METOP:NTO` — Near Real-Time Total Column O3.
- Ozone already in DU.
- Standalone download: edit `DATE_START`, `DATE_END` in `GOME2/gome2_download.py`, then run `python GOME2/gome2_download.py`.

### OMI (Aura)
- OMDOAO3 total column from NASA Earthdata CMR API (NetCDF).
- AVDC overpass collocated text and OMO3PR profile HDF5 also supported.
- Conversion factor: ×0.01 to DU.
- Standalone download: edit `DATE_START`, `DATE_END` in `OMI/download_omi.py`, then run `python OMI/download_omi.py`.

### OMPS (Suomi-NPP)
- NMTO3 total column from NASA Earthdata CMR API (HDF5).
- AVDC collocated text file also supported.
- Standalone download: edit `DATE_START`, `DATE_END` in `OMPS/download_omps.py`, then run `python OMPS/download_omps.py`.

## Notes

- All instruments plotted on a shared continuous datetime axis.
- SAOZ sunrise (SR) and sunset (SS) annotations are shown separately.
- Pandora and S5P conversion: 1 mol/m² = 2241 DU (0.159 mol/m² ≈ 356 DU).
- S5P returns ~2-3 orbits per day over Sodankylä.
- Ozonesondes show total column as a constant horizontal line over the ~2h ascent.
- The Dash GUI loads all 9 instruments concurrently via `ThreadPoolExecutor`.
