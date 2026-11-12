"""Reproduce the analysis from the bundled, time-audited feature tables."""
import argparse
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
SCRIPTS=ROOT/"code/scripts"


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--jobs",type=int,default=4)
    parser.add_argument("--compiler",default="tectonic")
    parser.add_argument("--smoke",action="store_true")
    parser.add_argument("--verify-originals",action="store_true")
    parser.add_argument("--refresh-new-features",action="store_true")
    args=parser.parse_args()
    def step(name,*flags):
        subprocess.run([sys.executable,"-u",str(SCRIPTS/name),*flags],cwd=ROOT,check=True)
    if args.verify_originals:
        step("download_originals.py")
    if args.refresh_new_features:
        step("acquire.py","landsat")
        step("acquire.py","terrain")
    step("audit.py")
    if args.smoke:
        step("benchmark.py","--smoke","--jobs","1")
        return
    step("benchmark.py","--jobs",str(args.jobs))
    for name in ("evaluate.py","figures.py","manuscript_numbers.py"):
        step(name)
    subprocess.run([args.compiler,"--keep-logs","main.tex"],cwd=ROOT/"paper",check=True)
    subprocess.run([sys.executable,"-m","pytest","-q",str(ROOT/"code/tests")],cwd=ROOT,check=True)


if __name__=="__main__":
    main()
