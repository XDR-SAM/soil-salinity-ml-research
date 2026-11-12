"""Create and validate the neutral submission archive and the Overleaf source ZIP."""
import argparse
from hashlib import sha256
from pathlib import Path
import re
from zipfile import ZIP_DEFLATED, ZipFile

ROOT=Path(__file__).resolve().parents[2]
DOCUMENTS=("README.md","CITATION.cff","EXECUTIVE_SUMMARY.md","CLAIMS_AND_EVIDENCE.md",
           "PUBLICATION_READINESS.md","CHANGELOG_V1_TO_V3.md")
EXCLUDE_PARTS={"__pycache__", ".downloads", ".pytest_cache", ".ruff_cache", ".venv", "raw", "smoke", "_build"}
EXCLUDE_EXT={".pyc",".log",".blg",".bbl",".aux",".tif",".tiff",".xlsx",".docx",".part",".pem",".key",".out"}


def allowed(relative):
    return (not set(relative.parts)&EXCLUDE_PARTS and relative.suffix not in EXCLUDE_EXT
            and not relative.name.startswith(".env"))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output",type=Path,default=Path.cwd())
    args=parser.parse_args()
    args.output.mkdir(parents=True,exist_ok=True)
    root_names=set(DOCUMENTS)|{"LICENSE",".gitignore",".gitattributes"}
    included_roots={"paper","figures","code","results","data","reports","archive"}
    selected=[]
    for path in sorted(ROOT.rglob("*")):
        if not path.is_file():
            continue
        relative=path.relative_to(ROOT)
        if (relative.parts[0] in included_roots or relative.as_posix() in root_names) and allowed(relative):
            selected.append(relative)
    filename=args.output/"FINAL_SUBMISSION.zip"
    patterns=(
        rb"(?i)[a-z]:[\\/](?:users|desktop)[\\/]",
        rb"(?i)github\.com/[^/\s]+/soil-salinity",
        rb"(?i)(?:ryzen [0-9]|intel core [a-z0-9]|windows 1[01] x64)",
        rb"(?i)(?:[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}|[?&]sig=[^,\s]+)",
    )
    text_suffix={".md",".csv",".txt",".tex",".bib",".json",".svg",".cff"}
    for relative in selected:
        data=(ROOT/relative).read_bytes()
        if relative.suffix in text_suffix and any(re.search(pattern,data) for pattern in patterns):
            raise ValueError(f"Privacy audit failed on {relative}")
    with ZipFile(filename,"w",ZIP_DEFLATED,compresslevel=8) as zipout:
        for relative in selected:
            zipout.write(ROOT/relative,"FINAL_SUBMISSION/"+relative.as_posix())
    with ZipFile(filename) as package:
        assert package.testzip() is None
        files=set(package.namelist())
        required={*DOCUMENTS,"LICENSE","paper/main.tex","paper/main.pdf","paper/numbers.tex","paper/references.bib",
                  "code/run_all.py","code/requirements.txt","code/configs/frozen_primary_protocol.sha256",
                  "figures/proposed_framework.svg","figures/proposed_framework.pdf","figures/proposed_framework.png",
                  "results/predictions.csv","results/metrics.csv","results/paired_deltas.csv","results/subgroups.csv",
                  "reports/runtime_and_reproducibility.md","reports/validation_audit.md"}
        assert {"FINAL_SUBMISSION/"+path for path in required}<=files
        assert sha256(package.read("FINAL_SUBMISSION/paper/main.pdf")).digest()==sha256(
            (ROOT/"paper/main.pdf").read_bytes()).digest()

    paper=(ROOT/"paper/main.tex").read_text(encoding="utf-8")
    figures=re.findall(r"\\includegraphics\[[^\]]*\]\{([^}]+)\}",paper)
    overleaf=args.output/"OVERLEAF_READY.zip"
    with ZipFile(overleaf,"w",ZIP_DEFLATED,compresslevel=8) as zipout:
        for name in ("main.tex","numbers.tex","references.bib"):
            zipout.write(ROOT/"paper"/name,name)
        for name in figures:
            zipout.write(ROOT/"figures"/(name+".pdf"),f"figures/{name}.pdf")
    with ZipFile(overleaf) as package:
        assert package.testzip() is None
        assert len(package.namelist())==3+len(figures)
    print(f"{filename.name}: {len(selected)} files, {filename.stat().st_size:,} bytes")
    print(f"{overleaf.name}: {3+len(figures)} files, {overleaf.stat().st_size:,} bytes")


if __name__=="__main__":
    main()
