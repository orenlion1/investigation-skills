---
name: parallel-alert-investigation
description: Investigate a Grafana alert with two parallel read-only sub-agents — a Grafana Assistant prompt and gcx's investigate-alert instructions — sharing the same resolved context, alert identity, environment, exact time window, and timezone, then reconcile, verify, and report. Use when a Grafana alert investigation is requested, when the alert sub-agents must be launched or degraded, when Assistant leads must be reconciled with direct alert evidence, or when billable Grafana Assistant prompts must be disabled for cost control.
---

# Parallel Alert Investigation

## Overview

Investigate a Grafana alert by launching two read-only sub-agents in parallel — a Grafana
Assistant conversation and gcx's `investigate-alert` instructions — and folding their results
together under verification. The repository policy's
[Grafana Investigation Entry Point](../../AGENTS.md#grafana-investigation-entry-point) owns
the route here and the rule that the investigation request itself carries the
authorization; this skill owns the workflow. Within a multi-store
[per-store fan-out](../per-store-fan-out/SKILL.md), this whole pattern nests inside the
Grafana branch.

Both agents here are delegated agents, so the launch-mode vocabulary, the manifest schema, the
harness launch and continuation mechanics, the degradation rules, and the rule that agent output
is leads until verified come from the
[shared delegation contract](../per-store-fan-out/references/delegation-contract.md). This skill
owns the two alert branches, their shared resolved inputs, and their reconciliation.
Delegating skills in this catalog share one delegation contract: copying any of them means copying the `per-store-fan-out` package too.

## When to Use

Use for a Grafana alert investigation request: launching the parallel Assistant and
`investigate-alert` sub-agents, degrading when parallel delegation is unavailable, or
reconciling Assistant leads with direct alert evidence. Do not use for non-alert gcx
investigations (the policy's Assistant-first entry applies there through
[gcx-cli](../gcx-cli/SKILL.md)) or for multi-store delegation as such
([per-store fan-out](../per-store-fan-out/SKILL.md) owns that and invokes this skill for
its Grafana alert branch).

## Workflow

1. **Resolve shared inputs.** One Grafana context, alert identity, environment, exact time
   window and timezone, and read-only scope, plus gcx authentication, all in the
   orchestrating session. Ask for missing context rather than starting live discovery to
   guess it; the request already authorizes the investigation, so do not pause to propose
   a plan or await separate approval.
2. **Launch both sub-agents before awaiting either result:**
   - **Grafana Assistant agent:** pass the problem to `gcx assistant prompt` with an
     explicit `--context`, a fresh conversation, and the shared read-only scope. Retain
     the prompt, response/conversation identifiers, source references, and limitations as
     investigation leads.
   - **Alert investigation agent:** load and invoke gcx's refreshed `investigate-alert`
     instructions through the active agent harness and gather bounded direct evidence.
     The command `gcx agent skills get investigate-alert` displays those instructions; it
     does not execute them. Do not invent a shell command for the invocation or duplicate
     the other agent's Assistant prompt. Direct reads in this branch need not wait for the
     Assistant response.
3. **Record the manifest.** Every run records a fan-out manifest under the schema in the
   [shared delegation contract](../per-store-fan-out/references/delegation-contract.md),
   including a degraded run and a run whose Assistant branch is disabled. One row per branch:
   the Assistant branch and the alert investigation branch, each with its own agent identity
   and launch time, or null identity when it was never launched. The report's Source snapshot
   cites it. Two agents that record nothing leave a hole in exactly the audit trail the
   repository's Report Evidence rules exist to guarantee, so the manifest is required here on
   the same terms as any other delegating run.
4. **Reconcile and verify.** Both agents must have used the same resolved Grafana context,
   alert identity, environment, exact time window and timezone, and read-only scope.
   Reconcile their findings, verify material claims against direct evidence, and report
   disagreements, gaps, and limitations.

If parallel delegation is unavailable, report that limitation without silently
substituting sequential execution. If Assistant is unavailable or denied, record the exact
sanitized failure and continue the direct branch when those reads remain available; do not
silently skip the Assistant attempt or change context to make it succeed. Each prompt
consumes billable Grafana Assistant tokens and may incur additional fees; avoid duplicate
starts and unnecessary retries. Resource changes, acknowledgments, messages, and
publication require separate authorization.

**Disabling the Assistant.** Grafana Assistant prompts are enabled by default. When the
user disables them — by instruction or with a `Grafana Assistant: disabled` line in the
task's Resources — send no Assistant prompt: launch only the alert investigation agent,
and record the disabled branch in the report as a configured limitation, not a failure.
The setting exists for cost control; honor it for the stated scope without re-asking, and
never treat it as disabling the investigation itself.

## Common Rationalizations

- "The Assistant is just a summary layer, skip it and query directly." Both branches
  launch; a skipped Assistant attempt is recorded as a failure only when it actually
  failed.
- "Wait for the Assistant, then decide whether direct evidence is needed." The direct
  branch launches alongside the Assistant and never waits for its response.
- "`gcx agent skills get investigate-alert` printed the instructions, so that branch
  ran." That command only displays instructions; execution happens through the agent
  harness.
- "The Assistant answered confidently, so the finding is verified." Assistant conclusions
  are leads; material claims are verified against bounded direct evidence.
- "One Assistant prompt is cheap, even though it's disabled." Disabled means no prompts;
  the direct branch carries the investigation and the report records the configuration.

## Red Flags

- One branch launched and awaited before the other exists.
- Briefs or prompts that differ in context, alert identity, window, or timezone between
  the two agents.
- An invented shell command standing in for harness skill invocation.
- Assistant inferences presented as observed runtime results, or a silent context switch
  after a denial.
- Sequential execution without a reported limitation.
- A completed run with no fan-out manifest, including a degraded or Assistant-disabled run.
- An Assistant prompt sent while the user's configuration disables it, or a disabled
  branch reported as a failure.

## Verification

- Both agents ran with the identical resolved context, alert identity, environment,
  window, timezone, and read-only scope, and were launched before either was awaited.
- The Assistant prompt, response/conversation identifiers, and limitations are retained as
  leads, separate from observed runtime results in the report.
- Material claims trace to direct evidence; disagreements, gaps, and degradations are
  reported, not smoothed over.
- When the Assistant is disabled, no prompt was sent and the report records the branch as
  a configured limitation.
- A fan-out manifest exists for the run, carries one row per branch with its observed agent
  identity or an explicit null, and its launch mode matches what actually happened.
