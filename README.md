# Ozone Instrument Comparison - Sodankylä, Finland

Multi-instrument comparison of total column ozone and vertical ozone profiles at the Sodankylä FMI station (67.37°N, 26.63°E), part of the NDACC network.

## Scripts

| Script | Purpose |
|---|---|
| `gs_comparison.py` | Total column O3 comparison - ground + satellite instruments |
| `gs_profile_comparison.py` | Vertical ozone profile comparison - sonde, S5P PR, GOME-2 NTO, OMI OMO3PR |
| `gs_comparison_gui.py` | Dash web GUI wrapping `gs_comparison` readers (port 8050) |

## Supported Instruments

| Instrument | Type | Source | Auto-download | Units |
|---|---|---|---|---|
| SAOZ | Ground | `http://saoz.obs.uvsq.fr/saoz/O3_YYYY.SK` | Direct download (no login) | DU |
| Pandora | Ground | PGN REST API (`api.pandonia-global-network.org`) | API (no login) | mol/m² → �-2241 → DU |
| Brewer #037 / #214 | Ground | FMI portal ([hav.fmi.fi](https://hav.fmi.fi/hav/asema/?fmisid=101932&page=obs)) | Local files (manual) | DU |
| BTS | Ground | Local CSV files in `ground/BTS/BTS_data/` | Local files (manual) | DU |
| Ozonesonde (ECC) | Ground | SHARP-format files in `ground/sondes/sondes_data/` | Local files (manual) | DU (COL1) |
| S5P TROPOMI | Satellite | Copernicus Data Space OData API | API (credentials required) | mol/m² → �-2241 → DU |
| GOME-2A / GOME-2B / GOME-2C | Satellite | NRT: `eumdac` (EUMETSAT coll. `EO:EUM:DAT:METOP:NTO`) / Archive: NASA AVDC (`https://avdc.gsfc.nasa.gov`) | NRT: API (credentials req.) / Archive: direct HTTP (no login) | DU |
| OMI (Aura) | Satellite | NASA GES DISC via CMR (`https://cmr.earthdata.nasa.gov`) | API (credentials required) | DU (�-0.01) |
| OMPS (Suomi-NPP) | Satellite | NASA GES DISC via CMR (`https://cmr.earthdata.nasa.gov`) | API (credentials required) | DU |

## Quick Start

### Getting started

1. **Install Git** from https://git-scm.com/ (if not already installed)
2. Open a terminal and clone the repository:
   ```bash
   git clone https://github.com/colineroy/Ozone-Download-and-Comparison-Data.git
   cd Ozone-Download-and-Comparison-Data
   ```
3. **Install Python dependencies** (recommended: use a virtual environment):
   ```bash
   python -m venv venv
   venv\Scripts\activate    # Windows
   # source venv/bin/activate   # Mac/Linux
   pip install -r requirements.txt
   ```
4. **Choose a comparison script to run:**

   | Command | What it does |
   |---|---|
   | `python gs_comparison.py` | Total column O3 comparison - all ground + satellite instruments |
   | `python gs_profile_comparison.py` | Vertical ozone profile comparison - sonde, S5P, GOME-2, OMI |
   | `python gs_comparison_gui.py` | Interactive Dash web interface at http://127.0.0.1:8050 |

### Credentials

Create a `.env` file at the project root with the following variables.
Register on each service to obtain your credentials:

| Service | Used by | Where to register | `.env` variables |
|---|---|---|---|
| Copernicus Data Space | S5P TROPOMI | https://dataspace.copernicus.eu/ | `COPERNICUS_USER`, `COPERNICUS_PASS` |
| EUMETSAT Data Store | GOME-2 | https://data.eumetsat.int/ → profile → API Keys | `EUMETSAT_KEY`, `EUMETSAT_SECRET` |
| EUBREWNET | Brewer (API, restricted) | https://eubrewnet.aemet.es/eubrewnet/default/registration | `EUBREWNET_USER`, `EUBREWNET_PASS` (optional) |
| NASA Earthdata | OMI, OMPS | https://urs.earthdata.nasa.gov/ | `EARTHDATA_USER`, `EARTHDATA_PASS` |

