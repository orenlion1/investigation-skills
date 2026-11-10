---
name: source-investigation
description: Trace an investigated problem to its source code across repositories — follow execution paths and consumers, search the authorized provider workspace beyond the supplied repository, establish an evidence-supported root cause with a concrete fix and validation, pin citations to the inspected commit, and verify the deployed revision. Use when a task supplies a source repository and the observed behavior, error, or alert must be explained by code.
---

# Source Investigation

## Overview

When a task supplies a source code repository, including through a loaded resource profile,
trace each investigated problem to the relevant source code. The supplied repository is a
starting point: search beyond it for the services, shared libraries, callers, consumers, and
configuration that explain the observed behavior. The provider-scope authorization grant (what
a supplied repository authorizes you to search) is repository policy and lives in the root
routing files; this skill owns how the investigation is done within that scope.

When this skill runs as part of an investigation, use the root
[soft delivery budget](../open-edit-close-execute/references/investigation-delivery.md)
from request receipt; carry its original start into this work and check it at control boundaries.
Reuse verified setup and shared evidence; preserve this skill's required coverage and gates.

## When to Use

- A task names a repository and asks why an observed error, alert, or behavior happens.
- An execution path crosses repository or service boundaries and consumers must be traced.
- A root cause, concrete fix proposal, or deployed-revision verification is required.

## Tracing Workflow

- Resolve the authorized search scope from the supplied repository per the root policy grant,
  honor any explicit narrower scope, keep searches relevant to the task, and record the
  repositories and search scope inspected.
- Trace observed errors, alerts, and affected resources through the relevant execution paths
  and dependencies. Inspect the actual implementation and consumers before drawing a
  behavioral conclusion, including across repositories when the path crosses a boundary.
- Use the provider's approved tooling and existing access for discovery, search, and
  inspection; reads only. Authentication requirements and separate gates for mutations,
  messages, publication, and deployment still apply.

## Root Cause and Fix

- Identify an evidence-supported root cause and propose a concrete fix. Connect the symptom,
  triggering conditions, causal code path, and proposed change; include how to validate the
  fix.
- Cite the repository, exact inspected commit, file path, line range, and commit-pinned
  source URL beside each material causal claim and proposed change location, using the
  [report-evidence](../report-evidence/SKILL.md) index discipline.
- Verify the deployed source revision when available. If deployment provenance is
  unavailable, distinguish findings in the inspected revision from claims about production.
- If evidence cannot establish a root cause or fix, report the unresolved gap, clearly label
  hypotheses and conditional proposals, and state the evidence needed to confirm them; never
  invent a causal explanation to satisfy this requirement.

## Common Rationalizations

- "The stack trace names the file, so that's the root cause." The frame shows where the
  symptom surfaced; trace the triggering conditions and callers before concluding.
- "It's in the supplied repo, so the search is done." The supplied repository is a starting
  point; consumers and shared libraries elsewhere in the authorized scope may own the cause.
- "The code on main shows the bug, so production has it." Verify the deployed revision, or
  label the finding as inspected-revision-only.
- "Something must be reported as the cause." An unresolved gap with labeled hypotheses is a
  valid, honest finding; an invented cause is not.

## Red Flags

- A behavioral conclusion drawn without inspecting the implementation and its consumers.
- A causal claim without a commit-pinned citation beside it.
- Production claims made from code alone, without deployment provenance or a disclaimer.
- A search scope wider than the provider grant, or an unrecorded search scope.
- A proposed fix with no validation path.

## Verification

- [ ] Inspected repositories and search scope are recorded.
- [ ] Each material causal claim and proposed change location carries a commit-pinned
      citation.
- [ ] The symptom, triggering conditions, causal path, fix, and validation connect.
- [ ] Deployed-revision identity is verified or its absence disclosed.
- [ ] Unresolved gaps are labeled with the evidence needed to close them.
