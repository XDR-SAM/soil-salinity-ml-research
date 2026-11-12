"""Build manuscript numerical macros directly from the reported results."""
import json
import pandas as pd

from download_originals import ROOT

RESULTS = ROOT / "results"
TRACKS = ("Spatial", "2024-to-2025", "2025-to-2024")


def main() -> None:
    metrics = pd.read_csv(RESULTS / "metrics.csv").set_index(["track", "feature", "model"])
    pairs = pd.read_csv(RESULTS / "paired_deltas.csv").set_index(
        ["track", "feature", "model", "baseline_feature", "baseline"])
    subgroup = pd.read_csv(RESULTS / "subgroups.csv").set_index(["track", "stratum", "level"])
    derived = ROOT / "data/derived"
    field = pd.read_csv(derived / "field.csv")
    sentinel = pd.read_csv(derived / "sentinel.csv")
    elevation = pd.read_csv(derived / "elevation.csv")
    satellite = field[["uid", "year"]].merge(sentinel, on="uid", validate="one_to_one")
    importance = pd.read_csv(RESULTS / "importance.csv")
    importance = (importance.loc[importance.track.eq("Spatial")].groupby("group")
                  .delta_rmse.mean().round(3).to_dict())

    def row(track, feature="E", model="Auto"):
        return metrics.loc[(track, feature, model)]

    def contrast(track, feature, base_feature, base, model="Auto"):
        return pairs.loc[(track, feature, model, base_feature, base)]

    def ci(item):
        return f"[{item.lo:.3f}, {item.hi:.3f}]"

    def describe(item):
        return f"{item.delta_rmse:+.3f} \\unit{{}} ({ci(item)})"

    spatial, forward, reverse = [row(track) for track in TRACKS]
    idw = contrast("Spatial", "E", "A", "IDW")
    coord = contrast("Spatial", "E", "A", "Auto")
    opt = contrast("Spatial", "B", "A", "Auto")
    elev = contrast("Spatial", "C", "B", "Auto")
    select = contrast("Spatial", "D", "C", "Auto")
    tune = contrast("Spatial", "E", "E", "RF-fixed", "RF")
    ridge_match = contrast("Spatial", "E", "A", "Ridge", "Ridge")
    forest_match = contrast("Spatial", "E", "A", "RF", "RF")
    high = subgroup.loc[("Spatial", "ec_bin", "[5.0, inf)")]
    low = subgroup.loc[("Spatial", "ec_bin", "[0.0, 0.5)")]
    blocks = subgroup.loc[("Spatial", "block")].sort_values("rmse")
    bounds = json.loads((ROOT / "reports/satkhira_boundary_check.json").read_text())["candidate_counts"]
    coverage = []
    for year, sample in satellite.groupby("year"):
        valid = sample.lag_days.dropna()
        coverage.append(f"{year}: {len(valid)}/{len(sample)}, median {valid.median():g} days, "
                        f"range {valid.min():g}--{valid.max():g} days")
    cov_text = ("The newest eligible optical scene was available for " + "; ".join(coverage) + ". "
                f"Surface elevation was available for {elevation.elevation.notna().sum()} of {len(field)} sites.")

    comparison = []
    for item, label in [(idw, "tuned IDW"), (coord, "coordinate-only Auto")]:
        if item.hi < 0:
            comparison.append(f"below zero against {label}")
        elif item.lo > 0:
            comparison.append(f"above zero against {label}")
        else:
            comparison.append(f"includes zero against {label}")
    spatial_words = "The paired interval " + " and ".join(comparison) + "."
    trans = []
    for track, label in zip(TRACKS[1:], ("the forward", "the reverse"), strict=True):
        diff = contrast(track, "E", "A", "IDW")
        trans.append(f"{describe(diff)} for {label} transfer")
    spatial_ref = row("Spatial", "A", "IDW").rmse
    transfer_ref = [row(track, "A", "IDW").rmse for track in TRACKS[1:]]
    related = (
        f"Spatial Auto and IDW achieved {spatial.rmse:.3f} and {spatial_ref:.3f} \\unit{{}} RMSE. "
        f"Across campaigns, the all-predictor procedure yielded {forward.rmse:.3f} and "
        f"{reverse.rmse:.3f} \\unit{{}} versus {transfer_ref[0]:.3f} and {transfer_ref[1]:.3f} for IDW."
    )
    table = []
    for name, f, m in [
        ("Training mean", "A", "Mean"), ("Training median", "A", "Median"),
        ("Coordinate OLS", "A", "OLS"), ("Tuned IDW", "A", "IDW"),
        ("A: Coordinates (Auto)", "A", "Auto"), ("B: Sentinel-2 (Auto)", "B", "Auto"),
        ("C: Sentinel-2 and elevation (Auto)", "C", "Auto"),
        ("D: Selected predictors (Auto)", "D", "Auto"), ("E: All predictors (Auto)", "E", "Auto"),
    ]:
        numbers = [f"{row(t, f, m)[key]:.3f}" for t in TRACKS for key in ("rmse", "mae", "r2")]
        table.append(" & ".join([name, *numbers]) + r" \\")
    values = {
        "SpatialRMSE": f"{spatial.rmse:.3f}", "SpatialRsq": f"{spatial.r2:.3f}",
        "ForwardRMSE": f"{forward.rmse:.3f}", "ReverseRMSE": f"{reverse.rmse:.3f}",
        "SpatialIDW": f"{spatial_ref:.3f}", "SpatialMean": f'{row("Spatial", "A", "Mean").rmse:.3f}',
        "SpatialDelta": f"{idw.delta_rmse:+.3f}", "SpatialDeltaCI": ci(idw),
        "CoordDelta": f"{coord.delta_rmse:+.3f}", "CoordDeltaCI": ci(coord),
        "BoundaryCount": f"{bounds['2024']} (2024) and {bounds['2025']} (2025)",
        "CoverageText": cov_text, "SpatialInterpretation": spatial_words,
        "AblationText": ("In spatial CV, replacing coordinate-only selection with optical-only "
                         f"selection changed RMSE by {describe(opt)}. Adding elevation to optical "
                         f"features changed it by {describe(elev)}. Restricting the candidate "
                         f"predictors with the nested selector changed it by {describe(select)}. "
                         "Within matched families, enriching coordinates with optical and elevation "
                         f"predictors changed RMSE by {describe(ridge_match)} for ridge and "
                         f"{describe(forest_match)} for the random forest."),
        "TuningText": ("With all predictors, tuning the random forest changed RMSE by "
                       f"{describe(tune)} relative to the fixed forest."),
        "TransferText": "Relative to tuned IDW, the RMSE differences were " + " and ".join(trans) + ".",
        "BufferedForward": f'{row("2024-to-2025-buffered").rmse:.3f}',
        "BufferedReverse": f'{row("2025-to-2024-buffered").rmse:.3f}',
        "ResidualText": (f"In spatial CV the {int(high.n)} observations at or above 5 \\unit{{}} "
                         f"had mean residual {high.bias:+.3f} \\unit{{}}, and the {int(low.n)} "
                         f"below 0.5 \\unit{{}} had mean residual {low.bias:+.3f} \\unit{{}}. "
                         f"Spatial fold RMSE ranged from {blocks.rmse.min():.3f} to "
                         f"{blocks.rmse.max():.3f} \\unit{{}}."),
        "ImportanceText": ("Across spatial folds, the mean increase in RMSE was "
                           f"{importance['Coordinates']:+.3f} for coordinates, "
                           f"{importance['Sentinel-2']:+.3f} for Sentinel-2 and "
                           f"{importance['Elevation']:+.3f} \\unit{{}} for elevation."),
        "ConclusionText": related,
        "ResultRows": "\n" + "\n".join(table) + "\n",
    }
    output = ["% Generated by scripts/paper_numbers.py from results and the acquisition logs."]
    output += [rf"\newcommand{{\{name}}}{{{value}}}" for name, value in values.items()]
    (ROOT / "paper/numbers.tex").write_text("\n".join(output) + "\n", encoding="utf-8")
    report = ["# Sentinel-2 and terrain coverage", "",
              *[f"- {line}." for line in coverage],
              f"- Optical column missing counts: {sentinel.isna().sum().to_dict()}.",
              f"- DEM missing: {elevation.elevation.isna().sum()}.",
              f"- DEM tiles: {', '.join(sorted(elevation.dem_tile.unique()))}.",
              "- Native spectral pixels are 10 m and 20 m. SCL is native 20 m.",
              "- Per-row source IDs, lags, SCL cells and elevation tile URLs are in "
              "`results/covariate_provenance.csv`.", ""]
    (ROOT / "reports/feature_coverage.md").write_text("\n".join(report), encoding="utf-8")
    sentinel.merge(elevation, on="uid", validate="one_to_one").to_csv(
        RESULTS / "covariate_provenance.csv", index=False)
    pd.read_csv(derived / "sentinel_log.csv").to_csv(RESULTS / "scene_log.csv", index=False)


if __name__ == "__main__":
    main()
