---
name: gcx-cli
description: "Install gcx when missing, prepare and refresh its official skills for Claude or Codex, authenticate a selected Grafana context with browser sign-in when needed, and investigate root causes through scoped queries. Use when handling gcx setup, connectivity, expired sessions, and read-only Grafana troubleshooting."
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
between <start> and <end> UTC; propose the parallel investigation plan without running it.
```

The context names are examples, not defaults. Resolve the actual configured context before
authentication or live queries, as `aws-mcp` resolves the supplied AWS profile.

## When to Use

Use for gcx authentication and connectivity, datasource discovery, PromQL, LogQL, TraceQL, and
dashboard or alert inventory. Task-specific dashboard authoring, incident handling, and Grafana
Assistant workflows retain their own scope; connecting does not authorize those mutations.

## Ensure gcx is installed

Before context discovery or any Grafana query, check `command -v gcx` and
`gcx --version`. Reuse a working compatible installation. If `gcx` is missing,
install it by default and continue the requested work **without requesting approval**.
Required installation and routine user-scoped PATH setup are already authorized;
do not stop at suggesting installation or asking the user to run it.

Use the [official installation guide](https://grafana.com/docs/grafana-cloud/ai-tools/gcx/installation/).
Prefer an existing package manager when it satisfies repository installation
boundaries. With an eligible existing Homebrew installation, run `brew install gcx`.
Otherwise use the documented installer or a verified official release at user scope,
such as `~/.local/bin`. Prefer a released or pinned version; preserve checksum
verification. Reuse an installed binary outside PATH before installing a duplicate.

Apply only the PATH adjustment needed for the selected executable, preserving
unrelated shell settings. Verify the resolved path, `gcx --version`, and `gcx --help`,
then prepare the harness skills below before context resolution and the requested query.
Report any installation/update, version, source, and runtime configuration changes.

Retain repository Required Dependencies safeguards: ask first only when setup would
require sudo/system-wide changes, weakened signing or certificate verification,
an undocumented package source, credentials, billing, or a license. Report the exact
blocker if no permitted installation method works; never bypass these safeguards.

## Detect the harness and prepare all gcx skills

Follow the [official gcx integration reference](https://github.com/grafana/gcx#use-with-your-ai-agent).
Detect the active host from the session identity and supported environment signals,
not from which executables or skill folders happen to exist. Codex session identity
and its `CODEX_THREAD_ID`/`CODEX_CI` signals identify Codex; `CLAUDECODE` or
`CLAUDE_CODE` identify Claude Code. Inspect only these non-secret identity signals.
For ambiguous or conflicting signals, use the verified host identity; ask which host
to target only if it remains unresolved. Install for that host, not both by default.

Inspect installed command help before choosing flags. Install the entire official
gcx skill suite for the detected harness automatically, without a separate approval
prompt, preserving unrelated skills and configuration:

- **Codex:** use the portable bundle in `~/.agents/skills`, which Codex discovers.
  Run `gcx agent skills update`, then `gcx agent skills install --all` to add any
  missing bundled skills. `update` alone does not install newly bundled skills.
  Pass the same `--dir` explicitly to install, update, and list when a verified
  user-scoped installation root differs from the default.
- **Claude Code:** use the official plugin described in the
  [Claude integration guide](https://github.com/grafana/gcx/blob/main/claude-plugin/README.md).
  Check the selected user's plugin/marketplace inventory, then register
  `grafana/gcx` if absent and install `gcx@gcx-marketplace` at user scope.
  Use the installed CLI's supported equivalents of these Claude commands:

  ```text
  /plugin marketplace add grafana/gcx
  /plugin install gcx@gcx-marketplace
  ```

  For refresh, update only `gcx-marketplace` and its `gcx@gcx-marketplace`
  plugin through the supported plugin manager. For example, where local help
  confirms support: `claude plugin marketplace update gcx-marketplace`, then
  `claude plugin update gcx@gcx-marketplace --scope user`.
  `gcx agent skills update` refreshes portable installations, not Claude's
  plugin cache. Do not create a second portable installation to disguise an
  unrefreshed plugin. Honor any actual reload requirement and read the current
  skill content explicitly when the session catalog has not reloaded yet.

Before **each operational gcx command**, refresh the detected harness's skills:
Codex runs `gcx agent skills update` against the selected root; Claude runs the
plugin refresh above. This includes context checks, authentication, Assistant,
discovery, and resource/telemetry queries. Availability/version/help checks and
skill installation, inventory, refresh, and content-loading commands are bootstrap
exceptions; they do not recursively trigger another refresh. After a gcx binary
upgrade, reconcile the full bundle again so newly shipped skills are installed.

Inspect previews/inventory and preserve unexpected symlinks, custom conflicting
files, and unrelated plugins; do not force overwrite or delete retired skills.
Check command exit status and verify the installed inventory against the current
bundle/plugin before claiming setup complete. If installation or refresh fails,
report the exact sanitized blocker and stop dependent operational commands rather
than silently using stale guidance. Read only the relevant refreshed skills for
the requested workflow; installing the suite does not authorize its write actions.
Report the detected harness, installation source/location, versions or available
bundle identity, refresh result, and any changes or remaining reload requirement.

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
duplicate permission. A status-only or explicit no-login request stops at the diagnostic result.
For an existing OAuth context the supported command is:

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
repository files and reports. Let the client handle credentials and callbacks, and keep that same
client/listener alive while the user signs in and consents.

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

Keep the same client and callback listener alive while the user signs in. Poll the tracked
process in short waits and provide progress updates. Browser opening, elapsed time, or a user
message does not establish completed login. Proceed only after the client exits successfully,
then repeat the same explicit-context check and requested bounded read. A successful login is
not itself query evidence. If the user declines, cancels, cannot sign in, or the retry
still fails, report the sanitized blocker and stop; do not repeatedly prompt or switch contexts.
For an explicit status-only or no-login request, report the next step without prompting.

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

## Start a root-cause investigation

For an alert investigation request, first propose two parallel sub-agents and wait for explicit
authorization to execute that plan. Do not run investigation commands, install or refresh skills,
start sign-in, or launch sub-agents while preparing the proposal. Use supplied or already
verified context and identify missing inputs without live discovery. This proposal-only rule
takes precedence over the operational setup steps above and any task execution continuation.

Propose the same Grafana context, alert identity, environment, exact time window and timezone,
and read-only scope for both agents:

1. **Grafana Assistant agent:** run `gcx assistant prompt` with explicit `--context` and a fresh
   conversation. Retain structured output, response/conversation identifiers, links, and limits.
2. **Alert investigation agent:** load and invoke the refreshed official `investigate-alert`
   skill through the active harness, gathering bounded direct evidence. The command
   `gcx agent skills get investigate-alert` only displays the instructions; it does not run an
   investigation. Do not invent a CLI invocation or start a second Assistant conversation.

After authorization, perform the required setup, refresh, context resolution, and authentication,
then launch both agents before awaiting either. Direct reads in the second branch need not wait
for the Assistant response; this parallel alert workflow replaces the sequential entry point
below. If delegation is unavailable, report the limitation rather than silently running serially.
Reconcile both results, verify material claims against direct evidence, and preserve disagreements,
gaps, and limitations. Changes, acknowledgments, messages, and publication need separate authority.

For other authorized problem investigations, resolve the symptoms, affected resources, environment, exact time
window and timezone, and questions to answer. After local help, context resolution,
authentication, and any bounded connectivity probes, start with `gcx assistant prompt` before
ad hoc datasource, dashboard, alert, metrics, logs, or traces investigation, as required by
repository policy. Check installed help first and use the same explicitly resolved context:

```bash
gcx assistant prompt --help
GCX_PROBLEM='<problem, resources, environment, time window/timezone, questions, read-only scope>'
gcx assistant prompt "$GCX_PROBLEM" --context "$GCX_CONTEXT" \
  --json --no-stream --timeout 300
