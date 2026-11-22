# Resource profile store and schema contract

The profile store is one `.env` file at the repository root. It is local, untracked, and
owner-only. This contract covers how it is parsed and written, how the profile schema is
derived from the task template, and what each command accepts.

## Key format

Every managed entry uses a three-part key with a double-underscore separator:

```
PROFILE__{PROFILE_NAME}__{FIELD}
```

- `PROFILE_NAME` is the profile name in upper case with hyphens replaced by underscores.
  Profile names are lowercase kebab-case (`example`, `other-team`), so an upper-cased name
  can never contain a double underscore and the separator stays unambiguous.
- `FIELD` is a field key derived from the task template, upper case with single underscores.
- Values are written single-quoted (`PROFILE__EXAMPLE__REPO='example-service'`), and read as data by the helper; never source `.env` as shell code.

A key inside the `PROFILE__` prefix that does not split into exactly three non-empty parts
is an error, not a key to ignore: the store fails closed rather than silently dropping an
entry someone expected to be in effect.

## Parsing and preservation

- Blank lines, `#` comments, and every assignment outside the `PROFILE__` prefix are
  preserved in place, in order, byte-for-byte. Their values are never parsed or printed.
- A managed value may be single-quoted, double-quoted, or a bare token without whitespace,
  `#`, quotes, or backslashes. Anything else is rejected rather than guessed at.
- An optional `export ` prefix is accepted when reading and not written.
- Writes are atomic: a temporary file in the same directory is replaced into place. Every
  store write leaves it `0600`, so a store that already existed with a looser mode is
  tightened rather than preserved, and `set`, `remove` and `init` report the resulting mode.
  The other files these commands touch — `.gitignore` and the task — are ordinary repository
  files and keep the mode they already have.
- A store that is a symlink, is not a regular file, or exceeds 256 KiB is refused.
- A new profile block is appended after a `# profile: {name}` marker line. Rewriting a
  profile keeps its position; removing one removes its marker with it.

## Value rules

A value must be non-empty, free of surrounding whitespace, at most 512 characters, and free
of control characters. Single quotes are rejected, because the store quotes with them.
Placeholder-shaped values (`<Parent page>`) are rejected: the task template documents them
as placeholders, and repository policy does not count a placeholder as a resource.
Credential-shaped values — AWS access key identifiers, Slack tokens, GitHub and Grafana
service tokens, PEM private key headers, JWTs — are rejected with a pointer back to the
credential store that owns them. The check is a guardrail against an obvious mistake, not a
secret scanner; it does not make the store a safe place for credentials.

## Schema derivation

The schema comes from the single `## Resources` section of the task template. Its body ends
at the next level-2 heading. Each line starting with `- ` must match:

```
- {Label}: `<{placeholder}>`[; {Sublabel} `<{placeholder}>`]...
```

A trailing ` (example: ...)` or ` (examples: ...)` parenthetical is documentation and is
stripped before parsing, so template examples never become schema or stored values.

- The field key is the label with parentheticals removed, non-alphanumeric runs collapsed to
  single underscores, and the result upper-cased: `Repo (Bitbucket/Github)` becomes `REPO`,
  `Slack channel` becomes `SLACK_CHANNEL`.
- A labeled segment after `; ` becomes a dependent field named `{PRIMARY}_{SUBLABEL}`:
  `- Alert: ...; UID ...` yields `ALERT` and `ALERT_UID`. A dependent field cannot be stored
  or rendered without its primary field.
- Duplicate derived keys, a bullet without exactly one backticked placeholder in its first
  segment, a template with no resource bullet, and a template with zero or several
  `## Resources` headings are all errors.

Rendering reverses the derivation: bullets are emitted in template order with the label text
verbatim and the stored values backticked. A bullet whose primary field is unset is omitted
entirely, which matches the template's instruction to omit settings that do not apply.

## Commands

