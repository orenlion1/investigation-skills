---
name: skill-ownership
description: "Audit a repository against skill ownership and refactor it toward a routing table with one skill per capability. Use when adopting, checking, or syncing the ownership contract."
metadata:
  version: "0.1.7"
---

# Skill Ownership

## Overview

A repository's root files (`AGENTS.md`, `CLAUDE.md`) open with the ownership clause:

> This document routes requests to their owners. Each owner holds its workflow, guidance, and
> verification; follow the owner rather than restating or overriding it here. Everything else
> here is policy that no owner covers, and where such a policy limits an owner, the limit holds.

So every root-file section is one of three things: a **route** to an owning skill, **residual
policy** that no skill covers, or **workflow content** that belongs in a skill. This skill
audits a repository against that model, guides the refactor, and runs the checks that keep it
true. [The principle](references/principle.md) defines the three classes.

Everything runs through one script, from the repository root:

```sh
python3 skills/skill-ownership/scripts/ownership.py <command> --repository .
```

## When to Use

- Adopting the principle in a repository, or checking that a repository still obeys it.
- A root file is growing, or a rule is stated in more than one place.
- Adding, moving, or economizing a skill.
- Checking whether the carried copy is behind upstream, or updating it.
- Never for releasing a repository or for the work a routed skill owns.

Typical requests, in the order a new repository meets them:

| Ask the agent | Runs | When |
| --- | --- | --- |
| "Adopt skill ownership from https://github.com/orenlion1/skill-ownership in this repository" | [Adopt](#adopt) | Once, while the repository carries no copy |
| "Audit this repository against skill ownership" | `audit` | Before a refactor, and after root files change |
| "Refactor the root files into a routing table" | [Refactor](#refactor) | The audit found workflow in a root file |
| "Run the skill ownership checks" | `check` | Before every pull request, and in CI |
| "Is our skill-ownership copy up to date?" | `sync` | Periodically, or when a release is announced |
| "Update skill ownership to the latest release" | `sync --apply` | `sync` exited 3 |

## Adopt

Use once, when the repository does not carry this skill yet. The script is not in the
target at that point, so run it from a full clone of the upstream (sync reads its release
tags). From the target repository's root:

```sh
git clone https://github.com/orenlion1/skill-ownership.git ../skill-ownership
python3 ../skill-ownership/skills/skill-ownership/scripts/ownership.py sync \
  --repository . --apply --upstream ../skill-ownership \
  --upstream-url https://github.com/orenlion1/skill-ownership
```

It copies the latest release into `skills/skill-ownership/` and writes
`policy/skill-ownership-pin.json`; add `--to <version>` for an older release. Next, add a
routing row for this skill to the root files so agents find it, then audit. Until a root
file exists `audit` stops with an error, and until `policy/root-contract.json` exists
`check` fails the root contract: both are expected before the refactor.

## Audit

`audit` is read-only: section classes, routing gaps, size, links and naming findings
(`--format json` for tools). Review each section's proposed class before acting.
Read [naming](references/naming.md) to evaluate names and advisories.

## Refactor

Follow [the refactor workflow](references/refactor.md) under the target repository's own
authorization. In short: add the clause, build the routing table, move each workflow section
into the skill that owns it, keep only limits in the root file, then add the policy files
from `templates/policy/` and raise their minimums to the real counts.

## Checks

`check` runs every check and prints one line each. An absent optional policy reports
`not configured`; a malformed one fails closed. The root contract and the downstream pin are
always required. [Policy schemas](references/policy-schemas.md) describes each file.

Keep always-loaded text small with the guardrails in
[economization](references/economization.md): `ratchet --record` admits deliberate growth,
and `preserve` proves a rewrite lost no command, flag, path or bound.

## Sync

`sync` is read-only by default: it reports the carried release, the latest release, what
changed between them, and any undeclared drift (exit 0 current and clean, 3 behind, 4
drift). `sync --apply` replaces the carried copy and updates the pin together.
[Sync](references/sync.md) covers adoption, local adaptations, and what sync never touches.

## Evals

Every skill needs an eval case. [Evals](references/evals.md) covers the case shape, the
quality gate, and optional model execution.

## Common Rationalizations

| Rationalization | Reality |
| --- | --- |
| "Allowlist the section so the check passes." | A section that holds steps is workflow; it moves to its owning skill and the root file keeps a route. |
| "Record a bigger baseline; the skill needed the text." | Detail a reader rarely needs belongs in a reference; record growth only when always-loaded text earns it. |
| "The audit said residual policy, so it stays." | The class is a proposal. A rule that tells the reader how, not what is limited, is workflow whatever the heuristic said. |

## Red Flags

- A root-file section that tells the reader how to do something rather than who owns it.
- A skill with no routing row, or a routing row with no skill.
- A policy minimum lowered, or a check removed, to make a run pass.
- A rule restated in the root file "for convenience".

## Verification

- `ownership.py check` passes, and no check the repository relies on reports `not configured`.
- The root files are byte-identical and open with the clause.
- After a sync, the pin and the carried `metadata.version` name the same release.
- A refactor's `preserve` run reports no lost token, or every removal is declared with a reason.
