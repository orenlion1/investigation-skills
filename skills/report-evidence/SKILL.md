---
name: report-evidence
description: Build and verify the evidence record of an investigation report before delivery — the Evidence index with its canonical Source snapshot, linked E1/E2 citation identifiers beside material claims, verified-versus-inferred labeling, bounded negative findings, and the required evidence-backed data pattern graphs. Use when assembling, citing, or verifying report evidence or checking a report's evidence discipline before delivery.
---

# Report Evidence

## Overview

Every investigation report and its supporting diagrams pass this evidence discipline before
delivery. This skill owns the Evidence index, the canonical `Source:` snapshot, citation
identifiers, the verified/inferred distinction, negative-finding bounds, and the requirement
that every reported data pattern is supported by an evidence-backed graph. Visual styling,
theming, captions, and rendering checks for those graphs belong to
[Diagramming Style](../diagramming-style/SKILL.md); this skill owns that the graphs exist and
match the evidence.

## When to Use

- Assembling the Evidence index and `Source:` snapshot for an investigation report.
- Placing or verifying `E1`/`E2` citation identifiers beside report claims.
- Checking a report's evidence discipline, citations, or graph coverage before delivery.
- Deciding whether a finding is verified, observed, inferred, assumed, or proposed.

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
Inventory every material incident, investigation, backing chat, conversation and cross-report
evidence reference at its point of use: reconciliation prose, coverage tables and evidence-index
entries all count. A working link elsewhere, attachment hash or report-title link never satisfies
an unlinked occurrence. Register source-derived identities and visible aliases, review the full
source for omitted references, and retain occurrence-level diagnostics and separate unique-target
counts. Unavailable provenance and unverified navigation remain explicit incomplete results.

## Evidence Discipline

- Distinguish verified source findings, observed runtime behavior, inferences, assumptions,
  and proposed designs. Code, schemas, migrations, or class names alone do not prove deployed
  configuration, active execution, customer behavior, or a production defect.
- Trace the relevant paths and consumers before drawing behavioral conclusions; do not
  generalize from one field, filename, screen, or legacy artifact.
- Bound negative findings by the scope examined; an empty search is not proof of universal
  absence. Record unresolved questions and the evidence needed to answer them.
- Keep connectivity evidence separate from behavioral evidence: a successful sample proves
  access to that object only.
- Tie diagram captions to the same evidence identifiers; mark current versus proposed
  relationships and keep unverified relationships in adjacent text, not depicted as
  implemented flows.

## Data Pattern Graphs

- Every reported data pattern must be supported by an evidence-backed graph: trends,
  spikes, recurrence, flapping, state transitions, distributions, comparisons, and
  correlations. One graph may support several claims when each pattern is clearly visible.
  Tables, prose, links to dashboards, and architecture or code-flow diagrams do not replace
  data graphs.
- Place each graph in the same report section as the claims it supports, immediately beside
  the relevant explanation, in every delivered format.
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

- A material claim without a linked evidence identifier, or an identifier whose index entry
  does not resolve to the cited revision.
- A `Source:` snapshot missing the inspected revision, data window, or untested remainder.
- A pattern section whose graph is missing, mismatched with its table, or replaced by prose.
- Connectivity evidence presented as behavioral evidence.
- Unverified relationships drawn as implemented flows in a diagram.

## Verification

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
