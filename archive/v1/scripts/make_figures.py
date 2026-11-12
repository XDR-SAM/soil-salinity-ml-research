"""Render publication figures from audited field observations and held-out predictions."""
from itertools import pairwise

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
import numpy as np
import pandas as pd

from download_originals import ROOT

BLUE = "#00759b"
ORANGE = "#b54915"
NAVY = "#1c3246"
GRAY = "#607583"
TEAL = "#d8ede8"
TRACKS = ["Spatial", "2024-to-2025", "2025-to-2024"]
LABELS = ["Spatial CV", "2024 → 2025", "2025 → 2024"]
PALETTE = {2024: BLUE, 2025: ORANGE}
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 9, "axes.spines.top": False,
                     "axes.spines.right": False, "axes.labelcolor": NAVY, "text.color": NAVY,
                     "pdf.fonttype": 42, "svg.fonttype": "none", "figure.dpi": 120,
                     "savefig.dpi": 320, "axes.titleweight": "bold"})
DEST = ROOT / "figures"
RESULTS = ROOT / "results"


def save(fig, name: str) -> None:
    DEST.mkdir(exist_ok=True)
    for extension in ("pdf", "svg", "png"):
        path = DEST / f"{name}.{extension}"
        fig.savefig(path, bbox_inches="tight", facecolor="white", pad_inches=.04)
        if extension == "svg":
            lines = path.read_text(encoding="utf-8").splitlines()
            path.write_text("\n".join(line.rstrip() for line in lines) + "\n", encoding="utf-8")
    plt.close(fig)


def workflow() -> None:
    fig, ax = plt.subplots(figsize=(7.08, 3.06))
    ax.set(xlim=(0, 12), ylim=(0, 5.2))
    ax.axis("off")
    boxes = {
        "input": (0.12, 3.86, "Field workbooks\n162 sites in 2024\n187 sites in 2025"),
        "audit": (3.15, 3.86, "Verify inputs\nCheck hashes, rows,\nunits and dates"),
        "features": (6.18, 3.86, "Link predictors\nUTM, Sentinel-2\nand elevation"),
        "fold": (9.21, 3.86, "Define partitions\nBy location\nor campaign"),
        "models": (0.12, 2.34, "Fit candidates\nBaselines and learners\ntuned in inner CV"),
        "prep": (3.15, 2.34, "Preprocess\nFit transformations\non training rows"),
        "spatial": (6.18, 2.34, "Spatial holdouts\nSix outer clusters\nwith 1 km buffer"),
        "temporal": (9.21, 2.34, "Year holdouts\nTrain 2024, test 2025\nand reverse"),
        "held": (0.12, 0.55, "Predict test EC\nRefit selections on\nouter training sets"),
        "assess": (3.15, 0.55, "Score predictions\nRMSE, MAE and R²"),
        "diagnose": (6.18, 0.55, "Diagnose errors\nResiduals, bootstrap,\nfeature reliance"),
        "paper": (9.21, 0.55, "Archive results\nPaper, code and\nheld-out predictions"),
    }
    w, h = 2.66, .96
    for key, (x, y, label) in boxes.items():
        face = TEAL if key in ("spatial", "temporal") else "#eef4f7"
        ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=.035,rounding_size=.12",
                                    facecolor=face, edgecolor="#9db2bc", lw=.65))
        title, subtitle = label.split("\n", 1)
        ax.text(x+w/2, y+.72, title, ha="center", va="center", fontsize=8.2, weight="bold")
        ax.text(x+w/2, y+.31, subtitle, ha="center", va="center", fontsize=7.2, linespacing=1.10)
    def arrow(a, b):
        ax.annotate("", xy=b, xytext=a, arrowprops=dict(arrowstyle="-|>", lw=.85, color=GRAY,
                                                        shrinkA=0, shrinkB=0))
    for names in (("input", "audit", "features", "fold"), ("held", "assess", "diagnose", "paper")):
        for a, b in pairwise(names):
            x, y, _ = boxes[a]
            nx, _, _ = boxes[b]
            arrow((x+w+.03, y+h/2), (nx-.03, y+h/2))
    for a, b in (("prep", "models"), ("spatial", "prep")):
        x, y, _ = boxes[a]
        nx, _, _ = boxes[b]
        arrow((x-.03, y+h/2), (nx+w+.03, y+h/2))
    arrow((10.54, 3.82), (10.54, 3.34))
    ax.plot([10.54, 7.51], [3.59, 3.59], lw=.85, color=GRAY)
    arrow((7.51, 3.59), (7.51, 3.34))
    ax.plot([10.54, 10.54, 4.48], [2.29, 1.98, 1.98], lw=.85, color=GRAY)
    arrow((4.48, 1.98), (4.48, 2.29))
    arrow((1.45, 2.29), (1.45, 1.55))
    save(fig, "workflow")


