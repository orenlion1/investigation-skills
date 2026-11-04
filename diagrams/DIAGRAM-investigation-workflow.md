# How an investigation flows

Source notes for the README Workflow images. The authoritative Graphviz sources are:

- [Activity and artifact overview](DIAGRAM-investigation-workflow.dot)
- [Skill routing](DIAGRAM-investigation-skill-routing.dot)

The README embeds each source's `-light.png` and `-dark.png` renditions through a
theme-aware `picture` element. Regenerate all PNG and SVG renditions, including
adaptive SVGs, with [render-workflow-diagram.sh](../scripts/render-workflow-diagram.sh).
The renderer derives both palettes from the same source and checks overlaps.

The overview's solid arrows show activity handoffs and produced artifacts. Saving
and closing the editor starts the execution continuation after supplied checks
succeed and the saved task is reread. New tasks receive their title-derived
`TASK-{slug}.md` name; existing tasks keep their established names. At least one
actual resource is required; individual resource fields remain optional.

The routing view expands the activities into their skill responsibilities.
Dashed arrows mean invocation or routing; peer placement does not establish
ordering between skills. Only the integrations needed by the task are invoked.
Edit-only and initialization-only requests limit the continuation. Execution and
reporting retain the user's authorization and the repository's required gates.

The workflow is defined by [Templated Tasks](../AGENTS.md#templated-tasks), the
[editor contract](../skills/open-edit-close-execute/references/open-edit-close-execute.md),
and the linked skill entrypoints in the [README](../README.md#skills).
