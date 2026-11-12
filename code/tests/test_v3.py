"""Regression checks for study output, fold isolation, and manuscript numbers."""
from hashlib import sha256
import json
from pathlib import Path
import re
import sys

import numpy as np
import pandas as pd
from scipy.spatial.distance import cdist

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"code/scripts"))
from audit import measures, verify_v1
from benchmark import (CONFIG_FILE, DERIVED, RESULTS, Trial, XY, design, fit,
                       gate, load_data, split_ids, weights)


def test_protocol_and_original_hashes():
    expected=CONFIG_FILE.with_suffix(".sha256").read_text().split()[0]
    assert sha256(CONFIG_FILE.read_bytes()).hexdigest()==expected
    for row in (ROOT/"reports/pre_evaluation_hashes.txt").read_text().splitlines():
        digest,path=row.split("  ",1)
        assert sha256((ROOT/path).read_bytes()).hexdigest()==digest
    field=load_data()
    assert field.groupby("year").size().to_dict()=={2024:162,2025:187}
    assert field.index.is_unique
    assert field.ec.ge(0).all()
    assert len(verify_v1(field))==2


def test_splits_and_no_cross_year_label_access():
    field=load_data()
    splits=pd.read_csv(DERIVED/"v1_splits.csv")
    for (track,_),outer in splits.groupby(["track","fold"]):
        a,b=split_ids(outer.query("stage=='outer'"))
        assert not set(a)&set(b)
        if track!="Spatial":
            assert set(field.loc[a,"year"]).isdisjoint(field.loc[b,"year"])
        if track=="Spatial" or track.endswith("buffered"):
            assert cdist(field.loc[a,list(XY)],field.loc[b,list(XY)]).min()>=1000
        for _,inner in outer.query("stage=='inner'").groupby("group"):
            t,v=split_ids(inner)
            assert set(t+v)<=set(a)
            assert not set(t)&set(v)
            assert cdist(field.loc[t,list(XY)],field.loc[v,list(XY)]).min()>=1000


def test_source_dates_qa_and_predictor_allowlist():
    data=load_data()
    feature_sets,_=design(data)
    forbidden={"ec","observed","year","date","sample_id","original_id","uid","team","ls_scene","scene","scl","ls_qa"}
    assert all(not forbidden.intersection(cols) for cols in feature_sets.values())
    for source,flag,lag,time,window in [("S2","s2_present","s2_lag","acquired_utc",30),
                                      ("Landsat","ls_present","ls_lag","ls_time",45)]:
        match=data[data[flag].eq(1)]
        if match.empty:
            continue
        day=pd.to_datetime(match[time],utc=True).dt.tz_convert("Asia/Dhaka").dt.tz_localize(None).dt.normalize()
        age=(match.date-day).dt.days
        assert age.between(1,window).all()
        np.testing.assert_array_equal(age,match[lag])
        if source=="S2":
            assert match.scl.isin([4,5]).all()
        else:
            assert ((match.ls_qa.astype(int)&191)==0).all() and match.ls_radsat.eq(0).all()
    c=pd.read_csv(RESULTS/"coverage.csv").query("stratum=='all'").iloc[0]
    assert c.any_optical==int((data.s2_present.eq(1)|data.ls_present.eq(1)).sum())
    assert c.recovered==int((data.s2_present.eq(0)&data.ls_present.eq(1)).sum())


def test_fold_local_preprocessing_and_blend_constraints():
    # Exercise the preprocessing contract without fitting on archived observations.
    sets={"full":list(XY)}
    train=pd.DataFrame({"easting":[0.0,1.0,np.nan,3.0],
                        "northing":[1.0,2.0,3.0,4.0],"ec":[1.0,2.0,3.0,4.0]})
    test=pd.DataFrame({"easting":[100.0,np.nan],"northing":[1000.0,2000.0]})
    model=fit(Trial("Ridge"),{"alpha":1.0},sets,train)
    model.predict(test[sets["full"]])
    expected=train[sets["full"]].median().fillna(0).to_numpy()
    np.testing.assert_allclose(model[0].statistics_,expected)
    matrix=np.array([[1,4],[2,2],[3,1],[4,3],[5,2],[6,1],[7,5],[8,2]],dtype=float)
    y=matrix[:,0]
    w=weights(matrix,y)
    assert np.isclose(w.sum(),1) and np.all(w>=0)
    global_w,conditional=gate(matrix,y,np.ones(len(y)))
    assert all(np.isclose(g.sum(),1) and np.all(g>=0) for g in [global_w,*conditional.values()])


