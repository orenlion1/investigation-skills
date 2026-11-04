# How an investigation flows

Source notes for the README Workflow images. The authoritative Graphviz sources are:

- [Lifecycle and integrations](DIAGRAM-investigation-workflow.dot)
- [Skill routing](DIAGRAM-investigation-skill-routing.dot)

The README embeds each source's `-light.png` and `-dark.png` renditions through a
theme-aware `picture` element. Regenerate all PNG and SVG renditions, including
adaptive SVGs, with [render-workflow-diagram.sh](../scripts/render-workflow-diagram.sh).
The renderer derives both palettes from the same source and checks overlaps.

The overview follows the left-to-right lifecycle and dashed invocation layout of
`agent-tasks/docs/diagrams/HOW-A-TASK-FLOWS-dark.svg`: oval lifecycle activities,
boxed integrations, shaded groups, and matching theme palettes. Solid arrows
show activity handoffs, including Report → Publish. Publication requires
separate authorization. The investigation activity artifacts are `TASK.md`, the saved task,
findings and evidence, and Markdown/PDF reports, respectively. Dashed arrows
from Investigate show invocation of `aws-mcp`, `gcx-cli`, `slack-mcp`, and
`rovo-dev-mcp` as needed for the task, without ordering the integrations. Saving
and closing the editor starts the execution continuation after supplied checks
succeed and the saved task is reread. New tasks receive their title-derived
`TASK-{slug}.md` name; existing tasks keep their established names. At least one
actual resource is required; individual resource fields remain optional.

The routing view expands the activities into their skill responsibilities. Each
activity also carries the editor mode it runs in — Initialize is Open and Edit,
Investigate is Close and Execute — so the routing and lifecycle views describe
the same modes in the same words. Dashed arrows mean invocation or routing; peer
placement does not establish ordering between skills. Only the integrations
needed by the task are invoked. Edit-only and initialization-only requests limit
the continuation. Execution and reporting retain the user's authorization and
the repository's required gates.

Publish is the view's fourth activity. It invokes Publish It and Rovo Dev MCP,
and the single solid arrow is a delivery rather than an invocation: the artifact
lands in a repository or content system so the next lifecycle step can pick it
up. Delivery still requires separate publication authorization.

The workflow is defined by [Templated Tasks](../AGENTS.md#templated-tasks), the
[editor contract](../skills/open-edit-close-execute/references/open-edit-close-execute.md),
and the linked skill entrypoints in the [README](../README.md#skills).
