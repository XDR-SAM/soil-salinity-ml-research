# Claims and evidence

| Claim | Evidence and scope |
| --- | --- |
| Alternative optical coverage recovered 54 original gaps. | `results/coverage.csv` and per-site lineage in `results/feature_provenance.csv`. Same 349 rows. |
| Lowest descriptive spatial RMSE was 1.729 for ET no_landsat. | `results/metrics.csv`, one pooled comparison across the archived six folds. It is a descriptive ranking of many evaluated procedures. |
| MISA vs V1 Auto and retrospectively identified ExtraTrees. | Paired RMSE deltas -0.079 [-0.146, -0.017] and +0.017 [-0.057, +0.071] mS/cm. |
| MISA vs the strongest matched comparator (ET no_landsat). | Paired RMSE difference +0.033 [-0.051, +0.095] mS/cm. See `paired_deltas.csv` and `verdict.json`. |
| High-EC MAE and optical missingness. | `subgroups.csv` and `subgroup_deltas.csv`. Differences are conditional on observed groups and six resampling blocks. |
| Exact 2026 published benchmark superiority. | Unavailable. Row identity, covariates, folds and exact scoring code were unverified. |
| Causality, general deployment or external validation. | Unsupported. Observed campaigns differ in month and site support, and prior outcomes were known. |
