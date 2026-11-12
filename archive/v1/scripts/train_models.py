"""Nested, buffered spatial CV and two locked campaign transfers."""
import argparse
from concurrent.futures import ProcessPoolExecutor
from functools import lru_cache
from importlib.metadata import version
import json
import platform
from time import perf_counter
import warnings

from catboost import CatBoostRegressor
from lightgbm import LGBMRegressor
import numpy as np
import pandas as pd
from scipy.spatial.distance import cdist
from sklearn.base import BaseEstimator, RegressorMixin, clone
from sklearn.cluster import KMeans
from sklearn.dummy import DummyRegressor
from sklearn.ensemble import ExtraTreesRegressor, GradientBoostingRegressor, RandomForestRegressor
from sklearn.feature_selection import SelectKBest, f_regression
from sklearn.impute import SimpleImputer
from sklearn.linear_model import ElasticNet, LinearRegression, Ridge
from sklearn.model_selection import ParameterGrid
from sklearn.neighbors import KNeighborsRegressor
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVR
from threadpoolctl import threadpool_limits
from xgboost import XGBRegressor

from download_originals import ROOT
from fetch_remote_sensing import SPECTRAL

CONFIG = json.loads((ROOT / "configs/experiment.json").read_text())
SEED = CONFIG["seed"]
XY = ["easting", "northing"]
ENV = ["elevation"]
FEATURES = {
    "A": XY, "B": list(SPECTRAL), "C": [*SPECTRAL, *ENV],
    "D": [*SPECTRAL, *ENV], "E": [*XY, *SPECTRAL, *ENV],
}


class IDW(RegressorMixin, BaseEstimator):
    def __init__(self, power: int = 2, neighbors: int = 12):
        self.power = power
        self.neighbors = neighbors

    def fit(self, X: np.ndarray, y: np.ndarray):
        self.coordinates_ = np.asarray(X)
        self.ec_ = np.asarray(y)
        return self

    def predict(self, X: np.ndarray) -> np.ndarray:
        distances = cdist(np.asarray(X), self.coordinates_)
        identical = distances < 1e-8
        count = min(self.neighbors, distances.shape[1])
        neighbors = np.argsort(distances, axis=1, kind="stable")[:, :count]
        near = np.take_along_axis(distances, neighbors, axis=1)
        weights = np.maximum(near, 1e-8) ** (-self.power)
        result = (weights * self.ec_[neighbors]).sum(axis=1) / weights.sum(axis=1)
        exact = identical.any(axis=1)
        result[exact] = (identical[exact] @ self.ec_) / identical[exact].sum(axis=1)
        return result


def groups(data: pd.DataFrame, n: int) -> np.ndarray:
    return KMeans(n_clusters=n, random_state=SEED, n_init=50).fit_predict(data[XY])


def remove_buffer(train: pd.DataFrame, test: pd.DataFrame) -> pd.DataFrame:
    distance = cdist(train[XY], test[XY]).min(axis=1)
    return train.loc[distance >= CONFIG["buffer_metres"]]


def spatial_splits(data: pd.DataFrame, labels: np.ndarray):
    for label in sorted(set(labels)):
        test = data.loc[labels == label]
        train = remove_buffer(data.loc[labels != label], test)
        if len(train) < 24:
            raise ValueError(f"Too few training points in spatial group {label}")
        yield str(label + 1), train, test


@lru_cache(maxsize=1)
def families() -> dict:
    return {
        "Mean": (DummyRegressor(strategy="mean"), {}, False),
        "Median": (DummyRegressor(strategy="median"), {}, False),
        "OLS": (LinearRegression(), {}, True),
        "Ridge": (Ridge(), {"alpha": [1, 10, 100]}, True),
        "ElasticNet": (ElasticNet(max_iter=10000), {"alpha": [.05, .25], "l1_ratio": [.25, .75]}, True),
        "KNN": (KNeighborsRegressor(weights="distance"), {"n_neighbors": [5, 12, 24]}, True),
        "SVR": (SVR(), {"C": [.5, 2], "epsilon": [.15, .4]}, True),
        "IDW": (IDW(), {"power": [1, 2], "neighbors": [8, 20]}, False),
        "RF": (RandomForestRegressor(n_estimators=100, random_state=SEED, n_jobs=1),
               {"min_samples_leaf": [4, 10], "max_features": [.6, 1.]}, False),
        "RF-fixed": (RandomForestRegressor(n_estimators=100, min_samples_leaf=4,
                                           random_state=SEED, n_jobs=1), {}, False),
        "ET": (ExtraTreesRegressor(n_estimators=100, random_state=SEED, n_jobs=1),
               {"min_samples_leaf": [4, 10], "max_features": [.6, 1.]}, False),
        "GB": (GradientBoostingRegressor(n_estimators=80, learning_rate=.05, random_state=SEED),
               {"max_depth": [1, 2], "min_samples_leaf": [5, 12]}, False),
        "XGB": (XGBRegressor(n_estimators=100, learning_rate=.05, tree_method="hist",
                             random_state=SEED, n_jobs=1, verbosity=0),
                {"max_depth": [2, 3], "min_child_weight": [4, 10]}, False),
        "LGBM": (LGBMRegressor(n_estimators=100, learning_rate=.05, random_state=SEED,
                               n_jobs=1, verbosity=-1, force_col_wise=True),
                 {"num_leaves": [5, 9], "min_child_samples": [10, 20]}, False),
        "CatBoost": (CatBoostRegressor(iterations=100, learning_rate=.05, random_seed=SEED,
                                      verbose=False, allow_writing_files=False, thread_count=1),
                     {"depth": [3, 5], "l2_leaf_reg": [3, 10]}, False),
    }


