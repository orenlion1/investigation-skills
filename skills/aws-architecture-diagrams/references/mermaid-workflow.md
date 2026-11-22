# Mermaid workflow

Steps follow the numbered list in [SKILL.md](../SKILL.md).

## 1. Select the Mermaid diagram type

Use `architecture-beta` or a flowchart for architecture and topology, a
`sequenceDiagram` for ordered exchanges, and a state diagram only for actual
state transitions. Confirm that the target renderer supports the selected
syntax and any icon pack; do not assume GitHub, a documentation site, and a
local Mermaid CLI run the same version or configuration. When using Iconify
symbols, keep the full AWS resource name and type in text; an icon must never be
the only resource identifier.

## 2. Encode the verified inventory

Represent AWS account, Region, VPC, Availability Zone, subnet, and ownership
boundaries only when the evidence establishes them. Use full resource names and
types, short labelled edges, and visible annotations for permitted or inferred
relationships. Keep the provenance in nearby Markdown and, when the syntax
allows, in a source comment.

## 3. Render and inspect in the target environment

Use the repository's pinned Mermaid command or documentation build. Validate
the exact fenced block or `.mmd` source that will ship, then inspect the rendered
result at its intended width and theme. Check clipped labels, overlapping edges,
unsupported icons or syntax, inaccessible contrast, and semantic drift from the
verified inventory. Fix the editable source and rerender until it is readable.

Register non-built-in icon packs explicitly. For Mermaid CLI, a reproducible
AWS-symbol render can use:

```bash
mmdc --iconPacks '@iconify-json/logos' \
  -i system-context-aws.mmd -o system-context-aws.svg -b white
```

Treat a `?` fallback as a failed render, not a cosmetic degradation. Icon-pack
support can vary by Mermaid version and layout renderer; verify the actual
output visually and structurally. If one supported renderer loses registered
icons, use another supported renderer that preserves them and document the
layout tradeoff. Do not claim inline portability unless the target host also
registers the required pack.

## 4. Deliver the required artifacts

Keep Mermaid inline when that is the repository contract. When standalone SVG
or PNG outputs are required, render them deterministically with the repository's
pinned Mermaid version and document the reproduction command.
