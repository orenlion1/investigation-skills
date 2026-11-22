---
name: gcx-cli
description: "Install gcx and its official Claude or Codex skills, keep them refreshed, and authenticate a selected Grafana context, including browser sign-in. Use when handling gcx setup, Grafana connectivity, or expired sessions. Grafana resource queries belong to parallel-grafana-investigation; this skill supplies their command mechanics."
---
<!-- source: self; self-authored: self; managed-by: https://github.com/orenlion1/dotfiles; sync-from: https://github.com/orenlion1/dotfiles; dotfiles-sync-date: 2026-08-30; dotfiles-sync-commit: 42a3e852aa9d6786e9e7f27e3fc77790fea09ffd -->

# Grafana CLI Authentication and Investigation

## Overview

Accept a Grafana context for authentication or a read-only root-cause investigation through
`gcx`. Keep local configuration, successful authentication, Grafana API access, datasource
query results, and diagnostic findings separate.

Example agent requests:

```text
Use $gcx-cli with context example to authenticate; open sign-in if needed and wait.
Use $gcx-cli with context example to investigate memory alerts for <service>
between <start> and <end> UTC through the parallel Grafana investigation.
```

The context names are examples, not defaults. Resolve the actual configured context before
authentication or live queries, as `aws-mcp` resolves the supplied AWS profile.

When this skill runs as part of an investigation, use the root
[soft delivery budget](../open-edit-close-execute/references/investigation-delivery.md)
from request receipt; carry its original start into this work and check it at control boundaries.
Reuse verified setup and shared evidence; preserve this skill's required coverage and gates.

## When to Use

Use for gcx installation, bundle preparation, authentication, connectivity and command mechanics.
Route every user-requested Grafana resource query to
[Parallel Grafana Investigation](../parallel-grafana-investigation/SKILL.md), including alerts,
non-alert troubleshooting, exact expressions, telemetry reads, health checks and inventory. That
skill owns both parallel branches, shared request scope, manifest, reconciliation, Assistant cost
controls and verification; this skill supplies setup, bundle refresh, context, authentication
and gcx command mechanics. Setup-only requests stop after the authorized checks; a resource read
explicitly requested after setup enters that workflow. Internal setup probes, metadata discovery
and queries within its existing branches never recursively launch another pair. Task-specific
authoring and incident handling retain their own scope; connecting does not authorize mutations.

## Ensure gcx and its skills are ready

Before context discovery or any Grafana query, check `command -v gcx` and `gcx --version`, and
reuse a working compatible installation. If `gcx` or the official gcx skill suite for the
active harness is missing, install it per
[Install gcx and its agent skills](references/install-and-skills.md) and continue the requested
work **without requesting approval**: required installation, routine user-scoped PATH setup and
the full skill suite are already authorized. Do not stop at suggesting installation or asking
the user to run it. That reference also holds the ask-first safeguards (sudo, weakened
verification, undocumented sources, credentials, billing, license) and the setup report.

Detect the active host from the session identity and supported environment signals, not from
which executables or skill folders happen to exist. Codex session identity and its
`CODEX_THREAD_ID`/`CODEX_CI` signals identify Codex; `CLAUDECODE` or `CLAUDE_CODE` identify
Claude Code. Inspect only these non-secret identity signals. For ambiguous or conflicting
signals, use the verified host identity; ask which host to target only if it remains
unresolved. Prepare that host, not both by default.

Before **each operational gcx command** — context checks, authentication, Assistant, discovery,
and resource/telemetry queries — refresh the detected harness's skills:

- **Codex:** `gcx agent skills update` against the selected root (`~/.agents/skills` unless a
  verified `--dir` differs).
- **Claude Code:** update only `gcx-marketplace` and its `gcx@gcx-marketplace` plugin through
  the supported plugin manager. For example, where local help confirms support:
  `claude plugin marketplace update gcx-marketplace`, then
  `claude plugin update gcx@gcx-marketplace --scope user`. Honor any actual reload requirement
  and read the current skill content explicitly when the session catalog has not reloaded yet.

Availability/version/help checks and skill installation, inventory, refresh, and
content-loading commands are bootstrap exceptions; they do not recursively trigger another
refresh. After a gcx binary upgrade, reconcile the full bundle again so newly shipped skills
are installed. If installation or refresh fails, report the exact sanitized blocker and stop
dependent operational commands rather than silently using stale guidance. Read only the
relevant refreshed skills for the requested workflow; installing the suite does not authorize
its write actions.

