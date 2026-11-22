# Install gcx and its agent skills

Read when `gcx` is missing or incompatible, when the official gcx skills are not installed for
the active harness, or after a gcx binary upgrade. Routine refresh and host detection are in
[SKILL.md](../SKILL.md#ensure-gcx-and-its-skills-are-ready).

## Install gcx

Use the [official installation guide](https://grafana.com/docs/grafana-cloud/ai-tools/gcx/installation/).

- Reuse an installed binary outside PATH before installing a duplicate.
- Prefer an existing package manager when it satisfies repository installation boundaries. With
  an eligible existing Homebrew installation, run `brew install gcx`.
- Otherwise use the documented installer or a verified official release at user scope, such as
  `~/.local/bin`. Prefer a released or pinned version; preserve checksum verification.
- Apply only the PATH adjustment needed for the selected executable, preserving unrelated shell
  settings.
- Verify the resolved path, `gcx --version`, and `gcx --help`, then install the harness skills
  below before context resolution and the requested query.
- Report any installation/update, version, source, and runtime configuration changes.

Retain repository Required Dependencies safeguards: ask first only when setup would require
sudo/system-wide changes, weakened signing or certificate verification, an undocumented package
source, credentials, billing, or a license. Report the exact blocker if no permitted
installation method works; never bypass these safeguards.

## Install the official skill suite

Follow the [official gcx integration reference](https://github.com/grafana/gcx#use-with-your-ai-agent).
Inspect installed command help before choosing flags. Install the entire official gcx skill
suite for the detected harness only (not both by default), automatically and without a separate
approval prompt, preserving unrelated skills and configuration.

**Codex** uses the portable bundle in `~/.agents/skills`, which Codex discovers. Run
`gcx agent skills update`, then `gcx agent skills install --all` to add any missing bundled
skills; `update` alone does not install newly bundled skills. Pass the same `--dir` explicitly
to install, update, and list when a verified user-scoped installation root differs from the
default.

**Claude Code** uses the official plugin described in the
[Claude integration guide](https://github.com/grafana/gcx/blob/main/claude-plugin/README.md).
Check the selected user's plugin/marketplace inventory, then register `grafana/gcx` if absent
and install `gcx@gcx-marketplace` at user scope. Use the installed CLI's supported equivalents
of these Claude commands:

```text
/plugin marketplace add grafana/gcx
/plugin install gcx@gcx-marketplace
```

`gcx agent skills update` refreshes portable installations, not Claude's plugin cache. Do not
create a second portable installation to disguise an unrefreshed plugin.

## Preserve, verify and report

- Inspect previews/inventory and preserve unexpected symlinks, custom conflicting files, and
  unrelated plugins; do not force overwrite or delete retired skills.
- Check command exit status and verify the installed inventory against the current
  bundle/plugin before claiming setup complete.
- Report the detected harness, installation source/location, versions or available bundle
  identity, refresh result, and any changes or remaining reload requirement.
