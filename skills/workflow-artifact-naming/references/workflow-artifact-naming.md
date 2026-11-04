# Workflow Artifact Naming and Placement

This contract covers workflow documents. Production source files and test files, vendor/build
output, repository metadata, imports and native packages retain their conventions. Naming grants
no mutation authority.

## Identity and Names

Read an existing TASK's `# Task Title` and verify filename/ownership; otherwise use an explicit
title or verified slug without creating a TASK. Conflicting/missing identity stops writes.
Display-title edits do not implicitly rename established slugs.

Lowercase the title, replace non-ASCII `a-z0-9` runs with one hyphen, trim boundary hyphens and
reject an empty result. Preserve legacy simple lowercasing (`İFoo` → `ifoo`); do not casefold or
transliterate (`CAFÉ` → `caf`). Explicit slugs/suffixes must already be lowercase ASCII kebab-case.
Reject name traversal/separators. Types are uppercase; extensions describe the actual format.

| Type | Unconfigured path |
| --- | --- |
| TASK | `docs/tasks/TASK-{slug}.md` |
| SPEC | `docs/specs/SPEC-{slug}.md` |
| PLAN | `docs/plans/PLAN-{slug}.md` |
| REPORT | `docs/reports/REPORT-{slug}.md` |
| LOG | `logs/LOG-{slug}.md` |

Supporting outputs use `{selected-dir}/{TYPE}-{slug}.{ext}`; additional outputs use
`{TYPE}-{slug}-{suffix}.{ext}`, e.g. `docs/decisions/ADR-scheduled-maintenance.md`.
Lifecycle child logs use `LOG-{slug}-{ticket}.md`, preserving the safe ticket's case. New logs are
Markdown. Reusable `assets/TASK.md` or `templates/TASK.md` source templates and temporary
TASK-directory `TASK.md` drafts are exceptions.
Historical extensionless logs, frozen reports and existing chart-family names/layout stay intact.

## Repository Location Configuration

Read only the target root's optional `workflow-artifact-naming.json`:

```json
{
  "schema": "workflow-artifact-naming/v1",
  "locations": {"LOG": "../logs", "SPEC": "../specs"}
}
```

Precedence: explicit destination directory > configured type directory > table default. Missing
keys inherit defaults without backfill. Relative directories resolve against the explicit target
repository, not caller cwd or skill location; absolute directories designate their own root.
For `/workspace/service`, the example yields `../logs/LOG-scheduled-maintenance.md` and
`../specs/SPEC-scheduled-maintenance.md`. Configured sibling roots are intentional placement.

Malformed JSON, duplicate/unknown keys, unsupported schema, invalid directories or ambiguity
stop resolution even with an explicit override. Expand no shell,
environment or glob expression. Preserve settings bytes/effective locations across copy, install, update, reinit and repeat use.
Edit settings only when requested; never
install defaults, reset choices, silently migrate artifacts or create a competing directory tree.

## Resolution Helper

From the complete copied skill directory, use Python 3.8+ (standard library only):

```bash
python3 scripts/resolve_artifact_names.py \
  --repository-root "$TARGET_REPOSITORY_ROOT" \
  --title 'Scheduled Maintenance' --type REPORT
```

`TARGET_REPOSITORY_ROOT` is the existing target root. Supply `--title` or verified `--slug`,
`--type` and root; no TASK, Epic, sibling skill, fixed workspace or service is required.
Optional flags: `--destination DIRECTORY`, `--suffix SLUG`, `--extension EXT` (without leading dot;
`md` default), `--ticket ID` (child LOG), `--draft` (TASK.md), `--asset` (LOG-related asset).
Assets use the effective LOG root's `assets/{slug}/{TYPE}-{slug}[-suffix].{ext}`; existing chart
families retain their owned layout. Other supporting types require an explicit directory.

`--repository-root "$TARGET_REPOSITORY_ROOT" --locations` resolves all five directories before
identity exists; `--normalize-title TITLE` alone supplies compatibility normalization. JSON
artifact output includes `slug`, `type`, `filename`, repository-relative `path`, `absolute_path`,
`output_root` and `location_source`. Resolution changes no files/parents, inspects only selected path entries and proves no
ownership/permission.

## Authorized Handling and Verification

Inspect target policies, selected root, case collisions, ownership and unrelated dirty work before
mutation. The approved containment boundary is the repository for defaults or the explicit/
configured output root for alternatives. Reject filesystem-root outputs, non-directory ancestors,
escaping/unexpected symlinks and conflicting content; invent no numeric collision suffix.
Revalidate roots/symlinks at the write boundary. Resume matching owned outputs; competing old/new
candidates after a settings change require a scoped decision. Create only missing parents needed
for an authorized write. Preserve unrelated bytes and format-specific native validation.

Read back outputs, identity, content and links. For authorized existing TASK/index updates,
index only verified local outputs as repository-relative paths,
including approved `../` roots. Resolve them through their approved root; Markdown links are
relative to their containing document (`document_link` helper). Never index planned, failed,
missing, ignored or unauthorized external outputs, or create a registry just to use this skill.
Lifecycle owners retain append/schema/indexing rules.

Explicit renames require a scoped old/new map, inbound-reference/ownership/collision checks,
preserved evidence, authorized reference updates and read-back. Stop on unresolved references or
preservation conflicts; adoption authorizes no bulk cleanup.
