---
name: workflow-artifact-naming
description: Name and place TASK, SPEC, PLAN, REPORT, LOG and supporting workflow artifacts. Use when resolving artifact paths, creating or updating workflow documents, and scoped artifact renames; exclude production source and test filenames.
metadata:
  version: "0.2.32"
---

# Workflow Artifact Naming

## Overview

Use the portable [naming and placement contract](references/workflow-artifact-naming.md)
when resolving, creating, updating, or explicitly renaming workflow artifacts. Read the
target repository's applicable instructions and preserve its approved destinations.

Resolve identity and location before a dependent write. The packaged
[read-only resolver](scripts/resolve_artifact_names.py) needs Python 3.8 or newer and
only its standard library. It works from any copied skill location with an explicit
target repository root, without a TASK, lifecycle skill, ticket, or external service.

Naming advice and configuration grant no write or migration authority. Inspect
ownership, collisions, symlinks, and local changes before authorized writes; preserve
historical artifacts and user configuration. Re-read successful outputs and their
links. Copy the complete runtime folder together so references and the helper remain
self-contained.

For a caller-requested edit of an existing TASK, use
[Open/Edit/Close/Execute](../open-edit-close-execute/SKILL.md) after verifying its identity,
ownership, and actual location. Pass the exact existing path, including a legacy or
configured location; resolver output does not replace that target or rename its
established slug. Wait for the saved-and-closed/editor/check barrier before dependent work.
Supply the caller's continuation explicitly. This repository continues from a verified saved
TASK into running its requirements and producing matching reports; an explicit edit-only or
initialization-only request limits that continuation. Retain the user's scope and required gates.
Caller-authorized supporting outputs still use this skill's resolver before writes.
Copy both complete skill folders together when using this editor integration; naming
alone remains independent of the editor skill.

When repository policy defines bare `open task` as template creation, the repository caller
owns its local template and temporary `TASK.md`; the shared editor skill receives that
existing draft and does not create or rename it. Resolve the directory before copying;
resolve the final `TASK-{slug}.md` from the saved title only after the editor/check
barrier. Verify the final copy before removing the owned draft, then pass the verified slugged
file to the caller's execution and reporting continuation. Existing-task edits preserve their
established names and use that actual saved path.

## When to Use

- Resolving the name, type, extension, or destination of a TASK, SPEC, PLAN, REPORT, or LOG artifact.
- Creating or updating workflow documents and their supporting outputs.
- An explicitly authorized, scoped rename of an existing workflow artifact.

## Common Rationalizations

- "A numeric suffix avoids the collision." Collisions stop the write; never invent suffixes or overwrite existing artifacts.
- "Production files should match the convention too." Production source, tests, native packages, imports, and repository metadata keep their established conventions.
- "The resolver is optional for a quick file." Resolve identity and destination with the read-only resolver before any dependent write.

## Red Flags

- A rename outside the explicitly authorized scope.
- A guessed destination instead of the documented precedence (explicit destination, repository configuration, defaults).
- An overwritten artifact, broken reference, or unnoticed symlink.

## Verification

- The resolver's output matches the written path, name, type, and extension.
- Saved files were reread and their identity, content, format, and links verified.
- Pre-existing artifacts, configuration, and references remain intact.
