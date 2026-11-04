#!/usr/bin/env bash
# Scan committed history, including deleted secrets, without exposing matched values.
set -euo pipefail

if [ "$#" -gt 1 ]; then
  echo 'Usage: bash scripts/scan-secrets.sh [repository]' >&2
  exit 2
fi

repository="${1:-.}"
scanner="${GITLEAKS_BIN:-gitleaks}"
"$scanner" version > /dev/null
git -C "$repository" rev-parse --git-dir > /dev/null
if [ "$(git -C "$repository" rev-parse --is-shallow-repository)" != false ]; then
  echo 'Secret scan requires complete history; fetch with depth 0.' >&2
  exit 2
fi

scan_dir="$(mktemp -d)"
trap 'rm -rf "$scan_dir"' EXIT
# Gitleaks also loads source/.gitleaksignore unconditionally. A bare mirror has no
# working-tree ignore file, while preserving every source ref and its history.
git clone --quiet --mirror --no-hardlinks -- "$repository" "$scan_dir/repository.git"
printf '[extend]\nuseDefault = true\n' > "$scan_dir/config.toml"
# Detached PR heads can be absent from advertised refs. Preserve that exact head
# as a scan-only ref as well as every mirrored branch and tag.
head=$(git -C "$repository" rev-parse HEAD)
git -C "$scan_dir/repository.git" update-ref refs/scan/head "$head"
set +e
"$scanner" git "$scan_dir/repository.git" --log-opts='--all --full-history' \
  --config "$scan_dir/config.toml" --gitleaks-ignore-path /dev/null \
  --ignore-gitleaks-allow --redact=100 --no-banner --no-color \
  > "$scan_dir/scanner.log" 2>&1
result=$?
set -e
case "$result" in
  0) echo 'Secret scan passed.' ;;
  1) echo 'Secret scan blocked credentials; matched values and paths omitted.' >&2 ;;
  *) echo 'Secret scan could not complete; scanner details omitted.' >&2 ;;
esac
exit "$result"
