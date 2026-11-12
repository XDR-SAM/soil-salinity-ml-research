"""Render editable IEEE figure assets from verified output CSVs."""
from pathlib import Path
import json

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/"figures"
R=ROOT/"results"
DARK="#183044"
BLUE="#087b9d"
ORANGE="#b44920"
TEAL="#087d66"
GRAY="#647785"
LIGHT="#eaf1f5"
plt.rcParams.update({"font.size":9,"font.family":"DejaVu Sans","svg.fonttype":"none",
                     "svg.hashsalt":"ec-framework","pdf.fonttype":42,"savefig.dpi":300,
                     "axes.spines.top":False,"axes.spines.right":False,
                     "axes.titleweight":"bold","axes.labelcolor":DARK,"text.color":DARK})
MAIN=["V1 Auto","V1 ExtraTrees (descriptive)","Mean","IDW","Ridge","RF","ExtraTrees","SVR",
      "XGBoost","LightGBM","CatBoost","AdaBoost","Huber-GB","XGB + spline","Inner champion","MISA"]
SHORT={"V1 ExtraTrees (descriptive)":"V1 ExtraTrees*","Inner champion":"Inner winner",
       "ET no_geo":"Drop coordinates","ET v1":"V1 inputs","ET no_landsat":"Drop Landsat",
       "ET no_terrain":"Drop terrain","ET no_flags":"Drop availability flags",
       "ET terrain_only":"Terrain + location","ET optical_only":"Optical only","ET compact":"Compact inputs",
       "ET log":"Log EC","ET weighted":"High-EC weight"}


def save(fig,name):
    OUT.mkdir(exist_ok=True)
    for ext in ("pdf","svg","png"):
        kw={"metadata":{"Date":None}} if ext=="svg" else {}
        path=OUT/f"{name}.{ext}"
        fig.savefig(path,bbox_inches="tight",pad_inches=.06,facecolor="white",**kw)
        if ext=="svg":
            lines=path.read_text(encoding="utf-8").splitlines()
            path.write_text("\n".join(line.rstrip() for line in lines)+"\n",encoding="utf-8")
    plt.close(fig)


def framework(has_landsat,has_terrain):
    fig,ax=plt.subplots(figsize=(7.12,3.65))
    fig.subplots_adjust(left=.015,right=.985,bottom=.01,top=.99)
    ax.set(xlim=(0,14),ylim=(0,8))
    ax.axis("off")
    def box(x,y,w,h,head,body,color=LIGHT):
        ax.add_patch(FancyBboxPatch((x,y),w,h,boxstyle="round,pad=.045,rounding_size=.13",
                    facecolor=color,edgecolor="#a6b8c4",lw=.65))
        ax.text(x+w/2,y+h*.70,head,ha="center",va="center",weight="bold",fontsize=8.8)
        ax.text(x+w/2,y+h*.33,body,ha="center",va="center",fontsize=7.8,linespacing=1.18)
    def arrow(x,y,a,b):
        ax.annotate("",xy=(a,b),xytext=(x,y),arrowprops={"arrowstyle":"-|>","lw":.85,"color":GRAY})
    box(.14,6.42,4.24,1.28,"Verified field observations","2024 (162) and 2025 (187)\nEC in 1:5 soil–water extract")
    optical="Sentinel-2 and Landsat" if has_landsat else "Sentinel-2 surface reflectance"
    surface="terrain" if has_terrain else "elevation"
    box(4.86,6.42,4.24,1.28,"Time-align predictors",f"{optical}\nQA, recency and {surface}")
    box(9.58,6.42,4.24,1.28,"Replay archived partitions","Six buffered spatial folds\nTwo campaign directions")
    arrow(4.42,7.06,4.82,7.06);arrow(9.14,7.06,9.54,7.06)
    ax.plot([1.77,13.25],[5.97,5.97],color=GRAY,lw=.85)
    ax.plot([11.7,11.7],[6.37,5.97],color=GRAY,lw=.85)
    arrow(1.77,5.97,1.77,5.04);arrow(13.25,5.97,13.25,5.04)
    ax.text(2.05,5.42,"OUTER TRAIN ONLY",color=TEAL,weight="bold",fontsize=8.5)
    ax.text(10.9,5.42,"OUTER TEST",color=ORANGE,weight="bold",fontsize=8.5)
    box(.14,3.73,3.26,1.28,"Inner buffered CV","Median imputation\nScaling and target variants","#e5f2ed")
    box(3.78,3.73,3.26,1.28,"Tune learner families","Depth, leaves, learning rate\nRidge penalty and SVR C","#e5f2ed")
    box(7.42,3.73,3.08,1.28,"Fit MISA weights","Inner out-of-fold estimates\nShrink by S2 availability","#e5f2ed")
    box(10.89,3.73,2.93,1.28,"Apply frozen fits","Baselines and MISA\nNo fitting on test","#f7eae3")
    for i in (3.44,7.08,10.54):
        arrow(i,4.37,i+.30,4.37)
    arrow(12.34,3.68,12.34,2.89)
    box(9.58,1.52,4.24,1.30,"Held-out EC predictions","All eligible records\nSame rows across procedures")
    box(4.86,1.52,4.24,1.30,"Score paired predictions","RMSE, MAE and R²\nSpatial-block intervals")
    box(.14,1.52,4.24,1.30,"Diagnose and archive","High EC, coverage, transfer\nPermutation and reproducibility")
    arrow(9.54,2.17,9.13,2.17);arrow(4.82,2.17,4.41,2.17)
    ax.text(7,.73,"Acquisition and split design precede fitting. Observed test EC enters scoring only.",
            ha="center",va="center",fontsize=8.5,color=GRAY)
    save(fig,"proposed_framework")


