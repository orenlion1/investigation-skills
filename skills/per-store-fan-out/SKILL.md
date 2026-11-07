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
run conform: store resolution, the brief and output contract templates, harness-specific
launch, iteration bounds, and the manifest that proves what happened.

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
   Reconcile its leads before the store batch; store agents never recursively repeat it.
   An unset field skips history search. Invalid configuration stops endpoint launches; failed
   providers block only their endpoints. Honor disabled parent fan-out by disabling nested
   endpoint delegation and recording that limitation. Ordinary inline store work may continue.
3. **Write one brief per store** from the templates in
   [references/sub-agent-brief.md](references/sub-agent-brief.md). Every brief carries
   the identical resolved block and the output contract verbatim; only the store,
   integration skill, and store-specific questions differ.
4. **Launch all briefs in one batch** before awaiting any result (see Harness Mechanics),
   and record the launch in the fan-out manifest.
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

## Harness Mechanics

- **Claude Code:** launch the batch as multiple Agent tool calls in a single message so
  the branches run concurrently; continue a branch with SendMessage to the same agent.
  Sequential Agent calls across messages are not a batch — if that is all the session can
  do, record the run as degraded.
- **Codex:** use native `spawn_agent` when exposed by the active harness. Launch independent
  briefs before waiting, retain each returned ID, and continue that same agent for follow-ups.
  With limited capacity, reserve the parent slot and launch concurrent waves; record the
  wave/capacity limitation. If native delegation is absent, run the same store briefs
  sequentially inline and record `sequential` mode. This existing store degradation does
  not satisfy Rhyming Incident Search's separate one-agent-per-endpoint contract.
- **Any harness without parallel delegation:** degrading to sequential execution is
  allowed only when it is declared — in the manifest and in the report's Source
  snapshot. Running inline ad hoc queries without briefs is not a degraded fan-out; it
  is a policy violation unless the user disabled fan-out.

## Fan-Out Manifest

Every fan-out run (including degraded and disabled runs) records a manifest as a LOG
artifact resolved through Workflow Artifact Naming (default destination `logs/`), using
the template in [references/sub-agent-brief.md](references/sub-agent-brief.md): stores in
scope, launch mode (`parallel`, `sequential`, or `disabled`), per-branch agent
identifiers and launch timestamps, the shared window and timezone, iteration rounds, and
per-branch blockers. The report's Source snapshot cites the manifest, so conformity is
auditable per run. The manifest stays local and untracked, like all investigation output.

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
