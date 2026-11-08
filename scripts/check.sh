#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
python3 scripts/release.py
python3 scripts/check-delegation-contract.py
python3 scripts/check-vendored-imports.py
python3 -m compileall -q scripts skills tests
python3 -m unittest discover -s tests -v
python3 -m unittest discover -s skills/diagramming-style/tests -v
cmp AGENTS.md CLAUDE.md
git diff --check
