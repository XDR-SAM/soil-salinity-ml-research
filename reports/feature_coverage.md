# Sentinel-2 and terrain coverage

- 2024: 140/162, median 3 days, range 1--26 days.
- 2025: 137/187, median 5 days, range 1--22 days.
- Optical column missing counts: {'uid': 0, 'blue': 72, 'green': 72, 'red': 72, 'nir': 72, 'swir16': 72, 'swir22': 72, 'ndvi': 72, 'ndmi': 72, 'scene': 72, 'acquired_utc': 72, 'lag_days': 72, 'scl': 72, 'scl_row': 72, 'scl_col': 72}.
- DEM missing: 0.
- DEM tiles: Copernicus_DSM_COG_10_N22_00_E088_00_DEM, Copernicus_DSM_COG_10_N22_00_E089_00_DEM, Copernicus_DSM_COG_10_N23_00_E088_00_DEM, Copernicus_DSM_COG_10_N23_00_E089_00_DEM.
- Native spectral pixels are 10 m and 20 m. SCL is native 20 m.
- Per-row source IDs, lags, SCL cells and elevation tile URLs are in `results/covariate_provenance.csv`.
