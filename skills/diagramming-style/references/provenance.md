# Reference Provenance

Origins of the [Diagramming Style Guide](diagramming-style.md) conventions. Nothing here is
required to use the skill.

The workflow-view concepts were checked against the local `agent-tasks` checkout at
commit `ceda802460c60a619d78960f4df23a63b12ebddd`, with no working changes, on
November 2, 2026:

- [HOW-A-TASK-FLOWS.dot](https://github.com/orenlion1/agent-tasks/blob/ceda802460c60a619d78960f4df23a63b12ebddd/docs/diagrams/HOW-A-TASK-FLOWS.dot)
  separates the main lifecycle from the skills it routes into.
- [TASK-FLOW-DIAGRAM.dot](https://github.com/orenlion1/agent-tasks/blob/ceda802460c60a619d78960f4df23a63b12ebddd/docs/diagrams/TASK-FLOW-DIAGRAM.dot)
  makes activity/artifact handoffs and invocation/output edges explicit, and uses rank,
  weight, ports, and invisible edges to arrange related paths.
- [pull-request-flow-diagram.md](https://github.com/orenlion1/agent-tasks/blob/ceda802460c60a619d78960f4df23a63b12ebddd/docs/diagrams/pull-request-flow-diagram.md)
  separates merge routing from five review dimensions. Its drawn chain does not establish
  that those dimensions must execute sequentially; the [workflow views](workflow-views.md) guidance avoids that inference.
- [render-diagrams.sh](https://github.com/orenlion1/agent-tasks/blob/ceda802460c60a619d78960f4df23a63b12ebddd/docs/diagrams/render-diagrams.sh)
  derives paired theme exports from committed Graphviz sources; the accompanying Markdown
  documents source ownership and regeneration, and uses primary themed images.

The portable examples are adaptations, not copies of that repository's execution contract.
No sibling checkout is required to use them. The remaining provenance describes earlier supplied
references; its screenshot hash is historical, not a digest of the inspected checkout.

The user-supplied Agent Tasks image `TASK-FLOW-DIAGRAM-dark.png` inspired the dark palette,
typography, spacing, and colored action words. The accompanying `TASK-FLOW-DIAGRAM.md` uses
paired images in a primary `picture` element, the model for the guide's Markdown pattern.
The image's SHA-256 is
`5154ef122819f670847451f9e34a82b3ba1ea0067aea7b41fc894e4e48dc8b91`.
The same Agent Tasks diagram set keeps one committed light Graphviz source per diagram and
derives the dark rendition with a committed palette-substitution script (`render-diagrams.sh`),
plus shared per-theme Mermaid configuration files; that practice is the model for the
single-canonical-source derivation guidance.
The reference also contains shapes and filled panels; this adaptation follows the plain-label
rules and is not an exact reproduction. The reference image is not bundled or required
to use this guide.

The supplied one-page document `The Tufte Aesthetic for Grafana Dashboard Design.pdf`
informed the information-hierarchy and context principles. Its SHA-256 is
`256ecbb65a691c83100851ce1331639ff7d8fff00098a3f0786d75f75f92fa90`.
This is an adaptation of the supplied document, not independent verification of Tufte's work
or Grafana standards. Its numbered references 1-6 have no corresponding sources in the
supplied file. Its Singlestat, Bar Gauge, Retro LCD/Basic, exact goal-threshold colors, and
dashboard row-placement recommendations are source-specific guidance, not universal diagram
rules. Its statement about a particular red meeting AA does not establish contrast compliance
for arbitrary backgrounds, text sizes, or themes. The PDF is not required to use this package.
