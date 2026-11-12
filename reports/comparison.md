# Same-protocol comparison with Sarkar and Ravela (2026)

| Component | Published Track I | Present audit |
| --- | --- | --- |
| Field records | 86 March 2024, 119 April 2025, Satkhira | A pinned geoBoundaries ADM2 point-in-polygon check gives 86 and 119 candidate records. Exact sample identities and the preprint's complete-predictor mask are unverified. |
| Target | 1:5 soil–water EC, mS/cm | Same assay and unit in the public workbooks. |
| Predictors | Landsat 8 C2 T1 L2, path 138/row 44, 13 predictors at 30 m | Extended study uses strictly pre-collection Sentinel-2 L2A and a static surface elevation model. |
| Validation | Six spatial K-means groups, seed 123, 50 starts | Extended study uses 349 records, projected coordinate clusters, a 1 km buffer and nested selection. Identical benchmark folds unavailable. |
| Tuning and calibration | caret XGBoost search; spline GAM fitted on XGBoost OOF pairs for maps | Exact predictor rasters, folds, and scored calibration workflow are unavailable. |
| Reported 2024 | R² 0.912, RMSE 0.454 mS/cm | Same-protocol estimate unavailable. |
| Reported 2025 | R² 0.856, RMSE 0.997 mS/cm | Same-protocol estimate unavailable. |
| Paired improvement | Requires aligned predictions | Indeterminate. |

The authors report the metrics in Sec. 3.2 and Fig. 6. Sections 2.4.2–2.4.4 describe spatial resampling, XGBoost search, and GAM training for mapping. They do not document whether Fig. 6 used predictions from a GAM evaluated on separate outer folds, or whether its scatterplots show the uncalibrated OOF XGBoost outputs. This is a verification limit, not an allegation about their implementation. Their stated February–April Landsat window may include post-collection acquisitions. See the [full preprint](https://arxiv.org/html/2604.23127v1).

For exact replication, obtain the retained sample IDs and same fold IDs or a hash-verified split reconstruction, the exported feature table and scene recipe (including compositing, masks and scaling), and the precise prediction-generation code. Run the published method and new estimators on those same samples, predictors, and folds. Assess calibrated models on outer folds with calibration fitted on inner OOF training predictions. If an exact published procedure differs, label the exact reproduction and the stricter comparison distinctly.

Source correction: the 2023 Scientific Reports study used 241 earlier records and reports ROC AUC. The 2024 root-zone preprint reports leave-one-out EBK RMSE of 1.3. Jia et al. predict converted soil salt mass concentration in g/kg. Arshad et al. report 0.841 test R² from 28 randomly held-out observations, using additional soil covariates. The 2025 field release was published in 2026.
