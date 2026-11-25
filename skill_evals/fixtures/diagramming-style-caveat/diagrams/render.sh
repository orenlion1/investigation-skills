#!/bin/sh
# Renders the light and dark SVG exports from the one DOT source; only the palette differs.
set -eu
cd "$(dirname "$0")"
dot -Tsvg -Gbgcolor=#ffffff -Gfontcolor=#111827 -Nfontcolor=#111827 -Ecolor=#4b5563 -Efontcolor=#374151 \
  queue-flow.dot -o queue-flow-light.svg
dot -Tsvg -Gbgcolor=#0f172a -Gfontcolor=#f1f5f9 -Nfontcolor=#f1f5f9 -Ecolor=#94a3b8 -Efontcolor=#cbd5e1 \
  queue-flow.dot -o queue-flow-dark.svg
