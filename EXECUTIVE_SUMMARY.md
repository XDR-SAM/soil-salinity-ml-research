# Executive summary

All 349 EC1:5 measurements were evaluated under the same archived spatial and campaign partitions. Sentinel-2 covered 277 sites. QA-screened Landsat covered 325, bringing either-source coverage to 331 and recovering 54 of 72 original gaps.

| Buffered spatial procedure | RMSE (mS/cm) | MAE (mS/cm) | R² |
| --- | ---: | ---: | ---: |
| ET no_landsat | 1.729 | 1.244 | 0.350 |
| MISA | 1.763 | 1.237 | 0.325 |
| V1 Auto | 1.842 | 1.312 | 0.263 |
| V1 ExtraTrees (descriptive) | 1.746 | 1.268 | 0.338 |

MISA minus V1 Auto RMSE: -0.079 mS/cm, +4.31% relative reduction, 95% spatial-block interval [-0.146, -0.017]. MISA minus ET no_landsat: +0.033 mS/cm, -1.94%, interval [-0.051, +0.095].

On the 38 high-EC spatial tests, MISA MAE was 3.643 and signed bias -3.643 mS/cm. V1 Auto yielded 3.780 and -3.780. The strongest spatial comparator yielded 3.432 and -3.432. The MISA–V1 high-EC paired MAE difference was -0.137 [-0.416, +0.370]. For sites missing Sentinel-2 it was -0.052 [-0.367, +0.112].

MISA transfer RMSE was 2.377 forward and 1.529 in reverse, with R² 0.070 and 0.007. Under 1 km training exclusion, RMSE was 2.399 and 1.674. All errors are in mS/cm.

High-EC weighting in Huber boosting lowered subgroup MAE by 0.420 mS/cm, paired interval [-0.625, -0.146] for weighted minus unweighted. It increased overall spatial RMSE from 1.772 to 1.845. The same directional trade-off appeared for weighted ExtraTrees and random forest.

The proposal's frozen paired-superiority criterion was **not met**. None of the study's labels provide untouched external validation. The manuscript requires further research before a confirmatory submission.

The descriptively lowest RMSE changed by -0.113 mS/cm versus V1 Auto (6.13% lower, interval [-0.212, +0.015]).
