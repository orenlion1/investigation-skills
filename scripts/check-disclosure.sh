#!/usr/bin/env bash
# Run locally before pushing; CI cannot undo an upload that already happened.
set -euo pipefail
# Git exports GIT_DIR and friends to its hooks, pointing at the main checkout when the hook
# runs from a linked worktree. Those ambient values override the explicit `-C` the scanners
# pass, so the pre-push hook failed in any worktree while the same command passed by hand.
# Scan the repository these scripts were pointed at, never the one Git happened to export.
unset GIT_DIR GIT_WORK_TREE GIT_INDEX_FILE GIT_OBJECT_DIRECTORY GIT_COMMON_DIR
repository_root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
bash "$repository_root/scripts/scan-secrets.sh" "$repository_root"
# Real institution fingerprints are private: load them from a local file outside the repository.
private_fingerprints=${DISCLOSURE_PRIVATE_FINGERPRINTS_FILE:-$HOME/.config/disclosure/private-fingerprints.json}
if [ -z "${DISCLOSURE_PRIVATE_FINGERPRINTS:-}" ] && [ -f "$private_fingerprints" ]; then
  DISCLOSURE_PRIVATE_FINGERPRINTS=$(cat -- "$private_fingerprints")
  export DISCLOSURE_PRIVATE_FINGERPRINTS
fi
if [ -z "${DISCLOSURE_PRIVATE_FINGERPRINTS:-}" ]; then
  echo "Private institution fingerprints not configured; scanning with the public policy only." >&2
fi
python3 "$repository_root/scripts/scan-institutional-data.py" --repository "$repository_root"
