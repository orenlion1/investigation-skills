# Collection provenance and event evidence

## Attribute every evidence source

For each Evidence index entry, distinguish:

- **Workflow owner:** the skill responsible for the evidence domain, linked to its entry point.
- **Collected with:** the tool, MCP server and operation or CLI/SDK command actually used,
  with relevant version, connection/context and a retrievable saved query/result reference.
  If a generated driver was used, link its source and identify the MCP transport it called.

Ownership is routing, not proof of execution. Do not claim a skill was invoked merely because
it owns the workflow; record historical collection as unknown when the method was not saved.
Keep the canonical Source snapshot and each entry's account/principal, Region, resource,
window/timezone, query filters, resolution/aggregation, caps and observation time sufficient
to recover the evidence. Do not copy credentials or transient sign-in links into the report.
When CLI authentication preceded an MCP query, identify those as separate steps rather than
attributing the resource result to CLI. Assistant summaries remain leads until verified.

## Bring relevant event findings into graphs

When an investigation has scoped AWS access, route AWS-related validation through
[AWS MCP](../../aws-mcp/SKILL.md). After evidence is collected, map relevant deployment,
configuration, restart and workload-lifecycle events to the report's metric, state, profile
and incident timelines. Include events even when correlation is incomplete or the event lies
outside the measured series' coverage.

Treat a relevant source configuration change as event evidence too: a Git merge changing a
Service's ExternalName is a source-state change, not proof that Kubernetes applied it. Keep
the merge and any independently observed Service PATCH as separate events. Carry the resource,
changed field, before/after values and actual event time into the graph handoff.

The coverage record maps each material event to its evidence ID, affected graph(s), or an
explicit relevance/representation reason for exclusion. A prose evidence entry alone does
not satisfy an event's graph coverage. Route visual construction, exact operation labels,
time alignment and zooms to [Diagramming Style's event overlays](../../diagramming-style/references/event-overlays.md).
Name that receiving owner explicitly in the returned plan or result, and apply its workflow
rather than supplying an independent presentation procedure.

Reconcile the coverage record after adding or rebuilding a graph. A significant change must
remain visible across all relevant views, not disappear from older graphs when a profile or
onset view is added. One mention in a caption or an evidence table does not replace its visual
coverage. Use the visual owner for prominence and scope-appropriate context; retain explicit
reasons for excluded views instead of implying that every event caused every signal.

Carry the evidence owner's supported interpretation and its limits into the headline
findings, captions and detail, without strengthening or omitting them. For AWS audit
semantics, use [AWS MCP's interpretation workflow](../../aws-mcp/references/investigation-evidence.md#interpret-the-audited-operation).
Report confidence consistently; graph coverage does not itself establish causation.

Before delivery, verify owner-versus-collector attribution, event coverage and citations in
every selected format. Regenerate affected graphs and outputs through their owners while
preserving canonical report identity and recording changes through Report Continuation.
Resolve formats through Investigation Delivery and Profile Manager; disabled outputs and
their checks remain disabled. No provider refresh is needed for a label-only correction
when saved records already establish the event.
