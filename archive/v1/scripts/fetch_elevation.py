"""Sample the 2021 Copernicus GLO-30 surface model at field coordinates."""
import numpy as np
import pandas as pd
import rasterio

from download_originals import ROOT


def main() -> None:
    path = ROOT / "data/derived"
    data = pd.read_csv(path / "field.csv").set_index("uid")
    data["lat_tile"] = np.floor(data.lat).astype(int)
    data["lon_tile"] = np.floor(data.lon).astype(int)
    frames = []
    with rasterio.Env(GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR", GDAL_HTTP_TIMEOUT="30"):
        for (lat, lon), group in data.groupby(["lat_tile", "lon_tile"]):
            name = f"Copernicus_DSM_COG_10_N{lat:02}_00_E{lon:03}_00_DEM"
            url = f"https://copernicus-dem-30m.s3.amazonaws.com/{name}/{name}.tif"
            with rasterio.open(url) as source:
                assert source.crs.to_epsg() == 4326
                sampled = source.sample(zip(group.lon, group.lat, strict=True), masked=True)
                elevation = [np.nan if np.ma.is_masked(v[0]) else float(v[0]) for v in sampled]
            frames.append(pd.DataFrame(dict(elevation=elevation, dem_tile=name, dem_url=url),
                                       index=group.index))
    pd.concat(frames).sort_index().to_csv(path / "elevation.csv")


if __name__ == "__main__":
    main()
