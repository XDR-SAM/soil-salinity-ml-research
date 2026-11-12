"""Score every archived prediction and compare matched predictions by spatial block."""
import json
import numpy as np
import pandas as pd

from audit import measures
from benchmark import P, RESULTS


def resample(blocks):
    random=np.random.default_rng(P["seed"])
    groups=[np.flatnonzero(blocks==key) for key in np.unique(blocks)]
    return [np.concatenate([groups[i] for i in indices]) for indices in
            random.integers(len(groups),size=(P["bootstrap"]["replicates"],len(groups)))]


def interval(values):
    return np.quantile(values,[.025,.975])


def paired(pred):
    rows, pairs, subpairs = [], [], []
    for track,chunk in pred.groupby("track"):
        table=chunk.pivot(index=["uid","observed","block"],columns="model",values="predicted")
        assert not table.isna().any().any()
        idx=table.index.to_frame(index=False)
        draws=resample(idx.block.to_numpy())
        y=idx.observed.to_numpy()
        errors={k:table[k].to_numpy()-y for k in table}
        boots={}
        for name,error in errors.items():
            boots[name]=np.array([np.sqrt(np.square(error[ix]).mean()) for ix in draws])
            low,high=interval(boots[name])
            rows.append(dict(track=track,model=name,**measures(y,table[name]),rmse_lo=low,rmse_hi=high))
        names=sorted(errors,key=lambda m: np.square(errors[m]).mean())
        pair_keys = {(first,other) for first in ("MISA",names[0]) for other in names if other!=first}
        for name,other in sorted(pair_keys):
            a,b=(np.sqrt(np.square(errors[k]).mean()) for k in (name,other))
            lo,hi=interval(boots[name]-boots[other])
            pairs.append(dict(track=track,model=name,baseline=other,delta_rmse=a-b,
                              rmse_reduction_pct=100*(b-a)/b,lo=lo,hi=hi))
        for label,mask in [("high_ec",y>=5),("s2_missing",idx.uid.map(SITES.s2_present).eq(0).to_numpy()),
                           ("any_optical",idx.uid.map(SITES.any_optical).eq(1).to_numpy())]:
            if not mask.any():
                continue
            sub_draws=[ix[mask[ix]] for ix in draws if mask[ix].any()]
            comparisons={("MISA",other) for other in ("V1 Auto","V1 ExtraTrees (descriptive)",names[0],names[1])}
            if label=="high_ec":
                comparisons.update((f"{family} weighted",f"{family} full-4")
                                   for family in ("ET","RF","Huber-GB"))
            if label=="s2_missing":
                comparisons.add(("ET full-4","ET no_landsat"))
            for first,other in sorted(comparisons):
                if first==other or not {first,other}<=errors.keys():
                    continue
                contrast=np.abs(errors[first])-np.abs(errors[other])
                lo,hi=interval([contrast[ix].mean() for ix in sub_draws])
                subpairs.append(dict(track=track,subgroup=label,n=int(mask.sum()),model=first,baseline=other,
                                     delta_mae=contrast[mask].mean(),lo=lo,hi=hi))
    return pd.DataFrame(rows),pd.DataFrame(pairs),pd.DataFrame(subpairs)


def main():
    global SITES
    SITES=pd.read_csv(RESULTS/"site_audit.csv").set_index("uid")
    pred=pd.read_csv(RESULTS/"predictions.csv")
    assert not pred.duplicated(["track","model","uid"]).any()
    metrics,pairs,subpairs=paired(pred)
    metrics.to_csv(RESULTS/"metrics.csv",index=False)
    pairs.to_csv(RESULTS/"paired_deltas.csv",index=False)
    subpairs.to_csv(RESULTS/"subgroup_deltas.csv",index=False)
    folds=[]
    for (track,fold,model),g in pred.groupby(["track","fold","model"]):
        folds.append(dict(track=track,fold=fold,model=model,**measures(g.observed,g.predicted)))
    pd.DataFrame(folds).to_csv(RESULTS/"fold_metrics.csv",index=False)
    aug=pred.join(SITES[["ec_group","s2_present","any_optical","recovered"]],on="uid")
    aug["distance_km"]=pd.cut(aug.nearest_train_m/1000,[0,1,5,15,np.inf],right=False).astype(str)
    sub=[]
    for name in ("year","ec_group","block","s2_present","any_optical","recovered","distance_km"):
        for (track,model,level),g in aug.groupby(["track","model",name]):
            sub.append(dict(track=track,model=model,stratum=name,level=level,**measures(g.observed,g.predicted)))
    pd.DataFrame(sub).to_csv(RESULTS/"subgroups.csv",index=False)
    ablation=metrics.loc[metrics.model.str.startswith(("ET ","RF ","MISA","Huber-GB "))|
                         metrics.model.isin(["ExtraTrees","RF","Huber-GB"])]
    ablation.to_csv(RESULTS/"ablations.csv",index=False)
    spatial=metrics.loc[metrics.track.eq("Spatial")].sort_values("rmse")
    primary=spatial.loc[spatial.model.eq("MISA")].iloc[0]
    best=spatial.iloc[0]
    next_best=spatial.loc[spatial.model.ne("MISA")].iloc[0]
    superiority=bool(primary.rmse<next_best.rmse and
                     (pairs.query("track=='Spatial' and model=='MISA'").hi<0).all())
    result=dict(proposed=primary.to_dict(), best=best.to_dict(), strongest_comparator=next_best.to_dict(),
                paired_superiority=superiority, independent_external_validation=False)
    (RESULTS/"verdict.json").write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")


if __name__=="__main__":
    main()
