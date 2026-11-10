---
name: token-usage
description: Derive investigation duration and token usage from explicitly selected local Codex conversation files, with verified task and turn boundaries and sanitized evidence. Use when reporting or checking investigation effort; this does not query billing or remote telemetry.
---

# Token Usage

## Overview

Use local conversation evidence to report an observed wall-clock interval and the tokens
recorded for that investigation. The bundled Python 3.8+ [collector](scripts/collect_token_usage.py)
uses only the standard library and does not require a lifecycle log or another checkout.

This skill owns token-usage collection, accounting, report presentation, and validation for
all repository reports. Other skills and policies should reference it to generate the token
usage report instead of maintaining separate formatting or accounting instructions.

## When to Use

- Reporting or checking investigation effort (duration and tokens) for an investigation report.
- Generating the token usage report and report metadata required by repository policy.
- Attributing editor-driven task turns after an editor/check barrier.

## Select the evidence

Read local conversation files only within the user's authorized scope. Identify the original
`run docs/tasks/TASK-{slug}.md` or explicit `edit task <task-path>` request, or a shorthand
`run task`, `open task`, or `edit task` request with verified task-resolution evidence,
and its native thread and turn IDs. The editor aliases include case and `.md` variants.
Read this contract before opening a templated task so its caller can retain the successful
resolution record after the editor/check barrier. Inspect subsequent
user turns to decide which continue that same investigation; repository cwd, filenames,
timestamps, copied policy, and a shared conversation alone do not prove task membership.
Keep unrelated requests and this accounting refresh outside a historical report's cutoff.

Select exact regular JSONL files, including contributing child threads. Child threads can be
reused across tasks and contain inherited parent messages: admit only their own responses
whose recorded parent-turn and root-turn ancestry reaches an admitted root turn. Do not infer
child ownership from an agent name or count a parent's cumulative counter plus child usage.

Measure elapsed wall time from the scoped investigation/report request through an explicit
report-generation cutoff, using timestamped native task records or other explicitly identified
observed boundaries. Preserve fractional seconds and timezone. Do not substitute file
timestamps, conversation lifetime, the first token row, summed parallel-agent runtimes, or
estimates. If an endpoint is unavailable, use `unavailable` for that field and any duration
that cannot be calculated from observed boundaries.

Retain the interval's included work, waits, pauses, and revision windows in supporting
evidence. Wall time includes waiting and gaps; it is neither active work nor model execution
time. When combining separate revision windows, record the calculation rule and excluded idle
gaps in that evidence. Editorial changes preserve the original investigation cutoff unless
the user requests an accounting refresh; record a refresh's own cutoff in supporting evidence
without implying a new investigation.

## Private manifest and collection

Create a private manifest outside committed paths. Use
[Workflow Artifact Naming](../workflow-artifact-naming/SKILL.md) to resolve saved supporting
artifacts before writes. Each proof uses its 1-based source line and the SHA-256 of
canonical JSON (`json.dumps(record, sort_keys=True, separators=(',', ':'), ensure_ascii=True)`
encoded as UTF-8). Source filenames and user text stay private; the output contains metadata.

```json
{
  "schema": "investigation-token-usage-bindings/v1",
  "task_artifact": "docs/tasks/TASK-example.md",
  "sources": [{"path": "/absolute/selected-session.jsonl", "thread_id": "native-thread-id"}],
  "bindings": [{
    "thread_id": "native-thread-id", "turn_id": "native-turn-id",
    "proof": {"source_line": 10, "sha256": "canonical-record-sha256"}
  }],
  "window": {
    "from": "2026-10-16T10:00:00Z", "to": "2026-10-16T10:10:00Z",
    "start": {"thread_id": "native-thread-id", "source_line": 8, "sha256": "canonical-record-sha256"},
    "end": {"thread_id": "native-thread-id", "source_line": 100, "sha256": "canonical-record-sha256"}
  }
}
```

