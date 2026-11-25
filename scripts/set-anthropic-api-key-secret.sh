#!/usr/bin/env bash
# Store ANTHROPIC_API_KEY as a GitHub Actions secret for the Live Behavioral Evals workflow.
# The key is read from the terminal without echo and passed to gh on stdin, so it never
# appears in arguments, shell history, the environment of other processes or a file.
set -euo pipefail
umask 077

if [ "$#" -gt 1 ]; then
  echo 'Usage: bash scripts/set-anthropic-api-key-secret.sh [owner/repository]' >&2
  exit 2
fi
command -v gh >/dev/null || { echo 'GitHub CLI (gh) is required.' >&2; exit 2; }
if [ ! -t 0 ]; then
  echo 'Run this from an interactive terminal; the key is never read from a pipe or file.' >&2
  exit 2
fi

repository="${1:-$(gh repo view --json nameWithOwner --jq .nameWithOwner)}"
printf 'Setting the ANTHROPIC_API_KEY Actions secret on %s\n' "$repository" >&2
printf 'Paste the API key (input hidden), then press Enter: ' >&2
IFS= read -rs key
printf '\n' >&2
trap 'unset key' EXIT

case "$key" in
  '') echo 'No key entered; nothing was changed.' >&2; exit 1 ;;
  *[[:space:]]*) echo 'The key contains whitespace; nothing was changed.' >&2; exit 1 ;;
  sk-ant-*) ;;
  *) echo 'The key does not start with sk-ant-; nothing was changed.' >&2; exit 1 ;;
esac

printf '%s' "$key" | gh secret set ANTHROPIC_API_KEY --app actions --repo "$repository"
unset key
gh secret list --app actions --repo "$repository" | awk '$1 == "ANTHROPIC_API_KEY" { print "Stored:", $1, "updated", $2; found = 1 } END { exit !found }'
