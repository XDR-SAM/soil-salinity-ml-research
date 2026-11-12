# Experiment log

The full study evaluated all 349 eligible workbook records. The candidate grids, target, feature allowlists and spatial split design were committed before inspecting the full held-out scores. The extended and transfer tracks use the same records for every model evaluated within each track.

| Track | Fit and prediction record |
| --- | --- |
| Track I exact Satkhira replication | Blocked. The pinned boundary yields the reported 86 and 119 candidates. The authors' retained row keys, Landsat feature matrix, exact folds and scored calibration implementation remain unavailable. |
| Track II full spatial CV | Executed. Outer test sizes 40, 64, 69, 37, 86 and 53. Outer training sizes after buffering 309, 285, 280, 312, 263 and 296. |
| Track III 2024 → 2025 | Executed. 162 training, 187 test. Training-campaign-only tuning. |
| Track III 2025 → 2024 | Executed. 187 training, 162 test. Training-campaign-only tuning. |
| Track IV 1 km sensitivity | Executed. 154 and 178 training rows in the forward and reverse directions. The test campaigns are unchanged. |
| Exploratory deployment, EBK, GAM or stacking, weather and additional terrain covariates | Not attempted. The executed models are point-prediction benchmarks. |

The full run logged 8,240 candidate/inner-fold fits and 510 selected-parameter outer refits. No estimator warnings were captured in either run log. Per-fit durations totaled 357.6 seconds for inner fits and 26.1 seconds for outer refits, summed across four concurrent workers. Individual outer folds took 34.6–42.4 seconds including selection, refitting and held-out permutations. The machine used an AMD Ryzen 5 5600 CPU on Windows 11 with CPython 3.14.3 and no GPU.

## Primary comparison

| Held-out design | All-predictor Auto RMSE | Tuned IDW RMSE | Paired difference and 95% block interval |
| --- | ---: | ---: | --- |
| Buffered spatial CV | 1.842 | 2.010 | −0.168 [−0.243, −0.093] |
| 2024 → 2025 | 2.416 | 2.526 | −0.110 [−0.196, 0.017] |
| 2025 → 2024 | 1.518 | 2.036 | −0.519 [−0.820, −0.142] |

All errors are in mS/cm. The reverse and spatial contrasts favor enrichment on these observations under the block resampling scheme. Both transfer R² values are close to zero (0.039 forward, 0.022 reverse). The mean signed residual for the 38 spatial test observations with EC ≥5 mS/cm was −3.780 mS/cm. The analysis supports cautious geographic generalization and illustrates the risk of extrapolating across campaigns or to EC extremes. See the [archived results](../results/metrics.csv) and [paired differences](../results/paired_deltas.csv).

## Reproduction checks

A clean CPython environment downloaded both source workbooks, verified their hashes and reproduced the coordinate-only smoke predictions byte for byte. A second full model-and-evaluation run in that environment used the independently rebuilt field table and the archived Sentinel-2 and elevation features. Its prediction, metric, fold membership, chosen parameter, permutation and paired-contrast files were byte-identical. Timing logs naturally differ. The PDF is generated from the same numerical tables and plotted values.
