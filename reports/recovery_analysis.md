# Recovery analysis and trade-offs

## What the original errors showed

V1 Auto had spatial RMSE 2.681 mS/cm at 72 sites lacking Sentinel-2, compared with 1.551 at 277 covered sites. Their mean EC differed substantially, 4.226 versus 1.499 mS/cm. Six 2024 records and 32 of the 2025 records had EC at or above 5 mS/cm. V1 Auto's mean error on the 38 spatial high-EC records was −3.780 mS/cm. These comparisons describe association and range compression. They do not separate masked land cover, sampling footprint mismatch, location, or season. See [coverage by region and EC band](../results/coverage.csv) and [per-site diagnostics](../results/site_audit.csv).

## Recovery experiments

- **Acquisition:** Landsat provided valid data at 325 sites, including 54 of the 72 original gaps. Either source was valid at 331 sites. High-EC coverage went from 14 to 30 of 38. Every site had at least one eligible Landsat scene footprint. The 18 remaining optically unmatched sites had no accepted pixel under the combined source rules. All 47 eligible Landsat scenes were read. GLO-30 derivatives were complete at 348 sites.
- **Training:** Main regressors received the same enriched predictor access. Prespecified four-trial controls isolated feature groups, availability flags, log targets and high-EC weighting. All fits reused archived buffered inner and outer memberships. Under identical four-trial settings, the full-input ExtraTrees spatial RMSE was 1.779 compared with 1.729 after omitting Landsat. On the 72 originally missing-Sentinel sites, full inputs increased paired MAE by 0.062 mS/cm (95% block interval [0.003, 0.128]). Better coverage did not imply lower error in this matched contrast.
- **Architecture:** MISA's gate gave RMSE 1.763, versus 1.773 with global weights and 1.792 with equal weights on the same experts. The gap to the best scored comparator remained +0.033 mS/cm (interval [−0.051, 0.095]). The method-inspired XGBoost spline and the single inner winner were also evaluated. The residual-correction follow-up stayed inside the outer training partitions. Four of six inner analyses preferred no correction, one preferred shrinkage 0.25 and one preferred 0.50. No outer score is assigned to this follow-up.

## Narrow finding at high EC

| Same-family four-trial comparison | Weighted minus unweighted high-EC MAE | 95% paired spatial-block interval | Pooled RMSE, unweighted → weighted |
| --- | ---: | ---: | ---: |
| Huber gradient boosting | −0.420 | [−0.625, −0.146] | 1.772 → 1.845 |
| Random forest | −0.402 | [−0.430, −0.315] | 1.823 → 1.890 |
| ExtraTrees | −0.329 | [−0.380, −0.142] | 1.779 → 1.824 |

Errors are in mS/cm. Each row uses the same 38 high-EC held-out sites and matched model-family search budgets. In this reanalysis, high-EC loss weighting reduced subgroup error across three families at an overall RMSE cost. This is a trade-off, not a general winning claim. The six spatial blocks limit inferential precision.

[Paired aggregate differences](../results/paired_deltas.csv) · [Subgroup contrasts](../results/subgroup_deltas.csv) · [Development-only correction results](../results/development_residual_correction.csv)
