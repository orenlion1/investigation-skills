# Resource profile store and schema contract

The profile store is one `.env` file at the repository root: local, untracked, owner-only.
This contract covers how it is parsed and written, how the schema is derived from the task
template, and what each command accepts. Rules stated once apply to every field of that kind.
A tested end-to-end run is in [profile-composition-example.md](profile-composition-example.md).

## Store format

Every managed entry is `PROFILE__{PROFILE_NAME}__{FIELD}='value'`.

- `PROFILE_NAME` is the lowercase kebab-case profile name (`example`, `other-team`) in upper
  case with hyphens as underscores, so it never contains the double-underscore separator.
- `FIELD` is a template-derived field key, upper case with single underscores.
- Values are written single-quoted and read as data; never source `.env` as shell code.
- A `PROFILE__` key that does not split into exactly three non-empty parts is an error, not
  a key to ignore: the store fails closed.

Reading and writing:

- Blank lines, `#` comments and assignments outside `PROFILE__` are preserved in place,
  byte-for-byte; their values are never parsed or printed.
- A managed value may be single-quoted, double-quoted, or a bare token without whitespace,
  `#`, quotes or backslashes; anything else is rejected. An `export ` prefix is read, never
  written.
- Writes are atomic (temporary file replaced into place) and leave the store `0600`, tightening
  a looser existing mode; `set`, `remove` and `init` report the mode. `.gitignore` and tasks
  keep the mode they have.
- A store that is a symlink, not a regular file, or over 256 KiB is refused.
- A new profile is appended after a `# profile: {name}` marker. Rewriting keeps its position;
  removing it removes the marker.
- No read command rewrites the store.

## Value rules

A value is non-empty, has no surrounding whitespace, is at most 512 characters, and contains
no control characters or single quotes (the store quotes with them). Rejected before any
write, with errors that never echo the value:

- placeholder-shaped values (`<Parent page>`): a placeholder is not a resource;
- credential-shaped values (AWS access key IDs, Slack tokens, GitHub and Grafana service
  tokens, PEM private key headers, JWTs), with a pointer to the owning credential store. This
  is a guardrail, not a secret scanner; the store is never a safe place for credentials.

Stored values, including manual edits, are validated by every command that reads them,
before it returns resources or changes a task.

## Schema derivation

The schema comes from the template's single `## Resources` section, which ends at the next
level-2 heading. Each `- ` line must match:

```
- {Label}: `<{placeholder}>`[; {Sublabel} `<{placeholder}>`]...
```

- A trailing ` (example: ...)` or ` (examples: ...)` is stripped first, so examples never
  become schema or values.
- The field key is the label without parentheticals, non-alphanumeric runs collapsed to
  underscores, upper-cased: `Repo (Bitbucket/Github)` is `REPO`, `Slack channel` is
  `SLACK_CHANNEL`.
- A `; Sublabel` segment is a dependent field `{PRIMARY}_{SUBLABEL}` (`ALERT`, `ALERT_UID`)
  that cannot be stored or rendered without its primary.
- Errors: duplicate keys, a first segment without exactly one backticked placeholder, no
  resource bullet, and zero or several `## Resources` headings.
- A field the template does not declare is rejected; a custom template without a field never
  acquires it or its default.

Rendering reverses this: bullets in template order, label verbatim, values backticked. A
bullet whose primary field is unset is omitted.

## Commands

All take `--repository-root`, optionally `--env` (default `.env`) and `--template` (default
`templates/TASK.md`). Commands print one JSON object; `render` prints Markdown. Writing
commands take `--dry-run`, which reports the same result without writing. Errors print one
sanitized line to standard error and exit `2`.

