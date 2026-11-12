"""Audit every populated field row and create the canonical analysis table."""
from hashlib import md5
from pathlib import Path

import numpy as np
import pandas as pd
from openpyxl import load_workbook
from pyproj import Transformer
from scipy.spatial.distance import cdist, pdist

from download_originals import ROOT, SOURCES

FIELDS = ["original_id", "sample_id", "lat", "lon", "ec", "sample_type", "date", "team"]
HEADER = ["ID", "SAMPLE_NO", "Latitude", "Longitude", "Electrical_Conductivity_EC(mS/cm)"]


def workbook_rows(path: Path, year: int) -> tuple[list[dict], list[str]]:
    rows = []
    sheets = []
    with path.open("rb") as handle:
        book = load_workbook(handle, read_only=True, data_only=True)
        for sheet in book:
            content = list(sheet.values)
            headers = [i for i, row in enumerate(content) if list(row[:5]) == HEADER]
            if len(headers) != 1:
                raise ValueError(f"Expected one table in {sheet.title}")
            start = headers[0]
            trailing = []
            footers = []
            for line, row in enumerate(content[start+1:], start + 2):
                if all(v is None for v in row):
                    trailing.append(line)
                    continue
                if isinstance(row[0], str) and "Copyright -" in row[0] and all(v is None for v in row[1:]):
                    footers.append(line)
                    continue
                rows.append(dict(uid=f"{year}-{line}", year=year, sheet=sheet.title,
                                 excel_row=line, **dict(zip(FIELDS, row, strict=True))))
            sheets.append(f"- {year}, `{sheet.title}`: header on row {start+1}; "
                          f"workbook headers {list(content[start])}; blank rows {trailing}; "
                          f"copyright footer rows {footers}.")
        book.close()
    return rows, sheets


def build() -> None:
    destination = ROOT / "data/derived"
    destination.mkdir(parents=True, exist_ok=True)
    report = ROOT / "reports"
    report.mkdir(exist_ok=True)
    records, notes = [], []
    for year, (_, name, expected_hash, expected_n) in SOURCES.items():
        path = ROOT / "data/raw" / name
        if md5(path.read_bytes()).hexdigest() != expected_hash:
            raise ValueError(f"Unexpected workbook bytes: {path}")
        rows, sheets = workbook_rows(path, year)
        if len(rows) != expected_n:
            raise ValueError(f"{year}: expected {expected_n}, got {len(rows)}")
        records.extend(rows)
        notes.extend(sheets)
    original = pd.DataFrame(records)
    data = original.copy()
    for key in ("lat", "lon", "ec"):
        data[key] = pd.to_numeric(data[key], errors="coerce")
    data["date"] = pd.to_datetime(data["date"], errors="coerce")
    is_coord = data.lat.between(21, 24) & data.lon.between(88, 91)
    is_target = np.isfinite(data.ec) & (data.ec >= 0)
    is_soil = data.sample_type.astype(str).str.strip().str.lower().eq("soil")
    status = np.select([~is_coord, ~is_target, ~is_soil],
                       ["invalid coordinate", "invalid EC", "non-soil sample"], default="eligible")
    original.assign(status=status).to_csv(destination / "processing_log.csv", index=False)
    data = data.loc[status == "eligible"].copy()
    transform = Transformer.from_crs(4326, 32645, always_xy=True)
    data["easting"], data["northing"] = transform.transform(data.lon.to_numpy(), data.lat.to_numpy())
    data.to_csv(destination / "field.csv", index=False)
    sections = ["# Workbook audit", "", *notes, "", f"**{len(original)} populated field rows; "
                f"{len(data)} eligible records.** No salinity outlier trimming.",
                "", "Blank formatted rows are distinct from populated samples. "
                "The laboratory contact rows are skipped and never exported.", ""]
    for year, group in data.groupby("year"):
        xy = group[["easting", "northing"]].to_numpy()
        dates = group.date.dropna()
        summary = group.ec.quantile([0, .25, .5, .75, 1]).round(4).tolist()
        sections += [
            f"## {year}", "",
            f"- Eligible {len(group)} of {sum(original.year == year)}. "
            f"Missing original values: {original[original.year == year][FIELDS].isna().sum().to_dict()}.",
            f"- Dates {dates.min().date()} to {dates.max().date()} "
            f"({group.date.isna().sum()} unparsed/missing; "
            f"{sum(dates.dt.year != year)} parsed outside source year).",
            f"- Latitude {group.lat.min():.6f} to {group.lat.max():.6f}; "
            f"longitude {group.lon.min():.6f} to {group.lon.max():.6f}.",
            f"- EC five-number summary {summary} mS/cm. "
            f"Mean {group.ec.mean():.4f}, sample SD {group.ec.std():.4f} mS/cm.",
            f"- Duplicate IDs beyond first: original ID {group.original_id.duplicated().sum()}, "
            f"sample number {group.sample_id.duplicated().sum()}. Exact coordinate pairs: "
            f"{sum(pdist(xy) == 0)}; pairs within 20 m: {sum(pdist(xy) <= 20)}.", ""]
    a = data[data.year == 2024][["easting", "northing"]]
    b = data[data.year == 2025][["easting", "northing"]]
    distance = cdist(a, b)
    sections += ["## Cross-year geography", "",
                 f"Exact cross-year coordinate pairs: {sum((distance == 0).ravel())}. "
                 f"Pairs within 20 m: {sum((distance <= 20).ravel())}. "
                 f"Median distance to nearest site in the other campaign: "
                 f"{np.median(distance.min(axis=1))/1000:.2f} km from 2024 and "
                 f"{np.median(distance.min(axis=0))/1000:.2f} km from 2025.",
                 "", "Location, month and year vary together. The campaign EC distributions "
                 "cannot identify within-site salinity change. Coordinates use WGS84 degrees, "
                 "projected to WGS84 / UTM zone 45N (EPSG:32645) for distances.", ""]
    (report / "data_audit.md").write_text("\n".join(sections), encoding="utf-8")


if __name__ == "__main__":
    build()
