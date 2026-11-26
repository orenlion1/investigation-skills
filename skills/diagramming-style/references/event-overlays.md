# Evidence event overlays

Use saved audit, deployment, restart, configuration or workload events supplied by the
caller with relevant measured-data graphs. This portable reference governs presentation;
the caller owns authorized collection, evidence attribution and required event coverage.
An overlay needs an observed event, not a confirmed causal explanation.

## Label the operation, not its storage provider

Use the API surface/kind, actual operation, resource identity, event time and short evidence
identifier. Include the changed field when it explains the operation. For example:

```text
Kubernetes StatefulSet pod-template PATCH
utility/example-store · 06:11:23 UTC [E27]
```

Given an evidence-owner-validated interpretation, an adjacent detail view or caption can
display its annotation path/value and interpretation:
"The PATCH sets kubectl.kubernetes.io/restartedAt; the payload is consistent with a rollout
restart. The exact CLI command was not captured. [E27]" This example is illustrative.
"AWS patch 06:11" hides the operation when CloudWatch merely stores Kubernetes audit logs.
Display only the operation and interpretation supplied by the evidence owner; this guide
does not derive API semantics or deployed-version conclusions.

Keep uncertainty and causal qualifications in adjacent captions/prose under the main style
guide. Render factual operation/resource labels in the chart and place the supplied
interpretation beside it.

## Make material state changes visible across views

Use a clearly visible marker and labelled callout or dedicated lane for a material change;
do not reduce it to an unexplained tick or bury it only in a caption. Show the resource,
changed field and before/after values when supplied, with time and evidence ID. For example,
label a source-only event as a Git merge changing a Service ExternalName from one value to
another; label an observed Kubernetes Service PATCH separately at its own time.

Use one descriptive display name for the same evidence event across graphs: evidence ID,
changed field or operation, and identifying resource/value, such as
`[E5] ExternalName: old.example.com → new.example.com`. Keep that name on markers, callouts
and event lanes; wrap it or provide a visible companion rather than substituting a generic
"Git merge", "source change" or bare ID in another view. Retain operation, resource and time
as context. Distinct events under one evidence ID still need distinct descriptive names;
a source merge and an observed Service PATCH never become one event because the field matches.

Repeat that event identity on each relevant metric, alert-state and profile timeline. Keep
the overview and add focused context where the label or distinct events would otherwise be
lost. For a narrow or non-temporal view, use a visible companion timeline or context callout,
not a timestamp on an unrelated axis. Do not widen measured coverage or imply a deployed
state from source history. When a graph is revised, preserve earlier relevant event annotations
and recheck their prominence at delivery size in both themes and in the assembled report,
including whether it loads the intended regenerated assets. The caller's evidence owner
decides relevance and causal interpretation.

## Align events without inventing coverage

- Normalize event times to the plotted timezone and retain the original timestamp/offset in
  linked evidence. Match account/cluster, namespace and workload before aligning records.
- Draw an event marker, interval or lane with a distinct line/shape and evidence ID. Preserve
  timestamp precision in saved data even when an overview label rounds it. Use separate
  markers for controller PATCH, pod delete/create and process start; they are not one event.
- Keep measured samples, units, resolution and missing intervals intact. If an event falls
  after the query cutoff, extend the context axis or add an aligned event panel, but leave
  unmeasured space blank and state the coverage cutoff beside the graph. Never extrapolate
  CPU, add post-event Normal states or imply observed recovery beyond the data.
- Add a focused event-time view when an overview merges distinct events. For example,
  a multi-day overview can accompany a minute-scale lifecycle lane. Preserve the overview
  and use independent lanes for telemetry and audit events when their semantics differ.
- For non-temporal views, use a companion timeline or an adjacent evidence callout rather
  than placing a timestamp on an unrelated axis. Describe incomplete correlation beside the
  figure. The caller owns which material events require representation.

## Verify and deliver

Render from saved inputs with reproducible plotting code. Retain source hashes, event times,
field selection and output identities with the caller's evidence. Change palettes only
between themes; check event position, geometry, titles and label parity. Regenerate all
delivered variants after a label or event changes and update captions and alt text.
Inspect both light/dark exports at delivery size for clipped or overlapping labels, event
lines obscuring samples, legibility and distinct event markers. Verify the composed output
loads the intended assets and remains readable. A hash match or successful render alone
does not establish visual correctness. Apply only the caller's selected report formats.
