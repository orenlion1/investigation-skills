# gcx query mechanics

Command mechanics for the direct reads that
[Parallel Grafana Investigation](../../parallel-grafana-investigation/SKILL.md) owns. Every
command passes the resolved `--context`; refresh, context and authentication rules are in
[SKILL.md](../SKILL.md).

## IRM context routing

Select context by command family before authentication, discovery or execution:

- Every `gcx irm ...` command, including incidents and OnCall alert groups, passes
  `--context` from the effective `Grafana IRM context` / `GRAFANA_IRM_CONTEXT` resource.
- Other command families use the effective `Grafana context` / `GRAFANA_CONTEXT`, or the
  explicit context of their configured historical endpoint.

These settings are independent: never substitute the ordinary Grafana context, an endpoint
context or current-context for a missing IRM context. Resolve missing IRM context with the user
before dependent reads; other authorized work may continue. Explicit user instructions override
TASK values, which override profile values. Verify/authenticate each selected context separately;
IRM setup probes such as `config check` and `login` target that same IRM context. Keep the
context mapping in delegated briefs and execution receipts. Assistant prompts remain on their
ordinary/endpoint context; IRM commands suggested by Assistant or bundled skills still use the
IRM setting. Do not share an Assistant execution across different contexts.

For example, a bounded prior-incident search is:

```sh
gcx irm incidents list --context "$GCX_IRM_CONTEXT" \
  --from "$HISTORY_START" --to "$HISTORY_END" --limit 20 -o json
```

Filter returned candidates for the incident's terms and verify relevant detail within the
read budget. Check installed help for filtering semantics and disclose truncation.

## Procedure

1. Resolve the signal, selected context, requested service/resource, and time range. Ask only for
   missing information that changes the query. Report the timezone and actual interval used.
2. Discover the datasource with `gcx datasources list`, filtering by `--type` and optionally
   `--name`, and use the returned UID with `-d`. An ambiguous match needs clarification. A cap
   is a sample, not a complete inventory; widen discovery within the same context when necessary.
3. Inspect labels or metadata before inventing selectors. `gcx metrics labels` supports
   `--metric`, `--match`, and `--label`; `gcx logs labels` supports `--label`. Check installed help:
   do not assume every discovery command supports time-range or result-limit flags.
4. Use dedicated signal commands and structured output. Bound time and results; avoid broad log
   selectors or full trace bodies merely to test a connection. For unknown commands, use
   `gcx help-tree <group> -o text` and the command's `--help`, not raw API passthrough.

## Signal queries

Replace the UID and selectors after discovery. The 15-minute window is an example, not a
replacement for the user's requested time range.

```bash
GCX_PROMETHEUS_UID='<confirmed-prometheus-uid>'
gcx metrics query --context "$GCX_CONTEXT" -d "$GCX_PROMETHEUS_UID" \
  'up{job="<discovered-job>"}' --from now-15m --to now --step 1m -o json
GCX_LOKI_UID='<confirmed-loki-uid>'
gcx logs query --context "$GCX_CONTEXT" -d "$GCX_LOKI_UID" \
  '{job="<discovered-job>"}' --since 15m --limit 20 -o json
GCX_TEMPO_UID='<confirmed-tempo-uid>'
gcx traces query --context "$GCX_CONTEXT" -d "$GCX_TEMPO_UID" \
  '{ resource.service.name = "<selected-service>" }' --since 15m --limit 5 -o json
```

- Use a datasource of the matching type for each command; do not reuse a Loki UID for metrics
  or traces.
- Prometheus instant queries use `--time`; range queries use `--from`/`--to` or `--since` with
  an appropriate `--step`. Do not combine instant and range flags.
- Metrics queries have no `--limit`: narrow selectors or use suitable PromQL aggregation/topk
  and disclose that choice.
- `--limit 0` on logs or traces is uncapped. Do not truncate output while claiming a complete
  result.
- Use `--share-link` on supported successful signal queries when a Grafana Explore link helps
  the user reproduce the result.

## Inventory and product queries

Use the relevant dedicated read command with filters and caps:

```bash
gcx resources get dashboards --context "$GCX_CONTEXT" --limit 20 \
  --json metadata.name,spec.title
gcx alert rules list --context "$GCX_CONTEXT" --limit 20 -o json
```

Specialized SLO, IRM, Synthetic Monitoring, profiling, or other product queries use their
installed command groups and task guidance with the same context rule. Assistant output does not
replace these direct queries or authorize remediation.

## Analysis and reporting

Correlate timestamps, resource identifiers, alerts, metrics, logs, and traces across the symptom
window and a relevant baseline. Test competing explanations. Return observed facts, the
supported cause or ranked hypotheses, evidence, gaps, and the next discriminating check. State
when root cause remains unconfirmed; an error string or correlation alone does not establish it.
For saved investigations, follow repository Report Authoring, Workflow Artifact Naming, Token
Usage, and required Markdown/PDF report contracts.