Example `.env` file:

```
COPERNICUS_USER=your_email@example.com
COPERNICUS_PASS=your_password
EUMETSAT_KEY=your_consumer_key
EUMETSAT_SECRET=your_consumer_secret
# EUBREWNET_USER=your_username    # optional (API restricted)
# EUBREWNET_PASS=your_password
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
| `SONDE_DIR` | `./ground/sondes/sondes_data` | Ozonesonde data directory |
| `S5P_PR_DIR` | `./satellite/S5P/s5p_data/profile` | S5P profile NetCDF directory |
| `GOME2_DIR` | `./satellite/GOME2/GOME2_data` | GOME-2 HDF5 directory |
| `AVDC_OMI_H5` | `./satellite/OMI/omi_data/satellite_aura_omi_l2ovp_omo3pr_sodankyla.h5` | AVDC OMI profile HDF5 |

### `gs_comparison_gui.py`

No configuration file needed. Date range is selected interactively in the web interface.

## Standalone Downloaders

Each instrument with auto-download has a dedicated script. Edit `DATE_START` and `DATE_END` at the top of the script, then run it directly to download data for a specific period without running the full comparison pipeline.

| Instrument | Script | Command | Config Variables |
|---|---|---|---|
| SAOZ | `ground/SAOZ/download_saoz.py` | `python SAOZ/download_saoz.py` | `STATION`, `DATE_START`, `DATE_END` |
| Pandora | `ground/Pandora/download_pandora.py` | `python Pandora/download_pandora.py` | `PAN_ID`, `DATE_START`, `DATE_END` |
| S5P TROPOMI | `satellite/S5P/S5Pozone.py` | `python satellite/S5P/S5Pozone.py` | `DATE_START`, `DATE_END`, Copernicus credentials |
| GOME-2 (NRT) | `satellite/GOME2/gome2_download.py` | `python satellite/GOME2/gome2_download.py` | `DATE_START`, `DATE_END`, EUMETSAT credentials |
| GOME-2 (Archive) | `satellite/GOME2/gome2_download.py` (auto-downloads AVDC txt) | same command | no credentials needed |
| OMI | `satellite/OMI/download_omi.py` | `python satellite/OMI/download_omi.py` | `DATE_START`, `DATE_END`, Earthdata credentials |
| OMPS | `satellite/OMPS/download_omps.py` | `python satellite/OMPS/download_omps.py` | `DATE_START`, `DATE_END`, Earthdata credentials |

Credentials are read from the `.env` file (see [Credentials](#credentials)).

BTS, Brewer, and ozonesonde data must be placed manually - there are no download scripts.

## Pipeline

All comparison scripts follow a 3-phase pattern:

1. **Phase 1 - Download/cache**: Check local cache; download missing files from APIs.
2. **Phase 2 - Read**: Parse raw measurement points (no daily averaging).
3. **Phase 3 - Plot**: Generate comparison plots in `plots/`.

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
+-- ground/
|   +-- Brewer/
|   |   +-- README.md                 # How to get Brewer data (FMI manual)
|   |   +-- brewer_data/              # FMI CSV files
|   |   +-- download_brewer.py
|   +-- BTS/
|   |   +-- README.md                 # How to get BTS data
|   |   +-- BTS_data/                 # Local BTS CSV files
|   |   +-- BTS_OZON_Sodanklya.zip
|   +-- FTIR/                         # Placeholder for future FTIR data
|   +-- Pandora/
|   |   +-- README.md                 # How to get Pandora data
|   |   +-- download_pandora.py
|   |   +-- pandora_data/             # Pandonia L2 text files
|   +-- SAOZ/
|   |   +-- README.md                 # How to get SAOZ data
|   |   +-- download_saoz.py
|   |   +-- saoz_data/                # Raw + parsed SAOZ data
|   |       +-- csvSAOZ/
|   +-- sondes/
|       +-- README.md                 # How to get ozonesonde data
|       +-- sondes_data/              # Ozonesonde files (SHARP format)
|           +-- parluku2.m                # MATLAB SHARP parser
|           +-- SondeInfo.m               # MATLAB metadata extractor
|           +-- table.m                   # MATLAB inventory generator
+-- satellite/
|   +-- GOME2/
|   |   +-- README.md                 # How to get GOME-2 data
|   |   +-- gome2_download.py         # Downloads NRT HDF5 + AVDC archive
|   |   +-- GOME2_data/               # GOME-2 NRT HDF5 files
|   |   +-- GOME2_avdc/               # GOME-2 archive text files (AVDC)
|   +-- MLS/
|   |   +-- MLS_download.py           # MLS data downloader
|   |   +-- ecc_mls_comparison.py     # ECC vs MLS profile comparison
|   |   +-- mls_data/
|   |       +-- ozone/                # MLS ozone HDF5
|   |       +-- hno3/                 # MLS HNO3 HDF5
|   +-- OMI/
|   |   +-- README.md                 # How to get OMI data
|   |   +-- download_omi.py
|   |   +-- omi_data/
|   |       +-- aura_omi_l2ovp_omto3_col4_v8.5_sodankyla_262.txt   # OMTO3 total column (AVDC)
|   |       +-- aura_omi_l2ovp_omdoao3_v03_sodankyla_262.txt       # OMDOAO3 DOAS total column (AVDC)
|   |       +-- satellite_aura_omi_l2ovp_omo3pr_sodankyla.h5        # OMO3PR profile (AVDC)
|   +-- OMPS/
|   |   +-- README.md                 # How to get OMPS data
|   |   +-- download_omps.py
|   |   +-- omps_data/
|   |   |   +-- suomi_npp_omps_l2ovp_nmto3_v2.1_sodankyla_262.txt # NMTO3 overpass (AVDC)
|   |   |   +-- noaa21_profile/        # NOAA-21 LP-L2-O3-DAILY daily profiles (AVDC)
|   +-- S5P/
|       +-- README.md                 # How to get S5P TROPOMI data
|       +-- S5Pozone.py               # TROPOMI downloader
|       +-- s5p_data/
|           +-- total_column/         # S5P total column NetCDF
|           +-- profile/              # S5P profile NetCDF
+-- plots/                        # Generated comparison plots
```

