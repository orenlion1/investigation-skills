# Profiling decision and delivery coverage

## When profiling applies

Make and record a profiling decision for every root-cause investigation handled by this
workflow. Unexplained sustained/high CPU, CPU-related alert flapping, suspected spinning or
deadlock, and a replay/processing CPU hypothesis require the direct branch to discover
Pyroscope coverage and attempt relevant incident-window profile reads. Do this when the
symptom is established, without waiting for a user to suggest profiling or an Assistant lead.
Memory, latency and contention investigations assess relevant allocation, wall or lock
profiles where supported. Do not invent an unsupported profile type.

Keep exact-query, inventory, setup-only, history-only and explicitly narrower requests within
their existing scope. A profiling decision never authorizes extra resources, a new context,
an expanded time window, instrumentation changes or another Assistant prompt. Record an
explicit user exclusion as a scope limitation. The existing pair owns all internal profiling
discovery and follow-ups; use the normal gcx setup, refresh and query mechanics.

## Gather and interpret

SKILL.md Workflow step 2 owns the discovery, comparison, retention and handoff steps; this
section adds their interpretation. Include service identity in discovery. Do not assume
profile labels match metric labels. Verify workload identity from returned labels and
corroborating signals, recording any attribution gap.

Retained metadata covers datasource UID, selector, profile type, exact timestamps/timezone,
limits/truncation, observed stacks and sampling/scaling. Do not sum overlapping ancestor
shares or convert sampled totals into actual CPU utilization without verified normalization. Compare like-for-like windows and expose
uncontrolled workload, sampling and aggregation differences.

Active CPU frames do not prove nonprogress or deadlock, and absent/short sampled contention
does not exclude unfinished waits. A restart followed by improvement establishes
temporal association; it does not establish the triggering defect or state that was cleared.

## Locate behavior onset

When a profile identifies a material behavior, attempt to locate its beginning in earlier
profiles within the authorized window. Define an observable signature from the inspected
stack and its measured activity before searching: ordinary frame presence is not evidence
that an abnormal workload began. Keep the behavior's name or causal interpretation separate
from that signature; parsing activity alone does not prove event replay.

Reuse saved profiles and inspect comparable earlier windows, coarsely first and then more
finely around a change. Retain the actual returned resolution, workload/pod identity,
profile type, sample totals, self/inclusive shares and limits. Explain any activity threshold
and retain continuous measurements rather than presenting the threshold as a defect test.
Do not assume behavior is monotonic: earlier episodes may disappear and recur. Long merged
windows can dilute short episodes, and a changed sample share can reflect a changed denominator.

Report the earliest observed matching window and the nearest inspected nonmatching window,
with their widths and gaps, as an onset bracket rather than an exact start. A bracket does
not exclude an earlier transient episode outside the inspected coverage. If the earliest
available window already matches, report onset unresolved at that coverage boundary; the
bucket's start is not the behavior's start. Say it predates the window only with separate
evidence supporting that bound. Empty, missing, truncated or incomparable profiles are not negative samples.
Record unavailable history or capability instead of silently widening scope or inventing a
start time. Hand these measurements and limits to Report Authoring for a timeline beside the
representative stack evidence.

## Hand off source leads

The handoff to [Source Investigation](../../source-investigation/SKILL.md) carries the
verified service/symbols, identity caveats and windows. Its owner discovers
relevant repositories, traces callers, scheduling/retry behavior and progress guarantees,
and checks the deployed revision. Keep the direct branch's gcx-only boundary. Candidate code
defects remain hypotheses until connected to incident execution; do not turn an observed
hotspot into a confirmed production bug.

## Required delivery outcome

Record one of these outcomes with the Source snapshot or retained audit record:

- **Inspected:** retain the actual discovery/profile query results and their limits, including
  successful empty reads. Empty results establish only the searched scope, not health.
- **Unavailable:** retain the attempted operation and sanitized authentication, permission,
  transport, retention or capability failure. No configured profiling datasource is an observed
  discovery result; do not label a skipped query as unavailable.
- **Excluded:** state the specific symptom-relevance or user-scope reason. Do not use elapsed
  time, a completed threshold analysis or an unrelated seed repository as an exclusion reason.

Before delivery, verify that applicable profiling was inspected or a concrete limitation was
recorded. An unexplored signal is an incomplete coverage gap, never silent success. Explain
the alert's threshold/reset/notification mechanism separately from the workload CPU driver.
If the latter or its source link remains unconfirmed, deliver the verified findings with that
gap and the evidence needed to close it; do not invent certainty or withhold useful findings.

Hand the retained profile results and metadata to
[Report Authoring's profiling evidence contract](../../report-authoring/references/profiling-evidence.md)
when they support a report finding; that owner decides graph coverage and placement.
[Diagramming Style](../../diagramming-style/SKILL.md) renders the onset timeline and stack
evidence. Name both receiving owners in the returned handoff, including a collection plan.
