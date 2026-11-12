# Literature verification

The [evidence matrix](literature_evidence.csv) records title, authors or standard citation, status, target, protocol, result and primary-paper location. Publisher article copies were used where the DOI page required access. No published scores enter the shared numerical leaderboard.

| Source | Primary evidence and treatment |
| --- | --- |
| Sarkar and Ravela (2026) | Sections 2.2–2.4 and 3.2 plus Fig. 6 describe the Satkhira subset, six spatial groups, 13 Landsat inputs, and reported RMSE 0.454 and 0.997 mS/cm with R² 0.912 and 0.856. Mapping calibration uses OOF pairs. The exact procedure scored in Fig. 6 is unverified. The retained row keys, feature matrix and folds were unavailable. V3 includes a nested XGBoost plus OOF quadratic spline inspired by that method. [arXiv v1](https://arxiv.org/html/2604.23127v1) |
| Sarkar et al. (2024) | Focus of Study and Fig. 7 give EBK leave-one-out RMSE 1.3 on the 162 March observations. V3 uses a spatial IDW comparator under the same V3 splits. [arXiv v1](https://arxiv.org/html/2412.19740v1) |
| Sarkar et al. (2023) | The earlier data contain 241 Satkhira records and an 80/20 allocation. The neural model's AUC 0.921 measures discrimination. Regression RF and AdaBoost in this study share some model-family ideas but do not reproduce that classification. [Scientific Reports article](https://pmc.ncbi.nlm.nih.gov/articles/PMC10564761/) |
| Jia et al. (2024) | Sections 2.2 and 2.7 and the results describe conversion from 1:5 EC to salt mass, the 98 coastal and 231 arid observations, 10-fold validation, and coastal R² 0.77 and RMSE 1.74 g/kg. [Ecological Indicators DOI](https://doi.org/10.1016/j.ecolind.2024.112364) |
| Arshad et al. (2025) | Secs. 3.1, 3.3, 4.3.2 and Appendix Table 4 describe 109 observations, additional lab predictors and the random 28-record test. The ensemble reports test R² 0.841, RMSE 1.382 and MAE 1.014 dS/m. [Energy Nexus DOI](https://doi.org/10.1016/j.nexus.2025.100374) |
| Sarkar et al. (2025) | The Scientific Data descriptor documents composite sampling, assay and the 2024 repository. The 2025 field release was published on Zenodo in 2026. [Scientific Data DOI](https://doi.org/10.1038/s41597-025-05447-1) |
