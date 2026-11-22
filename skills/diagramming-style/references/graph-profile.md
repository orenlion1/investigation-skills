# Report Graph Profile

Part of the [Diagramming Style Guide](diagramming-style.md); its visual, theme, caveat, and
delivery rules apply here.

Use the bundled palette-independent examples as the visual starting point for report graphs.
Keep the guide's shared typography, plain flow labels, restrained table outlines, and
light/dark profiles. Align related peer paths side by side where this makes comparison easier;
split a view when its text would otherwise become unreadable at the delivered page width.
Layout is not evidence: preserve the investigated relationships and current/proposed identity.

## ER relationships

Show verified keys, foreign-key targets, cardinality, nullability, and relevant uniqueness,
subject to the guide's
[conditional-constraint rule](diagramming-style.md#caveats-outside-drawings). Distinguish
physical tables from role aliases and entity assignments from dictionary mappings. Explain
selected columns, omitted relationships, conditional constraints, and migration scope in
adjacent captions or prose. A source declaration does not prove the deployed schema; state
that limitation outside the drawing.

Adapt [report-er.dot](../assets/report-er.dot). Center the bold entity title over two columns:
put `PK`, `FK`, and `UQ` markers in the narrow left column and field names, nullability, or
composite-key members in the right. Keep the table and title unfilled. A borderless outer
table with padding reserves space between the structural outline and endpoint marks.

Use crow's-foot marks at both ends instead of replacing them with floating numeric labels.
For `parent -> child`, `arrowtail` describes how many parents one child may reference;
`arrowhead` describes how many children one parent may have. Set `dir=both` so both render.
The profile uses these combinations of [Graphviz arrow shapes](https://graphviz.org/doc/info/arrows.html):

| Cardinality at an endpoint | Mark | Graphviz value |
| --- | --- | --- |
| Zero or one | Circle and bar | `teeodot` |
| Exactly one | Double bar | `teetee` |
| Zero or more | Circle and fork | `crowodot` |
| One or more | Bar and fork | `crowtee` |

Verify each endpoint from the applicable schema and constraints. A nullable FK permits zero
parents; a non-null FK requires one. A non-unique FK permits many children, but does not require
any child to exist. A unique FK may cap that count at one. Use `1..*` only when inspected
constraints or an explicitly scoped domain rule require at least one child. Do not infer
cardinality from field names or sample row counts. Explain conditional rules beside the graph.

The fictional example defines an optional team and a required category for each record;
each team and category may have zero or more records. `ExternalKey` is unique. These example
constraints are not findings about any repository. In a report, replace this annotation with
the actual schema scope, evidence, and omitted relationships. Explain the endpoint notation
in the caption or an essential-notation legend.

## SQL dependencies

Put SQL functions and procedures in a dependency view separate from the ER view. Adapt
[report-sql-dependencies.dot](../assets/report-sql-dependencies.dot). Prefix plain labels
with `Procedure`, `Function`, or `Table`, and use dashed directional arrows labeled with the
observed action: `reads`, `writes`, or `calls`. These edges are not foreign keys and do not
imply execution order or transaction boundaries. Arrange independent read and write paths in
parallel columns where useful. Any layout-only edges must be invisible; do not create a
dependency to align nodes. Dashed lines identify SQL dependencies in this profile, not
uncertainty. State evidence gaps, exceptions, source evidence, and unverified relationships
beside the graph and keep proposed behavior clearly identified.

The fictional example shows a read procedure calling a function that reads records, and a
write procedure calling another procedure that writes records. It does not establish order
between the two paths or a shared transaction. Both `Record` labels represent the same table,
repeated to keep the paths legible. Replace its symbols and edges with traced dependencies.

## Render and verify the examples

Run from a scratch output directory after defining the guide's
[`render_light` and `render_dark`](diagramming-style.md#graphviz-example) functions.
Set `DIAGRAM_SKILL` to the absolute path of this copied skill folder. The examples need no
sibling checkout or report assets. Use caller-resolved destinations for real report outputs.

```sh
DIAGRAM_SKILL='/absolute/path/to/diagramming-style'
for example in report-er report-sql-dependencies; do
  render_light -Tsvg -o "$example-light.svg" "$DIAGRAM_SKILL/assets/$example.dot"
  render_dark -Tsvg -o "$example-dark.svg" "$DIAGRAM_SKILL/assets/$example.dot"
  render_light -Tpng -Gdpi=200 -o "$example-light.png" "$DIAGRAM_SKILL/assets/$example.dot"
  render_dark -Tpng -Gdpi=200 -o "$example-dark.png" "$DIAGRAM_SKILL/assets/$example.dot"
  python3 "$DIAGRAM_SKILL/scripts/check_diagram_overlaps.py" \
    "$example-light.svg" "$example-dark.svg"
done
```

Inspect both palettes for the aligned key columns, visible endpoint marks, title and body
contrast, and labels clear of dashed lines. Preserve the canonical source and add adapted
graphs to the report inventory. The guide's
[Markdown and format-consistency checks](diagramming-style.md#markdown-presentation-and-format-consistency)
still apply; these standalone renders do not establish delivery-host acceptance.