def model_pipeline(name: str, feature: str, params: dict):
    estimator, _, scale = families()[name]
    if name in ("IDW", "Mean", "Median"):
        return clone(estimator).set_params(**params)
    model_params = {k: v for k, v in params.items() if k != "k"}
    stages = [SimpleImputer(strategy="median", keep_empty_features=True)]
    if scale:
        stages.append(StandardScaler())
    if feature == "D":
        stages.append(SelectKBest(score_func=f_regression, k=params["k"]))
    stages.append(clone(estimator).set_params(**model_params))
    pipeline = make_pipeline(*stages)
    pipeline.set_output(transform="pandas")
    return pipeline


def candidate_params(name: str, feature: str, smoke: bool) -> list[dict]:
    grid = dict(families()[name][1])
    if feature == "D":
        grid["k"] = [3, 5]
    candidates = list(ParameterGrid(grid))
    return candidates[:1] if smoke else candidates


def inputs(data: pd.DataFrame, feature: str) -> pd.DataFrame:
    return data[FEATURES[feature]].astype(float)


def predict(estimator, data: pd.DataFrame, feature: str) -> np.ndarray:
    return np.clip(estimator.predict(inputs(data, feature)), 0, None)


def fit_score(name: str, feature: str, params: dict, train: pd.DataFrame,
              validation: pd.DataFrame) -> tuple[np.ndarray, list[str], float]:
    start = perf_counter()
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        estimator = model_pipeline(name, feature, params)
        estimator.fit(inputs(train, feature), train.ec)
        prediction = predict(estimator, validation, feature)
    return prediction, sorted({str(w.message) for w in caught}), perf_counter() - start


def candidates_for(feature: str, smoke: bool) -> list[str]:
    if smoke:
        return ["Mean", "IDW", "Ridge"] if feature == "A" else ["Ridge"]
    if feature == "A":
        return list(families())
    return ["Ridge", "SVR", "RF", "RF-fixed", "ET", "GB", "XGB", "LGBM", "CatBoost"]


def explain(estimator, name: str, track: str, fold: str, test: pd.DataFrame) -> list[dict]:
    random = np.random.default_rng(SEED)
    observed = test.ec.to_numpy()
    reference = np.sqrt(np.mean((observed - predict(estimator, test, "E")) ** 2))
    rows = []
    for group, columns in {"Coordinates": XY, "Sentinel-2": list(SPECTRAL), "Elevation": ENV}.items():
        for rep in range(CONFIG["permutation_replicates"]):
            shuffled = test.copy()
            shuffled.loc[:, columns] = test[columns].to_numpy()[random.permutation(len(test))]
            score = np.sqrt(np.mean((observed - predict(estimator, shuffled, "E")) ** 2))
            rows.append(dict(track=track, fold=fold, selected_model=name, group=group,
                             replicate=rep, delta_rmse=score - reference))
    return rows


