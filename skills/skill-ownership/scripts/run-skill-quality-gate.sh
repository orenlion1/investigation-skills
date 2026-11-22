#!/usr/bin/env bash
set -euo pipefail

script_dir=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
repo_root=$PWD
readonly harness_repository=https://github.com/addyosmani/agent-skills.git
readonly harness_revision=7cb7a20bb38b199728d456999c725a0488490ab6
skills_dir=''
cases_dir=''
fixtures_dir=''
output_dir=''
harness_dir=''
runner_dir=''
only_skill=''
min_rank1=80
check_only=0
execute_behavioral=0

usage() {
  cat <<'EOF'
Usage: run-skill-quality-gate.sh [options]

Evaluate a skill catalog with the immutable upstream harness: standalone validation,
structural lint, command parity, deterministic routing, and behavioral dry-run plans.
Model execution of the behavioral evals is optional and never runs unless requested.

  --repository DIR       Repository to evaluate (default: the current directory).
  --check                Verify dependency, inputs, counts, and pinned harness only.
  --harness-dir DIR      Reuse a local harness checkout at the exact pinned revision.
  --skills-dir DIR       Override the skill catalog (default: REPOSITORY/skills).
  --cases-dir DIR        Override the cases (default: REPOSITORY/skill_evals/cases).
  --fixtures-dir DIR     Overlay fixtures (default: REPOSITORY/skill_evals/fixtures).
  --output-dir DIR       Preserve logs in DIR; otherwise logs are temporary.
  --min-rank1 PERCENT    Required rank-one routing rate (default: 80).
  --execute-behavioral   Also execute the behavioral evals against a model through the
                         headless `claude` command, and fail when an expectation fails.
  --runner-dir DIR       Directory holding the `claude` executable to use for execution
                         (default: the one on PATH). Tests pass a deterministic stub.
  --skill NAME           With --execute-behavioral, execute only this skill's evals.
EOF
}

while (($#)); do
  case $1 in
    --check)
      check_only=1
      shift
      ;;
    --execute-behavioral)
      execute_behavioral=1
      shift
      ;;
    --repository|--harness-dir|--skills-dir|--cases-dir|--fixtures-dir|--output-dir|--min-rank1|--runner-dir|--skill)
      if (($# < 2)) || [[ -z ${2:-} ]]; then
        printf 'error: %s requires a value\n' "$1" >&2
        exit 2
      fi
      case $1 in
        --repository) repo_root=$2 ;;
        --min-rank1) min_rank1=$2 ;;
        --runner-dir) runner_dir=$2 ;;
        --skill) only_skill=$2 ;;
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

if [[ ! -d $repo_root || -L $repo_root ]]; then
  printf 'error: repository must be a real directory: %s\n' "$repo_root" >&2
  exit 1
fi
repo_root=$(cd "$repo_root" && pwd)
: "${skills_dir:=$repo_root/skills}"
: "${cases_dir:=$repo_root/skill_evals/cases}"
: "${fixtures_dir:=$repo_root/skill_evals/fixtures}"
if [[ ! $min_rank1 =~ ^(100|[0-9]{1,2})$ ]]; then
  printf 'error: --min-rank1 must be an integer from 0 to 100\n' >&2
  exit 2
fi
if [[ -n $only_skill && ! $only_skill =~ ^[a-z0-9]+(-[a-z0-9]+)*$ ]]; then
  printf 'error: --skill must be a kebab-case skill name\n' >&2
  exit 2
fi
if ((!execute_behavioral)) && [[ -n $runner_dir || -n $only_skill ]]; then
  printf 'error: --runner-dir and --skill apply only with --execute-behavioral\n' >&2
  exit 2
fi
if [[ -n $runner_dir && (! -d $runner_dir || -L $runner_dir || ! -x $runner_dir/claude) ]]; then
  printf 'error: runner directory must be a real directory holding an executable claude: %s\n' \
    "$runner_dir" >&2
  exit 1
fi

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

workspace=$(mktemp -d "${TMPDIR:-/tmp}/skill-quality-gate.XXXXXX")
cleanup() {
  case $workspace in
    "${TMPDIR:-/tmp}"/skill-quality-gate.*) rm -R -- "$workspace" ;;
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
if ! python3 "$script_dir/skill_validation.py" --repository "$harness_work" \
  >>"$quick_log" 2>&1; then
  cat "$quick_log"
  printf 'error: standalone skill validation failed\n' >&2
  exit 1
fi
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

if ! node "$harness_work/scripts/run-evals.js" --min-rank1 "$min_rank1" >"$routing_log" 2>&1; then
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

execution_summary='model execution: not run'
execution_failed=0
if ((execute_behavioral)); then
  # Opt-in only: this spends model usage and needs the operator's own credentials.
  execution_log="$output_dir/tier3-execution.log"
  : >"$execution_log"
  if [[ -n $runner_dir ]]; then
    PATH="$(cd "$runner_dir" && pwd):$PATH"
    export PATH
  fi
  if ! command -v claude >/dev/null 2>&1; then
    printf 'error: --execute-behavioral needs the claude command on PATH or in --runner-dir\n' >&2
    exit 1
  fi
  executed_skills=0
  for skill_dir in "$harness_work"/skills/*; do
    skill_name=${skill_dir##*/}
    if [[ -n $only_skill && $skill_name != "$only_skill" ]]; then
      continue
    fi
    executed_skills=$((executed_skills + 1))
    if ! node "$harness_work/scripts/run-evals.js" --behavioral "$skill_name" \
      >>"$execution_log" 2>&1; then
      execution_failed=$((execution_failed + 1))
    fi
  done
  cat "$execution_log"
  if ((executed_skills == 0)); then
    printf 'error: no skill matched --skill %s\n' "$only_skill" >&2
    exit 1
  fi
  if [[ -d $harness_work/evals/results ]]; then
    mkdir -p "$output_dir/results"
    cp -R "$harness_work/evals/results/." "$output_dir/results/"
  fi
  executed_evals=$(grep -c ' expectations passed -> ' "$execution_log" || true)
  execution_summary="model execution: $executed_evals eval(s) graded across $executed_skills skill(s), $execution_failed skill(s) with a failed or ungraded eval"
fi

{
  printf 'harness revision: %s\n' "$resolved_revision"
  printf 'skills: %s\n' "$skill_count"
  printf 'case files: %s\n' "$case_count"
  printf 'behavioral dry-run plans: %s\n' "$planned_evals"
  printf '%s\n' "$execution_summary"
  if ((execution_failed)); then
    printf 'Skill quality gate FAILED: behavioral execution\n'
  else
    printf 'Skill quality gate passed\n'
  fi
} | tee "$summary_log"
if ((execution_failed)); then
  exit 1
fi
