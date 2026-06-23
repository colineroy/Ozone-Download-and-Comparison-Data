# SAOZ — Ozone & NO2 data download

Downloads total column O3 and NO2 from the SAOZ network
(http://saoz.obs.uvsq.fr/).

## What gets downloaded

`download_saoz.py` fetches yearly files from:

    http://saoz.obs.uvsq.fr/saoz/O3_YYYY.STATIONCODE

Each file contains **one line per day** with two measurements (sunrise + sunset):

| Column   | Description                                      |
|----------|--------------------------------------------------|
| O3sr     | Ozone at sunrise (Dobson units)                  |
| O3ss     | Ozone at sunset (Dobson units)                   |
| dO3sr    | O3 sunrise uncertainty                           |
| dO3ss    | O3 sunset uncertainty                            |
| NO2sr    | NO2 at sunrise (×1e15 mol/cm²)                   |
| NO2ss    | NO2 at sunset (×1e15 mol/cm²)                    |
| dNO2sr   | NO2 sunrise uncertainty                          |
| dNO2ss   | NO2 sunset uncertainty                           |

Output:
- **Raw file**: `saoz_data/O3_YYYY.STATIONCODE`
- **Parsed CSV**: `saoz_data/STATIONCODE/saoz_STATIONCODE_START_END.csv`

## Configuration

Edit the top of `download_saoz.py`:

| Variable | Default | Description |
|---|---|---|
| `STATION` | `"SK"` | Station code (see table below) |
| `DATE_START` | `"2025-04-15"` | Start date (YYYY-MM-DD) |
| `DATE_END` | `"2025-04-15"` | End date (YYYY-MM-DD) |
| `BASE_URL` | `"http://saoz.obs.uvsq.fr/saoz"` | SAOZ data server |
| `OUT_DIR` | `Path("./saoz_data")` | Output directory |

### Station codes

| Code | Station            | Lat     |
|------|--------------------|---------|
| SK   | Sodankyla (FMI)    | 67°N    |
| NY   | Ny-Alesund         | 78°N    |
| SC   | Scoresby-Sund      | 71°N    |
| EU   | Eureka             | 80°N    |
| SS   | Kangerlussuaq      | 67°N    |
| OH   | OHP (France)       | 44°N    |
| RE   | Réunion            | 21°S    |
| KR   | Kerguelen          | 49°S    |
| RG   | Rio Gallegos       | 52°S    |
| DD   | Dumont d'Urville   | 67°S    |
| DO   | Dome C / Concordia | 75°S    |
| PA   | Paris              | 49°N    |
| GU   | Guyancourt         | 49°N    |

## How to download

```bash
# From the SAOZ/ directory
python download_saoz.py

# Or from the project root
python SAOZ/download_saoz.py
```

No login required — data is public.