def study_area(sites):
    fig,axes=plt.subplots(1,2,figsize=(7.1,3.5),layout="constrained",sharey=True)
    pts=sites.assign(x=sites.easting/1000,y=sites.northing/1000)
    for year,g in pts.groupby("year"):
        axes[0].scatter(g.x,g.y,s=12,marker="o" if year==2024 else "^",
                        c=BLUE if year==2024 else ORANGE,linewidths=0,label=str(year),alpha=.75)
    colors=[BLUE,ORANGE,TEAL,"#9362a3","#92712b","#52628d"]
    for i,(k,g) in enumerate(pts.groupby("block")):
        axes[1].scatter(g.x,g.y,s=12,c=colors[i],marker=("o","^","s","D","P","X")[i],
                        label=f"{k} ({len(g)})",linewidths=0)
    axes[0].set(title="(a) Field campaigns",ylabel="UTM northing (km)")
    axes[1].set_title("(b) Archived spatial test folds")
    for i,ax in enumerate(axes):
        ax.set(xlabel="UTM easting (km)",aspect="equal")
        ax.grid(alpha=.14)
        ax.legend(loc="upper center",bbox_to_anchor=(.5,-.17),ncols=2 if i==0 else 3,
                  frameon=False,fontsize=8,handletextpad=.3,columnspacing=.9)
    x,y=pts.x.min()+2,pts.y.min()+.3
    axes[0].plot([x,x+10],[y,y],c=DARK,lw=2)
    axes[0].text(x+5,y+2,"10 km",ha="center",fontsize=8)
    axes[0].annotate("N",xy=(.92,.94),xytext=(.92,.82),xycoords="axes fraction",
                     ha="center",arrowprops={"arrowstyle":"-|>","color":DARK})
    save(fig,"study_area")


def coverage_plot(sites,cover):
    fig,axes=plt.subplots(1,2,figsize=(7.1,2.45),layout="constrained")
    ax=axes[0]
    for year,g in sites.groupby("year"):
        a=np.sort(g.ec)
        high=g.ec.ge(5).sum()
        ax.step(np.r_[0,a,11],np.r_[0,np.arange(1,len(a)+1)/len(a),1],where="post",
                color=BLUE if year==2024 else ORANGE,ls="-" if year==2024 else "--",
                label=f"{year}: {high}/{len(g)} at EC ≥5")
    ax.axvspan(5,11,color=ORANGE,alpha=.08)
    ax.set(xlim=(0,11),ylim=(0,1.03),xlabel="Measured EC (mS/cm)",ylabel="Cumulative fraction",
           title="(a) Campaign shift")
    ax.legend(loc="lower right",frameon=False,fontsize=8)
    ax=axes[1]
    sub=cover.loc[cover.stratum.eq("all")|cover.stratum.eq("year")|
                  (cover.stratum.eq("ec_group")&cover.level.str.startswith("[5"))]
    labels=["All" if x=="all" else "EC ≥5" if x.startswith("[") else x for x in sub.level]
    y=np.arange(len(sub))
    for col,c,offset,label in [("s2_present",GRAY,-.17,"Sentinel-2"),("any_optical",BLUE,.17,"Either optical sensor")]:
        bars=100*sub[col]/sub.n
        ax.barh(y+offset,bars,height=.29,color=c,label=label)
        for yi,perc,n,total in zip(y+offset,bars,sub[col],sub.n,strict=True):
            ax.text(perc-1.6,yi,f"{n}/{total}",ha="right",va="center",color="white",fontsize=7.6)
    ax.set(yticks=y,yticklabels=labels,ylim=(len(y)-.5,-.52),xlim=(0,103),
           xlabel="Sites with a valid observation (%)",title="(b) Optical availability")
    ax.legend(loc="lower center",bbox_to_anchor=(.5,-.41),ncols=2,frameon=False,fontsize=8)
    save(fig,"coverage_shift")


