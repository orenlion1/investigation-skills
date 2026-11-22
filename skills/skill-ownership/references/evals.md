# Evals

An eval case is a skill's test. Each skill has one file at
`skill_evals/cases/<skill-name>.json`.

## Case shape

| Part | Minimum | Purpose |
| --- | --- | --- |
| `trigger.positive` | 3 prompts | Requests that must route to this skill |
| `trigger.negative` | 2 prompts, each with an `owner` | Near misses that belong to another skill in the catalog |
| `evals` | 1 behavioral eval | A prompt, the expected outcome, and explicit expectations |

A behavioral eval of kind `dialogue` grades the conversation. Kind `execution` grades what
the agent did in a throwaway workspace and needs fixture files under `skill_evals/fixtures/`.
Write expectations a grader can check against a transcript: observable behavior, not intent.

## The quality gate

```sh
skills/skill-ownership/scripts/run-skill-quality-gate.sh --repository .
```

It runs the pinned upstream harness: standalone validation, structural lint, command
parity, catalog-wide routing with a rank-one threshold (`--min-rank1`, default 80), and a
dry-run plan for every behavioral eval. A dry run plans the eval; it does not run a model.

## Executing against a model

```sh
skills/skill-ownership/scripts/run-skill-quality-gate.sh --repository . \
  --execute-behavioral --skill <skill-name>
```

Execution is optional and opt-in. It runs each behavioral eval through the headless
`claude` command with the operator's own access, grades every expectation, keeps the
grading files under `--output-dir`, and exits non-zero when an expectation fails. It spends
model usage, so it never belongs in a required check. `--runner-dir` substitutes another
`claude` executable; tests use a deterministic stub that contacts no model.
