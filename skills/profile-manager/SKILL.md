---
name: profile-manager
description: "Maintain the local, untracked .env store of named resource profiles. Create, inspect, compose, lint and remove profiles, derive the profile schema from the TASK template, and load a profile into a task's Resources. Use when managing .env profiles or their ignore rules, storing repositories, Slack channels, publish destinations or settings, composing environment and application profiles, or loading task Resources. Credentials stay in their own stores."
---

# Profile Manager

## Overview

A resource profile is a named set of the values a task's Resources section takes: repositories,
Slack channels, an AWS profile, a Grafana context, an alert identity, publish destinations,
typed historical-search endpoints, and run settings. This skill owns the store, its schema, and
the ignore rules that keep it out of Git. The
[store and schema contract](references/profile-store.md) holds the file format, value rules,
limits and per-command behavior; read the linked section before a dependent operation. A tested
end-to-end run is in [profile-composition-example.md](references/profile-composition-example.md).

- **Store.** One `.env` at the repository root: local, untracked, owner-only, never committed.
  It names one person's accounts, channels and contexts, not reviewed repository policy. Only
  `PROFILE__` keys are interpreted; other entries are preserved byte-for-byte and their values
  never parsed, printed, or rewritten. Never source `.env` as shell; read it through the helper.
  See [store format](references/profile-store.md#store-format).
- **Schema.** Derived, never hardcoded: each labeled bullet in the `## Resources` section of
  [the task template](../../templates/TASK.md) is one field, and a trailing labeled segment on
  the same bullet is a dependent field that cannot be stored or rendered without its primary.
  A template change changes the schema on the next command; an undeclared field is rejected.
  Verify the derived schema before trusting a stored profile. See
  [schema derivation](references/profile-store.md#schema-derivation).
- **Helper.** The bundled Python 3.8+ [helper](scripts/profile_env.py) uses only the standard
  library and works from any copied skill location with an explicit repository root. Every
  write supports `--dry-run`, reports what it changed, and reads the result back. Resolve paths
  for saved supporting artifacts through
  [Workflow Artifact Naming](../workflow-artifact-naming/SKILL.md) before writing them.
- **Not authorization, not a credential store.** A stored AWS profile name or Grafana context
  still authenticates through its own skill, and a loaded value stays subject to every gate the
  requested operation has. Credential-shaped values are refused.

## When to Use

- Adding, updating, inspecting, composing, or removing a named profile in the local `.env` store.
- Creating or deleting that `.env` store, or making sure Git ignores it.
- Filling a task's Resources section from a saved profile instead of retyping identifiers.
- Checking which profile fields exist, because the TASK template's Resources section changed.
- `lint profiles` or `lint task <path>`: updating hand-edited or legacy settings.

## Commands

Every command is run as below; the later forms show only what follows `--repository-root .`.
Name the template with `--template` when it is not the repository default. Options, write
guards and scope are in the [command reference](references/profile-store.md#commands).

```sh
python3 -B skills/profile-manager/scripts/profile_env.py --repository-root . schema
```

```text
schema
ignore [--dry-run]
init
set --profile example --field REPO=example-service --field GRAFANA_CONTEXT=example [--replace]
list
show --profile example
render --profile example
endpoints --profile example
compose --profile prod-us --profile app-alpha --into prod-us-app-alpha [--field F=v] [--replace] [--dry-run]
load --profile example --task docs/tasks/TASK.md [--field F=v] [--replace] [--dry-run]
lint [--profile example] [--task docs/tasks/TASK.md] [--fix] [--dry-run]
remove --profile example
remove-env [--dry-run] [--force]
```

## Derive the schema

Read `schema` before a dependent read or write. Each field reports its `label`, optional
`sublabel`, and the field it `requires`. Report an unknown field against the template rather
than inventing a key for it.

## Keep the store out of Git, then create it

Ignore coverage comes first, because a store created before it is ignored can be staged by an
unrelated `git add`: run `ignore --dry-run`, `ignore`, then `init`. The helper refuses to write
a store that Git does not ignore or already tracks. `ignore` appends the `.env` patterns only
when the path is not already ignored, keeps an existing `.env.example` trackable, and verifies
coverage afterward. An already-tracked store is a repository problem, not a profile problem:
untrack it and confirm its history before storing anything.

## Add, update, inspect, and remove a profile

Profile names are lowercase kebab-case. `list` never prints a value; `show` names anything
stored outside the schema without interpreting it.

Supply actual resources. Placeholder-shaped values, example values from the template, and
credential-shaped values are refused ([value rules](references/profile-store.md#value-rules)):
ask for the actual value rather than inventing one. Loading a profile supplies Resources values
only: it does not satisfy the actual-resource requirement with a placeholder, authenticate an
integration, close an editor barrier, or authorize a gated operation.

Accept the spelling the user gives: field names match by key or template label regardless of
case, spaces, hyphens and underscores (`fan out`, `fan_out`, `FAN OUT`, `Fan-out`), and an
assignment may be `FIELD=value` or `field: value`. Pass the user's wording to `--field` rather
than asking them to restate it; an unknown or ambiguous name fails before any write. See
[field names and assignments](references/profile-store.md#field-names-and-assignments).

## Delete the store

Deleting the file removes every profile at once and is not recoverable from the repository,
since the store is untracked. Preview with `remove-env --dry-run`, confirm with the user, and
keep `--force` for a store they have agreed to delete whole: without it, a store holding keys
outside the `PROFILE__` namespace is preserved and those key names are reported.

## Lint hand-edited and legacy settings

The store and task files are the user's, and people edit them by hand. `lint` finds settings
in a legacy or non-canonical form and `lint --fix` updates them; rules and exit statuses are in
the [lint reference](references/profile-store.md#lint).

- **Never repair implicitly.** When any helper result carries `lint_notice` (or `render`
  prints it), finish the requested operation, then tell the user their `.env` holds legacy or
  hand-edited settings and ask them to run `lint profiles`. Do not run `lint --fix` on your
  own initiative.
- **`lint profiles`** is the user's request to update their `.env`: run `lint`, then
  `lint --fix`, and report what changed by rule and field, never by value.
- **Tasks are linted separately.** When a store lint returns `task_notice`, name each listed
  task and ask the user to run `lint task <path>`; on that request run
  `lint --task <path> --fix`. A finalized task stays subject to the editor contract.
- **Findings that need a decision** (`invalid-value`, `conflicting-duplicate`,
  `unknown-field`) are never guessed. Show the field and line, state the legal values, and ask
  the user to choose; apply their answer with `set` or by the task edit they request.

## List fields

`REPO`, `SLACK_CHANNEL` and `PUBLISH` each keep their key and accept a scalar or a JSON array
of 1–16 unique strings, for example `--field 'SLACK_CHANNEL=["#ops-alpha","#app-alpha"]'`.
Arrays render and load as one bullet per entry; never drop all but the first. Limits, entry
rules and validation are in [list fields](references/profile-store.md#list-fields).

- `set` replaces the field; it never appends. To add an entry to a list that already has one,
  read the stored value with `show` and set the complete array, keeping every existing entry
  unless the user asked to remove it.
- `PUBLISH` may name Confluence parent pages, GitHub or Bitbucket repositories, or both.
  Profile operations never contact a destination and storing one authorizes nothing;
  [Publish It](../publish-it/SKILL.md#destinations) resolves each saved bullet's kind, identity
  and access when the user asks to publish.
- Profile operations never query Slack. The parent resolves actual workspace/channel
  identities and cardinality after user overrides, then routes multiple channels to
  [Per-Store Fan-Out](../per-store-fan-out/SKILL.md#channel-resolution-and-scheduling).

## Compose environmental and application profiles

`compose` persists a named combined snapshot of ordered sources in `.env`; preview it with
`--dry-run`, then `load` the snapshot into a TASK. Display names “Prod US” and “App Alpha” use
CLI identifiers `prod-us` and `app-alpha`. Source, target, union, `--replace` and snapshot
rules are in [profile composition](references/profile-store.md#profile-composition).

- List fields form an ordered union; every other stored field, including stored PDF and
  history defaults, must agree. A conflict fails before any write, naming the field without its
  values. Never pick a winner: align or clear the conflicting source setting, or resolve that
  one field with `--field`.
- Compose does not export shell variables, load a TASK, authenticate, or run an investigation.

## User configuration takes precedence

Explicit user configuration wins over injected profiles, for every field (Slack, repositories,
AWS, Grafana, publication and dependent fields, not only PDF). Order, highest first: current
user instructions; `--field FIELD=value` overrides; explicit values already in the TASK;
selected profile fields; defaults. Resolve current user instructions before investigation
shared inputs, and never reload a profile over a user-selected resource. Existing TASK values
count as user configuration on later loads. Details are in
[precedence](references/profile-store.md#precedence).

- `compose` and `load` accept repeated `--field` overrides, validated against the same schema.
  A compose override resolves a conflict only for that field (others still fail) and persists
  only in the named target; a load override changes only the TASK. Sources remain unchanged.
- An explicit `REPO`, `SLACK_CHANNEL` or `PUBLISH`, from a command or a saved TASK, replaces
  the inherited list rather than appending to it.
- Empty or duplicate override assignments, invalid scalar duplicates and duplicate list entries
  in known TASK settings fail before writing.
- The supplied-resource guard remains: `load --replace` only permits rewriting an
  already-populated Resources section while retaining user values. It never authorizes
  investigation, editor closure, or scope expansion.

## Load resolved resources

`load` writes the effective Resources (user fields layered above the profile) and reads them
back; preview with `--dry-run`. Its guards are in the
[command reference](references/profile-store.md#commands).

- Load into the draft the repository created for `open task`, before the editor opens, so the
  person edits resolved values rather than placeholders. The editor and check barrier stays
  with [Open/Edit/Close/Execute](../open-edit-close-execute/SKILL.md); loading a profile is
  not a close signal and does not start execution.
- A saved finalized task is an existing artifact: change its resources through that editor
  route, at its actual path, and never rename it.

## Toggle settings

`GENERATE_PDF`, `GRAFANA_ASSISTANT` and `FAN_OUT` derive from the template's **Generate PDF**,
**Grafana Assistant** and **Fan-out** bullets and share one
[settings contract](references/profile-store.md#settings-contract): `enabled` or `disabled`,
default `enabled`, input case-insensitive and stored lowercase; `GENERATE_PDF` also accepts
legacy `T` and `F`. Set one with, for example, `set --profile team --field FAN_OUT=disabled`,
then confirm with `show`, which reports the `effective_*` value beside the stored fields;
render and load include the effective value alongside actual resources. The contract owns persistence, defaults on read, task forms, failure cases and what `disabled`
means for a run ([Generate PDF](references/profile-store.md#generate-pdf),
[Fan-out](references/profile-store.md#fan-out)).

A toggle or historical-window setting alone is configuration: never an actual resource, never
a trigger for the supplied-resource overwrite guard, never scope or authorization for an
investigation, query or publication. The profile must already contain or be supplied with an
actual resource. Differing stored settings are a composition conflict like any other field.

## Grafana Assistant

Grafana Assistant incurs additional cost. `GRAFANA_ASSISTANT=disabled` means zero prompts,
including indirect prompts from bundled guidance: Grafana work uses only gcx and relevant gcx
agent skills. The setting is never permission to query Grafana, and profile commands
themselves never prompt Assistant or query Grafana. It follows
[Toggle settings](#toggle-settings); see also the
[reference](references/profile-store.md#grafana-assistant).

## Rhyming endpoint resources

`RHYMING_ENDPOINTS` is the optional JSON array declared by the template's `Rhyming endpoints`
bullet. Read the [endpoint contract](references/profile-store.md#rhyming-endpoints) before
storing it, and validate it through the helper. Each object names an endpoint, not a
credential or authorization. Old profiles need no change.

- `endpoints --profile NAME` returns only that profile's validated endpoint list, or an empty
  list when unset, without network queries or authentication.
- The kinds include `grafana-assistant-search` (id/kind/target/context) for a scoped Assistant
  matching request. Profile operations do not send prompts; history-only kinds retain list/get
  behavior.
- Use [Rhyming Incident Search](../rhyming-incident-search/SKILL.md) to dispatch these
  endpoints, one read-only agent each. Profile management never starts a history search.
- Configuring endpoints needs only the Python 3.8+ standard library and Git, no integration
  connection. Executing them needs the integrations their kinds select; authentication belongs
  to those integrations, and a dependency absent during execution is reported per endpoint.

## Rhyming historical window

The template-derived `RHYMING_HISTORICAL_WINDOW_DAYS` field takes positive integer days,
default `7`, persisted in a new profile when omitted; override it with
`--field RHYMING_HISTORICAL_WINDOW_DAYS=30`. Render and load inject it into task Resources
only when validated `RHYMING_ENDPOINTS` exist; alone it is configuration, never an actual
resource. Persistence, reset, validation and the `endpoints` output are in
[the window contract](references/profile-store.md#rhyming-historical-window).

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
