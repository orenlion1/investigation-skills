#!/usr/bin/env bash
# The gate itself is owned by the carried skill-ownership skill; this entry point keeps the
# documented command and evaluates this repository's catalog.
set -euo pipefail
repo_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
exec "$repo_root/skills/skill-ownership/scripts/run-skill-quality-gate.sh" \
  --repository "$repo_root" "$@"