def maps(data: pd.DataFrame, pred: pd.DataFrame) -> None:
    xy = data.assign(x=data.easting/1000, y=data.northing/1000)
    folds = pred[pred.track.eq("Spatial")].set_index("uid").block
    fig, axes = plt.subplots(1, 2, figsize=(7.05, 3.55), layout="constrained", sharex=True, sharey=True)
    for y, group in xy.groupby("year"):
        axes[0].scatter(group.x, group.y, s=12, color=PALETTE[y], marker="o" if y == 2024 else "^",
                        label=f"{y} (n={len(group)})", alpha=.8, linewidths=0)
    colors = ["#0072b2", "#d55e00", "#009e73", "#cc79a7", "#765a19", "#593aa3"]
    for block, group in xy.assign(block=xy.uid.map(folds)).groupby("block"):
        axes[1].scatter(group.x, group.y, s=12, color=colors[int(block)-1],
                        label=f"{int(block)} ({len(group)})", linewidths=0)
    axes[0].set(title="(a) Field campaigns", ylabel="UTM northing (km)")
    axes[1].set_title("(b) Outer spatial folds")
    for ax, cols in zip(axes, [2, 3], strict=True):
        ax.set(xlabel="UTM easting (km)", aspect="equal")
        ax.legend(loc="upper center", bbox_to_anchor=(.5, -.17), ncols=cols, frameon=False,
                  fontsize=8, markerscale=1.15, handletextpad=.25, columnspacing=.8)
        ax.grid(alpha=.16)
    axes[0].annotate("N", xy=(.91, .94), xytext=(.91, .81), xycoords="axes fraction", ha="center",
                     arrowprops=dict(arrowstyle="-|>", color=NAVY))
    x, y = xy.x.min()+4, xy.y.min()+1
    axes[0].plot([x, x+10], [y, y], color=NAVY, lw=2)
    axes[0].text(x+5, y+1.6, "10 km", ha="center", fontsize=8)
    save(fig, "study_area")


def distributions(data: pd.DataFrame) -> None:
    fig, ax = plt.subplots(figsize=(3.42, 2.18), layout="constrained")
    for year, group in data.groupby("year"):
        x = np.sort(group.ec)
        ax.step(np.r_[0, x, 11], np.r_[0, np.arange(1, len(x)+1)/len(x), 1],
                where="post", color=PALETTE[year], label=str(year))
    ax.set(xlabel="Measured EC (mS/cm)", ylabel="Cumulative fraction", xlim=(0, 11), ylim=(0, 1.03))
    ax.grid(alpha=.18)
    ax.legend(loc="lower right", frameon=False)
    save(fig, "ec_distribution")


def model_scores(metrics: pd.DataFrame) -> None:
    chosen = [("A", "Mean", "Train mean"), ("A", "IDW", "IDW"), ("A", "Auto", "Coordinates"),
              ("B", "Auto", "Sentinel-2"), ("C", "Auto", "Sentinel-2 + elev."),
              ("D", "Auto", "Selected features"), ("E", "Auto", "All predictors")]
    fig, axes = plt.subplots(1, 3, figsize=(7.06, 2.68), layout="constrained", sharex=True, sharey=True)
    for ax, track, title in zip(axes, TRACKS, LABELS, strict=True):
        table = metrics[metrics.track.eq(track)].set_index(["feature", "model"])
        for i, (feature, model, _) in enumerate(chosen):
            if (feature, model) not in table.index:
                continue
            row = table.loc[(feature, model)]
            color = BLUE if i >= 3 else GRAY
            ax.hlines(i, row.rmse_lo, row.rmse_hi, color=color, linewidth=1.2)
            ax.scatter(row.rmse, i, color=color, s=19, zorder=3)
        ax.set(title=title, xlabel="RMSE (mS/cm)", xticks=[1.5, 2., 2.5, 3.], yticks=range(len(chosen)),
               yticklabels=[v[2] for v in chosen], ylim=(len(chosen)-.5, -.5))
        ax.grid(axis="x", alpha=.2)
    save(fig, "model_comparison")