def leaderboard(metrics,verdict):
    names=list(dict.fromkeys([*MAIN,verdict["best"]["model"]]))
    sub=metrics.query("track=='Spatial' and model in @names").set_index("model").loc[names]
    labels=["ExtraTrees without Landsat" if k=="ET no_landsat" else SHORT.get(k,k) for k in sub.index]
    fig,axes=plt.subplots(1,3,figsize=(7.1,3.42),layout="constrained",sharey=True)
    y=np.arange(len(sub))
    colors=[TEAL if k=="MISA" else GRAY for k in sub.index]
    for ax,col,title in zip(axes,["rmse","mae","r2"],["RMSE (mS/cm)","MAE (mS/cm)","R²"],strict=True):
        ax.scatter(sub[col],y,c=colors,s=17,zorder=3)
        if col=="rmse":
            ax.hlines(y,sub.rmse_lo,sub.rmse_hi,color=colors,lw=.85)
        ax.set(title=title,yticks=y,yticklabels=labels,ylim=(len(y)-.5,-.5))
        ax.grid(axis="x",alpha=.18)
        if col=="r2":
            ax.axvline(0,ls="--",c=GRAY,lw=.65)
    save(fig,"model_comparison")


def diagnostics(p,sites):
    preds=p.query("model=='MISA' and track=='Spatial'")
    fig,axes=plt.subplots(1,3,figsize=(7.08,2.9),layout="constrained")
    ax=axes[0]
    for year,g in preds.groupby("year"):
        ax.scatter(g.observed,g.predicted,s=9,c=BLUE if year==2024 else ORANGE,
                   marker="o" if year==2024 else "^",label=str(year),alpha=.63,linewidths=0)
    ax.plot([0,11],[0,11],ls="--",c=GRAY,lw=.8)
    ax.set(xlim=(0,11),ylim=(0,11),xlabel="Observed EC (mS/cm)",ylabel="Predicted EC (mS/cm)",title="(a) Spatial predictions")
    ax.legend(frameon=False,loc="upper left",fontsize=8)
    ax=axes[1]
    spatial=preds.join(sites[["easting","northing"]],on="uid")
    err=spatial.predicted-spatial.observed
    radius=np.abs(err).max()
    pc=ax.scatter(spatial.easting/1000,spatial.northing/1000,c=err,s=12,cmap="RdBu_r",
                  vmin=-radius,vmax=radius,edgecolor=GRAY,linewidth=.22)
    fig.colorbar(pc,ax=ax,fraction=.075,label="Residual (mS/cm)")
    ax.set(xlabel="UTM easting (km)",ylabel="Northing (km)",title="(b) Spatial residuals",aspect="equal")
    ax=axes[2]
    shortlist=["V1 Auto","V1 ExtraTrees (descriptive)","MISA"]
    high=p.query("track=='Spatial' and observed>=5 and model in @shortlist").copy()
    arrays=[(high.loc[high.model.eq(k),"predicted"]-high.loc[high.model.eq(k),"observed"]).to_numpy() for k in shortlist]
    box=ax.boxplot(arrays,patch_artist=True,tick_labels=["V1 Auto","V1 ET*","MISA"],widths=.54,
                   medianprops={"color":DARK,"linewidth":1.2},flierprops={"markersize":2})
    for patch in box["boxes"]:
        patch.set_facecolor(LIGHT)
        patch.set_edgecolor(GRAY)
    ax.axhline(0,c=GRAY,ls="--",lw=.7)
    ax.set(ylabel="Residual (mS/cm)",title=f"(c) EC ≥5 (n={len(arrays[0])})")
    ax.tick_params(axis="x",labelsize=8)
    save(fig,"diagnostics")


