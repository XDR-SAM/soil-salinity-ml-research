"""Evaluate a frozen, source-aware out-of-fold ensemble and matched comparators."""
import argparse
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass
from functools import lru_cache
from hashlib import sha256
from importlib.metadata import version
import json
import platform
from time import perf_counter
import warnings

from catboost import CatBoostRegressor
from lightgbm import LGBMRegressor
import numpy as np
import pandas as pd
from scipy.optimize import minimize
from scipy.spatial.distance import cdist
from sklearn.ensemble import AdaBoostRegressor, ExtraTreesRegressor, GradientBoostingRegressor, RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.linear_model import Ridge
from sklearn.model_selection import ParameterSampler
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import SplineTransformer, StandardScaler
from sklearn.svm import SVR
from sklearn.tree import DecisionTreeRegressor
from threadpoolctl import threadpool_limits
from xgboost import XGBRegressor

from acquire import BANDS, DERIVED, ROOT, TERRAIN

CONFIG_FILE = ROOT / "code/configs/frozen_primary_protocol.json"
P = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
SEED = P["seed"]
XY = ("easting", "northing")
S2 = ("blue", "green", "red", "nir", "swir16", "swir22", "ndvi", "ndmi")
L8 = tuple("ls_" + k for k in (*BANDS, "ndvi", "ndmi"))
RESULTS = ROOT / "results"


@dataclass(frozen=True)
class Trial:
    family: str
    features: str = "full"
    target: str = "raw"
    budget: int = 8


def design(data: pd.DataFrame) -> tuple[dict, dict]:
    optical2 = [*S2, "s2_lag", "s2_present"]
    optical8 = [*L8, "ls_lag", "ls_present"] if data.ls_present.any() else []
    terrain = ["elevation", *[c for c in TERRAIN if data[c].notna().any()]]
    full = [*XY, *terrain, *optical2, *optical8]
    sets = {
        "full": full, "no_geo": [*terrain, *optical2, *optical8],
        "v1": [*XY, "elevation", *S2], "no_landsat": [*XY, *terrain, *optical2],
        "no_terrain": [*XY, *optical2, *optical8],
        "no_flags": [c for c in full if not c.endswith("_present")],
        "terrain_only": [*XY, *terrain], "optical_only": [*optical2, *optical8],
        "compact": [*terrain, "ndvi", "ndmi", "s2_present",
                    *[c for c in ("ls_ndvi", "ls_ndmi", "ls_present") if c in optical8]],
    }
    return sets, {"Location": list(XY), "Terrain": terrain, "Sentinel-2": optical2, "Landsat": optical8}


def load_data() -> pd.DataFrame:
    field = pd.read_csv(DERIVED / "field.csv", parse_dates=["date"]).set_index("uid")
    s2 = pd.read_csv(DERIVED / "sentinel.csv").set_index("uid")
    elevation = pd.read_csv(DERIVED / "elevation.csv").set_index("uid")
    field = field.join(s2, validate="one_to_one").join(elevation, validate="one_to_one")
    field["s2_present"] = field.scene.notna().astype(int)
    field["s2_lag"] = field.lag_days
    ls_path = DERIVED / "landsat.csv"
    if ls_path.exists():
        field = field.join(pd.read_csv(ls_path).set_index("uid"), validate="one_to_one")
        field["ls_present"] = field.ls_scene.notna().astype(int)
    else:
        field["ls_present"] = 0
    terrain_path = DERIVED / "terrain.csv"
    if terrain_path.exists():
        field = field.join(pd.read_csv(terrain_path).set_index("uid"), validate="one_to_one")
    else:
        field[list(TERRAIN)] = np.nan
    assert len(field) == P["population"] and field.index.is_unique
    return field


