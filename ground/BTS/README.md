# BTS - BiTec Sensor Solar Spectroradiometer ozone data

## Data source

BTS data is provided by FMI (Finnish Meteorological Institute).
Contact FMI to obtain the CSV files.

No public API or auto-download script is available.

## How to get the data

1. Request BTS total column ozone data for Sodankyla from FMI
2. Place the CSV files in `ground/BTS/BTS_data/`
3. The main script `comparaison/gs_comparison.py` will read them automatically

## File format

CSV with columns:

```
Time (ISO 8691, GMT),Airmass,Ozone (DU),Ozone_STD,Ozone_Uncertainty
```

- Header must contain `"Ozone (DU)"` to be detected
- Timestamp format ends with `Z` (UTC)
- Units: DU (Dobson Units) - no conversion needed

Example filename: `20260410_TOC_BTS_66639_V1.csv`

## Output

No output - files are read directly by `comparaison/gs_comparison.py`.
