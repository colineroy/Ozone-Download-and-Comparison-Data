# Ozonesonde (ECC) - Vertical ozone profile data

## Data source

Ozonesonde data is provided by FMI (Finnish Meteorological Institute).
Sondes are launched at Sodankyla (~08:30 UTC) as part of the NDACC program.

Contact FMI or download from the NDACC database: https://www.ndaccdemo.org/

No auto-download script is available.

## How to get the data

1. Obtain SHARP-format sonde files (`.q*` extension) from FMI or NDACC
2. Place the files in `sondes/`
3. The main scripts will read them automatically

File naming pattern: `soYYMMDD.qXX` (e.g. `so260415.q08`)

## File format

SHARP ASCII format:

- Multi-line header with metadata
- Trigger line containing `"Sodankyla"` for station identification
- Date from header line 7 (YYYY MM DD)
- Launch hour from the line after `"Sodankyla"`
- Total column ozone (`COL1`) from field index 10 after trigger line
- Units: DU (Dobson Units)

## MATLAB parsers

Additional tools for raw SHARP data are in `sondes/`:

| Script | Purpose |
|---|---|
| `parluku2.m` | Parse raw SHARP binary/ASCII file into arrays |
| `SondeInfo.m` | Extract metadata (launch time, ECC serial, flow rate) |
| `table.m` | Generate sonde inventory spreadsheet |