| Command | Writes | Purpose |
| --- | --- | --- |
| `schema` | no | Derived fields, labels, sublabels, dependencies, types, limits and defaults. |
| `list` | no | Profile names and the store's existence, ignore and tracking status. |
| `show --profile NAME` | no | Stored fields, unknown keys, missing fields and `effective_*` setting values. |
| `render --profile NAME` | no | The rendered `## Resources` section. |
| `endpoints --profile NAME` | no | Validated historical-search endpoints only. |
| `lint` | no | Hand-edited or legacy settings in the store, and in a task with `--task PATH`. |
| `lint --fix` | `.env`, task | Rewrite fixable findings canonically; the rest are left. |
| `ignore` | `.gitignore` | Ensure Git ignores the store, then verify it. |
| `init` | `.env` | Create an empty owner-only store. |
| `set --profile NAME --field FIELD=value` | `.env` | Merge fields; `--replace` discards unmentioned fields; an empty value clears one. |
| `compose --profile A --profile B --into NAME` | `.env` | Persist a combined snapshot; `--replace` replaces an existing target. |
| `remove --profile NAME` | `.env` | Delete one profile's keys and marker. |
| `remove-env` | `.env` | Delete the store; `--force` when it holds unmanaged keys. |
| `load --profile NAME --task PATH` | task | Load effective Resources; `--replace` permits rewriting a populated section. |

Write guards:

- `set` and `init` refuse unless Git ignores the store; `remove`, `remove-env` and `ignore`
  refuse a store Git tracks.
- `set` validates the merged profile, confirms it renders at least one actual resource, then
  re-reads the store and compares. `remove` re-reads and fails if the profile remains.
- `load` requires an existing non-symlink task with exactly one `## Resources` heading,
  refuses a profile that renders no bullet, keeps already-supplied values unless `--replace`,
  and re-reads the written section. It never closes an editor or starts an investigation;
  loading a finalized task stays subject to the editor contract.
- `remove-env` reports the profiles and unmanaged key names it would delete and confirms the
  file is gone.
- Repeating a command with the same inputs yields the same bytes.

Scope: the helper manages the store and a task's Resources section. It does not authenticate,
query or contact any resource, resolve artifact names, create or rename a task, read or write
process environment variables, or export anything to a child process. Storing a value proves
neither access nor permission, and authorizes nothing.

## Field names and assignments

Wherever a command takes a field assignment (`set`, `load` and `compose` `--field`):

- **Names** match regardless of case, spaces, hyphens and underscores, against the field key
  or its template label: `FAN_OUT`, `fan_out`, `fan out`, `Fan-out` and `fanout` are one
  field. A name matching no field, or more than one, fails before any write.
- **Delimiters.** `FIELD=value` and `field: value` are both accepted; whichever delimiter
  comes first decides, so `REPO=ssh://git@example.com/org/repo.git` and
  `publish: https://example.atlassian.net/wiki/spaces/OPS` parse as written. The colon form
  trims whitespace around the value. An empty value clears the field.
- **Task bullets** match their template label the same way: `- fan out: disabled` is the
  Fan-out setting.

The store and rendered Resources always use the canonical key, label and value.

```sh
python3 -B skills/profile-manager/scripts/profile_env.py --repository-root . set --profile team --field 'fan out: disabled'
```

## Precedence

Highest first: the user's current instructions; explicit `--field` overrides; values already
saved in the task; profile fields; defaults. A template placeholder counts as absent.

- `load` keeps every explicit task field, even with `--replace`, and preserves bullets whose
  label is not in the template. `--replace` only permits rewriting a section that already
  holds actual values. Later loads treat saved task values as user configuration: change them
  in the editor or with a newer `--field`. Task values never modify the store.
- Loading replaces recognized resource bullets in place, preserving introductory guidance,
  comments, blank lines and unknown bullets. Fields missing from the task are added at the
  end of its recognized resource list; list values expand at their original field position.
  A section without recognized bullets receives the resource list after its existing prose.
- Known scalar duplicates, malformed bullets and invalid values in a task fail before writes.
  Repeated bullets of a list field form one validated list.
- Invalid stored values fail before an override can mask them.
- When preparing an investigation's effective resources, reflect the chosen values in the
  shared resolved input before delegation, honoring all scope and authentication gates.

## List fields

`REPO`, `SLACK_CHANNEL` and `PUBLISH` each hold a scalar or a JSON array of 1–16 unique
non-empty strings, at most 512 characters per entry and 8192 UTF-8 bytes per field, stored as
one string (`PROFILE__APP_ALPHA__REPO='["org/service-a","org/shared-library"]'`). `schema`
exposes the limits.

- Rejected before writes: malformed or empty arrays, duplicates, non-strings, placeholders,
  credentials, controls, backticks, angle brackets, backslashes, and URL user information.
- `set` replaces or clears the whole field; it never appends. `show` keeps the stored format.
  `render` and `load` emit one bullet per entry, in order. Scalars need no migration.
