---
name: token-usage
description: "Derive an investigation's duration and token usage from explicitly selected local Codex conversation files, with verified task and turn boundaries and sanitized evidence. Use when reporting or checking investigation effort. Does not query billing or remote telemetry."
---

# Token Usage

## Overview

Use local conversation evidence to report an observed wall-clock interval and the tokens
recorded for that investigation. The bundled Python 3.8+ [collector](scripts/collect_token_usage.py)
uses only the standard library and does not require a lifecycle log or another checkout. It
supports Codex JSONL; other hosts require a verified adapter, and another provider's counters
are never reinterpreted using Codex semantics.

This skill owns token-usage collection, accounting, report presentation, and validation for
all repository reports. Other skills and policies reference it instead of maintaining separate
formatting or accounting instructions.

[accounting-evidence.md](references/accounting-evidence.md) holds the manifest schema, proof and
rejection rules, validation codes, counter reconciliation and provenance. Read it before
building or repairing a manifest.

## When to Use

- Reporting or checking investigation effort (duration and tokens) for an investigation report.
- Generating the token usage report and report metadata required by repository policy.
- Attributing editor-driven task turns after an editor/check barrier.

## Select the evidence

Read local conversation files only within the user's authorized scope. Identify the original
`run docs/tasks/TASK-{slug}.md` or explicit `edit task <task-path>` request, or a shorthand
`run task`, `open task`, or `edit task` request (case and `.md` variants included) with verified
task-resolution evidence, and its native thread and turn IDs. Inspect subsequent user turns to
decide which continue that same investigation; repository cwd, filenames, timestamps, copied
policy, and a shared conversation alone do not prove task membership. Keep unrelated requests
and this accounting refresh outside a historical report's cutoff.

Read this contract before opening a templated task so its caller can retain the successful
resolution record after the editor/check barrier. That record is a completed command, exit code
zero, whose only output line is `Finalized: <absolute-task-path>`. During task finalization,
retain that line after the saved task's exclusive creation and byte verification have succeeded.
For a shorthand edit of an existing task, emit it after the editor/check barrier and saved-target
identity/read-back verification; this resolves the existing task and does not authorize a rename.

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

