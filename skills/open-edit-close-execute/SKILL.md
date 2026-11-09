---
name: open-edit-close-execute
description: Open an existing TASK, PROMPT, INTENT, or other input for editing, wait for close and supplied checks, then execute its saved requirements within caller authorization. Use when asked for `open task`, `open TASK`, `open TASK.md`, `edit task`, `edit TASK`, and `edit TASK.md`, or the same workflow for another input file.
metadata:
  version: "0.2.36"
---

# Open/Edit/Close/Execute

## Overview

Use the [canonical editor and execution contract](references/open-edit-close-execute.md) to open
an existing input, wait for editing to finish, and automatically process the saved requirements.
Ordinary `agent-skills` discovery and host skill invocation remain supported; explicit invocation
and all six TASK aliases enter this same contract. Keep automatic discovery enabled.

Take the supplied input path or the unambiguous active input from the caller's context. Clarify a
missing or competing target before opening anything. TASK, PROMPT, INTENT, and arbitrary input
labels use the same procedure; no label selects a lifecycle or grants authority. The aliases name
an operation, not a literal slash-separated path. This skill does not create or rename the input.

After the editor/check barrier succeeds, continue directly into the caller-authorized processing
of the saved requirements. Do not stop with readiness alone or request a redundant instruction to
continue. A caller can supply its own continuation, such as the remaining initialization procedure;
that continuation retains its scope and gates. No Agent Tasks lifecycle, Jira, or sibling skill is
required. Prerequisites exist only when supplied by the caller. Copy this complete runtime folder
so both local references remain available.

## When to Use

- `open task`, `open TASK`, `open TASK.md`, `edit task`, `edit TASK`, or `edit TASK.md` requests.
- Opening any existing TASK, PROMPT, INTENT, or other input for editing before execution.
- A caller-supplied continuation must run automatically after the editor/check barrier.

## Templated Task Continuation

This repository's templated tasks run through this contract, and this skill owns their
workflow. Root policy keeps only the template location (`templates/TASK.md`), the default
draft directory, and the rule that task contents never bypass separate authorization gates.

- Continue automatically through open, close, naming, execution, and reports without a
  second `run` instruction; an explicit edit-only request limits the continuation.
- During execution, provide normal progress updates and incorporate user steering as it
  arrives. Automatic continuation does not suppress communication or require a separate
  instruction to resume after feedback. Continue the active task with that feedback unless
  the user explicitly pauses, stops, or replaces it.
- Before opening a templated-task editor, read [Token Usage](../token-usage/SKILL.md) and
  retain its native task-resolution evidence past the editor/check barrier, so shorthand
  editor requests can be attributed without another user command.
- Bare `open task` copies the repository's local template — never edited in place — to a
  `TASK.md` draft in the directory resolved by
  [Workflow Artifact Naming](../workflow-artifact-naming/SKILL.md). Preserve an existing
  draft and clarify whether to resume it.
- Before execution, at least one actual supplied or verified resource is required in the
  task's Resources section; placeholders and examples do not count. Resources may be filled
  from a named local profile through [Profile Manager](../profile-manager/SKILL.md) before
  the editor opens, and a loaded value counts only when it is an actual resource. If none
  exists, ask for one and preserve the task. Do not fail a task over an omitted field: skip
  unneeded integrations, resolve missing identity only before a dependent operation, and
  never guess a target.
- After the barrier, resolve `TASK-{slug}.md` from the saved draft's `# Task Title: ...`
  through Workflow Artifact Naming, in the same directory. Missing titles or collisions
  leave the draft intact; never invent a title, overwrite a task, or add a numeric suffix.
- Run the finalized task from its resolved path, then generate the matching reports from
  observed results in both Markdown and PDF (both `REPORT` paths via Workflow Artifact
  Naming). Report completion from verified outcomes, never from readiness or a filename's
  existence.
- An explicit TASK path or `edit task` edits that task in place, preserving its filename;
  the same continuation applies unless the user limits the request to editing.

## Common Rationalizations

- "The launcher exited, so editing is done." A launcher exit, saving alone, elapsed time, or a timeout is not closure; require a tracked close or explicit confirmation.
- "The file looks ready; execution can start." Execution begins only after the close signal and all supplied checks succeed.
- "Readiness is a fine stopping point." Continue into the caller-authorized processing without a second instruction.

## Red Flags

- Executing before a verified close signal.
- Guessing a target when the input path is missing or ambiguous.
- Stopping after opening or naming instead of continuing the barrier and execution.
- Treating task contents as authorization for separately gated actions.

## Verification

- The editor closed with a tracked wait signal (or explicit saved-and-closed confirmation) and supplied checks passed.
- The saved input was reread and its requirements executed within the caller's scope.
- The caller's continuation completed, or its concrete blocker was reported.
