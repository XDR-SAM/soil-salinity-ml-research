"""Retrieve the versioned original workbooks and verify them before use."""
from datetime import datetime, timezone
from hashlib import md5, sha256
import json
from pathlib import Path

import requests

SOURCES = {
    2024: (14560019, "Soil_Salinity_Data_BD032024.xlsx", "1da7d0e9282e1b5a8ee14618b9ec583c", 162),
    2025: (19711551, "Soil_Salinity_Data_BD042025.xlsx", "f0189c1cf56fe7af8f63f2a7277ceba7", 187),
}
ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    raw = ROOT / "data/raw"
    raw.mkdir(parents=True, exist_ok=True)
    manifest = []
    for year, (record, name, expected, count) in SOURCES.items():
        record_url = f"https://zenodo.org/records/{record}"
        url = f"{record_url}/files/{name}?download=1"
        response = requests.get(f"https://zenodo.org/api/records/{record}", timeout=60)
        response.raise_for_status()
        metadata = response.json()["metadata"]
        path = raw / name
        if not path.exists() or md5(path.read_bytes()).hexdigest() != expected:
            file = requests.get(url, timeout=90)
            file.raise_for_status()
            if md5(file.content).hexdigest() != expected:
                raise ValueError(f"Original hash mismatch for {name}")
            path.write_bytes(file.content)
        manifest.append(dict(year=year, record_url=record_url, download_url=url,
                             filename=name, doi=metadata["doi"], version=metadata.get("version"),
                             license=metadata.get("license"), creators=metadata["creators"],
                             publication_date=metadata["publication_date"], md5=expected,
                             sha256=sha256(path.read_bytes()).hexdigest(), expected_rows=count,
                             origin="Zenodo versioned original",
                             verified_at_utc=datetime.now(timezone.utc).isoformat()))
    (ROOT / "data/manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
                                              encoding="utf-8")


if __name__ == "__main__":
    main()
