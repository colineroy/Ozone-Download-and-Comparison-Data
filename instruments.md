# Instruments

| Instrument | Type | File Format | Auto Download | Unit Conversion | Status |
|---|---|---|---|---|---|
| SAOZ | Ground | Text | Yes (HTTP) | Direct (DU) | Active |
| Pandora | Ground | Text | Yes https://api.pandonia-global-network.org/v1 | x2241 (mol/m2 to DU) | Active |
| Brewer | Ground | B-files / txt | Yes https://eubrewnet.aemet.es/eubrewnet | Direct (DU) | Active |
| BTS | Ground | CSV | No (local file) | Direct (DU) | Active |
| Ozonesonde (ECC) | Ground | SHARP ASCII | No (local file) | Layer integration, scaled to COL1 | Active |
| S5P TROPOMI | Satellite | NetCDF4 | Yes https://download.dataspace.copernicus.eu | x2241 (mol/m2 to DU) | Active |
| GOME-2B | Satellite | HDF5 | Yes pip install eumdac | Direct (DU) | Active |
| GOME-2C | Satellite | HDF5 | Yes pip install eumdac | Direct (DU) | Active |
| GOME-2A | Satellite | nc | No (decommissioned) | — | Inactive |
| OMI | Satellite | HDF5 (he5) | Yes https://avdc.gsfc.nasa.gov/pub/most_popular/overpass/OMI/OMTO3/ | x0.01 to DU | Active (placeholder credentials) |
| OMPS (Suomi-NPP) | Satellite | HDF5 / nc | Yes (CMR API) | — | Active (placeholder credentials) |
| OMPS (NOAA-20) | Satellite | HDF5 / nc | Yes (CMR API) | — | Active (placeholder credentials) |
