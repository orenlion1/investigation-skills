---
name: publish-it
description: "Publish an existing task, report, or both to one or more destinations, Confluence pages and GitHub or Bitbucket repositories, with the original files as downloadable evidence plus selected report formats, diagrams and cited assets, then verify each result. Use when handling `publish it` or `publish-it` requests with a TASK path, a report path, or both. Does not run an investigation or publish a software release."
---

# Publish It

## Overview

Package existing investigation artifacts once and publish them to every destination the caller
selected: Confluence pages, repositories in GitHub or Bitbucket, or both. This skill owns
destination resolution, artifact selection, page composition, uploads, media references,
repository branches and pull requests, publication and read-back. Use
[Rovo Dev MCP](../rovo-dev-mcp/SKILL.md) for Atlassian authentication, scoped grants, tool
discovery and transport, and approved GitHub tooling with existing access for GitHub; keep
publishing decisions here.

## When to Use

- `publish it` or `publish-it` requests with a saved TASK path, report path, or both.
- Authorized publication of an existing investigation task or report to a Confluence page.
- Authorized publication of the same artifacts to a GitHub or Bitbucket repository.
- Publishing one investigation to several destinations named in its task or the request.
- Packaging selected report formats, diagrams and cited assets for publication.

## Arguments

Accept `task` and/or `report` (at least one) as explicit local file paths, plus zero or more
destinations. These are arguments to the agent's skill invocation, not an installed shell
command; accept equivalent natural-language arguments:

```text
publish it --task docs/tasks/TASK-example.md
publish it --report docs/reports/REPORT-example.md --parent <Confluence parent URL> --repo <repository URL>
publish it --task <TASK path> --report <report path> --page <existing Confluence page URL>
```

| Argument | Identity (do not confuse them) |
| --- | --- |
| `task` | The parent TASK document |
| `report` | The report document |
| `parent` (may repeat) | Confluence page that will contain a new child report page |
| `page` | Existing report page to update |
| `repo` (may repeat) | Repository that receives the artifacts through a pull request |

## Destinations

Resolve the effective destination list before any write:

1. Destinations in the current request (`--parent`, `--page`, `--repo`, or their
   natural-language equivalents) replace the saved list for this publication.
2. Otherwise use every `Publish:` bullet in the verified saved task's Resources, in order. A
   profile loaded through [Profile Manager](../profile-manager/SKILL.md) renders one bullet per
   stored destination; read the saved task, never the profile store.
3. A request may narrow the saved list ("Confluence only", "skip the repository").

There is no default destination. Do not reuse a previous investigation's site, parent or
repository, or invent a location. When neither the request nor the saved task's Resources names
a destination, write nothing and tell the requester that no publish destination is configured,
offering both ways forward:

- **Supply one now.** Append the supplied destination as a `- Publish:` bullet under the saved
  task's Resources, one bullet per destination, leaving every other line unchanged; read the
  task back, then publish from the saved task. Record that the task changed, as for any task
  edit before publication.
- **Configure it once.** Add the destination to the profile through
  [Profile Manager](../profile-manager/SKILL.md) and reload the profile into the task, so later
  publications of tasks that load the profile do not stop here.

Give the same feedback for a repository destination that names no directory and whose
repository documents no location for investigation reports: the destination is incomplete, and
the requester either supplies the directory, which replaces that task bullet, or updates the
profile and reloads it. Other complete destinations in the list still publish.

Classify each entry, deduplicating aliases of the same page or repository:

| Entry | Destination kind | Procedure |
| --- | --- | --- |
| Confluence page URL, page ID, or page title | Page: a new child of that parent, or an update when `page` selects an existing report page | [Confluence publication](references/confluence-publication.md) |
| GitHub or Bitbucket repository URL, optionally with a branch and directory, or a short name with verified provider context | Repository: a publication branch and pull request | [Repository publication](references/repository-publication.md) |

Resolve an entry that fits neither kind, or both, with the user before dependent writes; never
guess a provider, site or repository from a bare name.

An explicit publish request authorizes each destination in the effective list: for a page, that
page and its supporting uploads; for a repository, one publication branch, its commits and one
pull request in that repository. It does not authorize investigation execution, messages,
tickets, releases, merging or approving the pull request, pushing to a default or protected
branch, other source-control changes, changes to production resources, or changes to other pages
or repositories. Existing authorization needs no repeat prompt.

