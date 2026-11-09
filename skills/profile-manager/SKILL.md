---
name: profile-manager
description: Maintain the repository's local untracked .env resource-profile store: create or delete .env, add, update, remove and inspect a named profile, keep .env ignored by Git, load a profile into a task's Resources section, and derive the profile schema from the TASK template. Use when asked to add, remove or load an .env profile, to set up .env ignore rules, or to fill task Resources from a saved profile; credentials stay in their own credential stores.
---

# Profile Manager

## Overview

A resource profile is a named set of the values a task's Resources section takes: a
repository, a Slack channel, an AWS profile, a Grafana context, an alert identity, a
publication parent page, or typed historical-search endpoints. This skill owns that store, its schema, and the ignore rules that
keep it out of Git. Reach for it when a profile is created, changed, inspected, deleted, or
loaded into a task; read the [store and schema contract](references/profile-store.md) for
the file format, parsing rules, and command reference.

The store is a single `.env` file at the repository root. It is local and untracked by
design: it names one person's accounts, channels, and contexts, which are not reviewed
repository policy. Only keys in the `PROFILE__` namespace are interpreted, so unrelated
local environment entries in the same file are preserved byte-for-byte and their values
are never parsed, printed, or rewritten.

The schema is derived, never hardcoded. Each labeled bullet in the `## Resources` section of
[the task template](../../templates/TASK.md) produces one field key, and a trailing labeled
segment on the same bullet produces a dependent field. A template change therefore changes
the profile schema on the next command, and a field the template does not declare is
rejected. Verify the derived schema before trusting a stored profile.

The bundled Python 3.8+ [helper](scripts/profile_env.py) uses only the standard library and
works from any copied skill location with an explicit repository root. Every write supports
`--dry-run`, reports what it changed, and reads the result back. Resolve paths for saved
supporting artifacts through [Workflow Artifact Naming](../workflow-artifact-naming/SKILL.md)
before writing them.

Profiles record which resources are in scope. They are not authorization and not a
credential store: a stored AWS profile name or Grafana context still authenticates through
its own skill, and a loaded value is still subject to every gate the requested operation
has. Values that look like credentials are refused.

## When to Use

- Adding, updating, inspecting, or removing a named profile in the local `.env` store.
- Creating or deleting that `.env` store, or making sure Git ignores it.
- Filling a task's Resources section from a saved profile instead of retyping identifiers.
- Checking which profile fields exist, because the TASK template's Resources section changed.

## Derive the schema

Read the schema before a dependent read or write, and name the template explicitly when it
is not the repository default.

```sh
python3 -B skills/profile-manager/scripts/profile_env.py --repository-root . schema
```

Each field reports its `label`, its optional `sublabel`, and the field it `requires`. A
dependent field cannot be stored or rendered without its primary field. Report an unknown
field against the template rather than inventing a key for it.

## Keep the store out of Git, then create it

Ignore coverage comes first: a store created before it is ignored can be staged by an
unrelated `git add`. The helper enforces that order and refuses to write a store that Git
does not ignore, or one that Git already tracks.

```sh
python3 -B skills/profile-manager/scripts/profile_env.py --repository-root . ignore --dry-run
python3 -B skills/profile-manager/scripts/profile_env.py --repository-root . ignore
python3 -B skills/profile-manager/scripts/profile_env.py --repository-root . init
```

`ignore` appends the `.env` patterns only when the path is not already ignored, keeps an
existing `.env.example` trackable, and verifies coverage afterward. An already-tracked store
is a repository problem, not a profile problem: untrack it and confirm its history before
storing anything. Every write leaves the store owner-only, tightening one that was looser;
`.gitignore` and the task are ordinary repository files and keep the mode they have.

## Add, update, inspect, and remove a profile

Profile names are lowercase kebab-case. `set` merges by default, `--replace` discards the
fields it does not mention, and an empty value clears one field.

```sh
python3 -B skills/profile-manager/scripts/profile_env.py --repository-root . \
  set --profile example --field REPO=example-service --field GRAFANA_CONTEXT=example
python3 -B skills/profile-manager/scripts/profile_env.py --repository-root . list
python3 -B skills/profile-manager/scripts/profile_env.py --repository-root . show --profile example
python3 -B skills/profile-manager/scripts/profile_env.py --repository-root . remove --profile example
```

`list` reports the stored profile names, whether the store exists, and its ignore and
tracking status; it never prints a value. `show` prints the values of schema fields for one
profile and names anything stored outside the schema without interpreting it. `remove`
deletes only that profile's keys and its own comment marker.

