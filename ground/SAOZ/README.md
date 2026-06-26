# SAOZ - Ozone & NO2 data download

Downloads total column O3 and NO2 from the SAOZ network
(http://saoz.obs.uvsq.fr/).

## What gets downloaded

`download_saoz.py` fetches the yearly file from:

    http://saoz.obs.uvsq.fr/saoz/O3_YYYY.STATIONCODE

Just set the `YEAR` you want — it downloads the **entire year** in one file (~1 sec)
and automatically converts it to CSV.

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
- **Raw file**: `ground/SAOZ/saoz_data/O3_YYYY.STATIONCODE`
- **CSV file**: `ground/SAOZ/saoz_data/csvSAOZ/saoz_STATIONCODE_YEAR.csv`

## Configuration

Edit the top of `ground/SAOZ/download_saoz.py`:

| Variable | Default | Description |
|---|---|---|
| `STATION` | `"SK"` | Station code (see table below) |
| `YEAR` | `2024` | Year to download |
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
# From the project root
python ground/SAOZ/download_saoz.py
```

No login required — data is public. The raw file is saved and the CSV is
generated automatically.
