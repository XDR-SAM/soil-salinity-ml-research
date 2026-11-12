# Quality assurance and reviewer self-critique

## Verified

- Both raw XLSX files matched the published MD5 values and the locally recorded SHA-256 values. The parser accounted for 349 field rows, two laboratory rows per workbook, the true headers and two copyright footers. All field rows passed eligibility.
- Eight tests passed in a clean CPython environment. They covered source hashes and data integrity, the predictor allowlist, fold-local preprocessing, metric and IDW calculations, archive disjointness and spatial distances, image acquisition dates and index calculations, inner-only model selection, and manuscript dependencies.
- The archived predictions contain 58,632 unique procedure/site/track values. The nearest observed spatial test-to-training separation was 1.161 km. Both main transfers used only the opposite campaign's labels for training. The two buffered transfers and all inner splits passed the 1 km exclusion test.
- The clean-environment smoke run started from freshly retrieved workbooks. A second full fit from the archived covariates reproduced all seven benchmark files checked byte for byte. Both source campaigns were independently spot-checked against pinned Sentinel-2 assets. This is a full model reproduction from the archived feature table and a targeted repeat check of the optical retrieval.
- Seven figure families were rendered in PDF, SVG and high-DPI PNG. The clean evaluation rerendered all seven PNGs byte for byte. The regenerated paper matched the archived text and raster on all seven pages.
- The manuscript was compiled with Tectonic and IEEEtran. All pages were rasterized and inspected at 118 dpi. The build has no unresolved citations or references, BibTeX errors, or overfull boxes. Remaining TeX diagnostics concern underfull line or float spacing, and Tectonic's Windows Fontconfig initialization. Embedded Times-style text fonts and rendered glyphs were checked.
- Printed benchmark values were checked against the generated macros and source CSV. The layout review corrected a crowded workflow, sample-obscuring map legends, comparison-table alignment, and late figure placement.
- The source evidence table records the five primary comparison candidates, separates classification from regression and records peer-review status. The precise obstacle to a matched 2026 comparison is documented in [comparison.md](comparison.md).

## Remaining scientific weaknesses

The strongest outcome is the matched comparison to local geographic baselines under the study's own protocol. An uncertainty interval based on six spatial groups has limited resolution and does not cover model refitting or a new campaign. The study has two sampling windows, different site support, uneven optical availability and limited training data at high EC. The substantial high-EC underprediction and near-zero transfer R² are particularly important for application. The Satkhira preprint is methodologically related, but no direct performance ranking follows from these tests. See the [limitations report](limitations.md).
