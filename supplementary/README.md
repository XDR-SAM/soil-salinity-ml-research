# Supplementary analysis

| Question | Auditable artifact |
| --- | --- |
| Which rows entered training, validation or testing? | [Split membership](../results/splits.csv) |
| Which hyperparameters were considered and which won? | [Per-candidate inner fold scores](../results/inner_scores.csv) and [best parameters](../results/best_params.json) |
| Do errors depend on geographic support? | [Fold-level errors](../results/fold_metrics.csv), nearest-training distance in [predictions](../results/predictions.csv), and [point residual map](../figures/spatial_errors.pdf) |
| How does error vary by EC range or sampling year? | [Stratified error table](../results/subgroups.csv) and [observed–predicted diagnostics](../figures/diagnostics.pdf) |
| How do the campaign EC distributions shift? | [Shift statistics](../results/distribution_shift.json), [distribution plot](../figures/ec_distribution.pdf), and [workbook audit](../reports/data_audit.md) |
| Which predictor groups influence held-out loss? | [Grouped permutation results](../results/importance.csv) and [plot](../figures/permutation.pdf) |
| What can we infer about a different model's advantage? | [Paired RMSE contrasts](../results/paired_deltas.csv); negative differences favor the first model in each row. |
| What scenes and DEM tiles were used? | [Per-record provenance](../results/covariate_provenance.csv), [scene selection log](../results/scene_log.csv), and [coverage report](../reports/feature_coverage.md) |

The interval resamples six spatial groups and uses matched predictions. It is conditional on the fitted procedures and study areas. Differences between non-aligned published protocols are described in the [comparison audit](../reports/comparison.md).

## Defending the analysis

- **Why two types of holdout?** The spatial test measures prediction into withheld regions while allowing both campaigns in training. The transfer tests require a model trained on a single campaign to predict the other campaign.
- **What does the matched comparison show?** On the same 349 held-out sites in spatial CV, all-predictor Auto reduced RMSE against IDW by 0.168 mS/cm. The 2024-to-2025 paired interval includes zero, and both transfer R² values are close to zero.
- **What does near-zero or negative R² mean?** R² divides held-out squared prediction error by squared deviations from the held-out response mean. Negative R² means prediction error exceeds that descriptive reference. The separate training-mean baseline is fit without the test labels.
- **Why is the Satkhira comparison unresolved?** Matching sample counts under an independent district polygon cannot verify the same row membership, raster values, folds, or scoring workflow.
- **Can the model be used for high-EC decisions?** The 38 spatial test observations at or above 5 mS/cm were underpredicted by 3.780 mS/cm on average. This benchmark provides no coverage guarantee for individual sites.
