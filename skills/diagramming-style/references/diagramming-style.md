# Diagramming Style Guide

Use clear labels, deliberate spacing, and restrained color to explain relationships. This guide
is portable: copy it into another project and use the examples in any working directory. It
requires no particular repository, naming tool, template, external image, or hosted service.

Topic references, loaded only when the task needs them: [workflow views](workflow-views.md),
[report graph profile](graph-profile.md) (ER and SQL dependency views),
[Grafana data and interactive graphs](grafana-graphs.md),
[flapping-alert graphs](flapping-alert-graphs.md), and
[reference provenance](provenance.md).

## Visual rules

- Prefer plain text labels. Use wording, whitespace, alignment, and typographic hierarchy for
  emphasis. Do not add decorative boxes, pills, shaded panels, filled clusters, or opaque
  backgrounds behind edge labels merely to highlight text. When the user explicitly asks
  to match a supplied workflow reference, use the scoped
  [lifecycle with integration branches](workflow-views.md#lifecycle-with-integration-branches)
  pattern.
- Keep minimal structural outlines when they carry meaning, such as an ER table boundary.
  Use the canvas color or transparency inside them in both modes; white backplates are not
  acceptable in dark mode. Explain meaningful shapes in a legend;
  never invent a group, relationship, or dependency to improve the composition.
- Choose one dominant reading direction: left to right for a short process, top to bottom
  for a hierarchy or a narrow page. Align peers, leave space between branches, and keep edges
  clear of labels. Split crowded views instead of shrinking their text.
- Use concise node labels and action words on directed edges, such as `reads`, `writes`,
  `calls`, or `produces`. Preserve the direction and meaning of every relationship.
- Use Trebuchet MS when available, with Arial, Helvetica, or an available sans-serif fallback.
  Font substitution is acceptable; inspect the resulting line breaks and spacing. Keep labels
  readable at the actual delivery size, including PDF page width.
- Use color as reinforcement. Text, notation, and captions must still explain the diagram
  without color. Identify current and proposed views clearly; explain inferences in adjacent prose.

## Edge length and overlap control

Edges carry notation: arrowheads, and in ER views stacked endpoint marks such as crow's-foot
circles, bars, and forks. A too-short edge merges those marks into the shapes it connects.

- Reserve enough run between connected shapes for every mark on the edge. In Graphviz, raise
  `ranksep`/`nodesep`, or set `minlen=2` (or more) on the specific short edge; compact values
  near `0.4` that suit plain flowcharts are usually too tight for ER edges, which stack two
  endpoint marks on one line — start ER views at `ranksep=0.7` or higher and confirm visually.
  In Mermaid, raise `rankSpacing`/`nodeSpacing` in the flowchart or ER configuration.
- Keep both endpoint marks fully visible in the open space between the two shapes, not
  touching, crossing, or merged into either outline or a nearby title row. If a mark lands on
  a border, lengthen the edge or move the node; do not shrink the mark or hide it.
- Keep labels clear of edge shafts, arrowheads, node outlines, and other labels. Offset the
  label (Graphviz `xlabel`, `labeldistance`/`labelangle`, or added spacing; Mermaid label
  offsets via `themeCSS`), reroute the edge, or lengthen it. Never resolve an overlap with an
  opaque backplate behind the label or by shrinking text below the readable delivery size.
- When spacing fixes crowd the layout instead, split the view.
- Inspect the rendered image in both themes at delivery size for short edges, clipped or
  merged endpoint marks, and label collisions. Layout settings in the source do not prove
  clearance; only the render does.

### Automated overlap checks

The bundled checker, `scripts/check_diagram_overlaps.py`, validates these rules on rendered
Graphviz SVG output (both themes render from the same geometry, so checking one theme's SVG
covers the layout; theme colors still need the visual pass):

```sh
python3 scripts/check_diagram_overlaps.py path/to/diagram-light.svg path/to/diagram-dark.svg
```

It fails (exit 1) and names the offending element pair when a label sits within the
clearance distance (default 2px) of an edge line, arrowhead, endpoint mark, shape outline,
or another label; when shape outlines or marks collide beyond boundary contact; or when an
edge's sampled run cannot fit the merged along-edge extent of its own notation plus
clearance. Pairs that meet by construction are exempt from the clearance distance but not
from actual penetration: an edge necessarily reaches the text of its endpoint nodes in
plain-label styling, and an edge's own label sits beside its own line. `--clearance`,
`--min-edge-run`, `--touch-tolerance`, and `--char-width-ratio` tune the thresholds;
`--json` emits a machine-readable report.

Known limits: it reads Graphviz `-Tsvg` structure only (Mermaid SVGs are rejected, not
guessed at), and text extents are estimated from font size and character count (default
ratio 0.48, calibrated for Trebuchet MS/Arial mixed case). Treat a pass as a spacing
regression gate alongside — never instead of — the visual inspection of both themes.

Run the checker's test suite, `tests/test_check_diagram_overlaps.py`, after any change to the
checker or its thresholds. It covers a clean pass, each defect class, the attachment
exemptions, invisible layout-edge handling, and — when Graphviz is installed — an end-to-end
render in which a spaced ER edge passes and a crammed one fails:

```sh
python3 -m unittest discover -s tests   # from the skill folder
```

## Titles inside diagrams

Use sentence-case titles inside diagrams, preserving domain acronyms, at the same readable
font size as the main body labels: `Current source flow`, not a large all-capital title.
Establish hierarchy with aligned placement and a clear gap between the title and diagram
body. Do not shrink a title below readable body text to make it unobtrusive. Titles remain
subject to [caveats outside drawings](#caveats-outside-drawings).

- Graphviz: set the graph's `fontsize` to the main node/body `fontsize`. Separate the title
  from the body with label spacing, such as a trailing `\n`, and the graph's padding.
- Mermaid: flowchart and ER title text elements use `.flowchartTitleText` and
  `.erDiagramTitleText`. Match their size to the body font through `themeCSS`; for a 16px
  body, use `font-size: 16px !important; font-weight: 400 !important;` on those selectors.
  Retain enough diagram padding for clear spacing. For another diagram type or renderer
  version, inspect the actual title element rather than assuming these selectors apply.

Apply the same title size, case, alignment, and spacing in both themes and every exported
format, including titles embedded in SVG, PNG, or PDF. Validate at the delivered size that
the title and body are equally readable and do not collide. Surrounding Markdown or PDF
report section headings retain their own document hierarchy.

## Information hierarchy and context

Apply these principles to make technical information easier to understand, not to minimize
the number of marks regardless of meaning:

- Remove nonessential ink while retaining useful structure. ER table boundaries, keys,
  crow's feet, optionality marks, and relationship labels carry information; keep evidence
  references in adjacent text. Do not erase meaning merely to achieve a sparse appearance.
  Keep backgrounds clean and structural fills canvas-matching.
- Start with neutral text and lines for routine structure. Use stronger accents for a defined
  status, important change, or consistent semantic role, and explain that role. The palette's
  edge-word accent identifies relationship actions; it does not imply a warning or outcome.
  Reinforce status and distinctions with text or line style so color is never the only signal.
- Check foreground/background contrast, text size, and line visibility in each rendered theme.
  A hex value alone cannot establish AA compliance; evaluate its actual use and background.
  Do not carry a light-theme threshold color into dark mode without checking it there.
- Present an overview before detailed views when a subject needs several diagrams. Let readers
  see the system or question first, then inspect relevant flows, structures, and dependencies.
  Use consistent identifiers to connect the views; do not force all detail into one canvas.
- Group related views through headings, alignment, and whitespace. Use available width for
  useful side-by-side comparisons while preserving readable labels and a clear reading order.
  Keep repeated entities in comparable positions where practical; preserve layout between
  themes and avoid unnecessary rearrangement between comparable versions. Grouping must reflect
  the subject, not invent a relationship or decorative enclosure.
- Place scope, assumptions, exclusions, legends, and evidence in an adjacent caption or prose
  outside the drawing. Retain essential edge labels and multiplicity inside the diagram.
  Explain what readers are comparing and what they cannot infer; preserve this context in
  static exports rather than relying only on a hover description.

## Light and dark profiles

Support both profiles from the same diagram definition. Change the palette only: preserve
identifiers, labels, edges, direction, grouping, layout settings, and adjacent captions, evidence,
and scope notes.
Use light as the print/PDF default; supply dark exports for dark viewing contexts. A dark canvas
is a page background, not a highlight panel around selected text.

Prefer one committed canonical source per diagram, with the second theme produced at render
time by a committed mechanism the repository can rerun, so the themes cannot drift
structurally: shared external theme configurations (as in the Mermaid example below),
renderer palette flags (as in the Graphviz example below), or a small committed script that
maps the light palette to the dark palette before rendering. When separate per-theme
source files must exist — for example, a renderer that only reads embedded front matter —
treat the light file as canonical, propagate every structural change to the dark file in the
same edit, and before delivery diff the pair with palette, background, and theme lines
filtered out; any remaining difference is drift to resolve.

| Role | Light / print | Dark |
| --- | --- | --- |
| Canvas | `#ffffff` | `#0f172a` |
| Main text | `#0f172a` | `#f1f5f9` |
| Arrows and secondary text | `#475569` | `#94a3b8` |
| Meaningful structural outlines | `#6366f1` | `#a5b4fc` |
| Edge action words | `#0e7490` | `#67e8f9` |
| Label and cluster backgrounds | Transparent | Transparent |

Check both profiles on their actual canvas. Do not let a viewer place light text on a light
background or dark text on a dark background by dropping the intended canvas color.

## Mermaid example

The example uses one graph and two complete configuration files. Save the following editable
source as `diagram.mmd`; it is shown as text to avoid an unverified inline theme. The labels
illustrate a generic process, not a claim about a real system.

```text
flowchart LR
    source["Source material"] -->|informs| review["Review evidence"]
    review -->|produces| findings["Document findings"]
    classDef plain fill:none,stroke:none;
    class source,review,findings plain;
```

Save this as `theme-light.json`:

```json
{
  "theme": "base",
  "flowchart": {"htmlLabels": false, "curve": "linear", "nodeSpacing": 40, "rankSpacing": 70},
  "themeVariables": {
    "darkMode": false,
    "background": "#ffffff",
    "fontFamily": "\"Trebuchet MS\", Arial, Helvetica, sans-serif",
    "fontSize": "16px",
    "primaryColor": "#ffffff",
    "primaryTextColor": "#0f172a",
    "primaryBorderColor": "#6366f1",
    "textColor": "#0f172a",
    "lineColor": "#475569",
    "edgeLabelBackground": "transparent",
    "clusterBkg": "transparent",
    "clusterBorder": "transparent"
  },
  "themeCSS": ".edgeLabel rect, .labelBkg, .relationshipLabelBox { background: transparent !important; fill: none !important; } .edgeLabel, .edgeLabel p { background-color: transparent !important; } .edgeLabel text { fill: #0e7490 !important; transform: translateY(-14px); }"
}
```

Save this as `theme-dark.json`:

```json
{
  "theme": "base",
  "flowchart": {"htmlLabels": false, "curve": "linear", "nodeSpacing": 40, "rankSpacing": 70},
  "themeVariables": {
    "darkMode": true,
    "background": "#0f172a",
    "fontFamily": "\"Trebuchet MS\", Arial, Helvetica, sans-serif",
    "fontSize": "16px",
    "primaryColor": "#0f172a",
    "primaryTextColor": "#f1f5f9",
    "primaryBorderColor": "#a5b4fc",
    "textColor": "#f1f5f9",
    "lineColor": "#94a3b8",
    "edgeLabelBackground": "transparent",
    "clusterBkg": "transparent",
    "clusterBorder": "transparent"
  },
  "themeCSS": ".edgeLabel rect, .labelBkg, .relationshipLabelBox { background: transparent !important; fill: none !important; } .edgeLabel, .edgeLabel p { background-color: transparent !important; } .edgeLabel text { fill: #67e8f9 !important; transform: translateY(-14px); }"
}
```

With Mermaid CLI (`mmdc`) installed, run these commands in the directory containing the files.
For PDF, set both the diagram and page canvas and preserve print colors; the CLI background
option alone does not reliably set PDF pages.
The example commands were checked with Mermaid CLI 11.16.0. Verify your renderer's behavior.
The label offset keeps action words above these horizontal edges; inspect and adjust label
placement when adapting the example to a different layout.

```sh
mmdc --version
printf '%s\n' 'html, body { background: #ffffff !important; } * { -webkit-print-color-adjust: exact !important; print-color-adjust: exact !important; }' > page-light.css
printf '%s\n' 'html, body { background: #0f172a !important; } * { -webkit-print-color-adjust: exact !important; print-color-adjust: exact !important; }' > page-dark.css
mmdc -i diagram.mmd -c theme-light.json -b '#ffffff' -o diagram-light.svg
mmdc -i diagram.mmd -c theme-dark.json -b '#0f172a' -o diagram-dark.svg
mmdc -i diagram.mmd -c theme-light.json -b '#ffffff' -s 2 -o diagram-light.png
mmdc -i diagram.mmd -c theme-dark.json -b '#0f172a' -s 2 -o diagram-dark.png
mmdc -i diagram.mmd -c theme-light.json -C page-light.css -b '#ffffff' -f -o diagram-light.pdf
mmdc -i diagram.mmd -c theme-dark.json -C page-dark.css -b '#0f172a' -f -o diagram-dark.pdf
```

For native inline Markdown, a `mermaid` fence is appropriate only after verifying the same
document in both host themes. A viewer does not automatically load neighboring JSON files. If
it supports Mermaid configuration, supply the selected profile through that viewer's supported
configuration. Some hosts restrict overrides or do not switch Mermaid when the page theme
changes. A fixed light configuration displayed in dark mode fails acceptance. When automatic
theming is unavailable or unverified, use the primary
[paired-image pattern](#markdown-presentation-and-format-consistency) and retain
the editable graph as non-rendering source. JSON profiles and successful standalone exports
do not prove inline theme behavior.

## Graphviz example

Save this palette-independent definition as `diagram.dot`. Plaintext nodes have no decorative
outlines or fill. Keep any palette overrides out of this definition so the two profiles use
identical geometry and content.

```dot
digraph Diagram {
  graph [rankdir=LR, margin=0, pad=0.25, nodesep=0.55, ranksep=0.85];
  node [shape=plaintext, fontname="Trebuchet MS", fontsize=16];
  edge [fontname="Trebuchet MS", fontsize=13, arrowsize=0.7];
  source [label="Source material"];
  review [label="Review evidence"];
  findings [label="Document findings"];
  source -> review [label="informs"];
  review -> findings [label="produces"];
}
```

With Graphviz (`dot`) installed, export both palettes. The shell functions below are complete
and need no project utility. They apply the same palette to each output format. The commands
were checked with Graphviz 16.1.0; available output renderers depend on the installation.

```sh
dot -V
render_light() {
  dot -Gbgcolor='#ffffff' -Gfontcolor='#0f172a' \
    -Nfontcolor='#0f172a' -Ncolor='#6366f1' \
    -Ecolor='#475569' -Efontcolor='#0e7490' "$@"
}
render_dark() {
  dot -Gbgcolor='#0f172a' -Gfontcolor='#f1f5f9' \
    -Nfontcolor='#f1f5f9' -Ncolor='#a5b4fc' \
    -Ecolor='#94a3b8' -Efontcolor='#67e8f9' "$@"
}
render_light -Tsvg -o diagram-light.svg diagram.dot
render_dark -Tsvg -o diagram-dark.svg diagram.dot
render_light -Tpng -Gdpi=200 -o diagram-light.png diagram.dot
render_dark -Tpng -Gdpi=200 -o diagram-dark.png diagram.dot
render_light -Tpdf -o diagram-light.pdf diagram.dot
render_dark -Tpdf -o diagram-dark.pdf diagram.dot
```

Run the Mermaid and Graphviz examples in separate directories: their output names intentionally
match. For an ER table, use a minimal table outline and row separators where useful, without a
shaded heading or cell fill. Avoid blanket shape-removal rules that would erase meaningful ER
structure. For a true grouping, prefer a plain heading and spacing; make any necessary boundary
minimal and explain its meaning.

## Caveats outside drawings

Keep all caveats in adjacent captions or prose. Rendered titles, subtitles, nodes, edges,
notes, and legends must contain no limitations, assumptions, exclusions, uncertainty, validation
status, or scope qualifications. For example, explanations that functions are not ER entities
or deployment was not verified belong beside the diagram, as does a disclaimer such as
"No clinical mapping prescribed". This applies to every diagram, theme, renderer, and delivered
format.

Preserve essential domain labels, current/proposed identity, keys, nullability, cardinality,
and relationship direction. Moving caveats is a presentation change, not permission to
strengthen claims or erase schema meaning. Explain conditional constraints beside the diagram;
an adjacent caption may explicitly scope a view to the schema where its key or uniqueness
annotations are true, such as operational rather than archive definitions. Keep those truthful
annotations, and omit one only if it remains misleading under the stated scope. Preserve the
complete condition in adjacent text; never turn a scoped constraint into a universal claim.

Keep only essential notation, such as abbreviations or multiplicity marks, in any legend
inside the drawing. Put qualifications, scope, assumptions, exceptions, and evidence beside
it, and preserve them in every delivered format, not solely in source comments. Check the
actual rendered text as well as source labels; removing a source note does not prove all
exported versions are free of caveats.

## Markdown presentation and format consistency

Maintain one canonical diagram definition and a complete inventory of diagram identifiers,
captions, evidence references, scope notes, themes, and deliverable formats. Every supported
report format must contain every inventoried diagram, including ER and SQL dependency views.
Separate renderer definitions, if needed, must preserve the same semantics. Layout and file
bytes may differ across renderers and formats.

Use native inline diagrams as the primary presentation only when their theme behavior has been
verified in the delivery host. Otherwise use paired themed images as the primary diagram, as
in this pattern. On a host that permits HTML `picture` and media queries, it selects dark for a
dark color-scheme preference and uses light by default. Bundle both assets and verify their
selection in the same Markdown document under both host themes. Do not hide the themed images
only in a collapsed fallback beneath a fixed light inline diagram. This pattern does not make
an inline Mermaid renderer switch themes.

```html
<picture>
  <source media="(prefers-color-scheme: dark)" srcset="diagram-dark.png">
  <img src="diagram-light.png" alt="Source material informs review, which produces documented findings.">
</picture>
```

Retain the editable Mermaid definition as a source link or in a collapsed `details` element
using a `text` fence or escaped `pre` content, rather than a second rendered `mermaid` fence.
For example, this source disclosure can accompany the primary image:

```html
<details>
  <summary>Editable Mermaid source</summary>
  <pre>flowchart LR
    source["Source material"] --&gt;|informs| review["Review evidence"]
    review --&gt;|produces| findings["Document findings"]
    classDef plain fill:none,stroke:none;
    class source,review,findings plain;</pre>
</details>
```

Provide the diagram identifier, caption, evidence, and caveats immediately beside the diagram.
If the host strips HTML, blocks bundled assets, or ignores the media query, use its supported
image attachment or embedding mechanism and provide explicitly labeled light and dark options.
Relative links alone do not prove visibility. Avoid duplicating both the live diagram and its
source disclosure in exported PDFs; include one complete, readable representation per inventory
entry. Do not claim automatic theme support if the delivery host could not be verified.

After a change:

- Regenerate all supported formats and both themes from the canonical source.
- Open the same rendered Markdown in light and dark mode and inspect exported SVG/PNG/PDF at
  the size readers will use. Verify the selected image asset where the host exposes it.
  Standalone image checks do not replace the Markdown check.
- Check the complete inventory, labels, edge direction, captions, evidence, legends, and
  caveats. Count primary rendered diagrams against the inventory; editable source fences and
  links do not count as rendered diagrams, regardless of their fence language.
- Verify that no caveat remains in rendered diagram text, including titles, subtitles, nodes,
  edges, notes, and legends, and that every relocated qualification remains in adjacent text.
- Inspect both profiles for text contrast, clipping, crossings, font substitution, missing
  canvas colors, default node/cluster/edge-label backgrounds, short edges whose arrowheads or
  endpoint marks collide with shape outlines, and labels overlapping edges, shapes, or other
  labels.
- Parsing, file existence, and link counts do not establish visual quality or complete
  delivery. Record the renderers and versions used, and state any delivery host or format
  that could not be checked.