The first binding proves an exact `run <task-path>` or `edit task <task-path>` user request.
For shorthand `run task`, `open task`, or `edit task` (case insensitive, optional `.md`),
also supply `task_resolution` on that binding: a proof object with `thread_id`,
`source_line`, and `sha256`. An editor command may be the first line of a user message
followed by inline requirements; a conflicting TASK filename in that message is rejected.
Select the native
`event_msg` / `item_completed` record for the successful finalization command in the same
thread and turn, after the request and no later than the report cutoff. Its item must be a
completed `CommandExecution` with exit code zero, an absolute `cwd` (or local `file:` URI),
and exactly one output line `Finalized: <absolute-task-path>` matching
`<cwd>/<task_artifact>`. During task finalization, retain that output line after the saved
task's exclusive creation and byte verification have succeeded. For a shorthand edit of an
existing task, emit it after the editor/check barrier and saved-target identity/read-back
verification; this resolves the existing task and does not authorize a rename.
For historical recordings only, a successful command whose entire output is the sole absolute
TASK path (with an optional final newline) is also accepted. Extra output, a different path,
or a failed, tampered, ambiguous, other-thread/turn, or out-of-window record is rejected.
An assistant message naming a path never substitutes for command evidence. Do not synthesize a past
record or use assistant prose, a user message, a failed command, or a different task as proof.
If this evidence is unavailable, preserve that limitation instead of assuming which task ran.

```json
"task_resolution": {
  "thread_id": "native-thread-id", "source_line": 20,
  "sha256": "canonical-completed-command-record-sha256"
}
```

For a later user revision, add another binding with `continuation_of` set to a previously bound
turn in that thread, after independently verifying that request continues the same task. This
explicit attribution is the agent's responsibility: a hash proves source identity, not intent.
The helper verifies the hashed user record, turn, continuity link, and absence of a conflicting
TASK filename. It never accepts injected AGENTS policy as a task request. List root bindings in
continuation order; child turns are admitted from their native lineage without invented bindings.

```sh
python3 -B skills/token-usage/scripts/collect_token_usage.py --manifest "$TOKEN_USAGE_MANIFEST"
```

`TOKEN_USAGE_MANIFEST` is the absolute path of the private verified manifest. Capture output
only to a resolved, authorized evidence destination. Source reads are bounded to 100 selected
files, 64 MiB each. Malformed/conflicting evidence fails closed with a sanitized error; repair
the selection or report unavailable evidence instead of relaxing validation.

## Interpret and retain accounting evidence

- Sum unique native `token_usage_record.usage` responses once, including identified compaction.
  Prefer those records over overlapping `token_count` notifications. Cached input is already
  inside input, reasoning output is already inside output, and total is input plus output.
- A request may start partway through a native turn that includes earlier editor/setup work.
  The collector uses the latest same-turn, same-lineage native counter before the window
  only to reconcile the first included response. It records that baseline's proof metadata,
  never adds its tokens, and preserves actual counter mismatches as coverage gaps. Legacy
  counter-only deltas still cannot cross the window start.
- When native usage is absent for an entire turn, the helper uses only nonnegative deltas
  between consecutive cumulative snapshots in that same turn. Missing baselines, resets,
  and deltas crossing the selected window's start remain gaps. Never sum snapshots, inherited
  history, or last-context counts as request usage.
- Retain total tokens, input/output/cached/reasoning breakdowns, root/child populations,
  contributing sessions/models, and coverage in supporting evidence. Null fields remain
  unavailable; partial coverage is an observed subtotal. Compaction is a subset, not an
  additional amount. Missing children and missing telemetry are not zero.
- Preserve incomplete-coverage status, missing sessions/counters/boundaries, and exclusions
  in that evidence. Keep separately billed Grafana Assistant or other service usage separate
  unless compatible units and non-overlap are verified. Never reuse historical tokens as a
  new investigation's usage or invent a command or task binding to satisfy the collector.
- Retain source/record hashes, native IDs, source-line references, exact cutoff, field coverage,
  and exclusions in sanitized supporting evidence. Do not copy prompts, tool payloads,
  encrypted content, credentials, or private source-store paths into deliverables. Preserve raw
  local transcripts outside Git and save only minimal accounting evidence with local report assets.
- Do not estimate cost or model execution time.

