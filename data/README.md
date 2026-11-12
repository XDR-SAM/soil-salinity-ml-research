# Data acquisition and rights

The source field measurements were collected and assayed by Showmitra Kumar Sarkar and the collaborators credited in each Zenodo record. This repository contains a secondary computational analysis.

- **March 2024** — [Zenodo 14560019](https://doi.org/10.5281/zenodo.14560019), v1, 162 observations. See the [2025 Scientific Data descriptor](https://doi.org/10.1038/s41597-025-05447-1).
- **April 2025** — [Zenodo 19711551](https://doi.org/10.5281/zenodo.19711551), v1, 187 observations, released in 2026.
- Both versioned Zenodo records specify [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). The source worksheets also retain copyright notices in their footers. Download the versioned originals using the script. The raw spreadsheets, contacts, and full processing table are excluded from Git. Derived figures and analysis tables containing or reflecting the source measurements carry the same attribution, with transformations described in the paper and reports. The software license does not relicense the source records.
- Sentinel-2 Collection-1 L2A observations are Copernicus Sentinel data from 2024 and 2025, processed through Element 84 Earth Search. The pinned JSON snapshots list source assets and file checksums. No imagery is bundled.
- Copernicus DEM GLO-30 Public, 2021 release, was accessed on November 12, 2026 from the [AWS Open Data Registry](https://registry.opendata.aws/copernicus-dem/). Produced using Copernicus WorldDEM-30 © DLR e.V. 2010-2014 and © Airbus Defence and Space GmbH 2014-2018 provided under COPERNICUS by the European Union and ESA; all rights reserved. EO data provided under COPERNICUS by the European Union and ESA. No elevation rasters are bundled. [Copernicus attribution terms](https://doi.org/10.5270/esa-c5d3d65)
- The independent Satkhira boundary check uses [geoBoundaries gbOpen](https://www.geoboundaries.org/), CC BY 4.0. The repository records its pinned URL and feature ID without bundling boundary geometry.

See [manifest.json](manifest.json) for the original filenames, publication dates, credit, MD5, SHA-256 and retrieval locations. The analysis unit is field-measured 1:5 soil–water EC in mS/cm. No conversion to saturated-paste EC or class labels was made.
