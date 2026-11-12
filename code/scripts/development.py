"""Explore geographic residual correction within archived outer training sets only."""
import json

import numpy as np
import pandas as pd
from scipy.spatial.distance import cdist
from threadpoolctl import threadpool_limits

from audit import measures
from benchmark import DERIVED, RESULTS, Trial, XY, design, estimate, fit, load_data, split_ids

TRIAL=Trial("ExtraTrees")
PARAMS={"n_estimators":120,"min_samples_leaf":4,"max_features":.75,"max_depth":8}
SHRINK=(0.,.25,.5,.75)


def buffered(frame,train_ids,test_ids):
    distance=cdist(frame.loc[train_ids,list(XY)],frame.loc[test_ids,list(XY)]).min(axis=1)
    return list(np.asarray(train_ids)[distance>=1000])


def run():
    field=load_data()
    features,_=design(field)
    splits=pd.read_csv(DERIVED/"v1_splits.csv")
    rows=[]
    with threadpool_limits(limits=1):
        for outer_fold,partition in splits[splits.track.eq("Spatial")].groupby("fold"):
            train_ids,_=split_ids(partition.query("stage=='outer'"))
            frame=field.loc[train_ids]
            inner=[(group,*split_ids(members)) for group,members in
                   partition.query("stage=='inner'").groupby("group")]
            for group,tr,va in inner:
                residual=pd.Series(index=tr,dtype=float)
                for g,_,subtest in inner:
                    if g==group:
                        continue
                    calibration=[uid for uid in subtest if uid in residual.index]
                    subtrain=[uid for uid in tr if uid not in set(calibration)]
                    if not calibration:
                        continue
                    subtrain=buffered(frame,subtrain,calibration)
                    base=fit(TRIAL,PARAMS,features,frame.loc[subtrain])
                    residual.loc[calibration]=frame.loc[calibration,"ec"]-estimate(
                        base,TRIAL,features,frame.loc[calibration])
                assert residual.notna().all()
                test=frame.loc[va]
                est=fit(TRIAL,PARAMS,features,frame.loc[tr])
                primary=estimate(est,TRIAL,features,test)
                distances=cdist(test[list(XY)],frame.loc[tr,list(XY)])
                ids=np.argsort(distances,axis=1,kind="stable")[:,:12]
                near=np.take_along_axis(distances,ids,axis=1)
                weight=near**-2
                correction=(residual.loc[tr].to_numpy()[ids]*weight).sum(axis=1)/weight.sum(axis=1)
                for fraction in SHRINK:
                    prediction=np.maximum(primary+fraction*correction,0)
                    rows.extend((outer_fold,group,fraction,uid,y,yhat)
                                for uid,y,yhat in zip(va,test.ec,prediction,strict=True))
    pred=pd.DataFrame(rows,columns=["outer_train_set","inner_validation_group","shrinkage","uid","observed","predicted"])
    pred.to_csv(RESULTS/"development_predictions.csv",index=False)
    aggregate=[]
    for (outer,shrink),group in pred.groupby(["outer_train_set","shrinkage"]):
        aggregate.append(dict(outer_train_set=outer,shrinkage=shrink,
                              **measures(group.observed,group.predicted)))
    out=pd.DataFrame(aggregate)
    out.to_csv(RESULTS/"development_residual_correction.csv",index=False)
    winners=out.loc[out.groupby("outer_train_set").rmse.idxmin()]
    print(json.dumps({"inner_only_winners":winners.shrinkage.value_counts().to_dict()},indent=2),flush=True)


if __name__=="__main__":
    run()
