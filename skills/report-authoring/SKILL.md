---
name: report-authoring
description: "Structures and verifies an investigation report before delivery: a key-findings-first layout with a proposed-remediation table and headline graphs, the Evidence index and Source snapshot, E1/E2 citations, verified-versus-inferred labels, bounded negative findings, and evidence-backed data pattern graphs. Use when writing, restructuring, citing, or checking an investigation report."
---

# Report Authoring

## Overview

Every investigation report and its supporting diagrams pass this skill before delivery. It
owns how the report is laid out and what its evidence record must contain: the
key-findings-first layout, the Evidence index, the canonical `Source:` snapshot, citation
identifiers, the verified/inferred distinction, negative-finding bounds, and the requirement
that every reported data pattern is supported by an evidence-backed graph.

[Diagramming Style](../diagramming-style/SKILL.md) owns visual styling, theming, captions and
rendering checks; this skill owns that the graphs exist, match the evidence and sit where the
layout puts them.

## When to Use

- Assembling the Evidence index and `Source:` snapshot for an investigation report.
- Placing or verifying `E1`/`E2` citation identifiers beside report claims.
- Checking a report's evidence discipline, citations, or graph coverage before delivery.
- Deciding whether a finding is verified, observed, inferred, assumed, or proposed.
- Writing a new investigation report, or restructuring one so its key findings, proposed
  remediation and graphs come first.

## Report Layout

Follow [the report layout](references/report-layout.md) for every investigation report. Assume
the reader stops after the first fifth: open with the title, then Key findings holding the
bottom line, a proposed-remediation table, an evidence-status table, the headline graphs and
the validation gate, in that order, with supporting detail below. Nothing in the opening is
new: each claim restates the detail with the same citation and the same qualification. Use
the reference's skeleton for a new report and its checklist before delivery.

- Each remediation row says whether it is proposed, implemented or validated, and names the
  gate that would confirm it.
- Every opening claim, however short, carries the same evidence identifiers as the detail it
  restates.
- To restructure an existing report, edit it: move text verbatim, link each detail section to
  a graph that moved, renumber figures in order of appearance, measure where the opening ends
  in every selected format, regenerate those formats, and record the restructure in the
  continuation record.
- A revision or publication note never goes above the title. Record what changed in the
  continuation record, and hand page composition and the version message to
  [Publish It](../publish-it/SKILL.md), which owns both.

## Evidence Index

- Start the Evidence index with the canonical `Source:` snapshot: investigated repository or
  resource, requested scope, exact inspected commit or source version, observation time or
  data window, investigation mode, what was inspected or executed, and what remains untested.
  Verify revision identity and pin code links to the inspected commit. Keep findings first,
  with relevant limitations beside them.
- Place linked evidence identifiers (`E1`, `E2`) beside material claims, with a matching
  index entry: for code, the repository-relative path, line range, and commit-pinned URL; for
  other sources, the object identity, retrievable reference, and version, timestamp, or query
  scope. Cite only sources actually inspected; disclose unavailable provenance.

## Reference completeness