```

Use a fresh conversation for a new investigation. Use `--continue` or a verified `--context-id`
only for the same investigation. Each prompt consumes billable Assistant tokens; avoid duplicate
starts and unnecessary retries. Retain the prompt, available conversation/response identifiers,
observation time, links, and limitations. If Assistant is unavailable or denied, record the
sanitized failure and continue authorized direct reads in the same context.

Treat Assistant conclusions and suggested queries as leads. Verify material claims with bounded
direct queries against actual datasource and resource identifiers. Authentication-only requests
stop after connectivity verification and do not start Assistant conversations.

## Query Grafana

1. Resolve the signal, selected context, requested service/resource, and time range. Ask only for
   missing information that changes the query. Report the timezone and actual interval used.
2. Discover the datasource with `gcx datasources list`, filtering by `--type` and optionally
   `--name`, and use the returned UID with `-d`. An ambiguous match needs clarification. A cap
   is a sample, not a complete inventory; widen discovery within the same context when necessary.
3. Inspect labels or metadata before inventing selectors. `gcx metrics labels` supports
   `--metric`, `--match`, and `--label`; `gcx logs labels` supports `--label`. Check installed help:
   do not assume every discovery command supports time-range or result-limit flags.
4. Use dedicated signal commands and structured output. Bound time and results; avoid broad log
   selectors or full trace bodies merely to test a connection. For unknown commands, use
   `gcx help-tree <group> -o text` and the command's `--help`, not raw API passthrough.

The following templates use task-selected values; replace the UID and selectors after discovery.
The 15-minute window is an example, not a replacement for the user's requested time range.

```bash
GCX_PROMETHEUS_UID='<confirmed-prometheus-uid>'
gcx metrics query --context "$GCX_CONTEXT" -d "$GCX_PROMETHEUS_UID" \
  'up{job="<discovered-job>"}' --from now-15m --to now --step 1m -o json
