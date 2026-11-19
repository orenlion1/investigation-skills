---
name: parallel-grafana-investigation
description: Handle any Grafana query request with two parallel read-only sub-agents — Grafana Assistant and direct gcx queries using relevant bundled agent skills — then reconcile and verify. Use when handling Grafana alerts, metrics and PromQL, logs and LogQL, traces and TraceQL, dashboards and datasource inventory, SLO health, Synthetic Monitoring, or other Grafana resource reads, including exact queries. Honor disabled Assistant and cost controls. Setup-only requests use gcx-cli; internal commands never recursively launch this workflow.
---

# Parallel Grafana Investigation

## Overview

For every user-requested Grafana query, launch a Grafana Assistant agent and a direct gcx
agent in parallel. Both answer the same request within the same resolved scope. An exact
query or inventory read stays that size; two methods do not authorize a broader investigation.
The repository's [Grafana Policy](../../AGENTS.md#grafana-policy) owns routing and authorization.
Within [per-store fan-out](../per-store-fan-out/SKILL.md), this pattern nests inside the
Grafana branch, including for non-alert requests.

Both agents use the [shared delegation contract](../per-store-fan-out/references/delegation-contract.md)
for launch modes, manifests, harness mechanics, degradation and leads versus findings.
This skill owns the two Grafana branches, their shared inputs and their reconciliation.

Delegating skills in this catalog share one delegation contract: copying any of them means copying the `per-store-fan-out` package too.

When part of an investigation, inherit its original request start and
[soft delivery budget](../open-edit-close-execute/references/investigation-delivery.md).
Reuse verified setup and evidence while preserving coverage and gates.

## When to Use

Use for user-requested Grafana telemetry queries, exact expressions, inventory listings,
resource reads, alert investigations, health checks and troubleshooting. Setup-only installation,
authentication or skill-refresh requests use [gcx-cli](../gcx-cli/SKILL.md) and do not start
Assistant. An explicitly requested resource read after setup uses this workflow.

Launch one pair per resolved Grafana request or existing Grafana store branch, not per command.
Internal authentication probes, metadata/datasource discovery, historical endpoint list/get reads,
verification queries and follow-ups remain with their existing owner; they never recursively
invoke this workflow. Preserve history-only endpoints' no-new-prompt restrictions and the
parent's delegation disable setting. A selected specialist skill supplies the direct method;
it does not replace this orchestration or widen the user's scope.

## Workflow

1. **Resolve shared inputs in the orchestrating session.** Use gcx-cli for required installation,
   bundle refresh, context resolution and authentication. Resolve one explicit context, the exact
   request/expression, target resources/datasources, filters, limits and output requirements,
   environment and read-only scope. Resolve an exact range or instant timestamp and timezone for temporal
   queries; for non-temporal inventory mark them not applicable rather than inventing a window
   or demanding alert/incident details. Ask only for missing inputs needed for this request;
   never guess the context through live discovery. The query request authorizes the read-only
   workflow without a separate plan-approval pause.
   Before launch, accept a parent-prepared `grafana-assistant-search` handoff under
   [Assistant matching](../rhyming-incident-search/references/assistant-search.md). Register the
   prospective branch with its original request, exact context/scope/shared block and unsent
   state. Only a compatible branch owns one combined initial prompt; retain separate endpoint
   children and manifest rows linked to its execution receipt. Do not broaden scope to combine
   requests. A late matching request does not automatically start another prompt.
