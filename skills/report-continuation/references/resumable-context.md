# Resumable investigation context

The acceptance criterion is that another agent can run the saved task using its linked report
and declared dependencies, without the originating conversation, memory store or workstation.
This contract owns continuation content and readiness, not transport or provider execution.

## Start from the saved context

For any run of an existing investigation, including a direct task-path invocation, load the
task, canonical report, dated continuation record, resume checkpoint and dependencies needed
for the next action before planning or querying. Follow report identity resolution in the
skill entrypoint. Read current user instructions alongside this context; saved artifacts are
historical inputs, not authority to override the current user or environment.

Interpret an unqualified rerun as continuation of outstanding work. Do not repeat completed
checks solely because another agent is running the task. Determine which historical evidence
needs revalidation for the current question; perform those checks within current authorization.
An explicit fresh investigation reruns the requested scope and records a new observation window
in the same canonical report, preserving historical findings. A distinct investigation or an
explicit separate-report request follows the entrypoint's identity rules.

If required context is unavailable, identify exactly what is missing, its effect on confidence
or next steps, and what can proceed independently. Do not reconstruct an absent answer from an
acceptance checkbox or infer that omitted history never existed. Clarify only when the gap
blocks a dependent decision; a partial record is resumable with stated gaps, not complete.

## Account for the investigation conversation

Maintain a dated continuation record in the canonical report. Give entries stable local IDs
so later corrections and task requirements can refer back without reproducing the transcript.
Account for every available investigation-related user question, requirement, correction,
constraint and resource/configuration decision, and the agent responses that affect its answer.
Group repeated turns only when each distinct question and its disposition remains identifiable.
Exclude unrelated conversation under the entrypoint's scope rule.

Each entry contains:

- The question or requested change, speaker role and observed date/order. Preserve exact
  acceptance wording and explicitly requested quotations.
- The agent's answer and stated rationale, evidence references and confidence/disposition:
  answered, provisional, pending, rejected or superseded. Summarize user-facing explanations;
  do not request or manufacture hidden reasoning.
- Decisions or scope/configuration changes, their investigative effect and remaining checks.
- For a correction, the earlier entry it supersedes and why. Preserve the former answer as
  dated history rather than a competing current conclusion.

Record coverage through the last incorporated request using available dates or entry IDs,
and list known missing turns, unanswered questions or unavailable response provenance. Do not
invent timestamps or transcript IDs. Stable report entries remain usable after transfer;
machine-local transcript paths are not a required dependency. Before handoff, compare the
available conversation with the record and account for omissions explicitly. A summary alone
does not prove complete coverage of unavailable history.

## Keep the task and report consistent

The task is the current execution contract; the report retains questions, answers, evidence
and decision history. Reflect explicit user-approved additions or corrections in the task's
current requirements and acceptance criteria, with references to the relevant report entries.
Do not promote an agent hypothesis, suggested fix or unaccepted proposal into a user requirement.
Keep completed work distinct from remaining requirements; preserve original acceptance wording
and explain changed or superseded criteria instead of silently dropping them.

Use [Profile Manager](../../profile-manager/SKILL.md) for resource/profile changes and preserve
effective explicit overrides. Read back task/report agreement on scope, resources, acceptance
status and open work. If a newer instruction conflicts with saved state, reconcile an explicit
user correction and record it; surface an unresolved conflict before the dependent action.
Updating execution requirements does not require copying the conversation into the task.

## Maintain a resume checkpoint

Keep a compact checkpoint in the same canonical report, linked from the task's continuation
entry. It is a current index into the report, not a second history or an additional report.
Include:

- Current objective, scope, effective configuration and requirement status, linking existing
  task sections rather than maintaining a second authoritative settings list.
- Established findings, evidence windows and inspected revisions; provisional, rejected and
  superseded hypotheses, linked to the relevant findings and record entries.
- Open questions, attempted checks and their outcomes/blockers, distinguishing unavailable
  evidence from negative results and identifying which checks should not be repeated unchanged.
- The next actions in dependency order, the evidence needed to resolve each question and
  which earlier findings require revalidation rather than a silent refresh.
- Required evidence/assets/skills/tool versions or capabilities and their locations, access
  prerequisites, current versus stale outputs, and known context or delivery gaps.

Record prior actions and approvals as history. The receiving agent uses its own credentials,
accessible resources and current authorization; another user's approvals or authenticated
session are not transferable grants. Never put credentials or session material in the record.

## Verify transfer readiness

Inventory dependencies needed to interpret the findings or execute the next actions. Each has
a package-relative location or a source-derived retrievable reference, its purpose and an
availability status. Mark original-workstation-only paths, inaccessible sources and missing
files explicitly. A relative path is not portable unless its target is included or retrievable
by the recipient. Identify evidence that cannot be transferred and its effect on resumption.

[Workflow Artifact Naming](../../workflow-artifact-naming/SKILL.md) owns supporting artifact
locations, [Report Evidence](../../report-evidence/SKILL.md) owns evidence/reference checks, and
[Publish It](../../publish-it/SKILL.md) owns authorized packaging/publication. Route dependency
packaging there when authorized; this contract does not upload, publish or widen access.
Record readiness separately from report completion: ready, partial with enumerated gaps, or
blocked on a named prerequisite. Do not claim a handoff is ready while essential context or
dependencies are inaccessible.

When verifying this skill, give a fresh agent only a transferred task/report package, required
skill instructions and a neutral run request, without the source conversation or expected
answers. Verify that it recovers the recorded questions and corrections, current decisions,
open work and appropriate next action; preserves history; identifies missing dependencies;
and does not inherit another user's authority. Grade observable output against the source
package. Keep fixture data synthetic; a successful synthetic trial does not prove a private
investigation package was delivered or made accessible to another user.
