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