All commands take `--repository-root`, and optionally `--env` (default `.env` in that root)
and `--template` (default `templates/TASK.md` in that root). Read-only commands print one
JSON object; `render` prints the Markdown section. Every writing command takes `--dry-run`
and reports the same result without touching the filesystem. Errors print one sanitized
line to standard error and exit `2`.

| Command | Writes | Purpose |
| --- | --- | --- |
| `schema` | no | Print the derived fields, labels, sublabels, and dependencies. |
| `list` | no | Print profile names and the store's existence, ignore, and tracking status. |
| `show --profile NAME` | no | Print one profile's schema fields, unknown keys, and missing fields. |
| `render --profile NAME` | no | Print the rendered `## Resources` section. |
| `endpoints --profile NAME` | no | Return validated historical-search endpoint objects only. |
| `ignore` | `.gitignore` | Ensure Git ignores the store, then verify it. |
| `init` | `.env` | Create an empty owner-only store. |
| `set --profile NAME --field FIELD=value` | `.env` | Merge fields; `--replace` discards unmentioned fields; an empty value clears one. |
| `compose --profile ENV --profile APP --into NAME` | `.env` | Persist a combined snapshot; `--replace` replaces an existing target. |
| `remove --profile NAME` | `.env` | Delete one profile's keys and marker. |
| `remove-env` | `.env` | Delete the whole store; `--force` is required when it holds unmanaged keys. |
| `load --profile NAME --task PATH` | task | Load effective Resources with user-field precedence; `--replace` permits rewriting an already-populated section. |

## Write guards

- `set` and `init` refuse to write unless Git ignores the store; `remove`, `remove-env`, and
  `ignore` refuse to touch a store Git tracks.
- `set` validates the merged profile against the schema and confirms it renders at least one
  bullet before writing, then re-reads the store and compares it with what was requested.
- `remove` re-reads the store and fails if the profile is still present.
- `load` requires an existing, non-symlink task with exactly one `## Resources` heading,
  refuses a profile that renders no bullet, preserves already-supplied values unless
  `--replace` is passed, and re-reads the written section.
- `remove-env` reports the profiles and unmanaged key names it would delete, and confirms
  the file is gone afterward.

## Scope

The helper manages the store and the task's Resources section. It does not authenticate to
any resource, resolve artifact names or destinations, create or rename a task, read or write
any environment variable of the running process, or export anything into a child process.

## Rhyming endpoints

The template now declares the optional **Rhyming endpoints** resource bullet. This is an additive,
optional `RHYMING_ENDPOINTS` field; existing profiles and the v1 store format remain valid.
A template change is required because undeclared fields are rejected by the derived schema.
`schema` exposes its type, kinds, maximum bytes/items, required and conditional keys.

The field is one JSON array, from 1 to 16 objects, at most 8192 UTF-8 bytes, kept on one line.
An unset field means no historical-search endpoints; `[]` is rejected to avoid an ambiguous
configured-empty run. Scalar fields and every object value retain the 512-character limit.
JSON keys and endpoint IDs must be unique. Each object has exactly `id`, `kind`, `target`,
and the conditional key below. IDs are lowercase kebab-case. Unknown keys/kinds are errors.

| kind | target | Conditional key |
| --- | --- | --- |
| grafana-investigations | Explicit prior-investigation scope or search phrase | context: configured gcx context |
| grafana-assistant-conversations | Explicit historical conversation scope or phrase | context: configured gcx context |
| grafana-assistant-search | Explicit historical resource scope or search phrase for an Assistant matching request | context: configured gcx context |
| confluence | HTTPS Atlassian Cloud page URL under /wiki/ | None |
| slack | Channel ID beginning C or G, or explicit #channel name | None |
| repository | HTTPS GitHub or Bitbucket owner/repository URL | provider: github or bitbucket, matching the host |

Example structure (documentation only; supply actual resources):

