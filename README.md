# Optical coverage recovery and soil salinity prediction in coastal Bangladesh

This project reanalyzes 349 field measurements of 1:5 soil–water extract electrical conductivity from the 2024 and 2025 campaigns. It evaluates MISA, a missingness-informed spatial ensemble, on archived buffered spatial folds and both campaign transfers. [IEEE manuscript](paper/main.pdf) · [Editable LaTeX](paper/main.tex) · [Executive summary](EXECUTIVE_SUMMARY.md)

| Buffered spatial procedure | RMSE (mS/cm) | MAE (mS/cm) | R² |
| --- | ---: | ---: | ---: |
| ExtraTrees without Landsat, lowest observed RMSE | 1.729 | 1.244 | 0.350 |
| MISA | 1.763 | 1.237 | 0.325 |
| V1 Auto | 1.842 | 1.312 | 0.263 |

Landsat recovered 54 of 72 Sentinel-2 gaps, raising optical coverage to 331 of 349 sites. MISA reduced RMSE relative to V1 Auto by 0.079 mS/cm (4.31%, paired 95% spatial-block interval [−0.146, −0.017]). The strongest-comparator comparison did not establish overall superiority. The study reuses previously examined campaigns. [Claims and evidence](CLAIMS_AND_EVIDENCE.md) · [Publication readiness](PUBLICATION_READINESS.md) · [Recovery analysis](reports/recovery_analysis.md)

## Verify and compile the archived study

Use CPython 3.14 and Tectonic. Create and activate an isolated environment before installing the pinned dependencies.

```text
python -m venv .venv
python -m pip install -r code/requirements.txt
python -m pytest -q code/tests
```

To build the paper with the bundled numerical macros and figures, run the following commands from the project root. Tectonic invokes BibTeX and can fetch standard TeX packages on first use.

```text
cd paper
tectonic --keep-logs main.tex
```

The v3.0.0 release includes the PDF, the full reproducible project ZIP, and the Overleaf source ZIP. Upload the Overleaf ZIP as a project and select `main.tex` as the main document. Use XeLaTeX to match the verified local build.

## Reproduce the experiments

For a new execution of the frozen benchmark, run from the root:

```text
python code/run_all.py --jobs 4 --compiler tectonic
```

This command fits the archived procedures on CPU and regenerates analysis outputs. The default uses bundled feature tables and fixed split memberships. Add `--verify-originals` to retrieve and verify the workbook originals. Run `python code/scripts/download_originals.py` to check workbook provenance without running the benchmark. The optional `--refresh-new-features` reacquires Landsat and terrain before analysis. Upstream changes can cause checksum differences. Keep the release snapshot separate when rerunning acquisition or fitting. Run `python code/scripts/development.py` for the separate training-only residual-correction study.

The inputs come from the official Zenodo releases [10.5281/zenodo.14560019](https://doi.org/10.5281/zenodo.14560019) and [10.5281/zenodo.19711551](https://doi.org/10.5281/zenodo.19711551). The workbooks and full rasters are retrieved from their sources. The permitted derived tables are bundled. [Provenance and data rights](data/README.md)

## Project structure

| Path | Contents |
| --- | --- |
| [paper/](paper/) | Final IEEE PDF, editable LaTeX, frozen numerical macros, and bibliography |
| [code/](code/) | Training, evaluation, feature acquisition, packaging, tests, dependencies, and the frozen protocol |
| [results/](results/) | Held-out predictions, metrics, paired differences, subgroups, fit logs, and selected hyperparameters |
| [figures/](figures/) | All seven figures in PDF, SVG, and PNG, including the proposed framework |
| [data/](data/) | Official sources, checksums, data licenses, and derived inputs |
| [reports/](reports/) | Protocol, literature review, data audit, and reproducibility checks |
| [archive/v1/](archive/v1/) | Historical source and selected baseline evidence |

Code is MIT-licensed. Source datasets and imagery follow the terms documented in the data guide. Cite the study using [CITATION.cff](CITATION.cff). [Final verification report](reports/final_submission_qa.md)
