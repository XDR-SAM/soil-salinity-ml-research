"""Extract one clear, pre-sampling Sentinel-2 Collection-1 pixel per site."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
import json

import numpy as np
import pandas as pd
import rasterio
from rasterio.warp import transform
import requests

from download_originals import ROOT

CATALOG = "https://earth-search.aws.element84.com/v1/collections/sentinel-2-c1-l2a/items"
BANDS = ("blue", "green", "red", "nir", "swir16", "swir22")
SPECTRAL = (*BANDS, "ndvi", "ndmi")
SCL_CLEAR = (4, 5)
WINDOW_DAYS = 30


def get_items(data: pd.DataFrame, year: int, use_snapshot: bool) -> list[dict]:
    snapshot = ROOT / f"data/sentinel_{year}.json"
    if use_snapshot:
        return json.loads(snapshot.read_text(encoding="utf-8"))
    start = data.date.min() - timedelta(days=WINDOW_DAYS)
    end = data.date.max()
    response = requests.get(CATALOG, params={
        "bbox": ",".join(str(v) for v in [data.lon.min(), data.lat.min(), data.lon.max(), data.lat.max()]),
        "datetime": f"{start:%Y-%m-%d}T00:00:00Z/{end:%Y-%m-%d}T00:00:00Z", "limit": 100,
    }, timeout=60)
    response.raise_for_status()
    items = []
    while True:
        page = response.json()
        for item in page["features"]:
            props = item["properties"]
            assets = {k: item["assets"][k] for k in ("scl", *BANDS)}
            items.append(dict(id=item["id"], datetime=props["datetime"],
                              product=props.get("s2:product_uri"), assets=assets))
        next_url = next((link["href"] for link in page["links"] if link["rel"] == "next"), None)
        if next_url is None:
            break
        response = requests.get(next_url, timeout=60)
        response.raise_for_status()
    items.sort(key=lambda item: (item["datetime"], item["id"]), reverse=True)
    snapshot.write_text(json.dumps(items, indent=2) + "\n", encoding="utf-8")
    return items


def pixels(asset: dict, points: pd.DataFrame, raw: bool = False) -> pd.DataFrame:
    # Read only the blocks containing candidate pixels. Native 10 m or 20 m
    # pixels are sampled without interpolation.
    with rasterio.Env(GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR", GDAL_HTTP_TIMEOUT="30",
                      GDAL_HTTP_MAX_RETRY="2", CPL_VSIL_CURL_ALLOWED_EXTENSIONS=".tif"):
        with rasterio.open(asset["href"]) as src:
            x, y = transform("EPSG:4326", src.crs, points.lon.tolist(), points.lat.tolist())
            locations = list(zip(x, y, strict=True))
            rc = [src.index(*xy) for xy in locations]
            valid = [i for i, (r, c) in enumerate(rc) if 0 <= r < src.height and 0 <= c < src.width]
            values = np.full(len(points), np.nan)
            for i, sample in zip(valid, src.sample([locations[i] for i in valid], masked=True), strict=True):
                if not np.ma.is_masked(sample[0]) and sample[0] != 0:
                    values[i] = sample[0]
            if not raw:
                band = asset["raster:bands"][0]
                values = values * band["scale"] + band["offset"]
            return pd.DataFrame({"value": values, "row": [v[0] for v in rc],
                                 "col": [v[1] for v in rc]}, index=points.index)


def ratio(a: pd.Series, b: pd.Series) -> pd.Series:
    denominator = a + b
    return ((a - b) / denominator.where(denominator > 1e-6)).clip(-1, 1)


def extract_year(data: pd.DataFrame, items: list[dict]) -> tuple[pd.DataFrame, list[dict]]:
    out = pd.DataFrame(index=data.index, columns=[
        *SPECTRAL, "scene", "acquired_utc", "lag_days", "scl", "scl_row", "scl_col"
    ])
    log = []
    with ThreadPoolExecutor(max_workers=6) as workers:
        for item in items:
            acquired = pd.to_datetime(item["datetime"], utc=True)
            acquired_day = acquired.tz_convert("Asia/Dhaka").tz_localize(None).normalize()
            lag = (data.date - acquired_day).dt.days
            candidates = data.loc[out.scene.isna() & lag.between(1, WINDOW_DAYS)]
            if candidates.empty:
                continue
            assets = item["assets"]
            mask = pixels(assets["scl"], candidates, raw=True)
            clear = candidates.loc[mask.value.isin(SCL_CLEAR)]
            if not clear.empty:
                tasks = [workers.submit(pixels, assets[key], clear) for key in BANDS]
                samples = [task.result().value for task in tasks]
                reflectance = pd.concat(samples, axis=1)
                reflectance.columns = list(BANDS)
                reflectance = reflectance.dropna()
                ix = reflectance.index
                out.loc[ix, list(BANDS)] = reflectance
                out.loc[ix, "ndvi"] = ratio(reflectance.nir, reflectance.red)
                out.loc[ix, "ndmi"] = ratio(reflectance.nir, reflectance.swir16)
                out.loc[ix, "scene"] = item["id"]
                out.loc[ix, "acquired_utc"] = acquired.isoformat()
                out.loc[ix, "lag_days"] = lag.loc[ix]
                out.loc[ix, ["scl", "scl_row", "scl_col"]] = mask.loc[ix].to_numpy()
                n_matched = len(ix)
            else:
                n_matched = 0
            print(item["id"], len(candidates), len(clear), n_matched, flush=True)
            log.append(dict(scene=item["id"], eligible=len(candidates), clear=len(clear), matched=n_matched))
    return out, log


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot", action="store_true", help="Reuse archived STAC metadata.")
    args = parser.parse_args()
    data = pd.read_csv(ROOT / "data/derived/field.csv", parse_dates=["date"]).set_index("uid")
    frames, scene_log = [], []
    for year, group in data.groupby("year"):
        table, log = extract_year(group, get_items(group, int(year), args.snapshot))
        frames.append(table)
        scene_log.extend(dict(year=int(year), **line) for line in log)
    pd.concat(frames).to_csv(ROOT / "data/derived/sentinel.csv")
    pd.DataFrame(scene_log).to_csv(ROOT / "data/derived/sentinel_log.csv", index=False)


if __name__ == "__main__":
    main()