@lru_cache(maxsize=1)
def factories() -> dict:
    return {
        "Ridge": (lambda **p: Ridge(**p),
                  {"alpha": [.1,.4,1,2,5,10,30,100]}, True),
        "RF": (lambda **p: RandomForestRegressor(random_state=SEED,n_jobs=1,**p),
               {"n_estimators": [100], "min_samples_leaf": [2,4,7,12],
                "max_features": [.45,.75,1.], "max_depth": [4,8,None]}, False),
        "ExtraTrees": (lambda **p: ExtraTreesRegressor(random_state=SEED,n_jobs=1,**p),
                       {"n_estimators": [120], "min_samples_leaf": [2,4,7,12],
                        "max_features": [.45,.75,1.], "max_depth": [4,8,None]}, False),
        "SVR": (lambda **p: SVR(**p),
                {"C": [.5,1,2,5,10], "epsilon": [.1,.25,.5], "gamma": [.02,.06,.16,"scale"]}, True),
        "XGBoost": (lambda **p: XGBRegressor(random_state=SEED,n_jobs=1,tree_method="hist",verbosity=0,**p),
                    {"n_estimators": [70,140], "max_depth": [2,3,4], "min_child_weight": [4,8,14],
                     "learning_rate": [.03,.07], "subsample": [.85,1.]}, False),
        "LightGBM": (lambda **p: LGBMRegressor(random_state=SEED,n_jobs=1,verbosity=-1,force_col_wise=True,**p),
                     {"n_estimators": [70,140], "num_leaves": [5,9,14],
                      "min_child_samples": [8,15,24], "learning_rate": [.03,.07]}, False),
        "CatBoost": (lambda **p: CatBoostRegressor(random_seed=SEED,thread_count=1,verbose=False,
                                                   allow_writing_files=False,**p),
                     {"iterations": [70,140], "depth": [3,4,5],
                      "l2_leaf_reg": [3,10,25], "learning_rate": [.035,.07]}, False),
        "AdaBoost": (lambda **p: AdaBoostRegressor(estimator=DecisionTreeRegressor(max_depth=2,
                                                    min_samples_leaf=5,random_state=SEED),
                                                   random_state=SEED,**p),
                     {"n_estimators": [50,100,150], "learning_rate": [.03,.1,.25],
                      "loss": ["linear","square"]}, False),
        "Huber-GB": (lambda **p: GradientBoostingRegressor(loss="huber",random_state=SEED,**p),
                     {"n_estimators": [60,110], "max_depth": [1,2,3],
                      "learning_rate": [.03,.065], "min_samples_leaf": [5,10]}, False),
    }


def fit(trial: Trial, params: dict, features: dict, data: pd.DataFrame):
    factory, _, scaling = factories()[trial.family]
    steps = [SimpleImputer(strategy="median", keep_empty_features=True)]
    if scaling:
        steps.append(StandardScaler())
    model = make_pipeline(*steps, factory(**params)).set_output(transform="pandas")
    y = data.ec.to_numpy()
    if trial.target == "weighted":
        last = model.steps[-1][0]
        model.fit(data[features[trial.features]], y, **{last+"__sample_weight": 1 + .75*(y >= 5)})
    else:
        model.fit(data[features[trial.features]], np.log1p(y) if trial.target == "log" else y)
    return model


def estimate(model, trial: Trial, features: dict, data: pd.DataFrame) -> np.ndarray:
    output = model.predict(data[features[trial.features]])
    return np.maximum(np.expm1(output) if trial.target == "log" else output, 0)


def cv_search(trial: Trial, features: dict, train: pd.DataFrame, inner: list, key: str) -> tuple:
    params = list(ParameterSampler(factories()[trial.family][1], n_iter=trial.budget, random_state=SEED))
    winner = None
    logs = []
    for choice in params:
        oof = pd.Series(index=train.index, dtype=float)
        for group, fit_rows, val_rows in inner:
            start = perf_counter()
            with warnings.catch_warnings(record=True) as caught:
                warnings.simplefilter("always")
                fitted = fit(trial, choice, features, train.loc[fit_rows])
                pred = estimate(fitted, trial, features, train.loc[val_rows])
            oof.loc[val_rows] = pred
            sse = np.square(pred-train.loc[val_rows,"ec"]).sum()
            logs.append((key, group, json.dumps(choice,sort_keys=True), float(sse), len(pred),
                         perf_counter()-start, json.dumps(sorted({type(v.message).__name__ for v in caught}))))
        assert oof.notna().all()
        rmse = float(np.sqrt(np.square(oof-train.ec).mean()))
        if winner is None or rmse < winner[0]:
            winner = (rmse, choice, oof)
    return (*winner, logs)


def idw(train: pd.DataFrame, test: pd.DataFrame, p: int, k: int) -> np.ndarray:
    distances = cdist(test[list(XY)],train[list(XY)])
    values = train.ec.to_numpy()
    neighbors = np.argsort(distances,axis=1,kind="stable")[:,:k]
    d = np.take_along_axis(distances,neighbors,axis=1)
    weights = np.maximum(d,1e-8)**(-p)
    out = np.sum(weights*values[neighbors],axis=1)/weights.sum(axis=1)
    exact = distances < 1e-8
    has = exact.any(axis=1)
    out[has] = (exact[has]@values)/exact[has].sum(axis=1)
    return out


def weights(matrix: np.ndarray, target: np.ndarray) -> np.ndarray:
    uniform = np.full(matrix.shape[1],1/matrix.shape[1])
    l2 = P["ensemble"]["l2_penalty"]
    def objective(w):
        residual = matrix@w-target
        return float(residual@residual/len(target) + l2*np.square(w-uniform).sum())
    def gradient(w):
        return 2*(matrix.T@(matrix@w-target))/len(target) + 2*l2*(w-uniform)
    solution = minimize(objective,uniform,jac=gradient,method="SLSQP",bounds=[(0,1)]*len(uniform),
                        constraints=[{"type":"eq","fun":lambda w: w.sum()-1}],
                        options={"ftol":1e-10,"maxiter":200})
    if not solution.success:
        raise RuntimeError("Convex blend optimization failed")
    return solution.x