def run_outer(task: tuple) -> tuple:
    (track, fold, train, test, test_groups), features, smoke = task
    predictions, best, tuning, membership, importance, fit_log = [], [], [], [], [], []
    with threadpool_limits(limits=1):
        start_outer = perf_counter()
        assert not set(train.index) & set(test.index)
        if track != "Spatial":
            assert set(train.year).isdisjoint(set(test.year))
        nearest = cdist(test[XY], train[XY]).min(axis=1)
        inner = list(spatial_splits(train, groups(train, CONFIG["inner_spatial_folds"])))
        for stage, group, training, held in [("outer", fold, train, test), *[
            ("inner", i, tr, va) for i, tr, va in inner
        ]]:
            for role, ids in (("train", training.index), ("test", held.index)):
                membership.extend(dict(track=track, fold=fold, stage=stage, group=group,
                                       role=role, uid=uid) for uid in ids)
        for feature in features:
            outer = {}
            inner_best = {}
            for name in candidates_for(feature, smoke):
                top = (np.inf, {})
                for params in candidate_params(name, feature, smoke):
                    sse, n = 0., 0
                    for i, tr, va in inner:
                        estimates, messages, seconds = fit_score(name, feature, params, tr, va)
                        squared = float(np.sum((va.ec - estimates) ** 2))
                        sse += squared
                        n += len(va)
                        tuning.append(dict(track=track, fold=fold, feature=feature, model=name,
                                           inner_fold=i, parameters=json.dumps(params, sort_keys=True),
                                           sse=squared, n=len(va), seconds=seconds,
                                           warnings=json.dumps(messages)))
                    score = np.sqrt(sse / n)
                    if score < top[0]:
                        top = (score, params)
                inner_best[name] = top
                score, params = top
                start = perf_counter()
                with warnings.catch_warnings(record=True) as caught:
                    warnings.simplefilter("always")
                    estimator = model_pipeline(name, feature, params).fit(inputs(train, feature), train.ec)
                    outer[name] = (predict(estimator, test, feature), estimator)
                fit_log.append(dict(track=track, fold=fold, feature=feature, model=name,
                                    seconds=perf_counter()-start, warnings=json.dumps(
                                        sorted({str(w.message) for w in caught}))))
                best.append(dict(track=track, fold=fold, feature=feature, model=name,
                                 inner_rmse=float(score), params=params))
            selected = min(inner_best, key=lambda key: inner_best[key][0])
            outer["Auto"] = outer[selected]
            if feature == "E":
                importance.extend(explain(outer[selected][1], selected, track, fold, test))
            for name, (estimate, _) in outer.items():
                table = pd.DataFrame(dict(track=track, fold=fold, feature=feature, model=name,
                                          selected_model=selected if name == "Auto" else name,
                                          uid=test.index, year=test.year, observed=test.ec,
                                          predicted=estimate, nearest_train_m=nearest, block=test_groups))
                predictions.append(table)
        print(track, fold, len(train), len(test), round(perf_counter() - start_outer, 1), flush=True)
    return predictions, best, tuning, membership, importance, fit_log


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--smoke", action="store_true")
    parser.add_argument("--coordinate-only", action="store_true")
    parser.add_argument("--jobs", type=int, default=1)
    args = parser.parse_args()
    if args.jobs < 1:
        parser.error("--jobs must be positive")
    if args.smoke:
        destination = ROOT / "data/derived/smoke"
    elif args.coordinate_only:
        destination = ROOT / "data/derived/coordinate-only"
    else:
        destination = ROOT / "results"
    destination.mkdir(parents=True, exist_ok=True)
    field = pd.read_csv(ROOT / "data/derived/field.csv").set_index("uid")
    features = ["A"]
    if not args.coordinate_only:
        source = ROOT / "data/derived"
        field = field.join(pd.read_csv(source / "sentinel.csv").set_index("uid"), validate="one_to_one")
        field = field.join(pd.read_csv(source / "elevation.csv").set_index("uid"), validate="one_to_one")
        features = list(FEATURES)
    predictions, best, tuning, membership, importance, fit_log = [], [], [], [], [], []
    labels = groups(field, CONFIG["outer_spatial_folds"])
    tests = [("Spatial", fold, train, test, pd.Series(fold, index=test.index))
             for fold, train, test in spatial_splits(field, labels)]
    for year in (2024, 2025):
        train, test = field[field.year == year], field[field.year != year]
        block = pd.Series(groups(test, CONFIG["outer_spatial_folds"]) + 1, index=test.index)
        tests.append((f"{year}-to-{int(test.year.iloc[0])}", "1", train, test, block))
        tests.append((f"{year}-to-{int(test.year.iloc[0])}-buffered", "1",
                      remove_buffer(train, test), test, block))

    tasks = [(test, features, args.smoke) for test in tests]
    if args.jobs == 1:
        runs = list(map(run_outer, tasks))
    else:
        with ProcessPoolExecutor(max_workers=args.jobs) as pool:
            runs = list(pool.map(run_outer, tasks))
    for target, chunks in zip((predictions, best, tuning, membership, importance, fit_log),
                              zip(*runs, strict=True), strict=True):
        for chunk in chunks:
            target.extend(chunk)
    pd.concat(predictions, ignore_index=True).to_csv(destination / "predictions.csv", index=False)
    pd.DataFrame(tuning).to_csv(destination / "inner_scores.csv", index=False)
    pd.DataFrame(fit_log).to_csv(destination / "fit_log.csv", index=False)
    pd.DataFrame(membership).to_csv(destination / "splits.csv", index=False)
    if importance:
        pd.DataFrame(importance).to_csv(destination / "importance.csv", index=False)
    (destination / "best_params.json").write_text(json.dumps(best, indent=2) + "\n", encoding="utf-8")
    packages = ["numpy", "scipy", "pandas", "scikit-learn", "openpyxl", "pyproj", "rasterio",
                "requests", "catboost", "lightgbm", "xgboost", "matplotlib", "threadpoolctl"]
    versions = dict(python=platform.python_version(), os=platform.platform(),
                    libraries={name: version(name) for name in packages})
    (destination / "versions.json").write_text(json.dumps(versions, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    with threadpool_limits(limits=1):
        main()
