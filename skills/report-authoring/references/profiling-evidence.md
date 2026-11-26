# Profiling evidence in reports

When an inspected Pyroscope profile materially supports a finding, include its flame graph
beside that finding in every selected report format. This applies to supporting evidence and
bounded negative findings as well as confirmed root causes. Put it among the headline graphs
when it supports the main conclusion. A dashboard link, percentage table or comparison bar
chart does not replace the stack evidence.

Use the inspected profile and cite its evidence identifier. The Evidence index retains the
workload identity, context/datasource, selector, profile type/units, exact window/timezone,
limits and sampling caveats, plus saved results and rendering provenance. Link that entry
from a concise caption stating the measured takeaway and its causal limit. Keep mechanical
descriptions and extended provenance out of the caption; retain qualifications needed to
interpret the finding. A hotspot stays a hotspot until evidence establishes its cause.

[Diagramming Style's profiling view](../../diagramming-style/references/grafana-graphs.md#profiling-views)
owns rendering and caption presentation. If stack data or rendering is unavailable, state the
specific gap beside the affected finding and mark visualization incomplete; do not invent
frames, substitute a schematic or broaden authorized reads to fill it. Deliver other verified
findings with their limits.

Before delivery, map each material profiling finding to a visible, evidence-matched flame
graph and verify scope, values, stack relationships, confidence and selected-format coverage.
A flame graph alone does not validate a root-cause claim, and a query-only request does not
become a report task through this contract.

When a behavior is identified, apply Parallel Grafana Investigation's
[behavior-onset search](../../parallel-grafana-investigation/references/profiling-coverage.md#locate-behavior-onset).
Graph its measured occurrence or intensity across the inspected profile windows, alongside
representative flame graphs, through Diagramming Style. Annotate the observed change and
onset bracket or coverage-boundary limit with evidence IDs; keep missing coverage distinct
from observed nonmatching behavior. Reconcile the earliest-observation claim, sampling limits
and unproven causal interpretation in the opening, detail and caption.
