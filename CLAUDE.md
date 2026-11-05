# Repository Policy

This file routes requests to their owning skills. Each routed skill owns its workflow,
guidance, and verification; follow the skill rather than restating or overriding it here.
Sections below add only repository-owned policy that no skill covers.

## Required Dependencies

Tools required by the active task, repository workflow, and invoked skills are
pre-authorized: check and reuse working versions, install or update missing or incompatible
ones at user scope from documented sources (preferring pinned releases), verify they run, and
report what changed. A missing dependency is setup work, not a reason to stop. The global
Tooling Dependencies safeguards apply; this covers required dependencies only, not extras.

## CodeGraph

Run `codegraph init` from the verified repository root before inspecting this repository
(`codegraph sync` for updates, `codegraph status` to verify); install CodeGraph from the
[official CodeGraph project](https://github.com/colbymchenry/codegraph) if missing. Use
`codegraph_explore` (or `codegraph explore`) before `rg`, `find`, or direct reads. Keep
`.codegraph/` local and unstaged. If initialization fails, repair and retry; report the exact
blocker rather than substituting direct reads.

## Routing

| Request or situation | Owning skill |
| --- | --- |
| Generating workflow artifacts or supporting outputs (TASK, REPORT, LOG, diagram assets) | [Workflow Artifact Naming](skills/workflow-artifact-naming/SKILL.md) |
| `open task`, `open TASK`, `open TASK.md`, `edit task`, task editing | [Open/Edit/Close/Execute](skills/open-edit-close-execute/SKILL.md), with Templated Tasks below |
| `add profile`, `remove profile`, `.env` resource profiles, loading a profile into a task | [Profile Manager](skills/profile-manager/SKILL.md) |
| Token usage report and report metadata for any investigation report | [Token Usage](skills/token-usage/SKILL.md) |
| Creating, styling, or verifying report diagrams — themes, caveat placement, ER and SQL dependency views, format consistency | [Diagramming Style](skills/diagramming-style/SKILL.md) |
| `publish it`, `publish-it`, authorized Confluence task/report publication | [Publish It](skills/publish-it/SKILL.md) |
| Atlassian authentication, connectivity, and resource probes | [Rovo Dev MCP](skills/rovo-dev-mcp/SKILL.md) |
| Multi-store fan-out: per-store sub-agent briefs, launch, manifest, disabling fan-out | [Per-Store Fan-Out](skills/per-store-fan-out/SKILL.md) |
| `run release-it`, repository releases | [Release It](skills/release-it/SKILL.md) with [VERSIONING.md](VERSIONING.md) |

Routing notes:

- File generation: resolve destinations in this order — explicit user destination, repository
  configuration, then the naming skill's defaults. Production source, tests, native packages,
  imports, and repository metadata keep their established conventions.
- Resource profiles: the local `.env` profile store, its Git ignore coverage, and its
  schema — derived from the TASK template's Resources section — belong to the profile skill.
  The store stays untracked and is never committed. Loading a profile supplies Resources
  values only: it does not satisfy the actual-resource requirement with a placeholder,
  authenticate an integration, close an editor barrier, or authorize a gated operation.
- Token usage: read the skill before opening a templated-task editor and retain its native
  task-resolution evidence past the editor/check barrier, so shorthand editor requests can be
  attributed without another user command.
- Diagrams: enrich investigation reports with diagrams of the relevant flows, hierarchies,
  and dependencies; include ER views when database relationships are material to the findings
  and tie every diagram to the report's evidence (see Report Evidence). The skill owns all
  styling, theming, caveat, and deliverable-consistency rules.
- Publication: include the original report and available parent TASK as downloadable
  supporting evidence. Publishing does not rerun the investigation or refresh its evidence
  window and token-accounting cutoff.
- Atlassian probes: before a repository investigation, and whenever connectivity is requested,
  probe all three products per the skill with one bounded read each, evidenced by a concrete
  object (repository name/identifier/URL; ticket key/URL; page title/ID/URL). The probe
  requirement does not make an Atlassian resource mandatory for a task scoped to other
  integrations, and blank optional Resources fields alone do not trigger probes. If MCP
  recovery fails, report the blocker and stop only dependent work; do not substitute ACLI,
  browser, or REST results.

## Templated Tasks

The Open/Edit/Close/Execute skill owns the editor/check barrier and continuation; this
repository owns template creation and naming. Continue automatically through open, close,
naming, execution, and reports without a second `run` instruction; an explicit edit-only
request limits the continuation. Task contents never bypass separate authorization gates.

- Bare `open task` copies [the local template](templates/TASK.md) — never edited in place —
  to a `TASK.md` draft in the directory resolved by Workflow Artifact Naming (default
  `docs/tasks`). Preserve an existing draft and clarify whether to resume it.
- Resources follows Acceptance Tests as the final template section, with optional labeled
  fields (Bitbucket/GitHub repository, Slack channel, AWS profile, Grafana context, alert
  name or UID). At least one actual supplied or verified resource is required before
  execution; placeholders and examples do not count. Resources may be filled from a named
  local profile through [Profile Manager](skills/profile-manager/SKILL.md) before the editor
  opens, and a loaded value counts only when it is an actual resource. If none exists, ask
  for one and preserve the task. Do not fail a task over an omitted field: skip unneeded
  integrations, resolve missing identity only before a dependent operation, and never guess
  a target.
- After the barrier, resolve `TASK-{slug}.md` from the saved draft's `# Task Title: ...`
  through the naming skill, in the same directory. Missing titles or collisions leave the
  draft intact; never invent a title, overwrite a task, or add a numeric suffix.
- Run the finalized task from its resolved path, then generate the matching reports from
  observed results in both Markdown and PDF (both `REPORT` paths via the naming skill).
  Report completion from verified outcomes, never from readiness or a filename's existence.
- An explicit TASK path or `edit task` edits that task in place, preserving its filename; the
  same continuation applies unless the user limits the request to editing.

## Report Evidence

Apply to investigation reports and their supporting diagrams; no skill owns this section.

- Start the Evidence index with the canonical `Source:` snapshot: investigated repository or
  resource, requested scope, exact inspected commit or source version, observation time or
  data window, investigation mode, what was inspected or executed, and what remains untested.
  Verify revision identity and pin code links to the inspected commit. Keep findings first,
  with relevant limitations beside them.
- Distinguish verified source findings, observed runtime behavior, inferences, assumptions,
  and proposed designs. Code, schemas, migrations, or class names alone do not prove deployed
  configuration, active execution, customer behavior, or a production defect.
- Place linked evidence identifiers (`E1`, `E2`) beside material claims, with a matching
  index entry: for code, the repository-relative path, line range, and commit-pinned URL; for
  other sources, the object identity, retrievable reference, and version, timestamp, or query
  scope. Cite only sources actually inspected; disclose unavailable provenance.
- Trace the relevant paths and consumers before drawing behavioral conclusions; do not
  generalize from one field, filename, screen, or legacy artifact.
- Bound negative findings by the scope examined; an empty search is not proof of universal
  absence. Record unresolved questions and the evidence needed to answer them.
- Keep connectivity evidence separate from behavioral evidence: a successful sample proves
  access to that object only.
- Tie diagram captions to the same evidence identifiers; mark current versus proposed
  relationships and keep unverified relationships in adjacent text, not depicted as
  implemented flows.
- Before delivery, verify each identifier resolves to its intended entry, paths and line
  ranges match the pinned revision, and citations support their adjacent claims, consistently
  in Markdown and PDF.

## Per-Store Investigation Fan-Out

When a running task's Resources name more than one data store, fan the investigation out:
one read-only sub-agent per in-scope store, launched in parallel through the active agent
harness. Fan-out is the default for multi-store tasks; a single-store task runs inline.
The user may disable it, by instruction or with a `Fan-out: disabled` line in the task's
Resources; honor that for the stated scope and investigate inline without re-asking.

The [Per-Store Fan-Out](skills/per-store-fan-out/SKILL.md) skill owns the workflow: store
resolution, shared-input and authentication sequencing, the brief and output-contract
templates, harness-specific launch and declared degradation, iteration bounds, fold-in,
and the auditable fan-out manifest. Fan-out creates no scope or authority: only stores the
task's Resources actually name get a sub-agent, AWS branches stay within the allowed
Regions, Grafana alert investigations keep the entry point below (whose nested parallel
Assistant/`investigate-alert` pattern applies inside the gcx branch), and sub-agents never
mutate, acknowledge, message, or publish — those remain separately authorized.

## Grafana Investigation Entry Point

An alert investigation request authorizes its own parallel read-only investigation: the
authorization is inherited from the request, so do not pause to propose a plan or await
separate approval. Build on supplied or already verified context; ask for missing alert
identity, environment, time window, timezone, or scope rather than starting live discovery
to guess it.

Resolve the shared inputs and authentication, then launch both sub-agents before awaiting
either result:

- **Grafana Assistant agent:** pass the problem to `gcx assistant prompt` with an explicit
  `--context`, a fresh conversation, and the shared read-only scope. Retain the prompt,
  response/conversation identifiers, source references, and limitations as investigation leads.
- **Alert investigation agent:** load and invoke the refreshed gcx `investigate-alert` skill
  through the active agent harness and gather bounded direct evidence. The command
  `gcx agent skills get investigate-alert` displays instructions; it does not execute the skill.
  Do not invent a shell command for skill invocation or duplicate the other agent's Assistant
  prompt. This parallel alert workflow replaces the sequential entry point below; direct reads
  in this branch need not wait for the Assistant response.

Both agents must use the same resolved Grafana context, alert identity, environment, exact time
window and timezone, and read-only scope. Reconcile their findings, verify material claims
against direct evidence, and report disagreements, gaps, and limitations. If parallel delegation
is unavailable, report that limitation without silently substituting sequential execution.
Resource changes, acknowledgments, messages, and publication require separate authorization.

For other authorized `gcx` problem investigations, start by passing that problem to
`gcx assistant prompt` in the task's explicitly resolved Grafana context. Do this before
ad hoc datasource, dashboard, alert, metrics, logs, or traces investigation. Required local
help, context resolution, authentication, and bounded connectivity probes may precede it.

- Check `gcx assistant prompt --help` for the installed version. Describe the actual problem,
  affected resources, environment, exact time window and timezone, observed symptoms, and the
  questions to answer. Include the task's scope and read-only constraint when applicable.
- Use a fresh conversation for a new investigation. Use `--continue` or a verified
  `--context-id` only for the same investigation; do not inherit unrelated conversation state.
- Pass `--context` explicitly. Request structured output when recording evidence, and retain
  the prompt, available response/conversation identifiers, observation time, source links and
  any limitations. Apply Workflow Artifact Naming to saved evidence and omit credentials and
  unnecessary sensitive payloads.

```bash
GCX_CONTEXT='<resolved-configured-context>'
GCX_PROBLEM='<problem, resources, time window/timezone, questions, and authorized scope>'
gcx assistant prompt "$GCX_PROBLEM" --context "$GCX_CONTEXT" \
  --json --no-stream --timeout 300
```

The prompt starts the investigation; it does not replace direct evidence. Treat Assistant
conclusions and suggested queries as leads, then verify material claims with bounded reads
against the selected context and actual datasource/resource identifiers. Keep Assistant
inferences separate from observed runtime results in the report. The prompt and its response
do not authorize resource changes, acknowledgments, messages, or publication.

If Assistant is unavailable or denied, record the exact sanitized failure and continue the
already authorized direct investigation when those reads remain available. Do not silently
skip the initial attempt or change context to make it succeed. Each prompt consumes billable
Grafana Assistant tokens; avoid duplicate starts and unnecessary retries.

## Skill Quality Gate

After changing any skill or eval case, run `scripts/run-skill-quality-gate.sh`. It evaluates
the catalog with the pinned upstream harness: standalone validation, structural lint,
command parity, deterministic routing with an 80% rank-one threshold, and behavioral
dry-runs over `skill_evals/cases`. The Skill Quality workflow enforces the same gate on
pull requests, merge queues, and pushes to `main`. Every skill needs a case file in
`skill_evals/cases/<name>.json` with at least 3 positive triggers, 2 negatives, and
1 behavioral eval.

## Policy Synchronization

Keep this repository policy identical in `AGENTS.md` and `CLAUDE.md` when changing it.