Package and run reference preflight once; publish in destination order. Destinations are
independent: a failed or blocked destination neither cancels nor rolls back the others, and no destination's success stands in for another's. Record every
destination's outcome in the publication manifest and return one result per destination.

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
3. Resolve the saved report's independent Markdown/PDF/HTML choices and same-source metadata under the
   [format contract](../open-edit-close-execute/references/investigation-delivery.md#report-formats).
   Defaults: Markdown/PDF `enabled`, HTML `disabled`; legacy PDF `T`/`F` remain valid.
   Disabled formats need no artifacts or tooling; preserve historical files outside the package.
   Reject invalid values and reconcile task/report conflicts before writes. An HTML-only report
   needs no Markdown/PDF companion. Follow [HTML generation](references/html-generation.md) and
   [HTML-only Confluence](references/confluence-html-only.md) for its format/theme overrides.
   `HTML theme` is `light`, `dark` or `system` (default `system`), set through Profile Manager
   separately from Generate HTML; reject other values before writes. Fixed light/dark sets both
   page colors and picture sources whatever the host browser theme.
   Build a bounded inventory: parent TASK, selected original reports and matching generated companions,
   every report diagram and caption, theme variants, editable diagram sources, and actually cited
   local evidence. Follow links only within verified authorized roots. Do not upload whole task/log
   directories, credential caches, conversation transcripts or unreferenced files. Resolve filename
   collisions and unsafe symlinks before upload. Preserve original filenames and bytes; disclose
   any necessary sanitized derivative rather than silently rewriting an original.
4. Inspect the current report validation and diagram inventory. Require selected deliverables to
   match the same source/version; do not silently attach a stale PDF. Publication alone preserves
   evidence windows, revision pins, findings, captions, caveats and token-accounting cutoffs.
   Reference [Token Usage](../token-usage/SKILL.md) for accounting requirements rather than
   recounting publishing as historical investigation. Generate selected HTML under its procedure;
   other new formats or evidence refreshes require authorization and their report/diagram checks.
5. Resolve any local publication manifest, composed HTML and read-back evidence paths through
   Workflow Artifact Naming before writes. Record input hashes, the selected destination, file
   roles, attachment/media mappings, published version, checks and remaining gaps. Preserve local
   source files and user configuration; never store upload credentials or signed URLs in evidence.

## Required reference preflight

Before **any publication write** to any destination, including attachment preparation/uploads,
draft creation, branch pushes and pull requests,
apply [Report Authoring reference completeness](../report-authoring/references/reference-completeness.md).
Apply its attachment-only source check before uploads, then its strict hosted-reference check
before page writes; require zero unresolved occurrences and reviewed targets. Link lists, inventories, hashes or conversion dry runs cannot substitute.
Keep every occurrence in the inventory, linked or not: local evidence links and plain-text
identifiers such as an incident ID stay in it, and an unlinked required occurrence blocks however
many links and hashes pass. The attachment-only check, Publish It's
[source validator](scripts/validate_publication_source.py), accepts a local occurrence only when
its authored and registered targets match, its regular non-symlink file exists inside the
approved roots and its hash is read back; its receipt permits only those uploads, never a page write.
Stop publication on a missing, wrong-target, broken-fragment, ambiguous, unavailable or unverified
required reference. Preserve the diagnostics; never invent a destination to pass the gate.

After publication, repeat the occurrence check against saved published HTML from the same page
identity/version, verify native media with adjacent captions and selected report downloads,
and compare download hashes. Retain the preflight and saved-page receipts with explicit browser,
anchor-landing and preview results. A browser capability or authentication gap stays incomplete.

## Publish and verify

Read the procedure for each destination kind in the effective list before external writes:
[Confluence publication](references/confluence-publication.md) for pages (live tool schemas,
semantic-success checks, draft snapshots, media collections, timeout reconciliation,
published-version read-back) and [repository publication](references/repository-publication.md)
for repositories.

For a page, verify the destination and duplicates, compose the report as the page body, attach the
original report and parent task as supporting evidence with clearly labeled download cards, and
include inventoried diagrams/evidence and each selected report format.

For HTML to Confluence, state each of these points in any plan or result:

- Package the download in its selected theme with both picture variants embedded. The packager's
  successful exit does not pass preflight: map each remaining local link, such as one to another
  report file, to a verified hosted target or stop, and rerun the reference checks on the derivative.
- Put figures in as native media from the owning page's collection with the caption adjacent;
  never assume CSS, `picture` sources or data URIs survive conversion.
- `HTML_THEME` governs the download only; the native page follows each viewer's Confluence
  theme. Without native automatic switching, use Dark/Light graph tabs (Dark first) or two
  labeled visible figures, and record automatic switching as incomplete.
- Run the reference checks on the source HTML, on each downloadable HTML derivative and on the
  published page; compare each downloaded attachment's exact SHA-256 with the package; report an
  unavailable preview and unsupported native automatic switching as incomplete. Install no apps
  and change no site or user theme settings.

Completion requires the intended published page and hierarchy, all selected file downloads,
the full diagram/caption/evidence inventory, working anchors and native media, and the requested
download/hash checks. Use the browser for visual acceptance where needed. Record partial delivery
and the exact remaining operation or unmet requirement if a capability is unavailable; retain the
existing page identity for resumption instead of creating duplicates. Update an owned local task or publication record
only within scope. After a task changes, update its attachment and reverify its hash, or explicitly
identify the attached saved snapshot. Do not silently invalidate a verified download.

Return, for each destination, the page URL or the pull request URL with its branch and commit,
what was published and attached, verification results, and any gaps. In every plan or result,
state that the investigation is not rerun and its evidence window and token-accounting cutoff
stay unchanged.

## Common Rationalizations

- "Rerun the investigation so the numbers look fresh." Publication never reruns the investigation or refreshes its evidence window and token-accounting cutoff.
- "The page link is proof enough." Read the published page back and verify content, attachments, and media.
- "One destination succeeded, so it is published." Every destination in the effective list gets its own outcome; report the ones that failed or were skipped.
- "No destination is configured, so pick a sensible one." There is no default: tell the requester, then append the supplied destination to the task's Resources or have the profile updated and reloaded.
- "Push straight to main; it is only documentation." A repository destination receives a publication branch and a pull request; merging stays separately authorized.
- "Skip the original files; the page summarizes them." The original report and available parent TASK ship as downloadable supporting evidence.

## Red Flags

- Regenerated or re-dated historical evidence during publication.
- Missing original TASK/report downloads on the published page.
- An unresolved, guessed or defaulted destination or repository directory, or a saved `Publish:` bullet silently dropped.
- A direct push to a default or protected branch, a force push, or a merged publication pull request.
- Atlassian authentication handled outside Rovo Dev MCP.

## Verification

- Each published page was read back and matches the packaged artifacts.
- Attachments download and cited media render, including diagram themes.
- Each repository pull request was read back: the pushed commit holds the packaged files with matching hashes, and the pull request is open and unmerged.
- Every destination in the effective list has a recorded outcome, and each destination, its permissions, and its page or repository identity match the authorized request.