GCX_LOKI_UID='<confirmed-loki-uid>'
gcx logs query --context "$GCX_CONTEXT" -d "$GCX_LOKI_UID" \
  '{job="<discovered-job>"}' --since 15m --limit 20 -o json
GCX_TEMPO_UID='<confirmed-tempo-uid>'
gcx traces query --context "$GCX_CONTEXT" -d "$GCX_TEMPO_UID" \
  '{ resource.service.name = "<selected-service>" }' --since 15m --limit 5 -o json
```

Use a datasource of the matching type for each command; do not reuse a Loki UID for metrics or
traces. Prometheus instant queries use `--time`; range queries use `--from`/`--to` or `--since`
with an appropriate `--step`. Do not combine instant and range flags. Metrics queries have no
`--limit`: narrow selectors or use suitable PromQL aggregation/topk and disclose that choice.
`--limit 0` on logs or traces is uncapped. Do not truncate output while claiming a complete result.

For inventory, use the relevant dedicated read command with filters and caps:

```bash
gcx resources get dashboards --context "$GCX_CONTEXT" --limit 20 \
  --json metadata.name,spec.title
gcx alert rules list --context "$GCX_CONTEXT" --limit 20 -o json
```

Use `--share-link` on supported successful signal queries when a Grafana Explore link helps the
user reproduce the result. Specialized SLO, IRM, Synthetic Monitoring, profiling, or other
product queries use their installed command groups and task guidance with the same context rule.
Assistant output does not replace these direct queries or authorize remediation.

Correlate timestamps, resource identifiers, alerts, metrics, logs, and traces across the symptom
window and a relevant baseline. Test competing explanations. Return observed facts, the
supported cause or ranked hypotheses, evidence, gaps, and the next discriminating check. State
when root cause remains unconfirmed; an error string or correlation alone does not establish it.
For saved investigations, follow repository Report Evidence, Workflow Artifact Naming, Token
Usage, and required Markdown/PDF report contracts.

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
