---
name: per-store-fan-out
description: Fan a multi-store investigation out into one read-only sub-agent per in-scope data store, with shared resolved inputs, templated briefs, batched parallel launch, bounded iteration, and an auditable fan-out manifest. Use when a task's Resources name more than one data store, when a per-store or parallel multi-store investigation is requested, or when fan-out must be disabled or degraded to sequential execution.
---

# Per-Store Fan-Out

## Overview

Delegate the gather step of a multi-store investigation: one read-only sub-agent per
in-scope store, every agent briefed from the same resolved block, all launched before any
result is awaited, and their candidate evidence folded in by the orchestrating session
alone. The repository policy's
[Per-Store Investigation Fan-Out](../../AGENTS.md#per-store-investigation-fan-out) section
owns the default-on rule and its disable switch; this skill owns the mechanics that make a
run conform: store resolution, the brief and output contract templates, and the per-store
iteration bound.

The machinery every delegating skill in this catalog shares — the launch-mode vocabulary, the
manifest schema, the harness launch and continuation mechanics, the degradation rules, and the
rule that delegated output is leads until verified — lives in this package's
[shared delegation contract](references/delegation-contract.md). This skill does not restate it.

Delegating skills in this catalog share one delegation contract: copying any of them means copying the `per-store-fan-out` package too.

## When to Use

Use when a running task's Resources name more than one data store, when the user asks to
fan out, parallelize, or delegate per-store investigation, or when fan-out must be
disabled (`Fan-out: disabled` or an equivalent instruction) or degraded because parallel
delegation is unavailable. Do not use for a single-store task, and do not let fan-out
widen scope: only stores the task actually names get an agent.

## Store Resolution

A store is an integration skill, not an object. Resolve the task's Resources to at most
one sub-agent per integration:

| Store | Integration skill | Covers |
| --- | --- | --- |
| Grafana | gcx-cli | Datasources, dashboards, alerts, metrics, logs, traces |
| AWS | aws-mcp | Resource state, CloudWatch, quotas, within allowed Regions |
| Atlassian | rovo-dev-mcp | Bitbucket, Jira, and Confluence together, one agent |
| Slack | slack-mcp | Named channels and threads |

Two or more resolved stores trigger fan-out; exactly one runs inline through its own
skill. A repository plus its Jira ticket is one Atlassian store, not two. A Grafana alert
investigation nests the [Parallel Alert Investigation](../parallel-alert-investigation/SKILL.md)
workflow inside the Grafana branch; the request itself carries that authorization.

## Workflow

1. **Resolve shared inputs in the main session.** One environment, exact time window and
   timezone, concrete object identities, and each store's authentication through its own
   skill. Interactive sign-in never happens inside a sub-agent. A store that cannot
   authenticate blocks only its own branch; record the exact blocker and continue.
2. **Invoke historical search once in the parent when configured.** Consume the selected
   profile's validated endpoint resources via [Profile Manager](../profile-manager/SKILL.md),
   then invoke [Rhyming Incident Search](../rhyming-incident-search/SKILL.md) once with the
   shared question/environment/windows. It owns one read-only sub-agent per endpoint,
   including same-store endpoints, parallel capacity waves, and a separate endpoint manifest.
   Reconcile its leads in the parent; store agents never recursively repeat it.
   Prepare historical requests before the store batch, but do not await matching results
   before their designated Assistant owner is scheduled.
   Before any Assistant prompt starts, prepare its handoff under
   [Assistant matching](../rhyming-incident-search/references/assistant-search.md). Register the
   prospective Grafana Assistant branch with exact scope and both windows so the combined
   initial prompt has one owner. Launch endpoint work and store work with linked execution
   receipts; do not wait for historical leads before scheduling their unsent Assistant owner.
   Preserve every endpoint child/row, honor disabled Assistant and never broaden scope to share.
   An unset field skips history search. Invalid configuration stops endpoint launches; failed
   providers block only their endpoints. Honor disabled parent fan-out by disabling nested
   endpoint delegation and recording that limitation. Ordinary inline store work may continue.
3. **Write one brief per store** from the templates in
   [references/sub-agent-brief.md](references/sub-agent-brief.md). Every brief carries
   the identical resolved block and the output contract verbatim; only the store,
   integration skill, and store-specific questions differ.
4. **Launch all briefs in one batch** before awaiting any result, through the mechanics in
   the [shared delegation contract](references/delegation-contract.md), and record the launch
   in the fan-out manifest it defines.
5. **Iterate within bounds.** Route a follow-up by continuing that store's existing
   sub-agent, never by spawning a fresh one. A finding in one store becomes the next
   query in another. Stop after three follow-up rounds without convergence, or whenever
   an iteration would widen the authorized scope, window, or Regions — both return to the
   user instead.
6. **Fold in, in the orchestrating session only.** Relate returned evidence on the shared
   timeline, verify material claims directly when they are load-bearing, report
   disagreements between stores explicitly, and write the report under the repository's
   Report Evidence rules. Sub-agent output is leads, never verified findings.

Sub-agents never mutate, acknowledge, message, or publish; those stay separately
authorized with the orchestrating session.

## Manifest and Store Branches

Every fan-out run records a manifest under the schema in the
[shared delegation contract](references/delegation-contract.md), including a degraded or
disabled run. The report's Source snapshot cites it, so conformity is auditable per run, and it
stays local and untracked like all investigation output.

This skill adds only what is specific to stores: each branch row carries `store` and
`integration_skill` beside the contract's own fields, and at most one row exists per resolved
integration — a repository plus its Jira ticket is one Atlassian row, not two. A store that
cannot authenticate blocks only its own branch; record the exact blocker and continue.

## Common Rationalizations

- "The harness can't parallelize, so the fan-out rules don't apply." Degradation changes
  the launch mode, never the briefs, the output contract, or the manifest.
- "The Grafana results will tell us whether AWS is worth querying." Launch order is not a
  triage tool; all in-scope branches launch before any result is awaited.
- "Widening the window one hour is still the same investigation." Scope, window, and
  Region changes return to the user; iteration happens inside the resolved bounds.
- "The sub-agent confirmed it, so it's verified." Sub-agent output is a lead; material
  claims are verified by the orchestrating session against retrievable evidence.

## Red Flags

- Inline store queries during a multi-store task with no manifest and no disable
  instruction.
- Briefs that differ in window, timezone, environment, or constraints between stores.
- A fresh sub-agent spawned for a store that already has one.
- More than one Atlassian agent, or any agent for a store the Resources never named.
- A report that presents sub-agent conclusions without orchestrator verification.

## Verification

- The manifest exists for the run, names every in-scope store, and its launch mode
  matches what actually happened.
- Every brief embeds the identical resolved block, and every branch result follows the
  output contract.
- Iterations are recorded, within the three-round bound, and inside the authorized scope.
- The report separates per-store leads from orchestrator-verified findings and lists each
  failed branch as an untested area with its exact blocker.
