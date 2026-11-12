"""Independently verify the prior benchmark and audit source coverage."""
from hashlib import md5, sha256
import json
import math

import numpy as np
import pandas as pd
from scipy.spatial.distance import cdist

from benchmark import DERIVED, P, RESULTS, ROOT, TERRAIN, XY, load_data
from acquire import eligible


def measures(observed, predicted) -> dict:
    y, p = list(observed), list(predicted)
    count = len(y)
    if not count:
        return {"n":0,"rmse":np.nan,"mae":np.nan,"r2":np.nan,"bias":np.nan}
    center = math.fsum(y)/count
    errors = [b-a for a,b in zip(y,p,strict=True)]
    sse = math.fsum(x*x for x in errors)
    sst = math.fsum((a-center)**2 for a in y)
    return {"n":count,"rmse":math.sqrt(sse/count),"mae":math.fsum(map(abs,errors))/count,
            "r2":1-sse/sst if sst else np.nan,"bias":math.fsum(errors)/count}


def verify_v1(field):
    old = ROOT/"archive/v1/results"
    full = pd.read_csv(DERIVED/"v1_predictions.csv")
    for levels,name in [(["track","feature","model"],"metrics"),(["track","feature","model","fold"],"fold_metrics")]:
        recorded = pd.read_csv(old/(name+".csv")).set_index(levels)
        for keys,g in full.groupby(levels):
            values = measures(g.observed,g.predicted)
            row = recorded.loc[keys]
            assert all(np.isclose(v,row[k],atol=1e-11,equal_nan=True) for k,v in values.items())
    split = pd.read_csv(DERIVED/"v1_splits.csv")
    nearest = []
    for (track,fold,stage,group),s in split.groupby(["track","fold","stage","group"]):
        tr = s.loc[s.role.eq("train"),"uid"]
        te = s.loc[s.role.eq("test"),"uid"]
        assert not set(tr)&set(te)
        d = cdist(field.loc[te,list(XY)],field.loc[tr,list(XY)]).min(axis=1)
        if stage == "inner" or track == "Spatial" or track.endswith("buffered"):
            assert d.min() >= P["buffer_m"]
        if stage=="outer":
            if track=="Spatial":
                nearest.append(d.min())
            else:
                assert not set(field.loc[tr,"year"])&set(field.loc[te,"year"])
            a=full.query("track == @track and fold == @fold and feature == 'E' and model == 'Auto'").set_index("uid").loc[te]
            np.testing.assert_allclose(d,a.nearest_train_m)
    for file in ("predictions.csv","splits.csv"):
        assert (DERIVED/("v1_"+file)).read_bytes()==(old/file).read_bytes()
    return len(full), min(nearest)


def main():
    field=load_data()
    prior_n, nearest=verify_v1(field)
    anchor=pd.read_csv(DERIVED/"v1_predictions.csv").query("feature=='E' and model=='Auto' and track=='Spatial'").set_index("uid")
    audit=field[["year","ec","s2_present","ls_present","easting","northing","date","s2_lag"]].join(
        anchor[["block","nearest_train_m","predicted"]])
    audit["v1_residual"]=audit.predicted-audit.ec
    audit["any_optical"]=(audit.s2_present.eq(1)|audit.ls_present.eq(1)).astype(int)
    audit["recovered"]=(audit.s2_present.eq(0)&audit.ls_present.eq(1)).astype(int)
    audit["terrain_complete"]=field[list(TERRAIN)].notna().all(axis=1).astype(int)
    audit["ec_group"]=pd.cut(audit.ec,[0,.5,2,5,np.inf],right=False).astype(str)
    audit["ls_candidates"]=0
    item_path=ROOT/"data/landsat_items.json"
    if item_path.exists():
        for item in json.loads(item_path.read_text(encoding="utf-8")):
            audit.loc[eligible(field,item).index,"ls_candidates"] += 1
    audit.to_csv(RESULTS/"site_audit.csv")
    coverage=[]
    for dimension,g in [("all",audit), *[(k,audit) for k in ("year","ec_group","block")]]:
        groups=[("all",g)] if dimension=="all" else g.groupby(dimension)
        for key,group in groups:
            coverage.append({"stratum":dimension,"level":key,"n":len(group),
                             **{k:int(group[k].sum()) for k in ("s2_present","ls_present","any_optical","recovered","terrain_complete")},
                             "no_ls_candidate":int(group.ls_candidates.eq(0).sum()),
                             "mean_ec":group.ec.mean(),"high_n":int(group.ec.ge(5).sum()),
                             "v1_rmse":np.sqrt(np.square(group.v1_residual).mean()),
                             "v1_bias":group.v1_residual.mean()})
    pd.DataFrame(coverage).to_csv(RESULTS/"coverage.csv",index=False)
    source=field.drop(columns=["ec","team","original_id","sample_id"],errors="ignore")
    source.to_csv(RESULTS/"feature_provenance.csv")
    result={"prior_predictions_audited":prior_n,"minimum_spatial_test_train_m":float(nearest),
            "years":field.groupby("year").size().to_dict(),
            "duplicate_coordinates":int(field.duplicated(list(XY)).sum()),
            "duplicate_s2_scene_cells":int(field.loc[field.s2_present.eq(1)].duplicated(["scene","scl_row","scl_col"]).sum()),
            "workbook_md5":{}}
    manifest=json.loads((ROOT/"data/manifest.json").read_text(encoding="utf-8"))
    for entry in manifest:
        file=entry["filename"]
        candidates=[ROOT/"data/raw"/file, ROOT.parent/"data/raw"/file]
        path=next((p for p in candidates if p.exists()),None)
        if path:
            digest=md5(path.read_bytes()).hexdigest()
            assert digest==entry["md5"] and sha256(path.read_bytes()).hexdigest()==entry["sha256"]
            result["workbook_md5"][file]=digest
    (RESULTS/"audit.json").write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")
    print(result,flush=True)


if __name__=="__main__":
    main()
