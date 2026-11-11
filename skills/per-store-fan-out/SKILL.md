---
name: per-store-fan-out
description: Fan out multi-store or multi-repository investigations with read-only inspection sub-agents, shared resolved inputs, bounded iteration and auditable manifests. Use when Resources name multiple stores or multiple repositories, when per-store or per-repository parallel fan-out is requested, or when delegation must be disabled or degraded.
---

# Per-Store Fan-Out

## Overview

Delegate the gather step of a multi-store or multi-repository investigation: one read-only
sub-agent per in-scope store and a separate inspection unit for each configured repository, every agent briefed from the same resolved block, all launched before any
result is awaited, and their candidate evidence folded in by the orchestrating session
alone. The repository policy's
[Per-Store Fan-Out Policy](../../AGENTS.md#per-store-fan-out-policy) section
owns scope and authority; this skill owns activation, the disable switch and run conformity: store resolution, the brief and output contract templates, and the per-store
iteration bound.

The machinery every delegating skill in this catalog shares — the launch-mode vocabulary, the
manifest schema, the harness launch and continuation mechanics, the degradation rules, and the
rule that delegated output is leads until verified — lives in this package's
[shared delegation contract](references/delegation-contract.md). This skill does not restate it.

Delegating skills in this catalog share one delegation contract: copying any of them means copying the `per-store-fan-out` package too.

When this skill runs as part of an investigation, use the root
[soft delivery budget](../open-edit-close-execute/references/investigation-delivery.md)
from request receipt; carry its original start into this work and check it at control boundaries.
Reuse verified setup and shared evidence; preserve this skill's required coverage and gates.

## When to Use

Use when a running task's Resources name more than one data store or multiple repositories,
including repositories on the same provider, or when the user asks to
fan out, parallelize, or delegate per-store investigation, or when fan-out must be
disabled (`Fan-out: disabled` or an equivalent instruction) or degraded because parallel
delegation is unavailable. A single-store task with one repository stays inline. Fan-out
never widens scope: only named stores and configured repositories receive inspection units.

## Store Resolution

A store is an integration skill, not an object. Resolve the task's Resources to at most
one ordinary store sub-agent per integration. Repository inspection is resolved separately
below, so several repositories do not create duplicate ordinary store agents:

| Store | Integration skill | Covers |
| --- | --- | --- |
| Grafana | gcx-cli | Datasources, dashboards, alerts, metrics, logs, traces |
| AWS | aws-mcp | Resource state, CloudWatch, quotas, within allowed Regions |
| Atlassian | rovo-dev-mcp | Bitbucket, Jira and Confluence; repository code ownership follows the repository workflow below |
| Slack | slack-mcp | Named channels and threads |

Two or more resolved stores trigger store fan-out. Multiple configured repositories
independently trigger repository fan-out, even when all are on one provider. A single
repository keeps its existing inline source-inspection path; other named stores still follow
store fan-out. A repository plus its Jira ticket does not create two ordinary Atlassian units. A Grafana alert
investigation nests the [Parallel Alert Investigation](../parallel-alert-investigation/SKILL.md)
workflow inside the Grafana branch; the request itself carries that authorization.

## Repository resolution and scheduling

1. **Resolve effective resources once in the parent.** Consume all repeated Repo bullets,
   including a composed profile's complete list, through [Source Investigation](../source-investigation/SKILL.md).
   Current explicit user configuration overrides saved/profile-injected settings; helper command
   overrides, saved TASK values, profile fields and defaults follow [Profile Manager](../profile-manager/SKILL.md#user-configuration-takes-precedence).
   Freeze the selected environment, window, questions, constraints and effective resources before
   preparing any brief. A store or repository agent never reloads a profile over this block.
2. **Resolve each repository independently.** Identify provider, canonical repository, inspected
   revision and authorized provider-account/workspace scope. GitHub uses existing approved GitHub
   tooling; Bitbucket uses Rovo MCP. Do not route GitHub through an Atlassian branch. Resolve short
   names from verified provider context; ambiguous, unsupported and inaccessible entries retain an
   explicit gap. Coalesce aliases of the same resolved repository and record every configured alias
   against its single inspection owner; do not silently drop an input.
3. **Delegate each distinct configured repository when multiple are present.** This applies even
   when no other store is named. The parent schedules the repository batch alongside ordinary store
   and historical endpoint work using the [shared delegation contract](references/delegation-contract.md).
   It owns the complete resource-to-owner map and capacity allocation. Repository/store agents do
   not recursively schedule repositories. Use the [repository brief](references/repository-brief.md)
   with the same resolved block and output contract as the store briefs.
4. **Avoid duplicate inspection.** Remove assigned repository code queries from ordinary store
   briefs. Keep an Atlassian store unit only for remaining named Jira/Confluence or other non-code
   work; do not launch an empty store unit when repository inspections cover its entire workload.
   A single repository accompanying other store work has one inline or store-owned code-inspection
   owner, not an additional repository agent. Discovered dependencies stay under existing provider
   authorization and parent coordination; they do not automatically create extra repository units.
5. **Reconcile every outcome in the parent.** Correlate cross-repository call paths, inspect material
   evidence directly and retain commit-pinned citations/deployment gaps under Source Investigation.
   Provider recovery stays in the parent under its owning skill. Continue unaffected inspections
   when one repository fails. Follow up with the existing inspection owner, within the same
   three-round bound as store work. A disabled parent fan-out also disables repository delegation;
   investigation still proceeds under the shared contract's declared degradation rules.

Repository runs use a separate linked manifest under the shared contract. Add only repository-owned
fields: `repository`, `configured_entries`, `provider`, `provider_scope`, `inspected_revision`,
`inspection_owner`, `outcome` and `store_manifest` (absent when no ordinary store work remains).
Each distinct repository gets its own row; unresolved inputs retain their own gap rows. These rows,
the ordinary store manifest and the resource-to-owner map together cover every configured entry
without duplicate inspection. Keep authentication, tooling and actual reads distinct as for stores.
Do not claim an inspection succeeded merely because its profile loaded or its provider authenticated.

## Workflow

1. **Resolve shared inputs and repository ownership in the main session.** Apply user
   precedence and repository scheduling above. One environment, exact time window and
   timezone, concrete object identities, and each store's authentication through its own
   skill. Assess authentication independently of connection/tool availability. When credentials
   need renewal and the owning skill permits sign-in, start that flow even if its tool or MCP
   connection is missing; prepare the permitted connection setup alongside recovery. Before
   declaring a store blocked, attempt both applicable recovery paths or record the explicit
   blocker for each. Honor no-login instructions, credential ownership, Region limits, and
   separate approval gates; missing tools never authorize a fallback provider or weaker controls.
   Interactive sign-in never happens inside a sub-agent. A store that cannot authenticate
   blocks only its own branch; record the exact blocker and continue independent branches.
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
   the identical effective resolved block and the output contract verbatim; only the store,
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
integration with remaining ordinary store work. Repository rows live in their linked manifest;
a repository plus its Jira ticket never duplicates an ordinary Atlassian row. A store that
cannot authenticate blocks only its own branch; record the exact blocker and continue.

Each store row also records `authentication_status`, `tool_status`, and
`resource_read_status` separately. Each contains an observed outcome and its evidence or
sanitized blocker; distinguish pending, verified, failed, unavailable, and operator-disabled
work. A successful login does not verify a resource read, and a missing tool does not imply
authentication failed. Update these store-owned fields after recovery and retain unresolved
steps rather than collapsing them into a single unavailable result.

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
- Duplicate ordinary Atlassian store agents, duplicate repository inspection owners, or a
  branch for a resource the effective Resources never named.
- A report that presents sub-agent conclusions without orchestrator verification.

## Verification

- The manifest exists for the run, names every in-scope store, and its launch mode
  matches what actually happened.
- Every brief embeds the identical resolved block, and every branch result follows the
  output contract.
- Iterations are recorded, within the three-round bound, and inside the authorized scope.
- Authentication recovery and connection/tool setup were assessed independently for every
  store; each applicable attempt or explicit blocker is recorded separately from resource reads.
- The report separates per-store leads from orchestrator-verified findings and lists each
  failed branch as an untested area with its exact blocker.

- Every configured repository has a unique inspection owner or an explicit gap, including
  same-provider lists, with user overrides preserved in shared inputs.
- Store briefs exclude code inspection already assigned to repository units; disabled and
  capacity-limited execution follow the shared contract without losing repository coverage.
