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
- Values are written single-quoted (`PROFILE__EXAMPLE__REPO='example-service'`), so the file
  stays safe to read with a dotenv parser or `set -a; . ./.env`.

A key inside the `PROFILE__` prefix that does not split into exactly three non-empty parts
is an error, not a key to ignore: the store fails closed rather than silently dropping an
entry someone expected to be in effect.

## Parsing and preservation

- Blank lines, `#` comments, and every assignment outside the `PROFILE__` prefix are
  preserved in place, in order, byte-for-byte. Their values are never parsed or printed.
- A managed value may be single-quoted, double-quoted, or a bare token without whitespace,
  `#`, quotes, or backslashes. Anything else is rejected rather than guessed at.
- An optional `export ` prefix is accepted when reading and not written.
- Writes are atomic: a temporary file in the same directory is replaced into place. A new
  store is created `0600`; an existing store keeps its current mode.
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
| `ignore` | `.gitignore` | Ensure Git ignores the store, then verify it. |
| `init` | `.env` | Create an empty owner-only store. |
| `set --profile NAME --field FIELD=value` | `.env` | Merge fields; `--replace` discards unmentioned fields; an empty value clears one. |
| `remove --profile NAME` | `.env` | Delete one profile's keys and marker. |
| `remove-env` | `.env` | Delete the whole store; `--force` is required when it holds unmanaged keys. |
| `load --profile NAME --task PATH` | task | Replace the task's `## Resources` body; `--replace` is required when it already supplies values. |

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
