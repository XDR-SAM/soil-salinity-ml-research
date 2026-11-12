# Soil salinity prediction in coastal Bangladesh

Secondary analysis of **349 measured 1:5 soil–water electrical conductivity records** from two field campaigns in coastal southwestern Bangladesh. The pipeline evaluates geographic extrapolation and both directions of campaign transfer with recorded train–test splits. It compares spatial interpolation and location-only regression with publicly retrievable Sentinel-2 and elevation predictors.

**Manuscript:** [IEEE conference-format PDF](paper/main.pdf) · [LaTeX](paper/main.tex) · [bibliography](paper/references.bib)

**Research outputs:** [metrics](results/metrics.csv) · [predictions](results/predictions.csv) · [paired intervals](results/paired_deltas.csv) · [workflow](figures/workflow.svg) · [supplement](supplementary/README.md)

## Source data

The original field data and assay belong to the Zenodo creators. The 2024 and 2025 releases are [10.5281/zenodo.14560019](https://doi.org/10.5281/zenodo.14560019) and [10.5281/zenodo.19711551](https://doi.org/10.5281/zenodo.19711551). Both records specify CC BY 4.0. See the [data guide](data/README.md) for attribution, workbook notices, the Copernicus Sentinel-2 and DSM sources, and the [manifest](data/manifest.json) for verified hashes. Original XLSX and raster files are retrieved at runtime. No credentials are required for the pinned sources.

## Reproduce

Tested on Windows 11 x64 using CPython 3.14.3 and an AMD Ryzen 5 5600 CPU. GPU is unnecessary. `requirements.txt` pins direct dependencies. [requirements-lock.txt](requirements-lock.txt) records the full dependency set from the fresh Windows environment. The [run environment](results/versions.json) includes model and data package versions. Install Tectonic for the Python reproduction entry point or use a TeX Live installation with latexmk and IEEEtran for the shell build. Tectonic 0.17.0 was used for the archived PDF. Its initial setup requires network access for TeX files.

```powershell
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements.txt
.venv/Scripts/python scripts/reproduce.py --smoke
.venv/Scripts/python scripts/reproduce.py --jobs 4 --compiler tectonic
```

On Linux or macOS, use `.venv/bin/python` and install the platform equivalents. Those environments were not exercised here. Remote raster reads may take several minutes, depending on range request latency. Four concurrent outer-fold workers fit on CPU, with each fit limited to one thread. The experiment log records measured runtimes.

Individual steps:

```text
python scripts/download_originals.py
python scripts/build_dataset.py
python scripts/audit_satkhira.py
python scripts/fetch_remote_sensing.py --snapshot
python scripts/fetch_elevation.py
python scripts/train_models.py --jobs 4
python scripts/evaluate.py
python scripts/make_figures.py
python scripts/paper_numbers.py
```

Use `scripts/build_paper.ps1 -Compiler tectonic` or `sh scripts/build_paper.sh` and finish with `python -m pytest -q`. The satellite snapshot pins the catalog items and asset metadata. Omitting `--snapshot` queries the live catalog and can change the available scenes. The smoke run downloads and verifies the originals, audits records and exercises the split/fitting path with a reduced coordinate-only grid. Smoke outputs are local under `data/derived/smoke`.

## Experiment card

| Experiment | Status | Design |
| --- | --- | --- |
| Field audit and source hashes | Executed | Both versioned releases and all 349 field rows |
| Sentinel-2 and GLO-30 acquisition | Executed | Pre-collection pixel observations and static surface elevation |
| Track I exact Satkhira comparison | Blocked | Candidate counts match. Author-selected records, exact features, folds and scoring workflow remain unverified. |
| Track II extended spatial CV | Executed | Six pooled geographic folds with 1 km buffers; four buffered inner folds |
| Track III cross-campaign transfer | Executed | Both directions with training-year-only tuning and full target-campaign testing |
| Track IV geographic buffer sensitivity | Executed | Both transfers with 1 km training exclusion |
| Feature reduction and fixed-vs-tuned random forest | Executed | Matched outer predictions with inner-only tuning |
| EBK, stacking/GAM, climate extensions and deep nets | Not attempted | Scope limited to the archived optical/DSM and location benchmark |
| Final experiments with unresolved runtime failures | None | Individual fit warnings, if any, are retained. |

A separate [benchmark audit](reports/comparison.md) explains the comparison boundary with the 2026 preprint. [Limitations and reviewer checks](reports/limitations.md) cover the six-block bootstrap, proxy quality, and the distinct effects of sampling month and location. The manuscript and results are for methodological assessment of point prediction.

## Outputs and attribution

- `data/derived/`: local processing ledger, cleaned field table and extracted feature tables.
- `results/`: exact held-out predictions, membership, feature provenance, search diagnostics, model metrics and paired spatial bootstrap intervals.
- `figures/`: vector PDF/SVG and high-DPI PNG versions.
- `paper/`: IEEEtran manuscript, bibliography and generated numerical macros.
- `reports/`: workbook audit, data dictionary, source and literature verification, and execution record.

Original research software is licensed under MIT. Dataset and asset attributions are listed in [the data guide](data/README.md). Use [CITATION.cff](CITATION.cff) for the project citation.