def ablation_plot(metrics,importance):
    spatial=metrics.query("track=='Spatial'").set_index("model")
    labels=[k for k in ["ET full-4","ET v1","ET no_geo","ET no_landsat","ET no_terrain","ET no_flags",
                        "ET compact","ET log","ET weighted","MISA","MISA global","MISA equal"] if k in spatial.index]
    fig,(ax,bx)=plt.subplots(1,2,figsize=(7.1,3.1),layout="constrained",gridspec_kw={"width_ratios":[1.2,1.]})
    y=np.arange(len(labels))
    sub=spatial.loc[labels]
    ax.hlines(y,sub.rmse_lo,sub.rmse_hi,color=GRAY,lw=.75)
    ax.scatter(sub.rmse,y,c=[TEAL if k.startswith("MISA") else BLUE for k in labels],s=17)
    ax.set(yticks=y,yticklabels=[SHORT.get(k,k) for k in labels],ylim=(len(y)-.5,-.5),
           xlabel="RMSE (mS/cm)",title="(a) Ablation and loss choices")
    ax.tick_params(axis="y",labelsize=8)
    ax.grid(axis="x",alpha=.18)
    values=importance.groupby(["group","fold"]).delta_rmse.mean()
    groups=list(values.index.get_level_values("group").unique())
    for i,name in enumerate(groups):
        points=values.loc[name]
        bx.scatter(points,np.full(len(points),i),s=17,c=BLUE,alpha=.65)
        bx.scatter(points.mean(),i,s=32,c=DARK,marker="D")
    bx.axvline(0,c=GRAY,ls="--",lw=.7)
    bx.set(yticks=np.arange(len(groups)),yticklabels=groups,ylim=(len(groups)-.5,-.5),
           title="(b) Grouped permutation",xlabel="Change in RMSE (mS/cm)")
    save(fig,"ablation_importance")


def transfer(metrics,verdict):
    winner=verdict["strongest_comparator"]["model"]
    names=list(dict.fromkeys(["V1 Auto",winner,"MISA"]))
    tracks=["2024-to-2025","2024-to-2025-buffered","2025-to-2024","2025-to-2024-buffered"]
    y=np.arange(len(tracks))
    fig,ax=plt.subplots(figsize=(6.8,2.2))
    fig.subplots_adjust(left=.24,right=.98,top=.96,bottom=.34)
    table=metrics.set_index(["track","model"])
    for i,(name,col,marker) in enumerate(zip(names,[GRAY,ORANGE,TEAL],["s","^","o"])):
        rows=table.loc[[(t,name) for t in tracks]]
        pos=y+(i-(len(names)-1)/2)*.19
        ax.hlines(pos,rows.rmse_lo,rows.rmse_hi,color=col,lw=.9)
        label="ExtraTrees without Landsat" if name=="ET no_landsat" else SHORT.get(name,name)
        ax.scatter(rows.rmse,pos,c=col,marker=marker,s=22,label=label,zorder=3)
    ax.set(yticks=y,yticklabels=["2024 → 2025","2024 → 2025, buffered",
        "2025 → 2024","2025 → 2024, buffered"],ylim=(3.53,-.55),xlabel="RMSE (mS/cm)")
    ax.grid(axis="x",alpha=.16)
    fig.legend(loc="lower center",bbox_to_anchor=(.61,.015),frameon=False,ncols=len(names),fontsize=8)
    save(fig,"transfer")


def main():
    sites=pd.read_csv(R/"site_audit.csv").set_index("uid")
    cover=pd.read_csv(R/"coverage.csv")
    metrics=pd.read_csv(R/"metrics.csv")
    p=pd.read_csv(R/"predictions.csv")
    verdict=json.loads((R/"verdict.json").read_text(encoding="utf-8"))
    framework(sites.ls_present.any(),sites.terrain_complete.any())
    study_area(sites)
    coverage_plot(sites,cover)
    leaderboard(metrics,verdict)
    diagnostics(p,sites)
    ablation_plot(metrics,pd.read_csv(R/"importance.csv"))
    transfer(metrics,verdict)


if __name__=="__main__":
    main()