```json
[{"id":"history","kind":"grafana-investigations","target":"service-a","context":"ops"},{"id":"code","kind":"repository","target":"https://github.com/example/service-a","provider":"github"}]
```

Use `set --profile NAME --field RHYMING_ENDPOINTS=VALUE` with a properly shell-quoted JSON
value. Prefer a structured process argument when automating; never interpolate profile values
into executable shell text. The helper writes the same single-quoted dotenv representation.
Object values cannot contain credential patterns, placeholders, control characters, backticks,
single quotes, dollar signs, angle brackets, or backslashes. Contexts use alphanumerics, dot,
underscore and hyphen; Grafana target phrases additionally allow spaces, colon and slash.
URLs reject userinfo, ports, IP literals, query strings, fragments, encoded controls and path
traversal. Only the two declared repository hosts and Atlassian Cloud wiki URLs are supported;
unsupported hosts require an explicit future schema extension, never a silent provider change.

`set`, `show`, `render`, `load`, and `endpoints` validate known stored values, including manual
edits, before returning resources or changing a task. `endpoints` also requires ignored,
untracked storage and rejects unknown fields. Errors do not echo endpoint values. The command
returns `{ "profile": "NAME", "endpoints": [...], "historical_window_days": 7 }`; no auth, query or delegation occurs there.

Search dependencies are conditional: gcx-cli for the three Grafana kinds, rovo-dev-mcp for
Confluence and Bitbucket, slack-mcp for Slack, and GitHub access tooling for GitHub. Native
agent delegation is required by the rhyming search contract. Profile management itself stays
Python/Git only and does not require credentials or any connected endpoint.

## Rhyming historical window

`RHYMING_HISTORICAL_WINDOW_DAYS` is declared by the template's **Rhyming historical window days**
bullet. The v1 format is unchanged. Schema metadata exposes type `positive-integer-days`,
default `7`, and `render_requires: RHYMING_ENDPOINTS`. Values are ASCII positive integers,
without units, signs, leading zeroes or whitespace, within the scalar 512-character limit.
Malformed stored values fail before show/render/load/endpoints or a write; errors omit values.

On new nonempty profile creation, `set` appends the missing default to that profile's `.env`
block, even when endpoints have not yet been supplied. An explicit value wins. Updates preserve
it; updates to legacy endpoint profiles persist a missing default. `--replace` builds a new
set of fields, applying the same missing-default rule to endpoint profiles. An empty window
assignment clears its stored key on that command; endpoint reads/rendering then use seven days.
Setting `7` explicitly persists a reset. A later endpoint-profile update may persist the default
again. Empty replacement/removal never creates a default-only profile. `--dry-run` shows the
would-be default without writing. Custom templates without this field receive no stored default.

Render/load include this setting only with validated endpoints, including a resolved default for
legacy profiles. Without endpoints it is omitted, and a window alone cannot satisfy the actual
resource requirement. `endpoints` returns integer `historical_window_days`, or `null` when the
endpoint list is absent. No read command rewrites `.env`; an unavailable search integration is
handled later by Rhyming Incident Search and never causes profile management to authenticate.

The explicit `grafana-assistant-search` kind permits a scoped billable Assistant prompt through
[Rhyming Incident Search](../../rhyming-incident-search/SKILL.md). It uses the same Grafana
validation; profile reads/writes never launch a prompt. `grafana-assistant-conversations`
continues to read existing history only. Honor `Grafana Assistant: disabled` during execution.

## Settings contract

Template bullets are either **resources** (what to investigate or where to publish) or
**settings** (how a run behaves). Every on/off setting is a toggle with one shared contract:

| Field | Task bullet | Default | Legacy values |
| --- | --- | --- | --- |
| `GENERATE_PDF` | `Generate PDF` | `enabled` | `T` = `enabled`, `F` = `disabled` |
| `GRAFANA_ASSISTANT` | `Grafana Assistant` | `enabled` | none |
| `FAN_OUT` | `Fan-out` | `enabled` | none |

