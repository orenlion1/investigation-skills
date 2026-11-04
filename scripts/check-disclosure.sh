#!/usr/bin/env bash
# Run locally before pushing; CI cannot undo an upload that already happened.
set -euo pipefail
repository_root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
bash "$repository_root/scripts/scan-secrets.sh" "$repository_root"
python3 "$repository_root/scripts/scan-institutional-data.py" --repository "$repository_root"