2. **Launch both sub-agents before awaiting either result:**
   - **Grafana Assistant agent:** send the same request through `gcx assistant prompt` with
     explicit `--context`, a fresh conversation and the shared read-only scope. For an exact
     query, retain the expression, parameters and requested output; do not substitute an
     Assistant-generated query. Include matching in the initial prompt only when this branch
     owns the prepared compatible handoff. Retain the prompt, response/conversation identifiers,
     source references and limitations as leads. Endpoint consumers use the retained response.
   - **Direct gcx agent:** load and execute the relevant refreshed bundled skills through the
     active harness, then gather bounded direct evidence. Select by the requested operation:

     | Request | Bundled skill guidance |
     | --- | --- |
     | Alert firing, pending or flapping | `investigate-alert` |
     | Metrics, logs, traces or cross-signal diagnosis | `debug-with-grafana` and/or `gcx` |
     | Dashboard inspection or inventory | `manage-dashboards` |
     | SLO health or investigation | `slo-check-status` or `slo-investigate` |
     | Synthetic Monitoring health or failure | `synth-check-status` or `synth-investigate-check` |
     | Other resource reads or exact queries | Relevant current bundled skill, with `gcx` command discovery |

     This table is illustrative; inspect the refreshed bundle for the actual operation.
     `gcx agent skills get <name>` displays instructions; it does not execute them. Invoke
     those instructions through the harness, never an invented shell skill runner. Use
     dedicated gcx reads, preserve exact expressions and result limits, and enforce explicit
     context/window over examples in bundled guidance. Do not duplicate the Assistant prompt
     or wait for its result. This agent uses gcx and gcx agent skills only; it sends no
     Assistant prompt, including when the selected bundled guidance suggests one. Necessary
     independent reads can run concurrently inside this agent without new delegation pairs.
3. **Record the manifest.** Follow the shared contract, including degraded or Assistant-disabled
   runs. Account for the Assistant branch and the direct gcx branch with their observed agent
   identities and launch times, or nulls when never launched. Record which bundled skills the
   direct branch used. The report or response's Source snapshot cites the local manifest.
   When the requested output excludes prose or citations (for example values-only or JSON),
   put that Source snapshot and manifest reference in the retained local audit record instead,
   preserving the requested response format.
4. **Reconcile and verify.** Check that both agents used the same resolved inputs. Verify
   material claims against direct evidence and report disagreements, gaps and limitations.
   For an exact query, report its observed direct result; for a capped listing, disclose the
   cap without claiming exhaustive coverage. Do not substitute Assistant prose for query data.
   A successful connection is not query success; an empty result is not proof of health.

## Cost controls and failures

Grafana Assistant incurs additional cost and is enabled by default. Honor a user instruction
or `Grafana Assistant: disabled` in task Resources without re-asking: send no Assistant prompt,
launch only the direct gcx agent, and record the disabled branch as a configured limitation,
not a failure. When disabled, only gcx and the relevant gcx agent skills are invoked for the
Grafana query work; no Assistant call is allowed indirectly through a bundled skill either.
Disabling Assistant never disables the requested queries.

If Assistant is unavailable or denied, retain the exact sanitized failure and continue the
direct branch when its reads remain available; never silently skip an enabled Assistant attempt
or switch context to make it succeed. Avoid duplicate starts and unnecessary billable retries.
If parallel delegation is unavailable, disclose and record the actual degradation under the
shared contract rather than silently substituting sequential execution. Resource changes,
acknowledgments, messages and publication require separate authorization.

## Common Rationalizations

- "This is only a dashboard listing, so one agent is enough." Every requested Grafana
  resource read uses the pair unless Assistant or delegation is disabled or unavailable.
- "Wait for Assistant to choose a query." Direct reads start independently; exact user
  expressions are preserved.
- "The bundled skill recommends Assistant, so the direct branch can prompt too." Only the
  designated Assistant branch sends prompts; disabled means zero calls from every branch.

## Red Flags

- Non-alert queries bypassing the pair, or an inventory read turned into root-cause analysis.
- Differing expressions, contexts, filters, limits or applicable windows across briefs.
- Skill instruction display presented as execution, or recursive pairs for internal commands.
- An indirect Assistant call while disabled, or a completed run without its manifest.

## Verification

- Both branches launched before either was awaited, using identical resolved request and scope;
  any degradation is recorded with actual branch identities under the shared contract.
- The direct agent loaded the relevant refreshed bundled skills and executed actual gcx reads;
  printing skill instructions alone was not treated as execution.
- Exact expressions, resource filters, limits, output constraints and applicable windows survived
  both briefs unchanged; non-temporal reads did not gain an invented time window.
- Assistant and delegated output stayed leads until the orchestrator verified material claims.
  Direct observed results, empty results, denials and unavailable evidence remain distinct.
- A disabled Assistant sent zero prompts, including through direct-branch skill guidance;
  the direct gcx branch continued and both branches remain accounted for in the manifest.
- No internal command recursively launched another pair; historical endpoint and parent
  delegation restrictions remained intact.

For a human-readable explanation of the split, bundled skills and context loading, see
[README.md](README.md). It is supporting documentation, not a required runtime read.
