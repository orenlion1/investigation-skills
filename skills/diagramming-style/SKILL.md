---
name: diagramming-style
description: Create, restyle, or review Mermaid and Graphviz diagrams with portable light and dark themes, plain labels, and consistent rendered outputs. Use when creating, restyling, or verifying diagrams and their themed renders.
---

# Diagramming Style

## Overview

Read the bundled [Diagramming Style Guide](references/diagramming-style.md) when creating,
restyling, or checking diagrams. It contains complete light and dark profiles, standalone
Mermaid and Graphviz examples, export commands, and delivery checks.

For investigation reports, apply the guide's [report graph profile](references/diagramming-style.md#report-graph-profile)
and adapt the bundled [ER](assets/report-er.dot) and [SQL dependency](assets/report-sql-dependencies.dot)
examples. Use aligned key columns and crow's-foot endpoints for ER relationships, and typed
plain labels with dashed action arrows for SQL dependencies. These examples establish visual
conventions; replace their fictional entities and relationships with inspected evidence.

For flapping or recurring alert investigations, apply the bundled
[flapping-alert graphs reference](references/flapping-alert-graphs.md): it owns the visual
specification of the required "Daily peaks and alert outcomes" and "Observed Pending and
Alerting intervals" graph pair, its outcome encoding, pairing, and PDF placement rules.

For process and skill diagrams, apply the guide's
[workflow views](references/diagramming-style.md#workflow-views): show the main activity/artifact
handoffs first, then a separate routing view for invoked skills and their outputs. Adapt the
plain-label [overview](assets/workflow-overview.dot) and
[routing](assets/workflow-routing.dot) examples. Distinguish activities, artifacts, and skills
through role words; label `input`, `produces`, `invokes`, and `routes` relationships explicitly.
Routing, review dimensions, and layout constraints do not establish execution order.

When relevant Grafana data is available within the authorized scope, enrich diagrams and
reports with evidence-backed graphs from Grafana CLI and interactive views supported by
the current host. Follow the guide's
[Grafana data and interactive graphs](references/diagramming-style.md#grafana-data-and-interactive-graphs)
for scoped queries, provenance, theme checks, and matching static report views. Use these
graphs to explain the findings; record unavailable capabilities and continue with verified
data rather than making Grafana a prerequisite for ordinary diagramming.

- Use plain labels, whitespace, and restrained typography. Avoid decorative node boxes,
  shaded panels, filled clusters, and opaque edge-label backplates. Keep minimal structural
  outlines when they explain meaning, such as ER table boundaries; retain keys, cardinality
  marks, and relationship labels, with evidence in adjacent text. Remove nonessential ink
  without losing information.
- Use sentence case and the same readable font size as body labels for titles inside diagrams.
  Establish hierarchy through whitespace and alignment, not oversized or all-capital text.
  Apply this to Mermaid, Graphviz, and every theme and export; surrounding report section
  headings follow the document's own hierarchy.
- Keep all caveats in adjacent captions or prose, outside rendered titles, subtitles, nodes,
  edges, notes, and legends. Preserve current/proposed identity and essential domain semantics.
  Explain conditional constraints and the diagram's applicable schema scope beside it. Keep
  truthful annotations within that explicit scope; omit any that remain misleading under it.
- Organize complex subjects from overview to detail. Use neutral defaults with defined accents,
  stable comparison layouts, and adjacent scope, assumptions, legends, and evidence notes.
  Check contrast in each theme; a color value alone does not establish accessibility.
- Give every edge enough run for its notation. Arrowheads and ER endpoint marks such as
  crow's-foot circles, bars, and forks need clear space between the shapes they connect;
  raise rank/node separation or per-edge minimum length rather than letting marks collide
  with or merge into node outlines. Keep labels clear of edge shafts, arrowheads, and shape
  boundaries by moving the label or lengthening the edge, never by adding an opaque backplate
  or shrinking text. Inspect the rendered output for these overlaps; source settings alone
  do not prove clearance.
- Validate spacing on Graphviz SVG renders with the bundled checker,
  [scripts/check_diagram_overlaps.py](scripts/check_diagram_overlaps.py): it tests label
  clearance from lines, arrowheads, endpoint marks, shapes, and other labels, shape and mark
  collisions, and whether each edge's run fits its notation. Run its own test suite with
  `python3 -m unittest discover -s <skill>/tests` after changing the checker. Its text
  extents are estimates, so a pass supplements the required visual inspection in both
  themes; it never replaces it.
- Derive light and dark versions from the same diagram definition. Preserve identifiers,
  labels, relationships, direction, layout settings, and adjacent captions, evidence, and caveats;
  change the palette only. Default print/PDF delivery to light and retain dark-mode support.
  Prefer one committed canonical source per diagram with the second theme produced by a
  committed script or shared theme configuration, so the themes cannot drift. When separate
  per-theme sources must exist, compare their structure ignoring palette lines before delivery.
- Preserve the caller's scope, destinations, repository policies, toolchain, and authorization
  boundaries. Use the examples for the requested formats; their export options do not require
  adding unsolicited deliverables. This skill does not authorize publication or external writes.
- Keep the complete diagram inventory consistent across the requested formats. Verify the same
  delivered Markdown document in both light and dark modes; standalone exports alone are not
  acceptance. Count primary rendered diagrams independently of source-fence language or links.
  A fixed light diagram displayed in dark mode fails this check.
- Use native inline diagrams as the primary presentation only when their theme behavior is
  verified on the delivery host. Otherwise use paired light/dark images in a primary `picture`
  element, retaining editable Mermaid as non-rendering source or a source link. Do not place
  the themed images only in a collapsed fallback beneath a fixed light diagram. Inspect text,
  arrows, structural fills, edge-label backgrounds, and the selected image in both modes.

This package is self-contained. Copy the whole folder to reuse it; no sibling repository,
workspace path, naming helper, source image, or remote service is required. Apply the caller's
naming conventions without changing the skill package's standard filenames.

## When to Use

- Creating or restyling Mermaid or Graphviz diagrams with portable light and dark themes.
- Reviewing rendered diagram outputs for theme, label, and spacing problems before delivery.
- Preparing report diagrams, including ER, SQL dependency, and workflow views.

## Common Rationalizations

- "The source sets no fill, so the render must be clean." Renderer defaults add fills and label backplates; inspect the actual renders in both themes.
- "A caveat inside the title is more visible." Caveats live in adjacent captions or prose, never in rendered titles, nodes, edges, or legends.
- "One theme is enough." Both light and dark deliverables must be derived from the same definition and verified.

## Red Flags

- Theme-default node or cluster fills and opaque edge-label backplates in a render.
- Caveat or uncertainty text inside a rendered diagram.
- A fixed light diagram shown in dark mode, or themed images hidden in a collapsed fallback.
- Per-theme sources that drift structurally.

## Verification

- Render every diagram in both themes and inspect text, fills, arrows, and label backgrounds.
- Run [scripts/check_diagram_overlaps.py](scripts/check_diagram_overlaps.py) on the SVG renders; a pass supplements, never replaces, visual inspection.
- Verify the delivered Markdown document in both host themes, including selected images and canvas colors.