## Dependencies

```bash
pip install requests numpy matplotlib scipy h5py python-dotenv
pip install xarray netCDF4
pip install beautifulsoup4 lxml     # SAOZ downloader
pip install eumdac                   # GOME-2 downloader
pip install dash plotly              # GUI
```

A `requirements.txt` is provided at the project root:

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
- See `ground/SAOZ/README.md` for details.
- Standalone download: edit `STATION`, `DATE_START`, `DATE_END` in `ground/SAOZ/download_saoz.py`, then run `python ground/SAOZ/download_saoz.py`.

### Pandora
- L2 files from PGN API, column 39 = total column O3 (mol/m²).
- Conversion: 1 mol/m² = 2241 DU.
- See `ground/Pandora/README.md` for details.
- Standalone download: edit `PAN_ID`, `DATE_START`, `DATE_END` in `ground/Pandora/download_pandora.py`, then run `python ground/Pandora/download_pandora.py`.

### Brewer
- Data manually downloaded from FMI portal: https://hav.fmi.fi/hav/asema/?fmisid=101932&page=obs
- Brewers #037 (MkII) and #214 — columns `OZONE #37 (DU)` and `OZONE #214 (DU)`.
- Place the CSV in `ground/Brewer/brewer_data/` — the reader detects it automatically.
- The EUBREWNET REST API also exists but requires special authorisation (a web
  account alone is not sufficient). See `ground/Brewer/README.md` for details.

### BTS (Brewer-TOCON-Solar array spectroradiometer)
- CSV format: `Time (ISO 8601, GMT), Airmass, Ozone (DU), ...`
- Place files manually in `ground/BTS/BTS_data/`.
- See `ground/BTS/README.md` for details.

### Ozonesonde (ECC)
- SHARP ASCII format, trigger line matching `Sodankyla`.
- Total column from `COL1` field.
- Ascension ~2h window starting at ~08:30 UTC.
- See `ground/sondes/README.md` for details.
- MATLAB parsers available in `ground/sondes/sondes_data/` for raw SHARP data.

