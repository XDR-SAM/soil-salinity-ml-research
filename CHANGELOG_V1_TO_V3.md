# V1 to V3

- Preserved the existing manuscript, numeric macros, code, figures, configs and results byte for byte in a local `archive/v1/`. Independently recomputed every archived metric and fold score from 58,632 predictions. V3 takes the same archived inner and outer split membership and retains all 349 rows.
- Added a native-pixel, pre-collection Landsat 8/9 search with QA masking and exact asset provenance, plus surface relief, local relative elevation and slope.
- Added random-search matched baselines, explicit optical availability and recency, log and high-EC losses, and regularized convex stacking with a Sentinel-2 availability gate. Compared the gate with global and equal blending of the same experts.
- Audited coverage by campaign, salinity range and region. Repeated both campaign directions and the 1 km sensitivity, with matched held-out predictions and paired intervals.
- Rewrote and rebuilt the manuscript with a new train/test workflow and figures. The submissions are local.

The submission ZIP includes byte-identical V1 results, numeric manuscript inputs and safe reference materials. It excludes the historical README, full manuscript and machine-specific historical metadata to preserve a neutral handoff. The untouched originals remain in the local archive.
