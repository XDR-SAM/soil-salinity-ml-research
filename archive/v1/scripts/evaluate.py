"""Aggregate untouched predictions and run paired spatial-block bootstraps."""
import json
import numpy as np
import pandas as pd
from scipy.stats import wasserstein_distance

from download_originals import ROOT

RESULTS = ROOT / "results"
CONFIG = json.loads((ROOT / "configs/experiment.json").read_text())
KEYS = ["track", "feature", "model"]


def score(observed: np.ndarray, predicted: np.ndarray) -> dict:
    error = predicted - observed
    sst = np.sum((observed - np.mean(observed)) ** 2)
    return dict(n=len(error), r2=float(1 - np.sum(error**2)/sst) if sst else np.nan,
                rmse=float(np.sqrt(np.mean(error**2))), mae=float(np.mean(abs(error))),
                bias=float(np.mean(error)))


def block_draws(group: pd.DataFrame) -> list[np.ndarray]:
    random = np.random.default_rng(CONFIG["seed"])
    indices = [np.flatnonzero(group.block.to_numpy() == b) for b in sorted(group.block.unique())]
    draws = random.integers(len(indices), size=(CONFIG["bootstrap_replicates"], len(indices)))
    return [np.concatenate([indices[i] for i in row]) for row in draws]


def interval(values: np.ndarray) -> tuple[float, float]:
    return tuple(float(x) for x in np.quantile(values, [.025, .975]))


def main() -> None:
    predictions = pd.read_csv(RESULTS / "predictions.csv")
    if predictions.duplicated(KEYS + ["uid"]).any():
        raise ValueError("Repeated test prediction")
    folds = []
    for keys, subset in predictions.groupby([*KEYS, "fold"]):
        folds.append(dict(zip([*KEYS, "fold"], keys, strict=True),
                          **score(subset.observed.to_numpy(), subset.predicted.to_numpy())))
    pd.DataFrame(folds).to_csv(RESULTS / "fold_metrics.csv", index=False)
    metrics, pairs = [], []
    for track, table in predictions.groupby("track"):
        wide = table.pivot(index=["uid", "observed", "block"], columns=["feature", "model"],
                           values="predicted").sort_index()
        blocks = wide.index.to_frame(index=False)
        assert not wide.isna().any().any()
        draws = block_draws(blocks)
        observed = blocks.observed.to_numpy()
        bootstrap = {}
        for (feature, model), values in wide.items():
            estimate = values.to_numpy()
            squared = (estimate - observed) ** 2
            resampled = np.array([np.sqrt(squared[ix].mean()) for ix in draws])
            bootstrap[feature, model] = resampled
            lo, hi = interval(resampled)
            metrics.append(dict(track=track, feature=feature, model=model,
                                **score(observed, estimate), rmse_lo=lo, rmse_hi=hi))
        comparisons = [
            ("A", "Auto", "A", "Mean"), ("B", "Auto", "A", "Auto"),
            ("C", "Auto", "B", "Auto"), ("D", "Auto", "C", "Auto"),
            ("E", "Auto", "A", "IDW"), ("E", "Auto", "A", "Mean"),
            ("E", "Auto", "A", "OLS"), ("E", "Auto", "A", "Auto"),
            ("E", "Ridge", "A", "Ridge"), ("E", "RF", "A", "RF"),
            ("E", "RF", "E", "RF-fixed"),
        ]
        for a, m, b, baseline in comparisons:
            if (a, m) not in bootstrap or (b, baseline) not in bootstrap:
                continue
            lo, hi = interval(bootstrap[a, m] - bootstrap[b, baseline])
            delta = score(observed, wide[a, m].to_numpy())["rmse"] - score(
                observed, wide[b, baseline].to_numpy())["rmse"]
            pairs.append(dict(track=track, feature=a, model=m, baseline_feature=b,
                              baseline=baseline, delta_rmse=delta, lo=lo, hi=hi))
    pd.DataFrame(metrics).to_csv(RESULTS / "metrics.csv", index=False)
    pd.DataFrame(pairs).to_csv(RESULTS / "paired_deltas.csv", index=False)
    data = pd.read_csv(ROOT / "data/derived/field.csv")
    main = predictions.loc[predictions.model.eq("Auto") & predictions.feature.eq(
        "E" if predictions.feature.eq("E").any() else "A")].copy()
    main["ec_bin"] = pd.cut(main.observed, [0, .5, 2, 5, np.inf], right=False)
    main["distance_km"] = pd.cut(main.nearest_train_m / 1000, [0, 1, 5, 15, np.inf], right=False)
    satellite = ROOT / "data/derived/sentinel.csv"
    strata = ["year", "ec_bin", "block", "distance_km"]
    if satellite.exists():
        coverage = pd.read_csv(satellite).set_index("uid").scene.notna()
        main["optical_available"] = main.uid.map(coverage)
        strata.append("optical_available")
    subgroups = []
    for kind in strata:
        for (track, level), subset in main.groupby(["track", kind], observed=True):
            subgroups.append(dict(track=track, stratum=kind, level=str(level),
                                  **score(subset.observed.to_numpy(), subset.predicted.to_numpy())))
    pd.DataFrame(subgroups).to_csv(RESULTS / "subgroups.csv", index=False)
    data_24, data_25 = [data[data.year == y].ec for y in (2024, 2025)]
    shift = dict(ec_wasserstein_mS_cm=float(wasserstein_distance(data_24, data_25)),
                 campaign_mean_difference=float(data_25.mean()-data_24.mean()))
    (RESULTS / "distribution_shift.json").write_text(json.dumps(shift, indent=2) + "\n")


if __name__ == "__main__":
    main()
