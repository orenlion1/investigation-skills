# Investigation delivery budget

This is the single timing contract for investigations, whether launched directly or through
the task editor. Reuse one root budget across setup and delegated work; a child never restarts
or extends it. Configuration and this contract grant no integration, mutation or publication
authority. These rules apply to investigations, not unrelated editing or software build work.

## Observe the budget

- Start at the observed receipt of the investigation request, before editor/setup/authentication,
  identity resolution or orchestration. Preserve that timestamp across continuations. If missing,
  state the boundary gap and use the first observed boundary as a lower bound; never invent it.
- The ten-minute (600-second) limit is SOFT. It includes setup, orchestration, essential provider,
  source/history evidence, report production and required QA. Finish is verified deliverable
  handoff, including required QA. A report-generation/accounting cutoff is a separate earlier
  endpoint when QA/delivery follows it; never present it as complete delivery duration.
- Use a monotonic timer for scheduling when available, with timezone-aware wall timestamps for
  provenance. Record clock discontinuities; do not fabricate durations. At each control boundary,
  including before/after provider calls, delegation waves and reporting/QA, check elapsed time.
  Bound tool waits and yield control often enough to surface progress; a blocked editor or auth
  wait is never a close signal. At 600 seconds, deliver the checkpoint on the next control
  opportunity even if the user/editor/authentication is still pending; do not run dependent work.
- Checkpoint contains verified essential findings, evidence links, remaining gaps/unavailable
  coverage, observed waits, remaining report/QA work and the reason for material continuation.
  Continue authorized necessary work without redundant approval. Explain a material extension
  or changed scope in further progress updates. Never hard-cancel, automatically fail, silently
  truncate evidence, or bypass safety, authorization, required coverage or quality gates.
- Record observed user, editor and authentication wait start/end pairs. Union overlapping waits
  before subtraction; per-kind totals may overlap and are not additive. Parallel children also
  overlap and their runtimes never sum to root wall time. Only when wait coverage is complete
  may total minus waits be called non-wait/agent-controlled wall time; it is not CPU/processing
  time. With partial coverage, report known waits and leave that split unavailable. Unknown
  phase measurements stay unavailable. End an ongoing wait at the observation only for the
  explicitly labeled observed-so-far interval; never claim the wait has ended.

Use the read-only Python standard-library helper at each boundary, substituting observed inputs:

```sh
python3 skills/open-edit-close-execute/scripts/investigation_budget.py --started "$INVESTIGATION_STARTED"
```

`--observed` accepts the current observation or actual handoff timestamp; otherwise the helper
reads the clock. Add `--wait KIND START END` for each observed user/editor/authentication wait.
`--wait-coverage complete` requires proven complete boundaries; the default is partial.
After delivering the soft checkpoint, supply its observed `--checkpoint` timestamp on subsequent
calls. The helper returns `checkpoint_due` and exits successfully past the limit: it does not
send the checkpoint, schedule work, cancel tools, or grant authority. The orchestrator must
send the findings/gaps checkpoint. Do not use the flag to suppress unexplained continuation.
Record request/checkpoint/handoff endpoints, observed wait coverage and any gaps with the report.

## Prioritize and reuse

Resolve cheap authoritative identities early (for example the named alert-channel message)
before broad capped discovery. Reuse the verified shared scope, resource probes, provider skills,
known identities and evidence within their validity window; refresh only when scope, credentials,
source version or observed state changes. Scope changes still get their owning checks.
Prepare minimal common briefs, share the root deadline, and fold candidate evidence into one
report; avoid duplicate prompts or discovery without a new question. Preserve the required
bounded provider/source/history coverage and disclose failed or capped queries.

Use existing graph styles, scripts and reporting machinery, supported readable layouts and
reusable templates. Avoid incident-specific rendering pipelines and cosmetic pagination loops;
fix a material readability/reference/overlap problem when required. Essential evidence, required
pattern graphs and meaningful QA remain mandatory. A soft checkpoint never makes unfinished QA
pass. Final delivery distinguishes completed findings from outstanding evidence/visual gaps.

## Report formats

Resolve the effective Generate PDF choice before PDF dependency setup, rendering or verification,
using [Profile Manager's contract](../../profile-manager/references/profile-store.md#generate-pdf).
For a finalized task use its validated saved Resources choice (explicit task > profile > absent T).
Reject invalid or duplicate values before report work; a toggle alone is never a resource.

Always produce verified Markdown with the required evidence and graphs. Record `Generate PDF: T`
or `Generate PDF: F` in the saved report's delivery metadata, its source revision/hash and the
produced/skipped formats. T generates and verifies a PDF companion from the same saved source,
including reference coverage and readable layout. F skips PDF rendering, PDF-only dependencies,
PDF-only reference checks and pagination checks; all Markdown/evidence/graph gates still apply.
A historical PDF is preserved, identified as historical and excluded from new companions and
current artifact links. Never delete it or infer freshness from the filename. Resolve only the
formats being produced through Workflow Artifact Naming, and read back those outputs.

Later authorized publication consumes that saved format decision and same-source inventory;
it does not refresh the investigation, timer or accounting cutoff. F needs no PDF attachment,
preview or download card. A changed task/profile cannot silently reinterpret a frozen report:
reconcile a conflict before dependent writes. Publication still requires separate authorization.
