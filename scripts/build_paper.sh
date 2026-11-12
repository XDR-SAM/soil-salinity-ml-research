#!/usr/bin/env sh
set -eu
cd "$(dirname "$0")/../paper"
if command -v latexmk >/dev/null 2>&1; then
    mkdir -p _build
    latexmk -pdf -outdir=_build -halt-on-error -interaction=nonstopmode main.tex
    cp _build/main.pdf main.pdf
else
    tectonic --keep-logs main.tex
fi