### S5P TROPOMI
- NetCDF4, group `PRODUCT`, variable `ozone_total_vertical_column` (mol/m²).
- Dimensions: `(time, scanline, ground_pixel)`.
- Filtered by `qa_value > 0.5` and co-located within `±0.5°`.
- Files ~100 MB (total column) to ~150 MB (profile) each.
- See `satellite/S5P/README.md` for details.
- Standalone download: edit `DATE_START`, `DATE_END` in `satellite/S5P/S5Pozone.py`, then run `python satellite/S5P/S5Pozone.py`.

### GOME-2
Two complementary data sources:

**1. NRT (EUMETSAT Data Store)** — last ~60 days
- HDF5 files via `eumdac` (MetOp-B + MetOp-C).
- Collection `EO:EUM:DAT:METOP:NTO` - Near Real-Time Total Column O3.
- Credentials required in `.env`: `EUMETSAT_KEY`, `EUMETSAT_SECRET`.
- See `satellite/GOME2/README.md` for details.

**2. Archive (NASA AVDC)** — 2007 to present
- Pre-computed overpass text files for Sodankyla, one file per satellite.
- MetOp-A (2007-2021), MetOp-B (2013-2019 reprocessed), MetOp-C (2019-present).
- Direct HTTP download, **no login required**.
- URL: `https://avdc.gsfc.nasa.gov/pub/data/satellite/MetOp/GOME2/V03/L2OVP/GOME2[B|C]/gome2[b|c]_l2ovp_sodankyla.txt`
- Column `VCD_O3` in DU, overpass within 100 km radius.
- Downloaded automatically by `gome2_download.py` into `satellite/GOME2/GOME2_avdc/`.

Standalone download: edit `DATE_START`, `DATE_END` in `satellite/GOME2/gome2_download.py`, then run `python satellite/GOME2/gome2_download.py`.
It downloads both NRT HDF5 files and AVDC archive text files.

**Note**: AVDC archive points appear more scattered than NRT HDF5 points because they are not quality-filtered (clouds, swath edges) and use a 100 km radius vs ±0.5° for NRT.

### OMI (Aura)
- OMDOAO3 total column from NASA GES DISC via CMR (`https://cmr.earthdata.nasa.gov`, collection `C3454342622-GES_DISC`). Requires NASA Earthdata Login. Alternatively, pre-computed overpass text files from NASA AVDC (`https://avdc.gsfc.nasa.gov`).
- AVDC overpass collocated text and OMO3PR profile HDF5 also supported.
- Conversion factor: �-0.01 to DU.
- See `satellite/OMI/README.md` for details.
- Standalone download: edit `DATE_START`, `DATE_END` in `satellite/OMI/download_omi.py`, then run `python satellite/OMI/download_omi.py`.

### OMPS (Suomi-NPP)
- NMTO3 total column from NASA GES DISC via CMR (`https://cmr.earthdata.nasa.gov`, collection `C1386443916-GES_DISC`). Requires NASA Earthdata Login. Also available as AVDC overpass text file (`https://avdc.gsfc.nasa.gov`).
- NOAA-21 OMPS LP-L2-O3-DAILY ozone profiles from NASA AVDC (`https://avdc.gsfc.nasa.gov/pub/data/satellite/NOAA21/OMPS/L2OVP/LP-L2-O3-DAILY_v1.0/`). Used by `gs_profile_comparison.py`.
- AVDC collocated text file also supported.
- See `satellite/OMPS/README.md` for details.
- Standalone download: edit `DATE_START`, `DATE_END` in `satellite/OMPS/download_omps.py`, then run `python satellite/OMPS/download_omps.py`.

## Notes

- All instruments plotted on a shared continuous datetime axis.
- SAOZ sunrise (SR) and sunset (SS) annotations are shown separately.
- Pandora and S5P conversion: 1 mol/m² = 2241 DU (0.159 mol/m² ≈ 356 DU).
- S5P returns ~2-3 orbits per day over Sodankylä.
- Ozonesondes show total column as a constant horizontal line over the ~2h ascent.
- The Dash GUI loads all 9 instruments concurrently via `ThreadPoolExecutor`.