Supply actual resources. Placeholder-shaped values, example values from the template, and
credential-shaped values are refused, because a placeholder in a task's Resources section is
not a resource. The same rule gates task execution: loading a profile supplies Resources
values only — it does not satisfy the actual-resource requirement with a placeholder,
authenticate an integration, close an editor barrier, or authorize a gated operation.

## Delete the store

```sh
python3 -B skills/profile-manager/scripts/profile_env.py --repository-root . remove-env --dry-run
```

Deleting the file removes every profile in it at once and is not recoverable from the
repository, since the store is untracked. Preview it first, confirm with the user, and keep
`--force` for a store they have agreed to delete whole: without it, a store holding keys
outside the `PROFILE__` namespace is preserved and those key names are reported.

## Load a profile into a task

`load` replaces the task's `## Resources` body with the profile's resolved bullets in
template order, omitting fields the profile does not set, and reads the section back.

```sh
python3 -B skills/profile-manager/scripts/profile_env.py --repository-root . \
  load --profile example --task docs/tasks/TASK.md --dry-run
```

Load into the draft the repository created for `open task`, before the editor opens, so the
person edits resolved values rather than placeholders. The editor and check barrier stays
with [Open/Edit/Close/Execute](../open-edit-close-execute/SKILL.md); loading a profile is
not a close signal and does not start execution. A saved finalized task is an existing
artifact: change its resources through that editor route, at its actual path, and never
rename it.

A task whose Resources section already carries real values is preserved unless `--replace`
is passed, and those values are reported so the user can decide. A profile that resolves to
no actual resource is refused rather than written, because an executable task needs at least
one.

## Rhyming endpoint resources

`RHYMING_ENDPOINTS` is the optional JSON array declared by the template's
`Rhyming endpoints` bullet. Validate it through the helper; never source `.env` as shell.
Read the [endpoint contract](references/profile-store.md#rhyming-endpoints) before storing it.
Each object names an endpoint, not a credential or authorization. Old profiles need no change.

```sh
python3 -B skills/profile-manager/scripts/profile_env.py --repository-root . endpoints --profile example
```

`endpoints` returns only the selected profile's validated endpoint list, or an empty list when
unset. It verifies the store is ignored and untracked and refuses unknown fields or malformed
stored endpoints before returning anything. It performs no network queries or authentication.
Use [Rhyming Incident Search](../rhyming-incident-search/SKILL.md) to dispatch these endpoints,
one read-only agent each.

## Dependencies

Profile management and endpoint validation require Python 3.8+ standard library and Git;
no integration connection is required to configure them. Historical endpoint execution
additionally requires the rhyming incident search skill, native agent delegation, and only
the integrations selected by endpoint kind: gcx-cli for Grafana, rovo-dev-mcp for Confluence
and Bitbucket, slack-mcp for Slack, and GitHub tooling for GitHub repositories. Authentication
belongs to those integrations. Dependency absence during execution is reported per endpoint.

## Common Rationalizations

- "The store can be committed; it only holds resource names." It names one person's accounts, channels, and contexts; the store stays untracked and ignored.
- "Create `.env` now and ignore it afterwards." Ignore coverage is verified first, or an unrelated `git add` can stage it.
- "The field list is obvious enough to hardcode." Fields are derived from the task template's Resources section, so a template change is picked up instead of silently diverging.
- "A loaded profile means the resources are reachable." A stored name is not access; each integration still authenticates and authorizes through its own skill.
- "An example value is good enough to start the task." Placeholders and examples are not resources and are refused.

## Red Flags

- A store that Git tracks, or one written before ignore coverage was verified.
- Values of keys outside the `PROFILE__` namespace parsed, printed, rewritten, or lost.
- A credential, token, or private key stored in a profile.
- A field accepted or rendered without a matching entry in the derived schema.
- A task's supplied resources overwritten, or a saved task renamed, while loading a profile.
- Deleting the store without a preview and the user's explicit agreement.

## Verification

- The derived schema was read from the intended template, and every stored and rendered field matches it.
- `.env` is ignored and untracked, owner-only, and holds exactly the intended profiles.
- Unmanaged lines in the store are unchanged, and no profile value is a placeholder, example, or credential.
- The written store or task Resources section was read back and matches the reported result.
- Deletions were previewed, explicitly agreed, and confirmed as applied.
