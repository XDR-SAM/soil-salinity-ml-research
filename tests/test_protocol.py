"""Unit and post-run integration checks for the research protocol."""
from hashlib import md5
from pathlib import Path
import re
import sys

import numpy as np
import pandas as pd
from scipy.spatial.distance import cdist

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from download_originals import ROOT, SOURCES
from evaluate import score
from train_models import FEATURES, IDW, inputs, model_pipeline, XY


def test_field_provenance():
    source = ROOT / "data/derived"
    field = pd.read_csv(source / "field.csv")
    ledger = pd.read_csv(source / "processing_log.csv")
    assert len(ledger) == 349 == len(field)
    assert field.uid.is_unique
    assert field.groupby("year").size().to_dict() == {2024: 162, 2025: 187}
    assert np.isfinite(field[XY + ["ec"]]).all().all()
    assert field.ec.ge(0).all()
    for _, name, digest, _ in SOURCES.values():
        assert md5((ROOT / "data/raw" / name).read_bytes()).hexdigest() == digest


def test_feature_allowlist():
    forbidden = {"year", "original_id", "sample_id", "uid", "team", "date", "lag_days",
                 "scene", "ec", "observed", "target", "scl", "acquired_utc"}
    assert all(forbidden.isdisjoint(values) for values in FEATURES.values())
    assert FEATURES["A"] == XY


def test_training_transform_isolation():
    field = pd.read_csv(ROOT / "data/derived/field.csv")
    train = inputs(field.iloc[:100], "A")
    test = inputs(field.iloc[100:110], "A").copy()
    test.loc[:, "northing"] += 1000000
    pipeline = model_pipeline("Ridge", "A", {"alpha": 1}).fit(train, field.ec.iloc[:100])
    pipeline.predict(test)
    assert np.allclose(pipeline[0].statistics_, train.median())
    assert np.allclose(pipeline[1].mean_, train.mean())


def test_scoring_and_idw():
    true = np.array([1., 3.])
    predicted = np.array([2., 3.])
    value = score(true, predicted)
    assert value["r2"] == 0.5
    assert value["mae"] == 0.5
    assert np.isclose(value["rmse"], np.sqrt(.5))
    model = IDW().fit(np.array([[0., 0.], [2., 0.]]), true)
    np.testing.assert_allclose(model.predict(np.array([[1., 0.], [0., 0.]])), [2., 1.])


def test_archived_splits_and_predictions():
    field = pd.read_csv(ROOT / "data/derived/field.csv").set_index("uid")
    splits = pd.read_csv(ROOT / "results/splits.csv")
    predictions = pd.read_csv(ROOT / "results/predictions.csv")
    assert not predictions.duplicated(["track", "feature", "model", "uid"]).any()
    assert np.isfinite(predictions.predicted).all() and predictions.predicted.ge(0).all()
    assert np.allclose(predictions.observed, field.loc[predictions.uid, "ec"])
    for (track, fold), group in splits.groupby(["track", "fold"]):
        outer = group[group.stage.eq("outer")]
        train = set(outer.loc[outer.role.eq("train"), "uid"])
        test = set(outer.loc[outer.role.eq("test"), "uid"])
        assert train.isdisjoint(test)
        if track != "Spatial":
            assert set(field.loc[sorted(train), "year"]).isdisjoint(field.loc[sorted(test), "year"])
        if track == "Spatial" or track.endswith("-buffered"):
            assert cdist(field.loc[sorted(train), XY], field.loc[sorted(test), XY]).min() >= 1000
        inner = group[group.stage.eq("inner")]
        assert set(inner.uid).issubset(train)
        for _, block in inner.groupby("group"):
            i_train = block.loc[block.role.eq("train"), "uid"]
            i_test = block.loc[block.role.eq("test"), "uid"]
            assert set(i_train).isdisjoint(i_test)
            assert cdist(field.loc[i_train, XY], field.loc[i_test, XY]).min() >= 1000
        scored = predictions.loc[predictions.track.eq(track) & predictions.fold.eq(fold)]
        assert set(scored.uid) == test
    assert len(predictions.query("track == 'Spatial' and feature == 'A' and model == 'IDW'")) == 349


def test_optical_causality_and_archive():
    source = ROOT / "data/derived"
    field = pd.read_csv(source / "field.csv", parse_dates=["date"]).set_index("uid")
    optical = pd.read_csv(source / "sentinel.csv").set_index("uid")
    assert set(field.index) == set(optical.index)
    matched = optical.dropna(subset=["scene"])
    days = pd.to_datetime(matched.acquired_utc, utc=True).dt.tz_convert(
        "Asia/Dhaka").dt.tz_localize(None).dt.normalize()
    lag = (field.loc[matched.index, "date"] - days).dt.days
    assert lag.between(1, 30).all()
    assert np.array_equal(lag, matched.lag_days)
    assert matched.scl.isin([4, 5]).all()
    assert (matched[["ndvi", "ndmi"]].abs() <= 1).all().all()


def test_paper_inputs():
    tex = (ROOT / "paper/main.tex").read_text(encoding="utf-8")
    bibliography = (ROOT / "paper/references.bib").read_text(encoding="utf-8")
    for key in re.findall(r"\\cite(?:\[[^\]]*\])?\{([^}]+)\}", tex):
        for reference in key.split(","):
            assert "{" + reference + "," in bibliography
    for figure in re.findall(r"\\includegraphics\[[^\]]*\]\{([^}]+)\}", tex):
        for suffix in ("pdf", "png", "svg"):
            path = ROOT / "figures" / f"{figure}.{suffix}"
            assert path.stat().st_size > 1000
    assert (ROOT / "paper/main.pdf").read_bytes().startswith(b"%PDF-")
