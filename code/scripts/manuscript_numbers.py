"""Generate manuscript numbers, claims, and decision documents from actual scores."""
import json
from pathlib import Path

import pandas as pd
from figures import MAIN, SHORT

ROOT=Path(__file__).resolve().parents[2]
R=ROOT/"results"


def signed(value):
    return rf"\ensuremath{{{value:+.3f}}}"


def tex_ci(item):
    return rf"\mbox{{$[{item.lo:.3f},\,{item.hi:.3f}]$}}"


def plain_ci(item):
    return f"[{item.lo:+.3f}, {item.hi:+.3f}]"


def comparison_label(name):
    return "ExtraTrees without Landsat" if name=="ET no_landsat" else SHORT.get(name,name)


def main():
    m=pd.read_csv(R/"metrics.csv").set_index(["track","model"])
    p=pd.read_csv(R/"paired_deltas.csv").set_index(["track","model","baseline"])
    s=pd.read_csv(R/"subgroups.csv").set_index(["track","model","stratum","level"]).sort_index()
    d=pd.read_csv(R/"subgroup_deltas.csv")
    sites=pd.read_csv(R/"site_audit.csv")
    cover=pd.read_csv(R/"coverage.csv")
    opt=cover.query("stratum=='all'").iloc[0]
    high=cover.query("stratum=='ec_group' and level.str.startswith('[5')",engine="python").iloc[0]
    v=json.loads((R/"verdict.json").read_text(encoding="utf-8"))
    a=v["proposed"]
    best=v["best"]["model"]
    strongest=v["strongest_comparator"]["model"]
    v1=p.loc["Spatial","MISA","V1 Auto"]
    against=p.loc["Spatial","MISA",strongest]
    prior_et=p.loc["Spatial","MISA","V1 ExtraTrees (descriptive)"]
    best_v1=p.loc["Spatial",best,"V1 Auto"] if best!="V1 Auto" else None
    high_key=high.level
    high_m=s.loc["Spatial","MISA","ec_group",high_key]
    high_v=s.loc["Spatial","V1 Auto","ec_group",high_key]
    high_other=s.loc["Spatial",strongest,"ec_group",high_key]
    high_compare=d.query("track=='Spatial' and subgroup=='high_ec' and baseline=='V1 Auto'").iloc[0]
    missing_compare=d.query("track=='Spatial' and subgroup=='s2_missing' and baseline=='V1 Auto'").iloc[0]
    high_weight=d.query("track=='Spatial' and subgroup=='high_ec' and model=='Huber-GB weighted'").iloc[0]
    high_raw=s.loc["Spatial","Huber-GB full-4","ec_group",high_key]
    high_robust=s.loc["Spatial","Huber-GB weighted","ec_group",high_key]
    fwd=m.loc["2024-to-2025","MISA"]
    rev=m.loc["2025-to-2024","MISA"]
    buff=[m.loc[t+"-buffered","MISA"] for t in ("2024-to-2025","2025-to-2024")]

    include=list(dict.fromkeys([*MAIN,"MISA global","MISA equal",best]))
    rows=[]
    base=m.loc["Spatial","V1 Auto"].rmse
    for key in include:
        r=m.loc["Spatial",key]
        label=comparison_label(key)
        rmse=f"{r.rmse:.3f}"
        if key==best:
            rmse=rf"\textbf{{{rmse}}}"
        rows.append(f"{label} & {int(r.n)} & {rmse} & {r.mae:.3f} & {r.r2:.3f} & {signed(r.rmse-base)} "+r"\\")

    if v["paired_superiority"]:
        abstract="The paired spatial intervals favored MISA over the matched comparators."
        conclusion="MISA had the strongest matched spatial score and favorable paired intervals within this reanalysis."
    else:
        strongest_label=comparison_label(strongest)
        abstract=f"{strongest_label} scored RMSE {m.loc['Spatial',strongest].rmse:.3f} \\unit{{}}. Overall superiority of MISA was unsupported."
        conclusion="Optical coverage improved, but the matched evaluation did not establish overall superiority for the missingness-informed ensemble."

    absent=sites.query("s2_present==0")
    present=sites.query("s2_present==1")
    old_missing=absent.v1_residual.pow(2).mean()**.5
    old_clear=present.v1_residual.pow(2).mean()**.5
    ab=m.loc["Spatial"]
    ab_text=(f"Equal-budget ExtraTrees RMSE was {ab.loc['ET full-4'].rmse:.3f} \\unit{{}} with full inputs, "
             f"{ab.loc['ET v1'].rmse:.3f} with V1 inputs and {ab.loc['ET no_flags'].rmse:.3f} "
             f"without availability flags. Log targets yielded {ab.loc['ET log'].rmse:.3f} and "
             f"high-EC weighting {ab.loc['ET weighted'].rmse:.3f} \\unit{{}}. The same MISA experts gave "
             f"{ab.loc['MISA global'].rmse:.3f} with global and {ab.loc['MISA equal'].rmse:.3f} with equal weights.")
    if "ET no_landsat" in ab.index:
        ab_text += f" Removing Landsat gave {ab.loc['ET no_landsat'].rmse:.3f} \\unit{{}}."
    high_text=(f"High-EC weighting in Huber boosting reduced high-EC MAE from {high_raw.mae:.3f} to "
               f"{high_robust.mae:.3f} \\unit{{}} (paired difference {signed(high_weight.delta_mae)}, "
               f"{tex_ci(high_weight)}). The pooled RMSE increased from {ab.loc['Huber-GB full-4'].rmse:.3f} "
               f"to {ab.loc['Huber-GB weighted'].rmse:.3f} \\unit{{}}. Weighted random forest and extra trees "
               "showed the same trade-off.")
    importance=pd.read_csv(R/"importance.csv").groupby("group").delta_rmse.mean().sort_values(ascending=False)
    importance_text="Mean RMSE changes were "+", ".join(f"{signed(value)} for {key}" for key,value in importance.items())+" \\unit{}."
    numeric={
        "SentinelCount":str(int(opt.s2_present)),"AnyCount":str(int(opt.any_optical)),
        "MisaRmse":f"{a['rmse']:.3f}","MisaMae":f"{a['mae']:.3f}","MisaRsq":f"{a['r2']:.3f}",
        "DeltaVone":signed(v1.delta_rmse),"DeltaVoneCI":tex_ci(v1),
        "AbstractVerdict":abstract,"ConclusionText":conclusion,
        "CoverageText":(f"Landsat matched {int(opt.ls_present)} sites and recovered optical predictors at "
                        f"{int(opt.recovered)} of the {int(opt.n-opt.s2_present)} originally unmatched sites. "
                        f"Among the {int(high.n)} high-EC sites, availability changed from {int(high.s2_present)} "
                        f"to {int(high.any_optical)}. Local terrain derivatives were available for {int(opt.terrain_complete)} sites."),
        "PriorFailureText":(f"Mean EC was {absent.ec.mean():.3f} \\unit{{}} without Sentinel-2 and "
                            f"{present.ec.mean():.3f} \\unit{{}} with Sentinel-2. V1 Auto spatial RMSE "
                            f"was {old_missing:.3f} and {old_clear:.3f} \\unit{{}} in those respective groups."),
        "SpatialText":(f"MISA scored {a['rmse']:.3f} \\unit{{}} RMSE, {a['mae']:.3f} \\unit{{}} MAE "
                       f"and $R^2={a['r2']:.3f}$. Its RMSE difference against V1 Auto was "
                       f"{signed(v1.delta_rmse)} \\unit{{}} ({tex_ci(v1)}), a "
                       f"{v1.rmse_reduction_pct:+.1f}\\% relative reduction."),
        "CompareText":(f"The lowest point estimate was {m.loc['Spatial',best].rmse:.3f} \\unit{{}} for "
                       f"{comparison_label(best)}. Against {comparison_label(strongest)}, the MISA difference "
                       f"was {signed(against.delta_rmse)} \\unit{{}} ({tex_ci(against)})."),
        "SubgroupText":(f"For EC at or above 5 \\unit{{}}, MISA MAE was {high_m.mae:.3f} \\unit{{}} and "
                        f"bias was {signed(high_m.bias)} \\unit{{}}, compared with {high_v.mae:.3f} "
                        f"and {signed(high_v.bias)} \\unit{{}} for V1 Auto. The paired high-EC MAE "
                        f"difference was {signed(high_compare.delta_mae)} \\unit{{}} ({tex_ci(high_compare)}). "
                        f"Without Sentinel-2, the paired MAE difference against V1 Auto was "
                        f"{signed(missing_compare.delta_mae)} \\unit{{}} ({tex_ci(missing_compare)})."),
        "TransferText":(f"Transfer RMSE was {fwd.rmse:.3f} \\unit{{}} ($R^2={fwd.r2:.3f}$) for "
                        f"2024 to 2025 and {rev.rmse:.3f} \\unit{{}} ($R^2={rev.r2:.3f}$) in reverse. "
                        f"The buffered counterparts were {buff[0].rmse:.3f} and {buff[1].rmse:.3f} \\unit{{}}."),
        "AblationText":ab_text,"HighWeightText":high_text,"ImportanceText":importance_text,
        "LeaderRows":"\n"+"\n".join(rows)+"\n",
    }
    output=["% Generated from held-out prediction summaries."]+[rf"\newcommand{{\{k}}}{{{value}}}" for k,value in numeric.items()]
    (ROOT/"paper/numbers.tex").write_text("\n".join(output)+"\n",encoding="utf-8")

    headline=f"""# Executive summary

All 349 EC1:5 measurements were evaluated under the same archived spatial and campaign partitions. Sentinel-2 covered {int(opt.s2_present)} sites. QA-screened Landsat covered {int(opt.ls_present)}, bringing either-source coverage to {int(opt.any_optical)} and recovering {int(opt.recovered)} of {int(opt.n-opt.s2_present)} original gaps.

| Buffered spatial procedure | RMSE (mS/cm) | MAE (mS/cm) | R² |
| --- | ---: | ---: | ---: |
"""
    for k in dict.fromkeys([best,"MISA","V1 Auto",strongest,"V1 ExtraTrees (descriptive)"]):
        r=m.loc["Spatial",k]
        headline+=f"| {k} | {r.rmse:.3f} | {r.mae:.3f} | {r.r2:.3f} |\n"
    headline+=f"""
MISA minus V1 Auto RMSE: {v1.delta_rmse:+.3f} mS/cm, {v1.rmse_reduction_pct:+.2f}% relative reduction, 95% spatial-block interval {plain_ci(v1)}. MISA minus {strongest}: {against.delta_rmse:+.3f} mS/cm, {against.rmse_reduction_pct:+.2f}%, interval {plain_ci(against)}.

On the {int(high_m.n)} high-EC spatial tests, MISA MAE was {high_m.mae:.3f} and signed bias {high_m.bias:+.3f} mS/cm. V1 Auto yielded {high_v.mae:.3f} and {high_v.bias:+.3f}. The strongest spatial comparator yielded {high_other.mae:.3f} and {high_other.bias:+.3f}. The MISA–V1 high-EC paired MAE difference was {high_compare.delta_mae:+.3f} {plain_ci(high_compare)}. For sites missing Sentinel-2 it was {missing_compare.delta_mae:+.3f} {plain_ci(missing_compare)}.

MISA transfer RMSE was {fwd.rmse:.3f} forward and {rev.rmse:.3f} in reverse, with R² {fwd.r2:.3f} and {rev.r2:.3f}. Under 1 km training exclusion, RMSE was {buff[0].rmse:.3f} and {buff[1].rmse:.3f}. All errors are in mS/cm.

High-EC weighting in Huber boosting lowered subgroup MAE by {-high_weight.delta_mae:.3f} mS/cm, paired interval {plain_ci(high_weight)} for weighted minus unweighted. It increased overall spatial RMSE from {ab.loc['Huber-GB full-4'].rmse:.3f} to {ab.loc['Huber-GB weighted'].rmse:.3f}. The same directional trade-off appeared for weighted ExtraTrees and random forest.

The proposal's frozen paired-superiority criterion was **{'met in this reanalysis' if v['paired_superiority'] else 'not met'}**. None of the study's labels provide untouched external validation. The manuscript requires further research before a confirmatory submission.
"""
    if best_v1 is not None:
        headline+=f"\nThe descriptively lowest RMSE changed by {best_v1.delta_rmse:+.3f} mS/cm versus V1 Auto ({best_v1.rmse_reduction_pct:.2f}% lower, interval {plain_ci(best_v1)}).\n"
    (ROOT/"EXECUTIVE_SUMMARY.md").write_text(headline,encoding="utf-8")
    claims=f"""# Claims and evidence

| Claim | Evidence and scope |
| --- | --- |
| Alternative optical coverage recovered {int(opt.recovered)} original gaps. | `results/coverage.csv` and per-site lineage in `results/feature_provenance.csv`. Same 349 rows. |
| Lowest descriptive spatial RMSE was {m.loc['Spatial',best].rmse:.3f} for {best}. | `results/metrics.csv`, one pooled comparison across the archived six folds. It is a descriptive ranking of many evaluated procedures. |
| MISA vs V1 Auto and retrospectively identified ExtraTrees. | Paired RMSE deltas {v1.delta_rmse:+.3f} {plain_ci(v1)} and {prior_et.delta_rmse:+.3f} {plain_ci(prior_et)} mS/cm. |
| MISA vs the strongest matched comparator ({strongest}). | Paired RMSE difference {against.delta_rmse:+.3f} {plain_ci(against)} mS/cm. See `paired_deltas.csv` and `verdict.json`. |
| High-EC MAE and optical missingness. | `subgroups.csv` and `subgroup_deltas.csv`. Differences are conditional on observed groups and six resampling blocks. |
| Exact 2026 published benchmark superiority. | Unavailable. Row identity, covariates, folds and exact scoring code were unverified. |
| Causality, general deployment or external validation. | Unsupported. Observed campaigns differ in month and site support, and prior outcomes were known. |
"""
    (ROOT/"CLAIMS_AND_EVIDENCE.md").write_text(claims,encoding="utf-8")
    readiness=f"""# Publication readiness

**Decision: requires further research before a confirmatory submission.**

The manuscript and reproducibility package are complete. The V3 proposal {'met' if v['paired_superiority'] else 'did not meet'} the frozen within-benchmark paired-superiority rule. The analysis reuses campaigns whose V1 outcomes were known. A third field campaign or geographically independent dataset should be held outside all method development. In addition, absolute high-EC errors and bidirectional transfer performance constrain deployment. The exact 2026 Satkhira comparison requires author-specific rows, inputs, folds and the scored prediction procedure.

The coverage result is directly established on these records. Method comparison and subgroup results are valid as reanalysis estimates under the archived split design, with uncertainty conditional on the assessed regions. There is no field-wide ranking or external validation claim.
"""
    (ROOT/"PUBLICATION_READINESS.md").write_text(readiness,encoding="utf-8")


if __name__=="__main__":
    main()
