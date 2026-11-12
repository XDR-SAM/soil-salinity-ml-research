"""Sample prior-date Landsat Collection 2 and static terrain at workbook sites."""
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import re
from urllib.parse import urlsplit

from matplotlib.path import Path as Polygon
import numpy as np
import pandas as pd
import rasterio
from rasterio.windows import Window
from rasterio.warp import transform
import requests

ROOT = Path(__file__).resolve().parents[2]
DERIVED = ROOT / "data/derived"
CATALOG = "https://planetarycomputer.microsoft.com/api/stac/v1/search"
SAS = "https://planetarycomputer.microsoft.com/api/sas/v1/token"
BANDS = ("blue", "green", "red", "nir08", "swir16")
LOOKBACK = 45
QA_BITS = 191  # fill, dilated cloud, cirrus, cloud, shadow, snow, water
TERRAIN = ("terrain_relief", "terrain_relative", "terrain_slope")


def sample_asset(href: str, points: pd.DataFrame) -> np.ndarray:
    with rasterio.Env(GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR", GDAL_HTTP_TIMEOUT="18",
                      GDAL_HTTP_MAX_RETRY="1", GDAL_HTTP_MAX_RETRY_DELAY="1"):
        with rasterio.open(href) as source:
            coords = transform("EPSG:4326", source.crs, points.lon.tolist(), points.lat.tolist())
            sampled = source.sample(zip(*coords, strict=True), masked=True)
            return np.array([float(v[0]) if not np.ma.is_masked(v[0]) else np.nan for v in sampled])


def fetch_catalog(field: pd.DataFrame) -> list[dict]:
    snapshot = ROOT / "data/landsat_items.json"
    if snapshot.exists():
        return json.loads(snapshot.read_text(encoding="utf-8"))
    scenes = {}
    for _, data in field.groupby("year"):
        start = data.date.min() - pd.Timedelta(days=LOOKBACK)
        end = data.date.max()
        bounds = [data.lon.min(), data.lat.min(), data.lon.max(), data.lat.max()]
        query = {"collections": "landsat-c2-l2", "bbox": ",".join(map(str, bounds)),
                 "datetime": f"{start:%Y-%m-%d}T00:00:00Z/{end:%Y-%m-%d}T00:00:00Z", "limit": 100}
        response = requests.get(CATALOG, params=query, timeout=45)
        response.raise_for_status()
        page = response.json()
        if any(link["rel"] == "next" for link in page["links"]):
            raise RuntimeError("Incomplete Landsat scene query")
        for item in page["features"]:
            props = item["properties"]
            keys = ("qa_pixel", "qa_radsat", *BANDS)
            if (props.get("platform") not in ("landsat-8", "landsat-9")
                    or not item["id"].endswith("_T1") or not set(keys) <= item["assets"].keys()):
                continue
            scenes[item["id"]] = {
                "id": item["id"], "datetime": props["datetime"], "platform": props["platform"],
                "geometry": item["geometry"], "created": props.get("created"),
                "assets": {key: item["assets"][key] for key in keys},
            }
    items = sorted(scenes.values(), key=lambda item: (item["datetime"], item["id"]), reverse=True)
    snapshot.write_text(json.dumps(items, indent=2) + "\n", encoding="utf-8")
    return items


def eligible(points: pd.DataFrame, item: dict) -> pd.DataFrame:
    date = pd.Timestamp(item["datetime"]).tz_convert("Asia/Dhaka").tz_localize(None).normalize()
    lag = (points.date - date).dt.days
    geometry = item["geometry"]
    rings = geometry["coordinates"] if geometry["type"] == "MultiPolygon" else [geometry["coordinates"]]
    xy = points[["lon", "lat"]].to_numpy()
    hit = np.zeros(len(points), dtype=bool)
    for exterior, *holes in rings:
        inside = Polygon(exterior).contains_points(xy)
        for hole in holes:
            inside &= ~Polygon(hole).contains_points(xy)
        hit |= inside
    return points.loc[hit & lag.between(1, LOOKBACK)].assign(ls_lag=lag)


def sample_scene(item: dict, field: pd.DataFrame, token: str) -> tuple:
    points = eligible(field, item)
    if points.empty:
        return None, None
    assets = item["assets"]
    def read(key):
        # Signed query strings are short-lived and never written into provenance.
        return sample_asset(assets[key]["href"] + "?" + token, points)
    qa = read("qa_pixel")
    sat = read("qa_radsat")
    clear = np.isfinite(qa) & np.isfinite(sat) & ((np.nan_to_num(qa).astype(int) & QA_BITS) == 0) & (sat == 0)
    log = {"scene": item["id"], "eligible": len(points), "clear": int(clear.sum())}
    if not clear.any():
        return None, log
    qa_clear = qa[clear]
    points = points.loc[clear]
    table = points[["ls_lag"]].copy()
    for key in BANDS:
        raw = read(key)
        props = assets[key].get("raster:bands", [{}])[0]
        table["ls_" + key] = np.where(raw > 0, raw, np.nan) * props.get("scale", .0000275) + props.get("offset", -.2)
    table["ls_qa"] = qa_clear
    table["ls_radsat"] = 0
    table["ls_scene"] = item["id"]
    table["ls_time"] = item["datetime"]
    table = table.dropna()
    return table, log | {"matched": len(table)}


