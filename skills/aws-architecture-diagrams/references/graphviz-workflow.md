# Graphviz workflow

Steps follow the numbered list in [SKILL.md](../SKILL.md).

## 1. Get the official icons

The asset package URL rotates, so discover it rather than hardcoding:

```bash
curl -fsSL https://aws.amazon.com/architecture/icons/ -o icons-page.html
grep -oiE 'https://d1\.awsstatic\.com/[^"]*Icon-package[^"]*\.zip' icons-page.html | head -1
```

Download, unzip, and copy only the 48px PNGs you actually use into
`<diagrams>/icons/`. Keep the original filenames — they identify the service and
the package version. Do not recolor, redraw, stretch, or substitute a generic
cloud glyph for a named service.

Record in the README where the icons came from and on what date, and note that
AWS trademark and icon terms apply and that the composition is not an AWS
endorsement.

## 2. Write the DOT source

Follow [dot-conventions.md](dot-conventions.md).

## 3. Render

Icon paths are resolved against the working directory of the `dot` process, not
against the DOT file, so always render from the diagram directory.

Graphviz's default SVG renderer leaves PNG icons as relative `icons/*.png`
references. That is acceptable only when the destination preserves and serves
the adjacent asset directory. For a standalone or sandbox-previewed SVG,
generate the standard SVG and run a repository-owned embedding step that
replaces only those image references with `data:` URLs while preserving
`preserveAspectRatio` and selectable text:

```bash
dot -Tsvg system-context-aws.dot -o system-context-aws.svg
node embed-svg-images.mjs system-context-aws.svg
dot -Tpng -Gdpi=180 system-context-aws.dot -o system-context-aws.png
```

Reuse an established repository helper when one exists. Otherwise create and
validate a narrowly scoped helper beside the diagrams, or keep the standard SVG
and ship its icon directory with it; never document a command for a helper that
does not exist in the delivered repository.

The embedding helper must be idempotent, validate its input, provide a
non-mutating `--check` mode, reject paths outside the diagram directory, and
verify that at least one image was embedded with no local references left.
Do not substitute `svg:cairo` without visual verification: tested Graphviz
15.1.1 output embedded the icons but applied a non-uniform `1 x 0.75` transform
that vertically compressed square AWS assets and converted text to glyph paths.
State which portability and text-accessibility contract the output satisfies.
SVG is for repositories and the web; PNG is for decks and issue threads.

## 4. Look at the result

Open the rendered PNG and actually inspect it. Check:

- no node has escaped its cluster box (a node drawn outside the boundary it
  belongs to is a **correctness** bug, not a cosmetic one);
- no edge label sits on top of another label or an icon;
- no edge crosses a cluster it has no business entering;
- the aspect ratio suits the destination — a diagram three times taller than it
  is wide will be illegible on a slide;
- **the type survives the scale it will be viewed at** — the failure shipped
  most often, because the diagram looks fine at 100%. Check the `width` the SVG
  declares: at a 900px page width, a 1900pt-wide diagram is drawn at about a
  third of size, so its 9pt labels land near 4px. Raising the font sizes alone
  makes it *wider* and no more readable. Past roughly 1200pt, switch `rankdir`
  to `TB` — height scrolls, width shrinks the type — or split the diagram;
- every icon is the service the label claims.

For a self-contained SVG, also verify that no relative icon link remains and
that embedded image data exists. For example:

```bash
xmllint --noout system-context-aws.svg
! grep -Eq '(xlink:)?href="icons/' system-context-aws.svg
grep -Eq '(xlink:)?href="data:image/png;base64' system-context-aws.svg
! grep -q 'matrix(1, 0, 0, 0.75' system-context-aws.svg
```

Open the SVG itself in the destination preview, not only the separately
rendered PNG. A PNG can look correct while the SVG silently depends on missing
relative icon files.

If it fails, fix it and render again. Common fixes are in
[dot-conventions.md](dot-conventions.md) under "When the layout fights you".

## 5. Write the README

List each diagram, its editable source, its rendered outputs, the render
commands, and the icon provenance. See [readme-template.md](readme-template.md).
