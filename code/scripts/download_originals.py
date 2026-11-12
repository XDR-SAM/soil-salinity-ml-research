"""Fetch the two versioned workbook originals and verify their recorded bytes."""
import hashlib
import json
import math
from pathlib import Path

import pandas as pd
import requests
from openpyxl import load_workbook

ROOT=Path(__file__).resolve().parents[2]


def main():
    raw=ROOT/"data/raw"
    raw.mkdir(exist_ok=True)
    manifest=json.loads((ROOT/"data/manifest.json").read_text(encoding="utf-8"))
    field=pd.read_csv(ROOT/"data/derived/field.csv",parse_dates=["date"]).set_index("uid")
    for entry in manifest:
        path=raw/entry["filename"]
        if not path.exists():
            response=requests.get(entry["download_url"],timeout=90)
            response.raise_for_status()
            if hashlib.sha256(response.content).hexdigest()!=entry["sha256"]:
                raise ValueError("Unexpected workbook bytes")
            path.write_bytes(response.content)
        content=path.read_bytes()
        assert hashlib.md5(content).hexdigest()==entry["md5"]
        assert hashlib.sha256(content).hexdigest()==entry["sha256"]
        with path.open("rb") as stream:
            workbook=load_workbook(stream,read_only=True,data_only=True)
            rows=list(workbook.active.values)
            workbook.close()
        assert rows[2][:5]==("ID","SAMPLE_NO","Latitude","Longitude","Electrical_Conductivity_EC(mS/cm)")
        observed=[(i,row) for i,row in enumerate(rows[3:],4) if isinstance(row[0],int)]
        assert len(observed)==entry["expected_rows"]
        for line,row in observed:
            canonical=field.loc[f"{entry['year']}-{line}"]
            assert canonical.sample_id==row[1] and canonical.original_id==row[0]
            assert all(math.isclose(canonical[key],value,abs_tol=1e-12)
                       for key,value in zip(("lat","lon","ec"),row[2:5],strict=True))
            assert canonical.date==pd.Timestamp(row[6]) and canonical.sample_type==row[5]
        print(f"{path.name}: {len(observed)} observations and both checksums verified")


if __name__=="__main__":
    main()
