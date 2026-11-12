# Runtime and reproducibility

## Executed

The V3 benchmark generated 37,692 unique model/site/track predictions. It ran 5,760 candidate/inner-fold fits and 270 fitted single-family outer models. Four concurrent fold workers performed single-threaded estimator fits on CPU. The archived fit records sum to 700.4 seconds of inner-fit time and 32.9 seconds of outer-refit time across workers. These sums are not end-to-end elapsed time. No GPU is needed. The version manifest gives software versions.

Full Landsat extraction read 47 eligible scenes and the terrain stage checked four DSM tiles. Scene and tile provenance are archived. The local optical-retrieval probe for each campaign matched the archived reflectance, lag and QA. A repeated terrain extraction from the verified tile bytes matched all 349 rows, including the single incomplete edge window.

## Independently rerun

A separate directory in the isolated pinned Python environment retrieved both workbook originals anew and verified their hashes and all field rows. From the locked feature tables and archived splits it ran the complete benchmark again. Nine prediction/metric/ablation/coverage/importance CSVs and two selected-parameter JSONs were byte-identical. Per-trial choices, counts and scores matched after removing timing. The rerun produced seven byte-identical result PNGs. The final rebuilt 7-page PDF had identical page text and raster content.

The four-terrain-tile extraction was repeated from verified local source bytes. The complete remote Landsat query and original Sentinel-2 extraction were not independently repeated. Two Landsat pixel recoveries were checked against upstream assets, one from each campaign. The V1 model training was not repeated in V3, but every V1 metric and fold score was independently recomputed from archived predictions.

## Additional recovery check

The residual-correction experiment used only archived outer training observations and their inner validation folds. The number of outer training sets choosing each shrinkage strength by its inner RMSE was {0.0: np.int64(4), 0.25: np.int64(1), 0.5: np.int64(1)}. The archived exploratory outcomes are not final test scores. The frozen outer procedure was never changed on the basis of those scores.

No independent field campaign, exact published Satkhira artifacts, or prospective product-delivery validation was available.
