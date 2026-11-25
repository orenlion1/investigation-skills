---
name: report-continuation
description: "Maintain a canonical investigation report and resumable task context. Use when running or handing off an existing investigation, incorporating follow-on questions, answers, findings or configuration decisions, or reconciling fragmented reports."
---

# Report Continuation

## Overview

Own the identity and progressive content of an investigation's canonical report. Follow-up
work for the same investigation updates that report in place; a new question, resource,
profile signal or rendering format does not by itself create another investigation.
This skill selects and maintains the report, not the editor, provider queries or publication.
The saved task and its linked report must support resumption without the originating conversation.

## When to Use

- An existing investigation receives follow-on questions, material agent answers or findings.
- Task resources or configuration change while the investigation continues.
- The user authorizes reconciling fragmented reports for the same investigation.
- An existing investigation is run again or transferred to another user or agent.

## Load and maintain resumable context

Before planning or querying for an existing investigation, read and apply the
[resumption contract](references/resumable-context.md). It owns context loading, complete
question/answer coverage, task/report reconciliation, the resume checkpoint and transfer
readiness. Apply it again before handoff; unavailable history is an explicit context gap.
Keep current requirements in the task and questions, answers, evidence and history in the
report. In the dependency inventory, name [Publish It](../publish-it/SKILL.md) as the owner that
packages each unavailable dependency once authorized and Report Authoring as the owner of evidence
checks; a handoff never uploads, publishes or copies credentials.

## Resolve the canonical report

Read the source task, relevant conversation turns, existing report links and report contents
before a dependent write. Use an explicit user-selected report first, then a verified existing
canonical binding. Otherwise establish the original report's relationship to the task from its
subject, scope and evidence; use [Workflow Artifact Naming](../workflow-artifact-naming/SKILL.md)
for path resolution, not to substitute a fresh output for an existing owned report.

A newer timestamp, a follow-up suffix or the most recently added task link cannot alone
establish canonical identity. If earlier work already fragmented the investigation, use an
explicit user decision or unambiguous established lineage; clarify a real conflict rather than
silently choosing or merging unrelated investigations. Record the selected report in the task's
report link when authorized. An absent report is an initial creation handled by the normal
report workflow, not permission to guess an existing report.

Create a separate report only for an explicit user request or a genuinely distinct investigation
with a stated reason and relationship to the original. A naming collision, a previous completion
label, a historical evidence window or an additional format is not such a reason. When you plan
or create a separate report, say that Workflow Artifact Naming resolves its name and path and
Report Authoring governs its evidence; never derive its name by adding a numeric suffix to the
earlier report. Never delete, rename, replace or consolidate other reports without authority for those changes.

## Update progressively

At each investigation question/answer, new finding or task-configuration decision, update the
canonical report at the next meaningful work boundary rather than waiting for a final rewrite.
Use the resumption contract's record to capture questions, answers and decisions, including
pending evidence. Preserve user wording when explicitly requested; otherwise summarize
faithfully instead of copying the entire chat.

Read back effective task resources and choices, including additions and explicit overrides.
Reflect their investigative effect in the report's scope/configuration record without silently
reloading a profile, dropping existing resources or exposing credentials. Task/profile writes
remain with their existing owners and caller authorization. Configured resources are not proof
that a query ran; a question, user lead or agent answer is not verified evidence by itself.

Reconcile the main conclusion, affected analysis, recommendations and open questions with each
update. [Report Authoring](../report-authoring/SKILL.md) owns the layout: update its opening
bottom line and tables in place, and keep the continuation record, checkpoint and dependency
inventory below the analysis rather than letting new entries push the findings down. Retain earlier observations with their dates/windows; identify corrected or superseded
conclusions and explain why, rather than leaving contradictory findings in separate sections.
Distinguish the incident timeline from the question/evidence-acquisition timeline. Unrelated UI
actions, repository delivery chatter and generic skill-design discussion do not belong in an
incident report unless they materially affect that investigation.

Mark partial updates in progress and identify missing checks; do not call a live draft or stale
companion complete. [The continuation example](references/progressive-example.md) illustrates
how questions, responses, added resources and new evidence stay in one report. Read it when
applying the workflow to an evolving task or repairing earlier fragmentation.

## Preserve evidence and deliver

[Report Authoring](../report-authoring/SKILL.md) owns claims, citations, Source snapshots and graphs;
[Token Usage](../token-usage/SKILL.md) owns accounting. Preserve each historical observation
window and accounting cutoff. Record new evidence and revision boundaries separately; do not
re-date old evidence, count old usage as new, invent totals or silently refresh accounting.

Use the existing [delivery contract](../open-edit-close-execute/references/investigation-delivery.md#report-formats)
and selected format owners to regenerate enabled companions from the updated canonical content
before final delivery. A format conversion does not create new findings or a new canonical report.
Record current versus stale/historical outputs. After writing, read the saved revision back and
run Report Authoring's evidence checks and the delivery contract's format checks on it, recording
each as passed or pending with its reason; do not invent rendering rules. Source content may be internal when Markdown delivery is disabled; canonical
identity belongs to the investigation, not a required extension.

For explicitly authorized fragmentation repair, integrate relevant earlier follow-up content
into the chosen report, repair authorized task links and identify preserved follow-up artifacts
as historical. Preserve original artifacts and provenance; do not delete them or update an
external publication implicitly. An already published report requires a separately authorized
publication update after local verification.

## Common Rationalizations

- "The question is new, so the report needs a new suffix." Decide identity from the investigation, not the turn.
- "The source task has the update, so the report can wait." Keep the question and current disposition in the canonical report at the next work boundary.

## Red Flags

- A second current conclusion for the same investigation, or a newer task link accepted without checking lineage.
- Agent reasoning presented as verified evidence, or old accounting relabeled as the current revision.
- Companions delivered as current after only the source report changed.

## Verification

- Canonical identity follows the user/task lineage, with no competing current report introduced.
- Relevant follow-on questions, material agent answers, findings and effective resource/config
  decisions are reflected in the same report, with dates, dispositions and explicit gaps.
- Main findings and recommendations reconcile new evidence with retained historical observations.
- Earlier evidence/accounting boundaries and unrelated local work remain intact.
- Enabled companions match the revised canonical content; completed versus pending QA is explicit.
- Context coverage, checkpoint and dependencies pass the resumption contract's handoff checks.