## Resolve the Context

Use the context explicitly selected in the request or already resolved for the active task.
For example, `context: example`, `context: example-eu`, or `context: example-secondary` maps to
the same `--context` value only if that context exists. These names are examples, not an allowlist:
another explicitly selected configured context is valid. Do not silently use `current-context`,
switch to a lookalike stack, or run a query across contexts to discover which one was intended.

Inspect local metadata before any live request:

```bash
gcx --version
gcx config path
gcx config list-contexts -o json
```

If the context is unresolved, ask one short question using the actual configured names. If the
user explicitly asks for the current context, resolve its name and server, then pass that name
explicitly. Confirm that the selected server matches the requested stack. A missing context or
conflicting server is a configuration blocker; do not let a login command create or repoint it
without the user's configuration request.

Keep the same working directory and configuration selection throughout the task. `GCX_CONFIG`
or `--config` selects one file; otherwise user and repository configuration can layer. Inspect
authentication method through redacted `gcx config view`, never raw files or `--raw`. Report only
the context, sanitized server, auth method, credential presence, and config paths. Never use
`--insecure-log-http-payload`, expose tokens/passwords, or collect browser callback URLs in chat.
Configured server and `auth-method` are not necessarily the effective runtime target and
credential source: check the presence and names of relevant `GRAFANA_*` overrides, including
`GRAFANA_SERVER`, without exposing their values. Resolve any target or credential conflict before
a live check; do not assume redacted configuration includes runtime overrides. An absent method
does not imply OAuth. Use the installed version's configuration
guidance; the [online configuration reference](https://grafana.com/docs/grafana-cloud/ai-tools/gcx/configuration/)
may describe a newer release.

## Open sign-in and wait

Default to browser-based OAuth when choosing authentication for a Grafana stack connection.
Prefer `gcx login ... --oauth` for new connections and user-requested authentication changes;
do not ask the user to create or supply an API token by default. Use token authentication only
when the user explicitly chooses it or the requested capability demonstrably requires it, such
as an API or unattended workflow that cannot use the supported OAuth flow. Explain that exception
and use the existing secure secret mechanism. If OAuth fails, report the blocker rather than
silently falling back to an API token.

Replace the placeholder with the resolved context. Check only that context: omitting `--context`
from `gcx config check` checks every configured context.

```bash
GCX_CONTEXT='<selected-configured-context>'
gcx config check --context "$GCX_CONTEXT"
```

Use existing working authentication and successful automatic token refresh without requesting
another login. When the user requests authentication or the task requires renewal, check installed
`gcx login --help` and start the supported flow within that authorization without asking for
duplicate permission. A status-only or explicit no-login request stops at the diagnostic result
and reports the next step without prompting. For an existing OAuth context the supported command is:

```bash
gcx login "$GCX_CONTEXT" --oauth
```

For explicitly requested new setup, first resolve the new context name and intended server;
use `gcx login "$GCX_CONTEXT" --server "$GCX_SERVER" --oauth` with those confirmed values.
Do not infer a server or override an existing context's destination as part of authentication.

Record the previous current context before login: login can select the authenticated context as
current. Preserve the previous default selection unless the user asked to switch, and read the
selection back afterward, including after a failed or cancelled flow.

Run the login client in a tracked interactive session. Attempt to open the browser; if automatic
opening fails, use the platform URL opener with the validated authorization-start URL passed
safely as an argument. Promptly provide the active client's authorization-start URL as
a clickable **Sign in to Grafana** link, even if browser opening was attempted. Name the actual
context and the check or query that will resume; do not assume a window appeared or wait silently
for timeout. Verify the URL belongs to the selected flow's provider and preserve its state/PKCE
parameters. Capture and filter client output: share only the intended sign-in link and sanitized
status, never raw logs, tokens, authorization codes, or callback URLs. Keep transient links out of
repository files and reports. Let the client handle credentials and callbacks.

Keep that same client and callback listener alive while the user signs in and consents. Poll the
tracked process in short waits and provide progress updates. Browser opening, elapsed time, or a
user message does not establish completed login. Proceed only after the client exits
successfully, then repeat the same explicit-context check and requested bounded read. A
successful login is not itself query evidence. If the user declines, cancels, cannot sign in, or
the retry still fails, report the sanitized blocker and stop; do not repeatedly prompt or switch
contexts.

If the flow ends or expires, say the link is no longer usable; never reuse it. If no link is
available or the flow cannot run here, explain the limitation and provide the supported command
with the actual context name. Do not invent a URL, start competing flows, or choose manual
callback-entry mode merely to obtain a link. A warranted retry requires a fresh supported flow.

For an existing service-account token, Cloud access-policy token, or Basic-auth context, ask the user to
renew the selected credential through its existing secure secret store or interactive client
flow unless they requested an authentication-method change. The OAuth default does not silently
migrate existing contexts. Do not copy credentials between contexts or pass token/password values
in command arguments. On this workstation, Bitwarden-backed gcx contexts
are refreshed by the dotfiles secret workflow; preserve that ownership and its runtime OAuth
state. A Grafana stack token and a Cloud management token serve different APIs: a working stack
query does not prove Cloud API access, and a missing Cloud token does not justify changing stack
authentication. Request new permissions only for the actual operation that needs them.

Treat permission errors, datasource failures, query syntax errors, and empty results separately
from missing login. A generic `403` is not proof of expired credentials. Respect rate limits and
keep retries bounded. Do not weaken TLS verification, override the server, or create resources
to make a connectivity check pass. For client-specific setup details, read the installed guide
with `gcx agent skills get setup-gcx -otext` and use current command help.

## Verify Grafana access

After the context check, prove the needed capability with a minimal read. If no object was
specified, a capped datasource listing is suitable; inspect supported output fields first:

```bash
gcx datasources list --help
gcx datasources list --context "$GCX_CONTEXT" --limit 1 --json uid,name,type
```

A successful listing proves inventory access, not successful Prometheus, Loki, or Tempo queries.
An empty listing is a successful empty response, not a retrieved datasource. Stop after this
probe for a connectivity-only request; proceed into telemetry queries only when requested.

## Query branch mechanics

Within the routed workflow, its Assistant branch uses `gcx assistant prompt` with explicit
`--context` and a fresh conversation. Inspect installed help before choosing flags. An example
after scope resolution:

```bash
gcx assistant prompt --help
GCX_PROBLEM='<exact request, expression/resources, applicable window/timezone, limits, output, read-only scope>'
gcx assistant prompt "$GCX_PROBLEM" --context "$GCX_CONTEXT" \
  --json --no-stream --timeout 300
```

Only that designated branch sends the prompt, including any compatible prepared matching handoff
under [Assistant matching](../rhyming-incident-search/references/assistant-search.md).
The direct branch uses relevant bundled gcx skills and dedicated reads concurrently; it never
starts another Assistant prompt. `gcx agent skills get <name>` displays instructions rather
than executing them. Honor disabled Assistant with zero prompts and direct gcx work only.
Retain prompt/response identifiers, references and limitations; treat conclusions as leads.
If Assistant fails, record the sanitized blocker and continue authorized direct reads without
switching context. Changes, acknowledgments, messages and publication need separate authority.

Direct reads follow [gcx query mechanics](references/query-mechanics.md): datasource and label
discovery, metrics/logs/traces and inventory command forms, instant versus range flags, limits
and caps, share links, and cross-signal analysis.

## Verification

Report the explicit context and server, datasource UID/type or resource identifier, query and
time range, outcome, and result limits. Separate a completed empty query from authentication,
permission, and transport failures. Never interpret no returned telemetry as proof of service
health. Do not hide a failed check with a later successful command or count a partial result as
complete. Keep credentials and unnecessary private log or trace content out of reports.

## Common Rationalizations

- "The current context is probably right" does not resolve the user's target.
- "Login succeeded" does not prove the requested datasource query works.
- "The query returned nothing" does not establish healthy services or missing permissions.

## Red Flags

Stop for an unresolved context, unexpected server, unavailable credentials, denied operation,
or a proposal to change authentication method or bypass TLS as a shortcut. Query and connectivity
requests do not authorize creating, updating, deleting, acknowledging, or publishing Grafana
resources. When the user separately requests a mutation, follow the owning workflow, preview
supported changes, and read back the affected resource in the same explicit context.
