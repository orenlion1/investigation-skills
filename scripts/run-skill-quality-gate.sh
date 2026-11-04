#!/usr/bin/env bash
set -euo pipefail

repo_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
readonly harness_repository=https://github.com/addyosmani/agent-skills.git
readonly harness_revision=7cb7a20bb38b199728d456999c725a0488490ab6
skills_dir="$repo_root/skills"
cases_dir="$repo_root/skill_evals/cases"
fixtures_dir="$repo_root/skill_evals/fixtures"
output_dir=''
harness_dir=''
check_only=0

usage() {
  cat <<'EOF'
Usage: scripts/run-skill-quality-gate.sh [options]

Evaluate the complete investigation-skills catalog with the immutable upstream harness.

  --check              Verify dependency, inputs, counts, and pinned harness only.
  --harness-dir DIR    Reuse a local harness checkout at the exact pinned revision.
  --skills-dir DIR     Override the skill catalog (test fixtures only).
  --cases-dir DIR      Override checked-in cases (test fixtures only).
  --fixtures-dir DIR   Overlay repository-owned fixtures from DIR.
  --output-dir DIR     Preserve logs in DIR; otherwise logs are temporary.
EOF
}

while (($#)); do
  case $1 in
    --check)
      check_only=1
      shift
      ;;
    --harness-dir|--skills-dir|--cases-dir|--fixtures-dir|--output-dir)
      if (($# < 2)) || [[ -z ${2:-} ]]; then
        printf 'error: %s requires a value\n' "$1" >&2
        exit 2
      fi
      case $1 in
        --harness-dir) harness_dir=$2 ;;
        --skills-dir) skills_dir=$2 ;;
        --cases-dir) cases_dir=$2 ;;
        --fixtures-dir) fixtures_dir=$2 ;;
        --output-dir) output_dir=$2 ;;
      esac
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      printf 'error: unknown argument: %s\n' "$1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

for required_command in cat cp find git grep mkdir mktemp node python3 rm tee tr wc; do
  if ! command -v "$required_command" >/dev/null 2>&1; then
    printf 'error: required command is unavailable: %s\n' "$required_command" >&2
    exit 1
  fi
done
if [[ ! $harness_revision =~ ^[0-9a-f]{40}$ ]]; then
  printf 'error: pinned harness revision is not a 40-character SHA\n' >&2
  exit 1
fi
for input_dir in "$skills_dir" "$cases_dir"; do
  if [[ ! -d $input_dir || -L $input_dir ]]; then
    printf 'error: required input must be a real directory: %s\n' "$input_dir" >&2
    exit 1
  fi
done
if [[ -e $fixtures_dir && (! -d $fixtures_dir || -L $fixtures_dir) ]]; then
  printf 'error: fixture overlay must be a real directory: %s\n' "$fixtures_dir" >&2
  exit 1
fi
if [[ -n $harness_dir && (! -d $harness_dir || -L $harness_dir) ]]; then
  printf 'error: harness override must be a real directory: %s\n' "$harness_dir" >&2
  exit 1
fi

skill_count=$(find "$skills_dir" -mindepth 2 -maxdepth 2 -type f -name SKILL.md | wc -l | tr -d ' ')
case_count=$(find "$cases_dir" -mindepth 1 -maxdepth 1 -type f -name '*.json' | wc -l | tr -d ' ')
if ((skill_count == 0 || case_count == 0)); then
  printf 'error: empty discovery is invalid (skills=%d cases=%d)\n' "$skill_count" "$case_count" >&2
  exit 1
fi

workspace=$(mktemp -d "${TMPDIR:-/tmp}/investigation-skill-quality.XXXXXX")
cleanup() {
  case $workspace in
    "${TMPDIR:-/tmp}"/investigation-skill-quality.*) rm -R -- "$workspace" ;;
    *) printf 'refusing workspace cleanup: %s\n' "$workspace" >&2 ;;
  esac
}
trap cleanup EXIT

harness_work="$workspace/harness"
if [[ -n $harness_dir ]]; then
  resolved_revision=$(git -C "$harness_dir" rev-parse HEAD 2>/dev/null || true)
  if [[ $resolved_revision != "$harness_revision" ]]; then
    printf 'error: harness override is at %s, expected %s\n' \
      "${resolved_revision:-<unresolved>}" "$harness_revision" >&2
    exit 1
  fi
  if ! git -C "$harness_dir" diff --quiet HEAD --; then
    printf 'error: harness override has local modifications at the pinned revision\n' >&2
    exit 1
  fi
  mkdir -p "$harness_work"
  cp -R "$harness_dir/." "$harness_work/"
