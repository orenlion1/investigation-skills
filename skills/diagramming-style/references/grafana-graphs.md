# Grafana Data and Interactive Graphs

Part of the [Diagramming Style Guide](diagramming-style.md); its visual, theme, caveat, and
delivery rules apply here.

Enrich data-based findings with relevant graphs from Grafana CLI when access and data are
available within the task's authorized scope. Prefer a graph that answers the investigation
question: a time series for trends, an aligned comparison for related metrics, a distribution
for variation, or a trace waterfall for a selected request. Keep architecture/dependency
diagrams alongside measured behavior when both help; correlation does not establish a
dependency, execution order, or root cause.

- Resolve the explicit Grafana instance/context and organization. Use the caller's supported
  authentication workflow, opening browser sign-in and waiting when needed. Discover the
  available gcx commands, datasource UIDs/types, and actual query capabilities; do not silently
  switch instances or treat catalog visibility as successful data access.
- Query bounded data with the selected resource filters, exact time window/timezone, and
  suitable step or aggregation. Preserve units, timestamps, missing intervals, series
  selection, and source-supported thresholds. Compare compatible windows and resolutions;
  do not invent points, interpolate unexplained gaps, or equate missing data with zero.
- Link the graph to short evidence identifiers and record the instance, datasource/resource
  IDs, query or panel identity, variables, window, step/aggregation, observation time, and
  limits in the evidence index. Retain the permitted query result and reproducible plotting
  source in caller-resolved paths. Keep credentials and unnecessary sensitive payloads out.
- When the current host supports interactive graphs, create the requested interactive
  graph/view from the verified query data. Verify that it uses the intended
  query, datasource, and time range. Test visible rendering and relevant interactions,
  such as time selection, zoom, series selection, or trace filtering; structured content
  or HTML retrieval alone does not prove an interactive view works.
- Provide a readable static representation for every requested static deliverable. Use a
  supported export or render the same saved query data with standard plotting tools, with
  the same graph identifier, meaning, units, window, and adjacent evidence/captions. Include
  it in the diagram inventory and matching Markdown/PDF outputs. A link to an interactive view is not a
  replacement for the static graph; a PNG/PDF cannot preserve hover, zoom, or filtering.
- Apply the light/dark and delivery-size checks to measured-data graphs too. Keep meaningful
  axes, ticks, units, and series labels; distinguish lines through labels or styles as well
  as color. Put data coverage, sampling limits, uncertainty, and other caveats beside the
  graph, preserving them across interactive and static delivery. Do not replace an accurate
  axis or scale with decorative grouping or an invented visual maximum.
- If gcx, a datasource, or an interactive view is unavailable or denied, record the exact limitation
  beside the affected finding. Use authorized saved data or an available static view and
  keep any unverified interaction claim explicit. Do not fabricate telemetry, broaden
  permissions, change monitoring resources, or block unrelated diagrams solely to add a
  graph. Retain existing investigation-entry requirements when using gcx or other tools.

Grafana enrichment is optional to this portable package. Installing or copying the
diagramming skill does not itself require a Grafana account, sibling skill, server, or host
with interactive graph support, and it grants no additional resource or publication authority.

## Profiling views

When the report owner requires a Pyroscope flame graph, render the actual inspected stack
results or a verified export. Preserve caller/callee nesting, inclusive widths, self values,
units and sampling semantics. Do not sum overlapping ancestor/descendant shares. Ordinary
frame rectangles encode sample weight and are meaningful structure, not decorative boxes.

Use a readable full stack or a clearly identified subtree focus. Keep the original profile
and a reproducible rendering source; record focus, depth limits, omitted frames and the
percentage denominator in linked evidence detail. Retain tiny frame widths when omitting
unreadable labels. An aggregate symbol list cannot reconstruct caller relationships; if only
such a list is available, report that limitation instead of inventing a flame graph.

Lead the caption with what the profile establishes about the investigated problem, followed
by the material uncertainty and an evidence link. Prefer one or two short sentences. Do not
narrate the image, explain colors or reading direction, or repeat query metadata there;
place those details in the linked Evidence index or methods. Keep an essential scope or
normalization qualification adjacent when omitting it would mislead. Accessible alt text
still identifies the stack/finding without copying a long caption.

For example: "S3 parsing accounts for 85% of sampled CPU during the incident. The profile
locates the hot path; duplicate replay remains unverified. [E1]" This is illustrative, not
a production observation. Apply this guide's existing theme, delivery-size and static-format
checks; stack evidence must remain readable in each selected output.