def gate(matrix: np.ndarray, observed: np.ndarray, present: np.ndarray) -> tuple[np.ndarray,dict]:
    global_weights = weights(matrix,observed)
    by_flag = {}
    for flag in (0,1):
        mask = present == flag
        n = int(mask.sum())
        share = n/(n+P["ensemble"]["shrinkage_n"])
        by_flag[flag] = (1-share)*global_weights + share*weights(matrix[mask],observed[mask]) if n >= 8 else global_weights
    return global_weights,by_flag


def trials_for(data: pd.DataFrame) -> dict:
    main = {name: Trial(name) for name in factories()}
    variants = {f"ET {group}": Trial("ExtraTrees",group,budget=4) for group in
                ("no_geo","v1","no_landsat","no_terrain","no_flags","terrain_only","optical_only","compact")}
    variants |= {
        "ET full-4": Trial("ExtraTrees","full","raw",4),
        "RF full-4": Trial("RF","full","raw",4),
        "Huber-GB full-4": Trial("Huber-GB","full","raw",4),
        "ET log": Trial("ExtraTrees","full","log",4),
        "ET weighted": Trial("ExtraTrees","full","weighted",4),
        "RF log": Trial("RF","full","log",4),
        "RF weighted": Trial("RF","full","weighted",4),
        "Huber-GB weighted": Trial("Huber-GB","full","weighted",4),
        "XGB no_geo": Trial("XGBoost","no_geo","raw",4),
        "Ridge compact": Trial("Ridge","compact","raw",4),
    }
    if not data.ls_present.any():
        del variants["ET no_landsat"]
    return main | variants


def split_ids(rows: pd.DataFrame) -> tuple[list, list]:
    return [rows.loc[rows.role.eq(r),"uid"].tolist() for r in ("train","test")]


