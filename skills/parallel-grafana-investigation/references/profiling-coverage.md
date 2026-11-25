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

Discover the selected context's profiling datasource, service identity, available profile
types, labels and time coverage. Inspect relevant CPU stacks for the affected workload and
time windows. Compare a suitable baseline or recovery period and other affected pods when
those comparisons are available inside the authorized scope; state missing comparisons.
Do not assume profile labels match metric labels. Verify workload identity from returned
labels and corroborating signals, recording any attribution gap.

Retain datasource UID, selector, profile type, exact timestamps/timezone, limits/truncation,
observed stacks and sampling/scaling metadata with the result. Distinguish inclusive from
self values; do not sum overlapping ancestor shares or convert sampled totals into actual
CPU utilization without verified normalization. Compare like-for-like windows and expose
uncontrolled workload, sampling and aggregation differences.

When deadlock is suspected, inspect available contention/blocking or wall profiles alongside
CPU profiles. Active CPU frames do not prove nonprogress or deadlock, and absent/short sampled
contention does not exclude unfinished waits. A restart followed by improvement establishes
temporal association; it does not establish the triggering defect or state that was cleared.

## Hand off source leads

When profiles identify application hotspots and a task supplies a VCS repository, pass the
verified service/symbols, identity caveats and windows to the orchestrating session's
[Source Investigation](../../source-investigation/SKILL.md) workflow. Its owner discovers
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
