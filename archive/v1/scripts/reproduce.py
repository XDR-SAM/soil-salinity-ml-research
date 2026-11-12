"""Run the versioned acquisition, benchmarking, and manuscript workflow."""
import argparse
import subprocess
import sys

from download_originals import ROOT


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--smoke", action="store_true", help="Run a reduced coordinate-only study.")
    parser.add_argument("--compiler", default="tectonic", help="Tectonic binary for the full run.")
    parser.add_argument("--jobs", default=2, type=int, help="Concurrent outer-fold workers.")
    args = parser.parse_args()
    steps = [["download_originals.py"], ["build_dataset.py"]]
    if args.smoke:
        steps.append(["train_models.py", "--smoke", "--coordinate-only"])
    else:
        steps.extend([["audit_satkhira.py"], ["fetch_remote_sensing.py", "--snapshot"],
                      ["fetch_elevation.py"], ["train_models.py", "--jobs", str(args.jobs)],
                      ["evaluate.py"], ["make_figures.py"], ["paper_numbers.py"]])
    for name, *flags in steps:
        print(f"Running {name}", flush=True)
        subprocess.run([sys.executable, "-u", str(ROOT / "scripts" / name), *flags],
                       cwd=ROOT, check=True)
    if not args.smoke:
        subprocess.run([args.compiler, "--keep-logs", "main.tex"], cwd=ROOT / "paper", check=True)
        subprocess.run([sys.executable, "-m", "pytest", "-q"], cwd=ROOT, check=True)


if __name__ == "__main__":
    main()