def diagnostics(pred: pd.DataFrame, data: pd.DataFrame) -> None:
    fig, axes = plt.subplots(2, 3, figsize=(7.06, 4.02), layout="constrained", sharex=True,
                             sharey="row")
    for i, (track, label) in enumerate(zip(TRACKS, LABELS, strict=True)):
        rows = pred[pred.track.eq(track)]
        for year, group in rows.groupby("year"):
            axes[0, i].scatter(group.observed, group.predicted, color=PALETTE[year], s=10, alpha=.62,
                               label=str(year), linewidths=0)
            axes[1, i].scatter(group.observed, group.predicted-group.observed, color=PALETTE[year],
                               s=10, alpha=.62, linewidths=0)
        axes[0, i].set_title(label)
        axes[0, i].plot([0, 11], [0, 11], color=GRAY, lw=.8, linestyle="--")
        axes[1, i].axhline(0, color=GRAY, lw=.8, linestyle="--")
        axes[1, i].set(xlabel="Observed EC (mS/cm)", xlim=(0, 11))
    axes[0, 0].set(ylabel="Predicted EC (mS/cm)", ylim=(0, 11))
    axes[1, 0].set(ylabel="Residual (mS/cm)")
    axes[0, 0].legend(loc="upper left", frameon=False, fontsize=8)
    save(fig, "diagnostics")

    fig, ax = plt.subplots(figsize=(3.42, 3.32), layout="constrained")
    subset = pred[pred.track.eq("Spatial")].merge(data, on="uid", validate="one_to_one")
    error = subset.predicted - subset.observed
    bound = np.max(np.abs(error))
    plot = ax.scatter(subset.easting/1000, subset.northing/1000, c=error, vmin=-bound, vmax=bound,
                      cmap="RdBu_r", s=18, linewidth=.2, edgecolor="#384a54")
    ax.set(xlabel="UTM easting (km)", ylabel="UTM northing (km)", aspect="equal")
    fig.colorbar(plot, ax=ax, fraction=.06, label="Predicted − measured (mS/cm)")
    save(fig, "spatial_errors")


def importance_plot(importance: pd.DataFrame) -> None:
    table = importance[importance.track.eq("Spatial")].groupby(["group", "fold"]).delta_rmse.mean()
    fig, ax = plt.subplots(figsize=(3.42, 2.08), layout="constrained")
    for i, group in enumerate(["Coordinates", "Sentinel-2", "Elevation"]):
        values = table.loc[group]
        ax.scatter(values, np.full(len(values), i), s=20, color=BLUE, alpha=.65)
        ax.scatter(values.mean(), i, s=50, marker="D", color=NAVY,
                   label="Mean across folds" if i == 0 else None)
    ax.axvline(0, color=GRAY, linestyle="--", linewidth=.8)
    ax.set(yticks=[0, 1, 2], yticklabels=["Coordinates", "Sentinel-2", "Elevation"],
           ylim=(2.5, -.5), xlabel="Permutation ΔRMSE (mS/cm)")
    ax.legend(loc="lower right", frameon=False, fontsize=8)
    save(fig, "permutation")


def main() -> None:
    data = pd.read_csv(ROOT / "data/derived/field.csv")
    pred = pd.read_csv(RESULTS / "predictions.csv")
    pred = pred[pred.model.eq("Auto") & pred.feature.eq("E" if pred.feature.eq("E").any() else "A")]
    workflow()
    maps(data, pred)
    distributions(data)
    model_scores(pd.read_csv(RESULTS / "metrics.csv"))
    diagnostics(pred, data)
    if (RESULTS / "importance.csv").exists():
        importance_plot(pd.read_csv(RESULTS / "importance.csv"))


if __name__ == "__main__":
    main()
