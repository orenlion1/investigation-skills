# Archive reader investigation

Synthetic fixture, not production findings. Status: partial, source provenance unresolved.

## Finding

The saved inspection establishes the alert threshold behavior and active parsing frames.
The original deadlock conclusion is superseded. Duplicate active-file scheduling is a static
candidate at synthetic revision r7, not a verified deployed defect. See
[saved inspection](../../evidence/inspection.json).

## Continuation record

Coverage: all available investigation requests Q1-Q5 through Q5. Original chat is not included;
earlier unrecorded turns, if any, cannot be recovered. Entries are ordered; exact timestamps
were not retained.

| Entry | User question or decision | Agent response and disposition |
| --- | --- | --- |
| Q1 | Explain why the alert repeatedly resets. | Answered: the saved rule has a pending period and no recovery hold-down. Below-threshold observations explain reset behavior; this does not identify the CPU driver. |
| Q2 | Did archived replay deadlock the reader? | Earlier answer: yes, a deadlock explains the incident. Superseded by Q3; the answer overreached the available evidence. |
| Q3 | Does active parsing actually prove deadlock? Correct the answer if needed. | Corrected: active parsing frames do not establish a wait-for cycle or progress. Deadlock is unverified, neither established nor excluded. Source inspection finds a duplicate-work candidate, not proof of its incident execution. |
| Q4 | Add a requirement to map the deployed binary to the inspected source before attributing the incident to that scheduling defect. | Accepted, pending. The previous agent did not add this requirement to the task acceptance tests. Required deployment metadata is missing. A proposed concurrency test remains an agent suggestion, not an accepted user requirement. |
| Q5 | Use UTC for further incident timestamps and preserve the historical evidence window. May we publish the report? | UTC and window preservation accepted. The prior operator approved publication in their earlier session; no publication occurred. Historical approval does not authorize this receiving user or agent to publish. |

## Resume checkpoint

- Objective: complete [the task](../tasks/TASK-archive-investigation.md) with the corrected Q3
  assessment and Q4 requirement. Task acceptance tests still omit Q4; reconcile that explicit
  requirement. Q5 sets UTC for further timestamps; do not invent dates for this ordered record.
- Established: alert mechanism, parsing frames and source candidate, bounded by the saved
  inspection. Unresolved: concrete replay requests, deployed revision and deadlock.
- Completed checks: the saved rule, profile frames and static candidate were inspected.
  Repeating those offline reads adds no incident evidence. No concurrency reproduction ran.
- Attempted check: deployed revision lookup failed because build metadata was not transferred.
  Next: obtain that metadata through the receiving user's authorized source access, then compare
  the deployed revision with r7. Until available, keep incident attribution provisional.
- Independent work: reconcile task requirements and the Q&A/checkpoint, inventory evidence
  accessibility, and report remaining prerequisites. This package authorizes no provider calls.
- Output: current Markdown only. PDF and HTML are disabled. No external report was published.

## Transfer dependencies

| Dependency | Purpose | Location and availability |
| --- | --- | --- |
| Saved inspection | Retained observation window, rule, frames and inspected revision | [Package evidence](../../evidence/inspection.json), included |
| Deployment metadata | Map the deployed binary to source for Q4 | `../../evidence/deployment-build.json`, missing; original workstation copy not transferred |
| Report Continuation skill | Load and reconcile saved context | Supplied separately with this exercise; no originating conversation required |

Readiness: partial. The task/report can be reconciled from included files, but missing deployment
metadata blocks defect attribution. Credentials and prior operator sessions are not included.

## Historical observation and accounting

Synthetic historical window W1 and source revision r7 are fixed. Accounting was unavailable;
no token totals or duration are asserted. This transfer does not refresh that window.
