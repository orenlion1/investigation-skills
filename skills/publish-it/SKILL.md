---
name: publish-it
description: Publish an existing task and/or report to Confluence with original files as downloadable supporting evidence, diagrams, PDF and cited assets. Use when handling publish it or publish-it requests with a TASK path, report path, or both; resolve related artifacts, package them and verify the published page. This does not run an investigation or publish a software release.
---

# Publish It

## Overview

Package existing investigation artifacts and publish them to the caller's Confluence destination.
This skill owns artifact selection, page composition, uploads, media references, publication and
read-back. Use [Rovo Dev MCP](../rovo-dev-mcp/SKILL.md) for authentication, scoped grants,
tool discovery and transport; keep publishing decisions here.

## When to Use

- `publish it` or `publish-it` requests with a saved TASK path, report path, or both.
- Authorized Confluence publication of an existing investigation task or report.
- Packaging companion artifacts, diagrams, and PDFs for a published page.

## Arguments

Accept `task` and/or `report` as explicit local file paths, plus the Confluence destination.
These are arguments to the agent's skill invocation, not an installed shell command:

```text
publish it --task docs/tasks/TASK-example.md --parent <Confluence parent URL>
publish it --report docs/reports/REPORT-example.md --parent <Confluence parent URL>
publish it --task <TASK path> --report <report path> --page <existing Confluence page URL>
```

`task` identifies the parent TASK document; `parent` identifies the Confluence page that will
contain a new child report page. `page` selects an existing report page to update. Do not confuse
these identities. Accept equivalent natural-language arguments and a destination supplied by
the user or verified saved task. Resolve ambiguous or conflicting inputs before dependent writes.
At least one task or report is required. Do not reuse a previous investigation's site or parent
as a default. An explicit publish request authorizes the selected page and its supporting uploads;
it does not authorize investigation execution, messages, tickets, source control, releases, changes
to production resources, or changes to other pages. Existing authorization needs no repeat prompt.

## Resolve and package

1. Read the supplied saved files and verify ownership, format, title, identity and relevant policy.
   Honor any active editor/check barrier before consuming its task; do not reopen an editor just
   to publish an already saved input. Resolve a relative path against the caller's target repository.
2. Locate an omitted companion using explicit artifact links, canonical metadata, or the verified
   task identity through [Workflow Artifact Naming](../workflow-artifact-naming/SKILL.md).
   Honor explicit paths and configured directories; never select the latest similarly named file,
   rename an existing task, or scan unrelated directories. Reject conflicting task/report identities.
   If no companion exists, publish the available input within scope and disclose what is missing;
   do not claim both were published. If the caller requires both, stop that publication until both
   are available. A task-only publication presents its saved requirements and recorded outcomes;
   it does not execute them or invent a completed investigation report.
3. Resolve the saved report's effective Generate PDF choice and same-source metadata under the
   [format contract](../open-edit-close-execute/references/investigation-delivery.md#report-formats).
   Legacy absent values default T. F excludes historical PDFs and requires no PDF attachment,
   card, preview, renderer or PDF-only validation dependency. Preserve old files. Reject invalid
   values and reconcile conflicting task/report decisions before writes.
   Build a bounded inventory: parent TASK, original report source, selected matching available PDF,
   every report diagram and caption, theme variants, editable diagram sources, and actually cited
   local evidence. Follow links only within verified authorized roots. Do not upload whole task/log
   directories, credential caches, conversation transcripts or unreferenced files. Resolve filename
   collisions and unsafe symlinks before upload. Preserve original filenames and bytes; disclose
   any necessary sanitized derivative rather than silently rewriting an original.
4. Inspect the current report validation and diagram inventory. Require selected deliverables to
   match the same source/version; do not silently attach a stale PDF. Publication alone preserves
   evidence windows, revision pins, findings, captions, caveats and token-accounting cutoffs.
   Reference [Token Usage](../token-usage/SKILL.md) for accounting requirements rather than
   recounting the publishing session as the historical investigation. Generate new formats or
   refresh evidence only when authorized, with the applicable report/diagram skills and checks.
5. Resolve any local publication manifest, composed HTML and read-back evidence paths through
   Workflow Artifact Naming before writes. Record input hashes, the selected destination, file
   roles, attachment/media mappings, published version, checks and remaining gaps. Preserve local
   source files and user configuration; never store upload credentials or signed URLs in evidence.

## Required reference preflight

Before **any publication write**, including attachment preparation/uploads and draft creation,
apply [Report Evidence reference completeness](../report-evidence/references/reference-completeness.md).
Check the selected Markdown/PDF and composed HTML from the same source revision; require zero
unresolved material occurrences and reviewed source-derived targets. A valid existing-link list,
complete attachment inventory, matching hashes or successful conversion dry run cannot substitute.
Stop publication on a missing, wrong-target, broken-fragment, ambiguous, unavailable or unverified
required reference. Preserve the diagnostics; never invent a destination to pass the gate.

After publication, repeat the occurrence check against saved published HTML from the same page
identity/version, verify native media with adjacent captions and refreshed source/PDF downloads,
and compare download hashes. Retain the preflight and saved-page receipts with explicit browser,
anchor-landing and preview results. A browser capability or authentication gap stays incomplete.

## Publish and verify

Read [the Confluence publication procedure](references/confluence-publication.md) before external
writes. Verify the destination and duplicates, compose the report as the page body, attach the
original report and parent task as supporting evidence, and include their clearly labeled download
cards. Include the matching PDF only when selected, and the inventoried diagrams/evidence. For a PDF-only report,
inspect it with suitable tooling, attach the original and publish a faithful readable summary or
conversion; disclose any conversion limitation. Do not claim a full rich page if only a file card
was delivered. A task-only page identifies its actual scope and includes its task download.

Use the complete live tool schemas and the procedure's semantic-success checks, draft snapshot
handling, media collection resolution, timeout reconciliation and published-version read-back.
Preserve unrelated content on an existing page and stop on conflicting concurrent edits.

Completion requires the intended published page and hierarchy, all selected file downloads,
the full diagram/caption/evidence inventory, working anchors and native media, and the requested
download/hash checks. Use the browser for visual acceptance where needed. Record partial delivery
and the exact remaining operation if a capability is unavailable; retain the existing page identity
for resumption instead of creating duplicates. Update an owned local task or publication record
only within scope. After a task changes, update its attachment and reverify its hash, or explicitly
identify the attached saved snapshot. Do not silently invalidate a verified download.

Return the page URL, what was published and attached, verification results, and any gaps.

## Common Rationalizations

- "Rerun the investigation so the numbers look fresh." Publication never reruns the investigation or refreshes its evidence window and token-accounting cutoff.
- "The page link is proof enough." Read the published page back and verify content, attachments, and media.
- "Skip the original files; the page summarizes them." The original report and available parent TASK ship as downloadable supporting evidence.

## Red Flags

- Regenerated or re-dated historical evidence during publication.
- Missing original TASK/report downloads on the published page.
- An unresolved or guessed Confluence destination.
- Authentication handled outside Rovo Dev MCP.

## Verification

- The published page was read back and matches the packaged artifacts.
- Attachments download and cited media render, including diagram themes.
- The destination, permissions, and page identity match the authorized request.