def test_prediction_recomputation_and_claim():
    p=pd.read_csv(RESULTS/"predictions.csv")
    assert not p.duplicated(["track","model","uid"]).any()
    m=pd.read_csv(RESULTS/"metrics.csv").set_index(["track","model"])
    for key,rows in p.groupby(["track","model"]):
        r=measures(rows.observed,rows.predicted)
        assert all(np.isclose(x,m.loc[key,k],atol=1e-11,equal_nan=True) for k,x in r.items())
    v=json.loads((RESULTS/"verdict.json").read_text(encoding="utf-8"))
    top=m.loc["Spatial"].rmse.idxmin()
    assert top==v["best"]["model"]
    q=pd.read_csv(RESULTS/"paired_deltas.csv").query("track=='Spatial' and model=='MISA'")
    assert v["paired_superiority"]==bool(top=="MISA" and q.hi.lt(0).all())
    assert not v["independent_external_validation"]
    numbers=(ROOT/"paper/numbers.tex").read_text(encoding="utf-8")
    for col,command in [("rmse","MisaRmse"),("mae","MisaMae"),("r2","MisaRsq")]:
        assert rf"\newcommand{{\{command}}}{{{m.loc[('Spatial','MISA'),col]:.3f}}}" in numbers


def test_meta_weights_and_inner_only_selection():
    fits=json.loads((RESULTS/"selected_models.json").read_text(encoding="utf-8"))
    trials=pd.read_csv(RESULTS/"inner_scores.csv")
    assert len(fits)==10
    for key,v in fits.items():
        track,fold=key.split("/")
        sub=trials[trials.track.eq(track)&trials.fold.eq(int(fold))]
        r=sub.groupby(["model","parameters"])[["sse","n"]].sum()
        r["rmse"]=np.sqrt(r.sse/r.n)
        assert np.isclose(r.loc[v["Inner champion"]["expert"]].rmse.min(),r.rmse.min())
        assert len(v["MISA"]["experts"])<=4
        for values in (v["MISA"]["global"],*v["MISA"]["conditional"].values()):
            assert np.isclose(sum(values),1) and min(values)>=-1e-12


def test_tex_sources_and_privacy():
    text=(ROOT/"paper/main.tex").read_text(encoding="utf-8")
    bibliography=(ROOT/"paper/references.bib").read_text(encoding="utf-8")
    barrier=text.rindex(r"\FloatBarrier")
    assert text.rindex(r"\end{figure*}") < barrier
    assert text.rindex(r"\end{table*}") < barrier
    assert barrier < text.index(r"\bibliography{references}") < text.index(r"\end{document}")
    for refs in re.findall(r"\\cite(?:\[[^\]]*\])?\{([^}]+)\}",text):
        assert all("{"+key+"," in bibliography for key in refs.split(","))
    assets=re.findall(r"\\includegraphics\[[^\]]*\]\{([^}]+)\}",text)
    assert "proposed_framework" in assets and len(assets)==7
    for name in assets:
        for suffix in ("pdf","svg","png"):
            assert (ROOT/"figures"/f"{name}.{suffix}").stat().st_size>1000
    assert (ROOT/"paper/main.pdf").read_bytes().startswith(b"%PDF-")
    privacy=re.compile(r"(?i)(?:[a-z]:[\\/](?:users|desktop)[\\/]|github\.com/[^/\s]+/soil-salinity|ryzen|intel core)")
    for path in [ROOT/"README.md",ROOT/"paper/main.tex",*list((ROOT/"figures").glob("*.svg"))]:
        assert not privacy.search(path.read_text(encoding="utf-8")),path.name