else
  git init --quiet "$harness_work"
  git -C "$harness_work" remote add origin "$harness_repository"
  git -C "$harness_work" fetch --quiet --depth 1 origin "$harness_revision"
  git -C "$harness_work" checkout --quiet --detach FETCH_HEAD
fi
resolved_revision=$(git -C "$harness_work" rev-parse HEAD)
if [[ $resolved_revision != "$harness_revision" ]]; then
  printf 'error: fetched harness is at %s, expected %s\n' \
    "$resolved_revision" "$harness_revision" >&2
  exit 1
fi
for harness_file in scripts/validate-skills.js scripts/validate-commands.js scripts/run-evals.js; do
  if [[ ! -f $harness_work/$harness_file || -L $harness_work/$harness_file ]]; then
    printf 'error: pinned harness file is missing or unsafe: %s\n' "$harness_file" >&2
    exit 1
  fi
done

printf 'harness revision: %s\n' "$resolved_revision"
printf 'skills: %s\n' "$skill_count"
printf 'case files: %s\n' "$case_count"
if ((check_only)); then
  printf 'Skill quality preflight passed; evaluation was not run.\n'
  exit 0
fi

rm -R -- "$harness_work/skills" "$harness_work/evals/cases"
mkdir -p "$harness_work/skills" "$harness_work/evals/cases" "$harness_work/evals/fixtures"
cp -R "$skills_dir/." "$harness_work/skills/"
cp -R "$cases_dir/." "$harness_work/evals/cases/"
if [[ -d $fixtures_dir ]]; then
  cp -R "$fixtures_dir/." "$harness_work/evals/fixtures/"
fi

if [[ -z $output_dir ]]; then
  output_dir="$workspace/results"
elif [[ -L $output_dir ]]; then
  printf 'error: output directory cannot be a symlink: %s\n' "$output_dir" >&2
  exit 1
fi
mkdir -p "$output_dir"

quick_log="$output_dir/tier1-quick-validate.log"
structure_log="$output_dir/tier1-structure.log"
command_log="$output_dir/tier1-command-parity.log"
routing_log="$output_dir/tier2-routing.log"
behavior_log="$output_dir/tier3-dry-run.log"
summary_log="$output_dir/summary.txt"
: >"$quick_log"
for skill_file in "$harness_work"/skills/*/SKILL.md; do
  if ! python3 "$repo_root/scripts/quick-validate-skill.py" \
    "${skill_file%/SKILL.md}" >>"$quick_log" 2>&1; then
    cat "$quick_log"
    printf 'error: standalone skill validation failed\n' >&2
    exit 1
  fi
done
cat "$quick_log"

if ! node "$harness_work/scripts/validate-skills.js" >"$structure_log" 2>&1; then
  cat "$structure_log"
  printf 'error: structural validation failed\n' >&2
  exit 1
fi
cat "$structure_log"
if grep -Fq 'WARN:' "$structure_log"; then
  printf 'error: structural validation reported warnings, including a dead cross-reference\n' >&2
  exit 1
fi

if ! node "$harness_work/scripts/validate-commands.js" >"$command_log" 2>&1; then
  cat "$command_log"
  printf 'error: command parity validation failed\n' >&2
  exit 1
fi
cat "$command_log"

if ! node "$harness_work/scripts/run-evals.js" --min-rank1 80 >"$routing_log" 2>&1; then
  cat "$routing_log"
  printf 'error: catalog-wide routing validation failed\n' >&2
  exit 1
fi
cat "$routing_log"

: >"$behavior_log"
for skill_dir in "$harness_work"/skills/*; do
  skill_name=${skill_dir##*/}
  if ! node "$harness_work/scripts/run-evals.js" \
    --behavioral "$skill_name" --dry-run >>"$behavior_log" 2>&1; then
    cat "$behavior_log"
    printf 'error: behavioral dry-run failed for %s\n' "$skill_name" >&2
    exit 1
  fi
done
planned_evals=$(grep -c '^\[dry-run\]' "$behavior_log" || true)
if ((planned_evals < skill_count)); then
  cat "$behavior_log"
  printf 'error: behavioral dry-run planned %d evals for %d skills\n' \
    "$planned_evals" "$skill_count" >&2
  exit 1
fi
cat "$behavior_log"

{
  printf 'harness revision: %s\n' "$resolved_revision"
  printf 'skills: %s\n' "$skill_count"
  printf 'case files: %s\n' "$case_count"
  printf 'behavioral dry-run plans: %s\n' "$planned_evals"
  printf 'model execution: not run\n'
  printf 'Skill quality gate passed\n'
} | tee "$summary_log"