Follow [the reference-completeness contract](references/reference-completeness.md) before
report delivery and pass its helper gate for every delivered Markdown, PDF and HTML artifact.
Resolve selected report formats through the [delivery contract](../open-edit-close-execute/references/investigation-delivery.md#report-formats) first. Disabled formats skip their tooling and checks; evidence and graphs pass in every selected output.
Inventory every material incident, investigation, backing chat, conversation and cross-report
evidence reference at its point of use: reconciliation prose, coverage tables and evidence-index
entries all count. A working link elsewhere, attachment hash or report-title link never satisfies
an unlinked occurrence. For each unlinked occurrence, report its location and the
destination derived from its source, or say the provenance is unavailable; a matching authored
link is not proof the destination opens. Register source-derived identities and visible aliases, review the full
source for omitted references, and retain occurrence-level diagnostics and separate unique-target
counts. Unavailable provenance and unverified navigation remain explicit incomplete results.

## Evidence Discipline

- Distinguish verified source findings, observed runtime behavior, inferences, assumptions,
  and proposed designs. Code, schemas, migrations, or class names alone do not prove deployed
  configuration, active execution, customer behavior, or a production defect.
- Trace the relevant paths and consumers before drawing behavioral conclusions; do not
  generalize from one field, filename, screen, or legacy artifact.
- Bound negative findings by the scope examined, stated as the concrete scope actually
  searched rather than a template; an empty search is not proof of universal absence. Record unresolved questions and the evidence needed to answer them.
- Keep connectivity evidence separate from behavioral evidence: a successful sample proves
  access to that object only.
- Tie diagram captions to the same evidence identifiers; mark current versus proposed
  relationships and keep unverified relationships in adjacent text, not depicted as
  implemented flows.

## Data Pattern Graphs

When Pyroscope profiles support a finding, apply the
[profiling evidence contract](references/profiling-evidence.md) before delivery.

- Every reported data pattern must be supported by an evidence-backed graph: trends,
  spikes, recurrence, flapping, state transitions, distributions, comparisons, and
  correlations. One graph may support several claims when each pattern is clearly visible.
  Tables, prose, links to dashboards, and architecture or code-flow diagrams do not replace
  data graphs.
- Place each graph beside the claims it supports, in every delivered format: in that
  claim's section, or as a headline graph in the opening with a linked cross-reference from
  that section, as the report layout sets out.
- Choose views that expose the claimed pattern: time series for trends and spikes, event
  or state timelines for recurrence and flapping, and suitable distribution or comparison
  plots for variation across resources. Add a focused view when a full-window graph hides
  short events.
- Link the same inspected evidence used by the claim; identify missing coverage and
  distinguish missing data from observed zero. If evidence cannot establish a pattern, label
  it unverified rather than inventing points or implying that an empty or unavailable result
  proves absence.
- For flapping or recurring alerts, always include the complementary graph pair defined by
  Diagramming Style's [flapping-alert graphs reference](../diagramming-style/references/flapping-alert-graphs.md);
  that reference owns the pair's visual specification, and this skill owns that the pair
  exists and matches the alert-state and metric evidence.
- Before delivery, map every pattern claim to a visible graph and verify that the plotted
  values, timing, and populations agree with its evidence and any accompanying table.
  Include the complete graph inventory in every delivered format, and apply Diagramming
  Style's theme, caption, rendering, and visual-verification requirements to every graph.

## Common Rationalizations

- "The table already shows the numbers." Tables, prose, and dashboard links do not replace
  evidence-backed data graphs; every pattern claim needs a visible graph.
- "The peak is above the threshold, so the alert fired." Outcomes come from saved alert-state
  history, independently of the peak; a peak proves magnitude, not firing.
- "Nothing came back, so it doesn't exist." An empty search bounds a negative finding to the
  scope examined; it never proves universal absence.
- "The class name says it all." Code, schemas, and names alone do not prove deployed
  configuration, active execution, or a production defect.

## Red Flags

- Findings, remediation or the graphs that prove them buried below process history, or a
  preamble above the report title.
- An opening that states a candidate or a correlation more strongly than the detail does.
- A material claim without a linked evidence identifier, or an identifier whose index entry
  does not resolve to the cited revision.
- A `Source:` snapshot missing the inspected revision, data window, or untested remainder.
- A pattern section whose graph is missing, mismatched with its table, or replaced by prose.
- Connectivity evidence presented as behavioral evidence.
- Unverified relationships drawn as implemented flows in a diagram.

## Verification

- [ ] The opening follows [the report layout](references/report-layout.md) and passes its
      checklist in every delivered format.
- [ ] The Evidence index opens with a complete `Source:` snapshot and pinned revision.
- [ ] Each identifier resolves to its intended entry; paths and line ranges match the pinned
      revision; citations support their adjacent claims, consistently in every delivered
      format.
- [ ] Reference completeness passes for every delivered artifact and every material occurrence;
      source provenance, structural link matching and browser acceptance are distinguished.
- [ ] Verified, observed, inferred, assumed, and proposed statements are labeled as such.
- [ ] Negative findings state the scope examined; unresolved questions are recorded.
- [ ] Every pattern claim maps to a visible, evidence-matched graph, and flapping-alert
      reports carry the required graph pair.