- **Values.** Only exact lowercase `enabled` or `disabled`. Other case, boolean words,
  numbers and surrounding whitespace are errors and fail before any write.
- **Schema.** `schema` reports each toggle as `type: enum`, `enum: [enabled, disabled]`, its
  `default`, and `resource: false`; a toggle with legacy values also reports `legacy_values`.
- **Precedence.** An explicit `--field` override, then the saved task value, then the profile,
  then the default. A template placeholder counts as absent.
- **Task form.** A task bullet may quote the value or write it bare
  (`- Generate PDF: disabled`); loading renders the quoted form.
- **Persistence.** New or updated nonempty profiles persist a missing default, except when
  the field is explicitly cleared with an empty `set` value, which restores the default.
- **Legacy values.** A legacy value in a command, a stored profile or a saved task resolves to
  its canonical value. Reads never rewrite the store; the next update of that profile, and
  any load into a task, writes the canonical value.
- **Not a resource.** A toggle alone is configuration: it never satisfies the
  actual-resource requirement, triggers the supplied-resource overwrite guard, or authorizes
  an investigation, a query or a publication.

A new on/off setting joins this contract by adding its template bullet and its entry in the
helper's toggle table; it does not define its own value vocabulary.

## Generate PDF

`GENERATE_PDF` derives from the template's **Generate PDF** Resources bullet and follows the
[settings contract](#settings-contract): exact `enabled` or `disabled`, default `enabled`.
The earlier `T` and `F` values remain accepted as legacy input and resolve to `enabled` and
`disabled`; they are never written again.

Profiles without the field resolve `enabled` on show/render/load without rewriting the store.
`show` distinguishes stored `fields` from `effective_generate_pdf`; custom templates without
the field do not materialize it. Invalid stored settings fail before writes, including when a
task overrides. A toggle or historical-window setting alone is configuration, never an actual
resource.

Render includes the effective choice alongside actual resources. Load preserves an explicit
task `Generate PDF` value even with `--replace`; duplicate or invalid task values fail
before mutation. A template placeholder is absent. An explicit toggle alone does not trigger
the supplied-resource overwrite guard; other existing Resources still require `--replace`.
Loading a finalized task remains subject to the editor contract. Repeated loads with the
same inputs and `--replace` produce the same bytes. Unrelated store lines remain untouched.

```sh
python3 -B skills/profile-manager/scripts/profile_env.py --repository-root . set --profile team --field GENERATE_PDF=disabled
python3 -B skills/profile-manager/scripts/profile_env.py --repository-root . show --profile team
```

Resolve this choice before report dependencies: `enabled` generates/verifies the current PDF;
`disabled` retains verified Markdown, evidence and required graphs, skips PDF-only tooling/checks,
and preserves older PDFs as historical. Record the choice with the saved report so later
publication honors it without attaching stale companions. Configuration never authorizes
an investigation or publication.


## Repository values

`REPO` remains a string in command JSON and `.env`: a legacy scalar repository or a JSON
array of 1–16 unique nonempty repository strings. The entire field is bounded to 8192 UTF-8
bytes and each entry to 512 characters. Schema metadata exposes both limits. Lists preserve
order, reject duplicate entries, non-strings, malformed JSON, placeholders, credentials,
controls, backticks, angle brackets and backslashes. URL credentials, queries and fragments are
refused; the conventional `git` username in `ssh://git@host/path` is supported, as is
legacy `git@host:owner/repo.git` syntax. Provider resolution and reachability belong to source investigation, not storage.
Use explicit GitHub/Bitbucket URLs for mixed-provider lists; a short name needs a verified
provider context before investigation.

```dotenv
PROFILE__APP_ALPHA__REPO='["org/service-a","org/shared-library"]'
```

Set replaces or clears this field just like a scalar. Show preserves its stored format;
render/load emit a separate Repo bullet for every entry. Existing scalar profiles need no
migration. All known-field readers validate manually edited arrays before returning them.

## Profile composition

`compose --profile prod-us --profile app-alpha --into prod-us-app-alpha` reads the ordered
source profiles and persists a new named snapshot in the same ignored, untracked `.env`.
It requires at least two unique sources and a distinct target. Names remain kebab-case;
“Prod US” and “App Alpha” are display names. No source is modified and no TASK is loaded
implicitly. Run the existing load command with the combined profile afterward.

Merge stored fields only. REPO, SLACK_CHANNEL and PUBLISH use first-seen order and exact-string deduplication across
profiles, then revalidates the union's limits; duplicates within one input array are errors.
A one-entry result uses scalar form. Identical non-list values are compatible; differing
values fail without a write and identify only the conflicting field. This includes endpoint
JSON strings and stored PDF/history defaults, since the store has no provenance distinguishing
implicit defaults from explicit values. Missing defaults are filled after merging. Align or
clear a conflicting stored setting explicitly; composition never silently chooses a winner.
Unknown source fields fail rather than disappearing. Validate dependencies and require an
actual resource in the effective result before persistence.

An existing target needs `--replace`, which replaces its whole field set instead of preserving
stale fields. Sources remain unchanged, unrelated bytes (including CRLF line endings) remain
unchanged, and the store stays owner-only. Dry-run validates and previews without filesystem
writes. A store-size overflow fails before mutation. Atomic persistence is followed by a
read-back of all profiles. Repeating replacement with the same inputs yields the same bytes.
Refresh the snapshot explicitly after changing sources. Direct multi-profile TASK loading and
shell environment export are outside this command's scope.

### Worked example

The agent runs these commands when asked to compose and load profiles; the repository test
suite executes this block verbatim. All values are synthetic. `prod-us` is the environmental
profile, `app-alpha` the application profile with multiple repositories and Slack channels.
The first block creates the store and `prod-us`, the second `app-alpha`, and the third
composes them into a snapshot and loads it into the `docs/tasks/TASK.md` draft.

<!-- profile-composition-example:start -->
```sh
python3 -B skills/profile-manager/scripts/profile_env.py --repository-root . ignore
python3 -B skills/profile-manager/scripts/profile_env.py --repository-root . init
python3 -B skills/profile-manager/scripts/profile_env.py --repository-root . \
  set --profile prod-us \
  --field AWS_ACCOUNT=demo-prod-us-readonly \
  --field AWS_REGION=us-east-1 \
  --field GRAFANA_CONTEXT=demo-prod-us \
  --field SLACK_CHANNEL='#demo-ops' \
  --field PUBLISH=https://example.atlassian.net/wiki/spaces/OPS/pages/123/Investigations \
  --field REPO=https://github.com/demo-org/shared-config \
  --field 'RHYMING_ENDPOINTS=[{"id":"prior-work","kind":"confluence","target":"https://example.atlassian.net/wiki/spaces/OPS/pages/456/History"}]'
```

“App Alpha” (`app-alpha`) supplies the application configuration: multiple repositories
and multiple Slack channels. SLACK_CHANNEL accepts the same scalar-or-array shape and limits
as REPO, rendering a separate Slack channel bullet for every entry.
`REPO` keeps its field name and accepts either the existing scalar or a JSON array of up to
16 unique strings, 512 characters each and 8192 UTF-8 bytes total.

```sh
python3 -B skills/profile-manager/scripts/profile_env.py --repository-root . \
  set --profile app-alpha \
  --field 'REPO=["https://github.com/demo-org/app-alpha","https://github.com/demo-org/app-alpha-lib"]' \
  --field 'SLACK_CHANNEL=["#demo-app","#demo-library"]'
```

Compose both profiles into a named snapshot in `.env`, then load that snapshot into the
existing `docs/tasks/TASK.md` draft created by `open task`. `--dry-run` previews without writes.

```sh
python3 -B skills/profile-manager/scripts/profile_env.py --repository-root . \
  compose --profile prod-us --profile app-alpha --into prod-us-app-alpha --dry-run
python3 -B skills/profile-manager/scripts/profile_env.py --repository-root . \
  compose --profile prod-us --profile app-alpha --into prod-us-app-alpha
python3 -B skills/profile-manager/scripts/profile_env.py --repository-root . \
  render --profile prod-us-app-alpha
python3 -B skills/profile-manager/scripts/profile_env.py --repository-root . \
  load --profile prod-us-app-alpha --task docs/tasks/TASK.md --dry-run
python3 -B skills/profile-manager/scripts/profile_env.py --repository-root . \
  load --profile prod-us-app-alpha --task docs/tasks/TASK.md
```
<!-- profile-composition-example:end -->

The effective task Resources are:

```markdown
## Resources

- Repo (Bitbucket/Github): `https://github.com/demo-org/shared-config`
- Repo (Bitbucket/Github): `https://github.com/demo-org/app-alpha`
- Repo (Bitbucket/Github): `https://github.com/demo-org/app-alpha-lib`
- Slack channel: `#demo-ops`
- Slack channel: `#demo-app`
- Slack channel: `#demo-library`
- AWS account: `demo-prod-us-readonly`
- AWS region: `us-east-1`
- Grafana context: `demo-prod-us`
- Grafana Assistant: `enabled`
- Publish: `https://example.atlassian.net/wiki/spaces/OPS/pages/123/Investigations`
- Rhyming endpoints: `[{"id":"prior-work","kind":"confluence","target":"https://example.atlassian.net/wiki/spaces/OPS/pages/456/History"}]`
- Rhyming historical window days: `7`
- Generate PDF: `enabled`
- Fan-out: `enabled`
```


## User configuration precedence

User-specified values win over Profile Manager injection. For `load`, layer explicit repeated
`--field FIELD=value` overrides above saved TASK Resources, above profile fields, above defaults.
The existing guard requires `--replace` when Resources already contain actual values, but
replacement now retains all explicit user fields rather than only Generate PDF. Preserve task
bullets whose label is not in the template. Known scalar duplicates, malformed bullets and invalid
values fail before writes; repeated repository bullets form one validated list. Subsequent loads
treat saved task values as user configuration. Change them in the editor or use a newer explicit
command field. TASK user fields do not modify the profile store.

`compose` also accepts repeated `--field FIELD=value`. Validate all sources; resolve scalar
conflicts only when the user supplies that field explicitly, then layer the override before
missing defaults and effective dependency validation. An explicit REPO, SLACK_CHANNEL or PUBLISH replaces its inherited
union. Overrides must be nonempty, unique, schema-declared, validated values. They change only
the composed target, never its sources. All other conflicting stored fields remain errors.

Current explicit user instructions are the highest authority when the orchestrator prepares an
investigation's effective resources; profile values cannot replace them. Reflect the chosen
values in the shared resolved input before delegation, honoring all scope and authentication gates.


## Slack channel values

SLACK_CHANNEL accepts the existing scalar or a JSON array of 1–16 unique strings, at most
512 characters per entry and 8192 UTF-8 bytes total, using the same bounded resource-list
parser as REPO. Malformed/empty arrays, duplicates within an input list, non-strings,
placeholders, credentials, controls and unsafe Markdown delimiters fail before writes.
No stored value is migrated by reading. Set replaces/clears the field; show retains stored
format; render/load emit every channel as a repeated Slack channel bullet.

Compose forms a stable first-seen union of channel entries across profiles, then revalidates
limits. User --field overrides and existing explicit TASK channel selections replace inherited
lists. Repeated TASK channel bullets form one validated list, while other scalar duplicate
settings remain errors. All source profiles and unrelated .env bytes remain unchanged. A
single resulting channel uses scalar form. Resolve names, IDs, aliases, workspaces and access
later through Slack MCP; successful storage proves neither access nor permission to query.

## Publish destinations

PUBLISH accepts the existing scalar or a JSON array of 1–16 unique strings, at most 512
characters per entry and 8192 UTF-8 bytes total, using the same bounded resource-list parser
as REPO and SLACK_CHANNEL. Each entry is one publication destination: a Confluence parent page
(URL, ID or title) or a GitHub or Bitbucket repository URL, optionally with a branch and
directory. The store does not classify entries; Publish It does when publication is requested.

Malformed/empty arrays, duplicates within an input list, non-strings, placeholders,
credentials, URL user information, controls and unsafe Markdown delimiters fail before writes.
Unlike REPO, a URL query is permitted, because a Confluence page URL may carry its page ID
there. No stored value is migrated by reading, and existing scalar profiles need no change. Set
replaces/clears the field; show retains stored format; render/load emit every destination as a
repeated Publish bullet.

Compose forms a stable first-seen union of destinations across profiles, then revalidates
limits. User --field overrides and existing explicit TASK Publish bullets replace inherited
lists. Repeated TASK Publish bullets form one validated list. A single resulting destination
uses scalar form. Successful storage proves neither access nor permission to publish; an
explicit publish request remains required.

## Fan-out

`FAN_OUT` derives from the template's **Fan-out** bullet and follows the
[settings contract](#settings-contract): exact `enabled` or `disabled`, default `enabled`. `disabled`
makes the investigation run inline instead of fanning out;
[Per-Store Fan-Out](../../per-store-fan-out/SKILL.md) owns what that means for a run. `show`
distinguishes stored fields from `effective_fan_out`. Profiles stored before the setting
existed resolve `enabled` without a store rewrite. This is configuration, never an actual
resource, and it creates no scope or authority.

```sh
python3 -B skills/profile-manager/scripts/profile_env.py --repository-root . set --profile team --field FAN_OUT=disabled
python3 -B skills/profile-manager/scripts/profile_env.py --repository-root . show --profile team
```

## Grafana Assistant

`GRAFANA_ASSISTANT` derives from the template's **Grafana Assistant** bullet and follows the
[settings contract](#settings-contract): exact `enabled` or `disabled`, default `enabled`. New or updated
nonempty profiles persist a missing default, except when explicitly cleared with an empty
`set` value. Legacy read-only operations resolve the default without rewriting the store.
`show` distinguishes stored fields from `effective_grafana_assistant`; custom templates
without the field do not acquire it. This is configuration, never an actual resource or
permission to query Grafana.

```sh
python3 -B skills/profile-manager/scripts/profile_env.py --repository-root . set --profile team --field GRAFANA_ASSISTANT=disabled
python3 -B skills/profile-manager/scripts/profile_env.py --repository-root . show --profile team
```

The profile must already contain or be supplied with an actual resource. Omitted fields
remain unchanged. Composition treats conflicting stored settings as scalar conflicts;
resolve one explicitly with `--field GRAFANA_ASSISTANT=disabled` or align the sources.
The target changes while source profiles and unmanaged store bytes remain unchanged.

Load uses command `--field` overrides above explicit TASK values, above profile values,
above the default. It accepts both `- Grafana Assistant: disabled` and the backticked
value form, and renders the canonical backticked form. A setting alone does not trigger
the supplied-resource overwrite guard. Invalid or duplicate TASK settings fail before
writes; repeated loads with the same effective inputs and `--replace` are byte-stable.
Invalid stored settings also fail before an override can mask them.

Grafana Assistant incurs additional cost. `disabled` means zero prompts, including
indirect prompts from bundled guidance: Grafana work uses only gcx and relevant gcx agent
skills. Profile commands themselves never prompt Assistant or query Grafana.