def landsat(field: pd.DataFrame) -> None:
    items = fetch_catalog(field)
    href = items[0]["assets"]["qa_pixel"]["href"]
    parsed = urlsplit(href)
    account = parsed.hostname.split(".")[0]
    container = parsed.path.split("/")[1]
    response = requests.get(f"{SAS}/{account}/{container}", timeout=30)
    response.raise_for_status()
    token = response.json()["token"].lstrip("?")
    usable = [item for item in items if not eligible(field, item).empty]
    frames, logs = [], []
    with ThreadPoolExecutor(max_workers=6) as pool:
        futures = [pool.submit(sample_scene, item, field, token) for item in usable]
        for item, future in zip(usable, futures, strict=True):
            # Do not include a signed URL in a saved exception.
            try:
                values, log = future.result()
            except Exception as error:
                logs.append({"scene": item["id"], "status": type(error).__name__})
                print(item["id"], type(error).__name__, flush=True)
                continue
            if log:
                logs.append(log | {"status": "read"})
                print(log, flush=True)
            if values is not None and not values.empty:
                frames.append(values)
    if not frames:
        pd.DataFrame(logs).to_csv(DERIVED / "landsat_scene_log.csv", index=False)
        raise RuntimeError("No valid Landsat pixels were retrieved")
    matches = pd.concat(frames)
    matches = matches.loc[~matches.index.duplicated()]
    for name, second in (("ndvi", "red"), ("ndmi", "swir16")):
        x, y = matches.ls_nir08, matches["ls_" + second]
        matches["ls_" + name] = ((x-y)/(x+y).where(x+y > 1e-6)).clip(-1, 1)
    field[[]].join(matches).to_csv(DERIVED / "landsat.csv")
    pd.DataFrame(logs).to_csv(DERIVED / "landsat_scene_log.csv", index=False)


def terrain(field: pd.DataFrame) -> None:
    sources = pd.read_csv(DERIVED / "elevation.csv").set_index("uid")
    groups = list(field.join(sources[["dem_url"]]).groupby("dem_url"))
    with ThreadPoolExecutor(max_workers=3) as workers:
        tiles = list(workers.map(terrain_tile, groups))
    rows = [row for tile, _ in tiles for row in tile]
    pd.DataFrame(rows, columns=["uid", *TERRAIN]).to_csv(DERIVED / "terrain.csv", index=False)
    (ROOT/"data/terrain_tiles.json").write_text(json.dumps([info for _, info in tiles],indent=2)+"\n",encoding="utf-8")


def download_dem(url: str, destination: Path) -> None:
    """Fetch checked byte ranges to avoid partial remote TIFF tile reads."""
    destination.parent.mkdir(exist_ok=True)
    first = requests.get(url, params={"range_start": "size"}, headers={"Range":"bytes=0-0"},timeout=30)
    first.raise_for_status()
    match = re.fullmatch(r"bytes 0-0/(\d+)", first.headers.get("Content-Range", ""))
    if not match:
        raise RuntimeError("Unexpected DEM range metadata")
    size = int(match[1])
    etag = first.headers.get("ETag")
    chunk = 2 * 1024 * 1024
    def read_range(start):
        end = min(start+chunk, size)-1
        expected=f"bytes {start}-{end}/{size}"
        for _ in range(3):
            try:
                answer=requests.get(url,params={"range_start":start},
                                    headers={"Range":f"bytes={start}-{end}"},timeout=55)
                if (answer.status_code==206 and answer.headers.get("Content-Range")==expected
                        and len(answer.content)==end-start+1 and answer.headers.get("ETag")==etag):
                    return answer.content
            except requests.RequestException:
                continue
        raise RuntimeError("Incomplete DEM byte range")
    temp=destination.with_suffix(".range-part")
    with ThreadPoolExecutor(max_workers=8) as workers, temp.open("wb") as out:
        for data in workers.map(read_range,range(0,size,chunk)):
            out.write(data)
    if temp.stat().st_size!=size:
        raise RuntimeError("Incomplete DEM product")
    temp.replace(destination)


def terrain_tile(task: tuple) -> tuple:
    url, subset = task
    name = url.rsplit("/", 1)[-1]
    response = requests.head(url, timeout=30)
    response.raise_for_status()
    cache = ROOT / "data/.downloads" / name
    if not cache.exists():
        download_dem(url,cache)
    with rasterio.Env(GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR", GDAL_HTTP_TIMEOUT="25",
                      GDAL_HTTP_MAX_RETRY="2"):
        with rasterio.open(cache) as dem:
            assert dem.crs.to_epsg() == 4326
            rows = []
            for uid, record in subset.iterrows():
                row, col = dem.index(record.lon, record.lat)
                if not (2 <= row < dem.height-2 and 2 <= col < dem.width-2):
                    rows.append((uid, np.nan, np.nan, np.nan))
                    continue
                array = dem.read(1, window=Window(col-2, row-2, 5, 5), masked=True)
                if np.ma.getmaskarray(array).any():
                    rows.append((uid, np.nan, np.nan, np.nan))
                    continue
                values = np.asarray(array, dtype=float)
                dx = abs(dem.res[0])*111320*np.cos(np.deg2rad(record.lat))
                dy = abs(dem.res[1])*111132
                slope = np.hypot((values[2,3]-values[2,1])/(2*dx), (values[1,2]-values[3,2])/(2*dy))
                rows.append((uid, np.ptp(values), values[2,2]-values.mean(), slope))
    digest = hashlib.sha256(cache.read_bytes()).hexdigest() if cache.exists() else None
    return rows, {"url":url,"filename":name,"etag":response.headers.get("ETag"),"sha256":digest}


def main():
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", choices=["landsat", "terrain"])
    args = parser.parse_args()
    field = pd.read_csv(DERIVED / "field.csv", parse_dates=["date"]).set_index("uid")
    {"landsat": landsat, "terrain": terrain}[args.source](field)


if __name__ == "__main__":
    main()
