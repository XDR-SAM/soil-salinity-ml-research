# Source data and rights

The original workbook measurements were collected and assayed by the Zenodo creators. Both versioned records specify CC BY 4.0. See [the manifest](manifest.json) for exact filenames, version, DOI, authors and MD5/SHA-256 checksums. The workbook footers retain copyright notices. Original workbooks are retrieved on request rather than redistributed.

- 2024, 162 observations. [Zenodo DOI 10.5281/zenodo.14560019](https://doi.org/10.5281/zenodo.14560019)
- 2025, 187 observations, published in 2026. [Zenodo DOI 10.5281/zenodo.19711551](https://doi.org/10.5281/zenodo.19711551)
- Sentinel-2, Collection-1 Level-2A. Contains modified Copernicus Sentinel data (2024–2025). See the pinned Earth Search catalogs.
- Landsat 8/9 Collection 2 Level-2 surface reflectance and QA, USGS, delivered via Planetary Computer. The STAC snapshot records asset filenames and metadata including checksums where supplied. No signed URLs are bundled. [USGS Landsat data](https://www.usgs.gov/landsat-missions/landsat-collection-2-surface-reflectance)
- Produced using Copernicus WorldDEM-30 © DLR e.V. 2010-2014 and © Airbus Defence and Space GmbH 2014-2018 provided under COPERNICUS by the European Union and ESA. All rights reserved. EO data provided under COPERNICUS by the European Union and ESA. See `terrain_tiles.json` for product identifiers and upstream ETags. [GLO-30 source](https://registry.opendata.aws/copernicus-dem/)

The bundle includes extracted per-site values and study results with attribution. It contains no raw rasters, lab contacts or credentials. EC is in mS/cm for a 1:5 extract. Projected coordinates are metres in EPSG:32645. Surface elevation and relief are in metres, slope is rise/run and reflectance is unitless. Image acquisition dates are interpreted in Asia/Dhaka for the pre-collection cutoff. Landsat QA uses bits 0–5 and 7 and an all-zero saturation flag. Scene availability and lag are used as predictors, while raw QA codes are reserved for the audit.