- An explicit `--field` or saved task list replaces an inherited list rather than appending.

| Field | Entry | Specifics |
| --- | --- | --- |
| `REPO` | Repository name or URL | URL queries and fragments are refused. `ssh://git@host/path` and `git@host:owner/repo.git` are accepted. Use explicit GitHub or Bitbucket URLs for mixed providers; a short name needs verified provider context. Resolution belongs to source investigation. |
| `SLACK_CHANNEL` | Channel name or ID | Names, IDs, aliases, workspaces and access are resolved later through Slack MCP. |
| `PUBLISH` | Confluence parent page (URL, ID or title), or a GitHub or Bitbucket repository URL with optional branch and directory | A URL query is permitted, since a Confluence URL may carry its page ID there. Publish It classifies entries; an explicit publish request is still required. |

## Profile composition

`compose --profile prod-us --profile app-alpha --into prod-us-app-alpha` reads the sources in
order and persists a new named snapshot. It needs at least two unique sources and a distinct
target; names are kebab-case (“Prod US” is a display name). No source is modified and no task
is loaded; run `load` with the combined profile afterward.

- **List fields** merge as a first-seen ordered union with exact-string deduplication, then
  the limits are revalidated. A one-entry result is stored as a scalar.
- **Other fields** must match across sources. A difference fails without a write and names
  only the field. This includes endpoint JSON strings and stored setting defaults, because
  the store cannot tell an implicit default from an explicit value. Align or clear the
  conflicting value, or supply that field with `--field`; composition never picks a winner.
- **`--field` overrides** must be non-empty, unique, schema-declared and valid. They resolve a
  conflict only for that field, replace an inherited list union, and change only the target.
- Missing defaults are filled after merging. Unknown source fields fail. Dependencies are
  validated and the result must hold an actual resource.
- An existing target needs `--replace`, which replaces its whole field set. Unrelated bytes,
  including CRLF line endings, are unchanged; a store-size overflow fails before mutation;
  the write is followed by a read-back of all profiles.
- A snapshot does not track its sources; recompose after changing them. Direct multi-profile
  task loading and shell export are out of scope.

## Settings contract

Template bullets are either **resources** (what to investigate, where to publish) or
**settings** (how a run behaves). Every on/off setting is a toggle under one contract:

| Field | Task bullet | Default | Legacy values | `show` reports | `disabled` means |
| --- | --- | --- | --- | --- | --- |
| `GENERATE_MARKDOWN` | `Generate Markdown` | `enabled` | none | `effective_generate_markdown` | No Markdown report artifact |
| `GENERATE_HTML` | `Generate HTML` | `disabled` | none | `effective_generate_html` | No standalone HTML artifact |
| `GENERATE_PDF` | `Generate PDF` | `enabled` | `T` = `enabled`, `F` = `disabled` | `effective_generate_pdf` | No PDF artifact |
| `GRAFANA_ASSISTANT` | `Grafana Assistant` | `enabled` | none | `effective_grafana_assistant` | No Assistant prompts |
| `FAN_OUT` | `Fan-out` | `enabled` | none | `effective_fan_out` | Inline investigation |

- **Values.** `enabled` or `disabled`. Input is case-insensitive and ignores surrounding
  whitespace, legacy values included, and is translated to the setting constant, so the
  stored and rendered value is always lowercase. Any other word or number fails before a
  write.
- **One source.** The helper defines the values once (`ENABLED`, `DISABLED`) and translates
  input in one function; its code and tests use those constants.
- **Schema.** `type: enum`, `enum: [enabled, disabled]`, `default`, `resource: false`, and
  `legacy_values` where they exist.
- **Task form.** A bullet may quote the value or write it bare (`- Generate PDF: disabled`);
  loading renders the quoted form. Duplicate or invalid task settings fail before writes.
- **Persistence.** New or updated non-empty profiles persist a missing default, unless the
  field is cleared with an empty `set` value, which restores the default. A profile without
  the field resolves the default on read.