Create a private manifest outside committed paths, following the
[manifest reference](references/accounting-evidence.md#manifest). Use
[Workflow Artifact Naming](../workflow-artifact-naming/SKILL.md) to resolve saved supporting
artifacts before writes. Every manifest must satisfy these rules:

- Each proof is a 1-based source line plus the SHA-256 of the record's canonical JSON.
- The first binding proves the exact `run <task-path>` or `edit task <task-path>` user request.
  A shorthand request also needs a `task_resolution` proof of the `Finalized:` command record.
- Request proofs select the canonical `response_item` with `role: user`, not the adjacent
  `UserMessage` completion event. Never repair a failed hash by inventing a user record.
- A later user revision is another binding whose `continuation_of` names a previously bound
  turn in that thread, added only after independently verifying that it continues the same
  task. A hash proves source identity, not intent.
- `expected_threads` is an explicit list of independently verified contributing thread IDs,
  including roots and children. Missing selected sources become `expected_source_missing`
  coverage gaps; every supplied child still needs native ancestry.
- An assistant message naming a path never substitutes for command evidence. Do not synthesize a
  past record or use assistant prose, a user message, a failed command, or a different task as
  proof, and never invent a command or task binding to satisfy the collector. If this evidence
  is unavailable, preserve that limitation instead of assuming which task ran.

```sh
python3 -B skills/token-usage/scripts/collect_token_usage.py --manifest "$TOKEN_USAGE_MANIFEST"
```

`TOKEN_USAGE_MANIFEST` is the absolute path of the private verified manifest. Capture output
only to a resolved, authorized evidence destination. Malformed/conflicting evidence fails closed
(exit 1, sanitized JSON diagnostic with a fixed `code` on stderr, no accounting JSON on stdout);
see the [limits and codes](references/accounting-evidence.md#collector-limits-and-diagnostics).
Repair the selection or report unavailable evidence instead of relaxing validation.

## Observe the report cutoff

A native endpoint still requires an exact timestamp match. If a future report will finish
between native events, record the current cutoff once at the accounting freeze, using the
[checkpoint recorder](scripts/record_accounting_cutoff.py):

```sh
python3 -B skills/token-usage/scripts/record_accounting_cutoff.py \
  --task-artifact "$TASK_ARTIFACT" --thread-id "$ROOT_THREAD_ID" --turn-id "$ROOT_TURN_ID" \
  --output "$CUTOFF_EVIDENCE"
```

Resolve `CUTOFF_EVIDENCE` to a new absolute private evidence path with existing real parent
directories. The recorder prints its raw-byte SHA-256, path and exact `observed_at`. Copy that
timestamp to `window.to`; use `{ "kind": "checkpoint", "path": "/absolute/cutoff.json", "sha256": "..." }`
for `window.end`. ID requirements and collection checks are in the
[checkpoint reference](references/accounting-evidence.md#checkpoint-cutoff-verification).

This observes a present boundary; it cannot restore a missing historical observation. Never run
it to fabricate a past cutoff, replace a frozen timestamp with now, or round a cutoff to the
nearest native event. Preserve a historical mismatch as the precise validation blocker until
an authentic original boundary source can be supported. Publication preserves the cutoff.

## Interpret and retain accounting evidence

- Sum unique native `token_usage_record.usage` responses once, including identified compaction.
  Prefer those records over overlapping `token_count` notifications. Cached input is already
  inside input, reasoning output is already inside output, and total is input plus output.
- Never sum snapshots, inherited history, or last-context counts as request usage. Baseline
  and cumulative-snapshot handling is in
  [counter reconciliation](references/accounting-evidence.md#counter-reconciliation).
- Retain total tokens, input/output/cached/reasoning breakdowns, root/child populations,
  contributing sessions/models, and coverage in supporting evidence. Null fields remain
  unavailable; partial coverage is an observed subtotal. Compaction is a subset, not an
  additional amount. Missing children and missing telemetry are not zero.
- Preserve incomplete-coverage status, missing sessions/counters/boundaries, and exclusions
  in that evidence. Keep separately billed Grafana Assistant or other service usage separate
  unless compatible units and non-overlap are verified. Never reuse historical tokens as a
  new investigation's usage.
- Retain source/record hashes, native IDs, source-line references, exact cutoff, field coverage,
  and exclusions in sanitized supporting evidence. Do not copy prompts, tool payloads,
  encrypted content, credentials, or private source-store paths into deliverables. Preserve raw
  local transcripts outside Git and save only minimal accounting evidence with local report assets.
- Do not estimate cost or model execution time.

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
[delivery contract](../investigation-delivery/references/delivery-contract.md#report-formats).
Generate PDF `disabled` skips PDF-only work; preserve historical PDFs without updating or claiming them.
Use the [shared renderer](scripts/render_token_usage.py) for the saved successful collector JSON:

```sh
python3 -B skills/token-usage/scripts/render_token_usage.py \
  --accounting "$ACCOUNTING_EVIDENCE" --format json \
  --subject "$REPORT_SUBJECT" --scope "$VERIFIED_SCOPE" --completed "$COMPLETION_DATE"
```

The date is the verified investigation completion date in `YYYY-MM-DD` form. With metadata
arguments, JSON contains `subheading` and `details`; put the former directly under the title and
the latter at the end of the canonical report. Without metadata arguments the helper renders only
details (`subheading: null`). Markdown output is also available. Reuse these same sections when
regenerating selected formats, then apply the owning delivery and evidence checks.

- The renderer reconciles response/session totals and duration before rendering. A successful
  partial collection displays its recorded subtotal, keeping coverage diagnostics in supporting
  evidence. Empty telemetry remains unavailable.
- A failed collector diagnostic or malformed/conflicting accounting file is rejected with
  nonzero exit and sanitized stderr, never converted into a successful report with permanent
  null values. Save that failure separately; repair and recollect before rendering recovered
  usage.
- A schema check cannot authenticate an arbitrary hand-authored JSON file: retain the
  successful collector receipt and original evidence proofs.
- Render the collector's numeric fields and session/model rows from the saved accounting data;
  do not hard-code `unavailable` in a renderer after records have been recovered.

Read each selected report format back: the final section and any subheading must agree across
formats on totals, duration, start/cutoff, and the recorded population. Compare displayed values and the
session/model table with the supporting evidence. Verify that the section ends at that table
and that omitted diagnostics have not reappeared elsewhere. When PDF is selected, check the rendered PDF for
readable labels and tables. A presentation change does not change historical accounting data.

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

Delivery elapsed time and observed waits follow the [single investigation timing contract](../investigation-delivery/references/delivery-contract.md). Keep the accounting cutoff distinct from verified handoff; never infer processing time from elapsed wall time.
**Report processing duration** is wall time from request to accounting cutoff, not
agent-controlled time; describe it as wall time. With partial wait coverage, report only the observed
waits and leave non-wait (processing) time and unmeasured phase timings `unavailable`.

When declining or planning accounting, say what reaches the report: the subheading and
**Token usage details** only, with sanitized supporting evidence and no prompts, tool payloads
or credentials. When planning a repair, also state that a collector failure (such as a cutoff
mismatch) is saved as a failure, distinct from unavailable or partial telemetry, and that
recovered totals and session/model rows render only from saved successful collector JSON.