The helper currently supports Codex JSONL. Other hosts require a verified adapter; never
reinterpret another provider's counters using Codex semantics.

## Render the limited token usage report

Apply this presentation to every investigation report that uses this skill. Unless the user
explicitly requests another format, put a subheading directly below the report title in
each delivered format:

`{resource or subject} | {verified environment or source scope} | Investigation completed {Month D, YYYY} | Report processing duration: {duration or unavailable} | Total recorded tokens: {total or unavailable}`

Use verified identities and the investigation completion date. For source-only work, name
the actual source scope without inventing an environment. **Total recorded tokens** names
the observed population; do not relabel an incomplete subtotal as complete usage or billing.

End the report with **Token usage details**, containing only these elements in this order:

1. **Total recorded tokens**, identical to the subheading when one is rendered; input and
   output totals, plus cached input and reasoning output when available. Label cached input as an input subset
   and reasoning output as an output subset. Use `unavailable` when no defensible total exists.
2. **Report processing duration**, observed start, report-generation cutoff, and timezone.
   Keep the exact endpoints and resulting elapsed duration consistent.
3. A **session/model breakdown table** for the recorded population, with recorded tokens
   and response counts where available. Use `unavailable` for missing values; do not invent
   session identities, model names, or counts. This table is the end of the rendered section.

Omit Method, coverage/partial-coverage caveat prose, sourcing diagnostics, proof hashes and
source-line references, root/child or compaction accounting narratives, inclusion/exclusion
explanations, and extraction/refresh commentary. Remove them even when they previously
appeared before the table; do not move them into another part of the rendered report.
Keep this metadata in sanitized supporting evidence. Factual `unavailable` fields and
subset labels remain part of the compact presentation.

## Validate the deliverables

Update the canonical report source and regenerate each selected deliverable format under the
[delivery contract](../open-edit-close-execute/references/investigation-delivery.md#report-formats).
Generate PDF F skips PDF-only work; preserve historical PDFs without updating or claiming them.
Render the collector's numeric fields and session/model rows from the saved accounting data;
do not hard-code `unavailable` in a renderer after records have been recovered.
Read the saved Markdown and, when selected, PDF back: the final section and any subheading must agree across
formats on totals, duration, start/cutoff, and the recorded population. Compare displayed values and the
session/model table with the supporting evidence. Verify that the section ends at that table
and that omitted diagnostics have not reappeared elsewhere. When PDF is selected, check the rendered PDF for
readable labels and tables. A presentation change does not change historical accounting data.

## Provenance

The attribution, deduplication, compaction, legacy-delta, and duration rules follow Agent Tasks
at commit `f274648836361bfa05a62f86d88a0191a708632f`:
[analysis-processing.md](https://github.com/orenlion1/agent-tasks/blob/f274648836361bfa05a62f86d88a0191a708632f/skills/agent-task/references/analysis-processing.md)
and [collect_local_usage.py](https://github.com/orenlion1/agent-tasks/blob/f274648836361bfa05a62f86d88a0191a708632f/skills/agent-task/scripts/collect_local_usage.py).
This focused implementation adds investigation request/continuation bindings and observed
conversation endpoints. It does not invoke the Agent Tasks lifecycle or alter frozen logs.

## Common Rationalizations

- "Billing estimates are close enough." Usage derives only from explicitly selected local conversation files, never billing or remote telemetry.
- "The boundaries are obvious." Task and turn boundaries must be verified before accounting.
- "Raw transcripts can ship as evidence." Evidence is sanitized before it enters a deliverable.

## Red Flags

- Numbers sourced from memory, billing, or remote telemetry.
- Unverified task or turn boundaries behind the accounting.
- Unsanitized conversation content in the report or its evidence.

## Verification

- The collector ran over the explicitly selected conversation files with verified boundaries.
- The rendered report passed the checks in [Validate the deliverables](#validate-the-deliverables).
- Evidence identifiers resolve and contain no credentials or private payloads.

Delivery elapsed time and observed waits follow the [single investigation timing contract](../open-edit-close-execute/references/investigation-delivery.md). Keep the accounting cutoff distinct from verified handoff; never infer processing time from elapsed wall time.