- **Legacy values** resolve to their canonical value wherever they are read. The next update
  of that profile, any load into a task, and [`lint --fix`](#lint) write the canonical value.
- **Not a resource.** A setting alone never satisfies the actual-resource requirement,
  triggers the supplied-resource overwrite guard, or authorizes an investigation, a query or
  a publication.
- **Composition** treats differing stored settings as a conflict like any other field.

A new on/off setting joins by adding its template bullet and its entry in the helper's
toggle table; it does not define its own values.

```sh
python3 -B skills/profile-manager/scripts/profile_env.py --repository-root . set --profile team --field GENERATE_PDF=disabled
python3 -B skills/profile-manager/scripts/profile_env.py --repository-root . show --profile team
```

### Report formats

`GENERATE_MARKDOWN`, `GENERATE_PDF` and `GENERATE_HTML` select independent outputs.
Each can be the only enabled format. Defaults preserve Markdown and PDF delivery, with HTML
opt-in. Disabling Markdown never suppresses HTML or PDF. Resolve settings before dependencies;
only selected formats require renderers and format-specific checks. All outputs retain the same
findings, evidence, graphs and accounting cutoff. The
[delivery contract](../../open-edit-close-execute/references/investigation-delivery.md#report-formats)
owns source identity and validation; [Publish It](../../publish-it/references/html-generation.md)
owns HTML generation and packaging. Settings do not authorize publication.

### HTML theme

`HTML_THEME` comes from the `HTML theme` template bullet. It is a non-resource enum:
`light`, `dark` or `system`, default `system`, with no legacy aliases. Input is case-insensitive
and stored lowercase. `show` reports `effective_html_theme`. Its default, persistence, clearing,
composition, task precedence, bare/quoted task values and lint rules follow the other settings.
A custom template without the bullet gains neither the field nor its default.

For the standalone HTML, `system` follows the browser preference. Fixed `light` or `dark` keeps the canvas
and theme-aware diagram selection in that mode, even when the viewer uses the opposite theme.
Confluence native figures follow Publish It's separate theme procedure.
The setting does not enable HTML generation or authorize publication. Resolve it before
rendering and record it in the HTML generation receipt. Publish It owns the
[renderer behavior](../../publish-it/references/html-generation.md#appearance).

### Generate PDF

Select and validate PDF under the report format contract above. Preserve older PDFs as historical
when disabled; never attach one as a current companion.

### Grafana Assistant

Grafana Assistant incurs additional cost. `disabled` means zero prompts, including indirect
prompts from bundled guidance: Grafana work uses only gcx and relevant gcx agent skills.
Profile commands never prompt Assistant or query Grafana.

### Fan-out

`disabled` runs the investigation inline instead of fanning out;
[Per-Store Fan-Out](../../per-store-fan-out/SKILL.md) owns what that means for a run. The
setting creates no scope or authority.

## Lint

`lint` finds settings that were hand-edited or written before the settings contract, in the
store and in a task's Resources; `--fix` rewrites what has one correct answer. Findings carry
a rule, location, line, field and, where one exists, the canonical spelling, never a stored
value.

| Rule | Where | Meaning | `--fix` |
| --- | --- | --- | --- |
| `legacy-value` | store, task | A pre-contract value such as `T` or `F` | Rewritten to `enabled` or `disabled` |
| `value-spelling` | store, task | A legal value in another spelling (`DISABLED`, a bare task value) | Rewritten to the constant |
| `key-spelling` | store | A key in another case or spelling (`PROFILE__team__fan_out`) | Rewritten |
| `label-spelling` | task | A bullet label in another spelling (`fan out`) | Rewritten to the template label |
| `formatting` | store | A correct entry not written as `KEY='value'` | Rewritten |
| `duplicate` | store, task | A setting repeated with the same value | Extra line removed |
| `conflicting-duplicate` | store, task | A setting repeated with different values | Left for the user |
| `invalid-value` | store, task | An illegal value, such as `off` for a toggle | Left for the user |
| `unknown-field` | store | A key that matches no template field | Left for the user |
| `invalid-key` | store | A managed key that is not `PROFILE__NAME__FIELD` | Left for the user |
| `invalid-resources` | task | The Resources section fails validation as a whole | Left for the user |

- `--profile NAME` limits store findings to one profile; `--task PATH` also lints that task;
  `--fix --dry-run` previews.
- Fixes rewrite only the affected lines. Unrelated store lines, other task sections and
  findings that need a decision stay exactly as written; the store keeps its mode.
- Exit status: `0` nothing unresolved, `1` findings remain, `2` error.

Two notices prompt for a lint without performing one:

- **`lint_notice`** is added to every other command's result (standard error for `render`)
  when the store holds findings. The command still completes and the store is not changed.
- **`task_notice`** is added to a lint run without `--task`: it scans `TASK*.md` in
  `--task-dir` (default `docs/tasks`) read-only and lists each task with findings. A task is
  only ever linted by its own named run.

```sh
python3 -B skills/profile-manager/scripts/profile_env.py --repository-root . lint --fix
python3 -B skills/profile-manager/scripts/profile_env.py --repository-root . lint --task docs/tasks/TASK.md --fix
```

## Rhyming endpoints

`RHYMING_ENDPOINTS` is optional: one JSON array on one line, 1–16 objects, at most 8192 UTF-8
bytes. Unset means no historical-search endpoints; `[]` is rejected as ambiguous. Each object
has exactly `id`, `kind`, `target` and the conditional key below. JSON keys and IDs are
unique; IDs are lowercase kebab-case; every value keeps the 512-character limit. Unknown keys
or kinds are errors. `schema` exposes type, kinds, limits, required and conditional keys.

| kind | target | Conditional key |
| --- | --- | --- |
| grafana-investigations | Explicit prior-investigation scope or search phrase | context: configured gcx context |
| grafana-assistant-conversations | Explicit historical conversation scope or phrase | context: configured gcx context |
| grafana-assistant-search | Explicit historical resource scope or search phrase for an Assistant matching request | context: configured gcx context |
| confluence | HTTPS Atlassian Cloud page URL under /wiki/ | None |
| slack | Channel ID beginning C or G, or explicit #channel name | None |
| repository | HTTPS GitHub or Bitbucket owner/repository URL | provider: github or bitbucket, matching the host |

```json
[{"id":"history","kind":"grafana-investigations","target":"service-a","context":"ops"},{"id":"code","kind":"repository","target":"https://github.com/example/service-a","provider":"github"}]
```

- Set it with a properly shell-quoted JSON value; prefer a structured process argument when
  automating and never interpolate profile values into executable shell text.
- Object values cannot contain credential patterns, placeholders, control characters,
  backticks, single quotes, dollar signs, angle brackets or backslashes. Contexts use
  alphanumerics, dot, underscore and hyphen; Grafana targets also allow spaces, colon and
  slash.
- URLs reject userinfo, ports, IP literals, queries, fragments, encoded controls and path
  traversal. Only the two repository hosts and Atlassian Cloud wiki URLs are supported; other
  hosts need an explicit schema extension, never a silent provider change.
- `endpoints` additionally requires ignored, untracked storage, rejects unknown fields, and
  returns `{ "profile": "NAME", "endpoints": [...], "historical_window_days": 7 }`. No
  authentication, query or delegation occurs there.
- `grafana-assistant-search` permits a scoped billable Assistant prompt through
  [Rhyming Incident Search](../../rhyming-incident-search/SKILL.md);
  `grafana-assistant-conversations` reads existing history only. Profile commands never
  launch a prompt. Honor `Grafana Assistant: disabled` during execution.
- Search needs gcx-cli for the Grafana kinds, rovo-dev-mcp for Confluence and Bitbucket,
  slack-mcp for Slack, GitHub tooling for GitHub, and native agent delegation. Profile
  management itself needs only Python and Git; an unavailable integration is handled later
  by Rhyming Incident Search.

## Rhyming historical window

`RHYMING_HISTORICAL_WINDOW_DAYS` is an ASCII positive integer without units, signs, leading
zeroes or whitespace. `schema` reports type `positive-integer-days`, default `7` and
`render_requires: RHYMING_ENDPOINTS`.

- **Persistence.** `set` writes the missing default when it creates a non-empty profile, even
  before endpoints exist, and when it updates a profile that has endpoints. An explicit value
  wins and is preserved. `--replace` applies the same rule to the new field set. An empty
  assignment clears the key for that command, after which reads use seven days and a later
  endpoint-profile update may persist the default again. Setting `7` persists it. An empty
  replacement or removal never creates a default-only profile.
- **Rendering.** `render` and `load` include it only with validated endpoints, resolving the
  default for profiles that lack it. Alone it is not an actual resource.
- **`endpoints`** returns integer `historical_window_days`, or `null` without endpoints.
