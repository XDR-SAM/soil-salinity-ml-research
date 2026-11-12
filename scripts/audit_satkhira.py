"""Count candidate Satkhira records under one pinned public boundary."""
import json

from matplotlib.path import Path as Polygon
import numpy as np
import pandas as pd
import requests

from download_originals import ROOT

URL = ("https://raw.githubusercontent.com/wmgeolab/geoBoundaries/9469f09/"
       "releaseData/gbOpen/BGD/ADM2/geoBoundaries-BGD-ADM2.geojson")


def main() -> None:
    response = requests.get(URL, timeout=90)
    response.raise_for_status()
    if response.text.startswith("version https://git-lfs.github.com/spec/v1"):
        response = requests.get(URL.replace("raw.githubusercontent.com", "media.githubusercontent.com/media"),
                                timeout=90)
        response.raise_for_status()
    boundary = next(f for f in response.json()["features"]
                    if "satkhira" in f["properties"]["shapeName"].casefold())
    geom = boundary["geometry"]
    polygons = geom["coordinates"] if geom["type"] == "MultiPolygon" else [geom["coordinates"]]
    field = pd.read_csv(ROOT / "data/derived/field.csv")
    xy = field[["lon", "lat"]].to_numpy()
    inside = np.zeros(len(field), dtype=bool)
    for exterior, *holes in polygons:
        part = Polygon(exterior).contains_points(xy)
        for hole in holes:
            part &= ~Polygon(hole).contains_points(xy)
        inside |= part
    counts = field[inside].groupby("year").size().to_dict()
    result = dict(boundary_url=response.url, properties=boundary["properties"], candidate_counts=counts,
                  published_counts={2024: 86, 2025: 119}, exact_membership_verified=False)
    (ROOT / "reports/satkhira_boundary_check.json").write_text(json.dumps(result, indent=2) + "\n")
    print(result)


if __name__ == "__main__":
    main()
