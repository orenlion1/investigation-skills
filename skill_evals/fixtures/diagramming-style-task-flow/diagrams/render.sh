#!/bin/sh
# Renders light, dark and adaptive SVG exports of one diagram from its single DOT source.
# Usage: diagrams/render.sh investigation-workflow
set -eu
cd "$(dirname "$0")"
name="$1"
dot -Tsvg -Gbgcolor=#ffffff -Gfillcolor=#fffde7 -Gcolor=#fffde7 -Gfontcolor=#111827 \
  -Nfillcolor=#ececff -Ncolor=#6366f1 -Nfontcolor=#111827 -Ecolor=#4b5563 -Efontcolor=#0e7490 \
  "$name.dot" -o "$name-light.svg"
dot -Tsvg -Gbgcolor=#0f172a -Gfillcolor=#374151 -Gcolor=#374151 -Gfontcolor=#f1f5f9 \
  -Nfillcolor=#1e293b -Ncolor=#a5b4fc -Nfontcolor=#f1f5f9 -Ecolor=#94a3b8 -Efontcolor=#a5f3fc \
  "$name.dot" -o "$name-dark.svg"
python3 make_adaptive.py "$name-light.svg" "$name-adaptive.svg"
