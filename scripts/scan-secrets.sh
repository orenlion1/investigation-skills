#!/usr/bin/env bash
# Scan committed history, including deleted secrets, without exposing matched values.
set -euo pipefail
umask 077

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
# Export every reachable blob independently of patch generation, including content
# introduced only in merges and blobs referenced directly by tags. Also export
# metadata and unquoted tree paths; none of the original names become disk paths.
# Git's object traversal includes nested annotations without their own refs.
metadata_dir="$scan_dir/metadata"
mkdir "$metadata_dir"
git -C "$scan_dir/repository.git" rev-list --objects --all --no-object-names HEAD \
  > "$scan_dir/objects"
git -C "$scan_dir/repository.git" cat-file --batch-check='%(objectname) %(objecttype)' \
  < "$scan_dir/objects" > "$scan_dir/object-types"
while read -r object kind; do
  case "$kind" in
    blob|commit|tag)
      git -C "$scan_dir/repository.git" cat-file "$kind" "$object" \
        > "$metadata_dir/$object"
      ;;
    tree)
      git -C "$scan_dir/repository.git" ls-tree -r -z --name-only "$object" \
        | tr '\0' '\n' > "$metadata_dir/$object"
      ;;
  esac
done < "$scan_dir/object-types"
git -C "$scan_dir/repository.git" for-each-ref --format='%(refname)' \
  > "$metadata_dir/refs"
set +e
"$scanner" git "$scan_dir/repository.git" --log-opts='--all --full-history' \
  --config "$scan_dir/config.toml" --gitleaks-ignore-path /dev/null \
  --ignore-gitleaks-allow --redact=100 --no-banner --no-color \
  > "$scan_dir/scanner.log" 2>&1
history_result=$?
"$scanner" dir "$metadata_dir" \
  --config "$scan_dir/config.toml" --gitleaks-ignore-path /dev/null \
  --ignore-gitleaks-allow --redact=100 --no-banner --no-color \
  > "$scan_dir/metadata-scanner.log" 2>&1
metadata_result=$?
set -e
result=0
if [ "$history_result" -gt 1 ] || [ "$metadata_result" -gt 1 ]; then
  result=2
elif [ "$history_result" -ne 0 ] || [ "$metadata_result" -ne 0 ]; then
  result=1
fi
case "$result" in
  0) echo 'Secret scan passed.' ;;
  1) echo 'Secret scan blocked credentials; matched values and paths omitted.' >&2 ;;
  *) echo 'Secret scan could not complete; scanner details omitted.' >&2 ;;
esac
exit "$result"