def outer(task: tuple) -> tuple:
    track, fold, memberships, field, anchor, smoke = task
    start = perf_counter()
    tr, te = split_ids(memberships[memberships.stage.eq("outer")])
    train, test = field.loc[tr], field.loc[te]
    inner = [(int(g), *split_ids(x)) for g,x in memberships[memberships.stage.eq("inner")].groupby("group")]
    features, feature_groups = design(field)
    models, predictions, selected, trace, refits = {}, {}, {}, [], []
    with threadpool_limits(limits=1):
        trials = trials_for(field)
        if smoke:
            trials = {k:Trial(v.family,v.features,v.target,1) for k,v in trials.items() if k in ("Ridge","XGBoost")}
        for key,trial in trials.items():
            score,params,oof,logs = cv_search(trial,features,train,inner,key)
            trace.extend((track,fold,*r) for r in logs)
            started=perf_counter()
            model=fit(trial,params,features,train)
            predictions[key]=estimate(model,trial,features,test)
            refits.append((track,fold,key,perf_counter()-started))
            models[key]=(model,trial,oof,score)
            selected[key]={"inner_rmse":score,"parameters":params,"feature_set":trial.features,
                           "target":trial.target,"family":trial.family}
        predictions["Mean"] = np.full(len(test),train.ec.mean())
        idw_trials = [(p,k) for p in (1,2,3) for k in (8,20)]
        def idw_score(pair):
            return sum(np.square(idw(train.loc[a],train.loc[b],*pair)-train.loc[b,"ec"]).sum()
                       for _,a,b in inner)
        p,k = min(idw_trials,key=idw_score)
        predictions["IDW"] = idw(train,test,p,k)
        selected["IDW"] = {"p":p,"k":k,"inner_rmse":float(np.sqrt(idw_score((p,k))/len(train)))}

        xgb_oof = models["XGBoost"][2].to_numpy()[:,None]
        cal = make_pipeline(SplineTransformer(n_knots=4,degree=2,extrapolation="linear"),Ridge(alpha=1.))
        cal.fit(xgb_oof,train.ec)
        predictions["XGB + spline"] = np.maximum(cal.predict(predictions["XGBoost"][:,None]),0)
        ranked = sorted(models,key=lambda key:models[key][3])
        unique = {}
        for key in ranked:
            unique.setdefault(models[key][1].family,key)
        ensemble = list(unique.values())[:P["ensemble"]["maximum_families"]]
        champion = ranked[0]
        predictions["Inner champion"] = predictions[champion]
        oof = np.column_stack([models[k][2] for k in ensemble])
        global_w, local_w = gate(oof, train.ec.to_numpy(), train.s2_present.to_numpy())
        def blend(data):
            matrix = np.column_stack([estimate(models[k][0],models[k][1],features,data) for k in ensemble])
            row_weights = np.vstack([local_w[x] for x in data.s2_present])
            return (matrix*row_weights).sum(axis=1)
        point_matrix = np.column_stack([predictions[k] for k in ensemble])
        predictions["MISA"] = blend(test)
        predictions["MISA global"] = point_matrix @ global_w
        predictions["MISA equal"] = point_matrix.mean(axis=1)
        if not smoke:
            selected["MISA"] = {"experts":ensemble,"global":global_w.tolist(),
                                "conditional":{str(k):v.tolist() for k,v in local_w.items()}}
            selected["Inner champion"] = {"expert":champion}

        permutation = []
        random = np.random.default_rng(SEED+fold)
        if track == "Spatial" and not smoke:
            reference = np.square(predictions["MISA"]-test.ec).mean()**.5
            for name,columns in feature_groups.items():
                if not columns:
                    continue
                for i in range(P["permutation_replicates"]):
                    shuffled = test.copy()
                    shuffled[columns] = test[columns].iloc[random.permutation(len(test))].set_axis(test.index)
                    diff = np.square(blend(shuffled)-test.ec).mean()**.5-reference
                    permutation.append((track,fold,name,i,float(diff)))
    result = pd.concat([anchor.assign(model=key,predicted=values) for key,values in predictions.items()],
                       ignore_index=True)
    print(track,fold,len(tr),len(te),f"{perf_counter()-start:.1f}s",flush=True)
    return result, (track,fold,selected), trace, refits, permutation


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--jobs",type=int,default=4)
    cli.add_argument("--smoke",action="store_true")
    args=cli.parse_args()
    if args.jobs < 1:
        cli.error("--jobs must be positive")
    frozen = CONFIG_FILE.with_suffix(".sha256").read_text(encoding="utf-8").split()[0]
    if sha256(CONFIG_FILE.read_bytes()).hexdigest() != frozen:
        raise ValueError("Frozen protocol checksum changed")
    field = load_data()
    splits = pd.read_csv(DERIVED / "v1_splits.csv")
    prior = pd.read_csv(DERIVED / "v1_predictions.csv")
    keep = ["track","fold","uid","year","observed","nearest_train_m","block","predicted","model"]
    prior = prior.loc[prior.feature.eq("E") & prior.model.isin(["Auto","ET"]),keep].copy()
    prior.model = prior.model.map({"Auto":"V1 Auto","ET":"V1 ExtraTrees (descriptive)"})
    data = []
    for (track,fold), group in splits.groupby(["track","fold"],sort=False):
        anchor = prior.loc[prior.track.eq(track) & prior.fold.eq(fold) & prior.model.eq("V1 Auto")]
        _, test_ids = split_ids(group[group.stage.eq("outer")])
        anchor = anchor.set_index("uid").loc[test_ids].reset_index()
        assert np.allclose(anchor.observed,field.loc[test_ids,"ec"])
        data.append((track,int(fold),group,field,anchor,args.smoke))
    if args.smoke:
        data = data[:1]
    if args.jobs == 1:
        runs = list(map(outer,data))
    else:
        with ProcessPoolExecutor(max_workers=args.jobs) as pool:
            runs = list(pool.map(outer,data))
    tables,chosen,traces,fits,importance = zip(*runs,strict=True)
    output = RESULTS if not args.smoke else ROOT / "code/smoke"
    output.mkdir(parents=True,exist_ok=True)
    pd.concat([prior,*tables],ignore_index=True).to_csv(output/"predictions.csv",index=False)
    for name,groups,cols in [
        ("inner_scores",traces,["track","fold","model","inner_fold","parameters","sse","n","seconds","warnings"]),
        ("fit_log",fits,["track","fold","model","seconds"]),
        ("importance",importance,["track","fold","group","replicate","delta_rmse"]),
    ]:
        pd.DataFrame([r for group in groups for r in group],columns=cols).to_csv(output/(name+".csv"),index=False)
    selection = {f"{track}/{fold}":config for track,fold,config in chosen}
    (output/"best_params.json").write_text(json.dumps(selection,indent=2)+"\n",encoding="utf-8")
    selections = {k:{n:p for n,p in v.items() if n in ("MISA","Inner champion")} for k,v in selection.items()}
    (output/"selected_models.json").write_text(json.dumps(selections,indent=2)+"\n",encoding="utf-8")
    packages = ["numpy","pandas","scipy","scikit-learn","catboost","lightgbm","xgboost","rasterio","matplotlib"]
    versions = {"python":platform.python_version(),"libraries":{name:version(name) for name in packages}}
    (output/"versions.json").write_text(json.dumps(versions,indent=2)+"\n",encoding="utf-8")


if __name__ == "__main__":
    main()
