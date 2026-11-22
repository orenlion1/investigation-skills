# Parallel Grafana Investigation

Every user-requested Grafana query — alerts, exact queries, metrics, logs, traces, inventory,
SLOs, Synthetic Monitoring and other resource reads — uses two independent methods at the same
time: Grafana Assistant supplies leads, while a direct agent uses gcx and the relevant bundled
gcx agent skills to gather evidence. The orchestrator prepares their shared scope, reconciles
the results and verifies material claims before answering.

The runtime rules live in [SKILL.md](SKILL.md) and its owning contracts; this README explains
them and is not loaded automatically or required at runtime. Read it only on request.

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="../../diagrams/DIAGRAM-parallel-alert-investigation-dark.png">
  <img alt="Three shaded rows show the Grafana query setup, two parallel read-only agents, and evidence verification and reporting. The launch activity highlights parallel-grafana-investigation in orange." src="../../diagrams/DIAGRAM-parallel-alert-investigation-light.png">
</picture>

The launch activity highlights this skill in orange. Ovals are activities, boxes are
agent calls, solid arrows are handoffs, and dashed arrows invoke agents. The request
already authorizes read-only work; the visual pattern introduces no separate approval
step. This depicts the workflow, not evidence of an executed investigation. See the
[diagram source and regeneration notes](../../diagrams/DIAGRAM-parallel-alert-investigation.md).

## How the work is divided

The split is by investigation method. Both agents answer the same request within the
same authorized scope. An inventory read remains an inventory read; an exact query is
not expanded into open-ended root-cause analysis.

| Participant | Responsibility | Result |
| --- | --- | --- |
| Orchestrator | Resolve shared inputs and authentication, launch both branches, reconcile results and verify claims | Direct observed results and evidence-backed findings with gaps and limitations |
| Grafana Assistant agent | Submit the same request using `gcx assistant prompt`, a fresh conversation, explicit context and read-only constraints | Leads, references, conversation/response identifiers and limitations |
| Direct gcx agent | Load and execute relevant refreshed gcx agent skills through the active harness; run bounded dedicated gcx reads independently | Direct query data and resource evidence |

Where each rule lives:

| Topic | Owner |
| --- | --- |
| Shared inputs, concurrent launch, one pair per request, no recursive pairs | [SKILL.md](SKILL.md) Workflow step 1–2 and When to Use |
| Which bundled gcx skill the direct agent selects | [SKILL.md](SKILL.md) Workflow step 2 table; the refreshed bundle is authoritative |
| Manifest contents, Source snapshot citation, values-only or JSON output | [SKILL.md](SKILL.md) Workflow step 3 |
| Reconciliation, leads versus verified findings | [SKILL.md](SKILL.md) Workflow step 4 |
| Manifest schema, harness launching and continuation, capacity, degradation | [Shared Delegation Contract](../per-store-fan-out/references/delegation-contract.md) |
| Prepared `grafana-assistant-search` handoff sharing the initial prompt | [Assistant matching](../rhyming-incident-search/references/assistant-search.md) |
| Nesting inside a multi-store task's Grafana branch | [Per-Store Fan-Out](../per-store-fan-out/SKILL.md) |
| Installation, skill bundle location and refresh, context, authentication | [gcx-cli](../gcx-cli/SKILL.md#ensure-gcx-and-its-skills-are-ready) |

The Assistant branch uses `gcx assistant prompt`, rather than
`gcx assistant investigations create`; the two branches here are active-harness agents.
Parent delegation disable settings also apply to nested work.

## Grafana Assistant incurs additional cost and can be disabled

**Grafana Assistant incurs additional cost beyond ordinary Grafana usage.** It is
enabled by default. Disable it by instruction, or place this line in task Resources:

```text
Grafana Assistant: disabled
```

You can also save this choice in an existing resource profile with
`--field GRAFANA_ASSISTANT=disabled` through
[Profile Manager](../profile-manager/SKILL.md#grafana-assistant). Its schema accepts exact
`enabled`/`disabled`, defaults to `enabled`, and loads the Resources bullet above.
Explicit TASK settings override the profile; load-command field overrides take highest
priority. The setting alone adds no Grafana resource or query authorization.

**When disabled, only gcx and the relevant gcx agent skills are invoked for Grafana
query work.** Only the direct gcx agent runs; no Assistant prompt is sent, directly or
indirectly through bundled guidance. The setting is honored for its stated scope without
asking again and recorded as a configured limitation, not a failure; the requested queries
still proceed and both branches remain in the manifest. Unavailable Assistant, unavailable
parallelism and the read-only boundary are covered in
[SKILL.md](SKILL.md#cost-controls-and-failures).
