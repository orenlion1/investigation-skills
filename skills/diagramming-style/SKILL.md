---
name: diagramming-style
description: "Create, restyle, or verify Mermaid and Graphviz diagrams and graphs with portable light and dark themes, plain labels, and consistent renders. Use when a diagram or its themed renders are created, restyled, or reviewed."
---

# Diagramming Style

## Overview

Read the bundled [Diagramming Style Guide](references/diagramming-style.md) when creating,
restyling, or checking diagrams. It contains the full rules, complete light and dark profiles,
standalone Mermaid and Graphviz examples, export commands, and delivery checks. Also read the
topic reference when the task matches:

| Task | Reference | Apply |
| --- | --- | --- |
| Investigation report graphs, ER and SQL dependency views | [Report graph profile](references/graph-profile.md) | Adapt the bundled [ER](assets/report-er.dot) and [SQL dependency](assets/report-sql-dependencies.dot) examples: aligned key columns and crow's-foot endpoints for ER relationships; typed plain labels with dashed action arrows for SQL dependencies. The examples establish visual conventions; replace their fictional entities and relationships with inspected evidence. |
| Process and skill diagrams, or matching a supplied workflow reference | [Workflow views](references/workflow-views.md) | Show the main activity/artifact handoffs first, then a separate routing view for invoked skills and their outputs. Adapt the plain-label [overview](assets/workflow-overview.dot) and [routing](assets/workflow-routing.dot) examples. Distinguish activities, artifacts, and skills through role words; label `input`, `produces`, `invokes`, and `routes` relationships explicitly. Routing, review dimensions, and layout constraints do not establish execution order. |
| Flapping or recurring alert investigations | [Flapping-alert graphs](references/flapping-alert-graphs.md) | Owns the visual specification of the required "Daily peaks and alert outcomes" and "Observed Pending and Alerting intervals" graph pair, its outcome encoding, pairing, and PDF placement rules. |
| Relevant Grafana data available within the authorized scope | [Grafana data and interactive graphs](references/grafana-graphs.md) | Enrich diagrams and reports with evidence-backed graphs from Grafana CLI and interactive views supported by the current host, following its scoped queries, provenance, theme checks, and matching static report views. Use the graphs to explain the findings; record unavailable capabilities and continue with verified data rather than making Grafana a prerequisite for ordinary diagramming. |
| Origin of the conventions | [Reference provenance](references/provenance.md) | Background only. |
| Audit, deployment, restart or configuration events alongside measured data | [Evidence event overlays](references/event-overlays.md) | Align saved events with telemetry, label the actual operation and resource, and retain incomplete correlations with adjacent qualifications. |

Before returning a caption-only or prose edit, inspect **both theme exports themselves**
(read SVG text or view raster images). Name both checked files and the title/caveat result
in delivery. A file listing, unchanged DOT source or unchanged bytes is not that inspection.

Core rules, detailed in the guide:

- Use plain labels, whitespace, and restrained typography. Avoid decorative node boxes,
  shaded panels, filled clusters, and opaque edge-label backplates. Keep minimal structural
  outlines that explain meaning, such as ER table boundaries, with keys, cardinality marks,
  and relationship labels. Remove nonessential ink without losing information.
- Titles inside diagrams use sentence case and the body-label font size in every renderer,
  theme, and export; hierarchy comes from whitespace and alignment.
- Keep all caveats in adjacent captions or prose, outside rendered titles, subtitles, nodes,
  edges, notes, and legends. Preserve current/proposed identity and essential domain
  semantics. Explain conditional constraints and the applicable schema scope beside the
  diagram; keep truthful annotations within that scope and omit any that remain misleading.
  After moving a caveat out, read the text of both theme exports and report that neither
  contains it and the rendered title is unchanged, even when no export was edited.
- Organize complex subjects from overview to detail, with neutral defaults, defined accents,
  and stable comparison layouts. Check contrast in each theme; a color value alone does not
  establish accessibility.
- Give every edge enough run for its arrowheads and ER endpoint marks, and keep labels clear
  of shafts, arrowheads, and shape boundaries by raising separation, lengthening the edge, or
  moving the label, never by adding an opaque backplate or shrinking text.
- Derive light and dark versions from the same diagram definition, changing the palette
  only. Default print/PDF delivery to light and retain dark-mode support. Prefer one committed
  canonical source per diagram with the second theme produced by a committed script or shared
  theme configuration; when separate per-theme sources must exist, compare their structure
  ignoring palette lines before delivery.
- A user-supplied reference style (shapes, shaded groups, palette) applies only to the diagram
  it was requested for; inspect both the reference render and its source. After any label or
  edge change, regenerate every delivered variant from the one source (light, dark and any
  adaptive SVG), update captions and alt text, and recheck theme parity and overlaps. Update
  captions and alt text even when rendering is blocked, and report stale exports rather than
  hand-writing SVG. For a lifecycle-with-integrations view, edit the prose beside the diagram
  to state artifact details, as-needed integration selection and Publish's separate
  authorization, keeping all three out of the diagram.
- Flame graph captions: one or two sentences leading with what the profile establishes, then
  the material uncertainty and an evidence reference (for example `[E1]`). Move colors, reading
  direction, widths, query arguments and export commands to the linked evidence or methods;
  details and profiling rules are in [Grafana graphs](references/grafana-graphs.md#profiling-views).
- Keep the complete diagram inventory consistent across the requested formats. Use native
  inline diagrams as the primary presentation only when their theme behavior is verified on
  the delivery host; otherwise use paired light/dark images in a primary `picture` element,
  retaining editable Mermaid as non-rendering source or a source link.
- Preserve the caller's scope, destinations, repository policies, toolchain, and authorization
  boundaries. Use the examples for the requested formats; their export options do not require
  adding unsolicited deliverables. This skill does not authorize publication or external writes.

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

- Render every diagram in both themes and inspect text, arrows, structural fills, edge-label
  backgrounds, and overlaps; source settings alone do not prove clearance.
- Run [scripts/check_diagram_overlaps.py](scripts/check_diagram_overlaps.py) on the Graphviz
  SVG renders. Its text extents are estimates, so a pass supplements, never replaces, visual
  inspection. After changing the checker, run `python3 -m unittest discover -s <skill>/tests`.
- Verify the same delivered Markdown document in both host themes, including selected images
  and canvas colors; standalone exports alone are not acceptance, and a fixed light diagram
  displayed in dark mode fails. Count primary rendered diagrams against the inventory,
  independently of source-fence language or links.
