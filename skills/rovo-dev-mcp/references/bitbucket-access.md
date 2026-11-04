# Bitbucket access and recovery

## Diagnose the credential before changing the organization

A valid Rovo Dev login and a successful MCP `resources` call do not establish Bitbucket access.
For v2 reads, verify `read:bitbucket:agent-interface` and `read_bitbucket`, then discover and execute
the requested repository operation. Legacy scopes such as `read:repository:bitbucket` do not replace
the v2 grant. The OAuth consent controls which operations the server exposes.
[Atlassian scopes](https://developer.atlassian.com/cloud/rovo-mcp/guides/supported-tools/),
[OAuth authorization](https://developer.atlassian.com/cloud/rovo-mcp/guides/configuring-oauth-2-1/)

Inspect only credential provenance, authentication scheme, scope names, and expiry. In particular,
a Basic header in the matching Rovo MCP configuration can shadow a newly refreshed Keychain token.
Never display tokens, authorization headers, full configuration, environment files, returned
authorization codes, callback URLs, or browser tab titles containing a callback. A client-issued
authorization-start link intended for the user is distinct from those secrets; surface it using
the [handoff below](#authorization-link-handoff). Filter subprocess output before it reaches tool
logs; do not forward raw client output.

If discovery exposes only `system` operations or `getContentFormatGuide`, check the selected
credential and product scope first. This symptom suggests missing authorization; it does not prove
an absent repository, an unlinked workspace, or an MCP outage. `?tools=all` can check the full
paginated catalog, but it cannot grant missing permissions.

## Establish scoped MCP OAuth

Use the current provider discovered from the v2 endpoint's `WWW-Authenticate` resource metadata.
The public metadata is at
`https://mcp.atlassian.com/.well-known/oauth-protected-resource/v2/mcp`.
Let the OAuth client follow its advertised authorization server and registration endpoints. Do
not reuse a legacy client registration or invent `audience` parameters.

If a native MCP login fails with `invalid_request`, try the documented `mcp-remote` client with
a fresh, dedicated cache. A native-client failure is not proof of an account permission problem.
The following flow was verified with the released npm package `mcp-remote@0.15.1`; reuse a compatible
installed version or the pin, and do not repeatedly install or erase unrelated credential caches.
[Atlassian client setup](https://atlassian.github.io/atlassian-mcp-server/),
[mcp-remote options](https://github.com/punkpeye/mcp-remote)

Set `ROVO_BITBUCKET_OAUTH_CACHE` to a dedicated user-owned directory. Preserve an existing metadata
file if it contains a different requested scope; resolve that choice before replacing it.

```bash
ROVO_BITBUCKET_OAUTH_CACHE="$HOME/.mcp-auth/rovo-bitbucket-v2"
umask 077
mkdir -p "$ROVO_BITBUCKET_OAUTH_CACHE"
```

Create `client-metadata.json` in that directory only if absent, with:

```json
{
  "scope": "read:me read:account offline_access read:bitbucket:agent-interface"
}
```

Then authenticate or refresh through the OAuth client. Reuse a working grant or successful
automatic refresh without prompting. When interactive sign-in is required, keep the client
running and follow the handoff below. Omit `--silent` from this standalone recovery command so
the client can emit its authorization link; capture and filter output before displaying it.

```bash
MCP_REMOTE_CONFIG_DIR="$ROVO_BITBUCKET_OAUTH_CACHE" \
  npx --yes --package=mcp-remote@0.15.1 mcp-remote-client \
  https://mcp.atlassian.com/v2/mcp \
  --transport http-only \
  --static-oauth-client-metadata "@$ROVO_BITBUCKET_OAUTH_CACHE/client-metadata.json" \
  --auth-timeout 300
```

Keep the directory private (`0700`) and credential files private (`0600`). Verify cached scope
and expiry without printing credentials. `mcp-remote` owns refresh; the helper reads the current
cache and does not perform its own OAuth grant. Do not copy a short-lived token into MCP config,
shell history, a managed source file, or a command argument.

Use `--oauth-cache "$ROVO_BITBUCKET_OAUTH_CACHE"` on each bundled-helper command. This explicit
selection overrides inherited headers and fails rather than switching accounts or auth methods
when the cache is unusable. Exactly one valid scoped credential must resolve. The helper accepts
the official `/v2/mcp` endpoint, including its `?tools=all` catalog variant, for this credential.
The credential must include a parseable future `expires_at`; a file modification time is not
evidence of token freshness.

For Jira and Confluence, use the [separate grant contract](../SKILL.md#separate-mcp-grants).
Create a distinct `rovo-jira-confluence-v2` cache and its own metadata; preserve the Bitbucket
cache. For one known Jira issue plus a page search and read, the metadata is:

```json
{
  "scope": "read:me read:account offline_access read:jira:agent-interface read:confluence:agent-interface search:confluence:agent-interface"
}
```

Run the same OAuth client with that cache's metadata path and `MCP_REMOTE_CONFIG_DIR`, then select
it explicitly with `--oauth-cache` and the operation's `--oauth-scope`. Supported scopes are the
Bitbucket read scope and Jira/Confluence read or search scopes listed in the skill. The flag checks
the cached grant; it does not request new consent or expand permissions. Without this flag, cache
validation still requires the Bitbucket read scope.

Resource and tool-catalog probes can succeed with a credential whose product calls return 403.
Check the product call's fixed error category and obtain its own scoped grant when needed. A
legacy-scoped Rovo Dev token and configured Basic token can both lack these v2 grants; switching
between them or repeatedly refreshing CLI login does not establish product authorization.

## Authorization-link handoff

When the selected OAuth client requires user interaction:

1. Use the supported flow for the selected connection and product grant. Honor an explicit
   status-only or no-login request and any applicable prerequisite login barrier. Keep one active
   client and its callback listener running; do not start competing flows to obtain another link.
2. Capture the authorization-start URL emitted by that client and verify it belongs to the
   provider discovered from the official endpoint's metadata. Extract only that intended link
   and sanitized status/error text before forwarding output. Never forward arbitrary URLs from
   logs, returned authorization codes, access/refresh tokens, or callback URLs. Do not derive a
   link from credential caches or browser callback state.
3. Attempt to open the link in the user's browser and immediately present it as a clickable link
   in chat, even when opening reports success. For example, use **Sign in to Bitbucket MCP** as
   the link label, name the selected connection, and explain that its repository read will resume
   after sign-in. Do not claim the window appeared without evidence or wait silently for timeout.
   Preserve the client-issued URL, including its state and PKCE parameters; do not construct or
   edit it. Keep transient authorization links out of repository files, reports, and saved logs.
4. Let the user complete sign-in and consent; do not collect credentials or callback values in
   chat. Keep the callback process alive while waiting. If it exits, expires, or is cancelled,
   say that the link is no longer usable. Do not reuse it or repeatedly restart a failed flow.
   A warranted retry must use a fresh link from a fresh supported flow.
5. If the client exposes no authorization URL or cannot run here, state that limitation and
   identify its actual Connect/Reconnect control or give its supported local command with the
   resolved connection/cache paths. Do not invent a URL or switch to a manual callback-entry
   mode merely to obtain one. A hosted connector reconnects through its host; local MCP OAuth
   does not renew that hosted grant.

After completion, recheck the same credential source and product grant, reconnect as needed,
then repeat authenticated resources, the complete tool catalog, discovery, and the requested
bounded object read. Login completion alone does not prove access. Diagnose missing scopes and
permission failures separately; a generic 403 does not justify repeated sign-in prompts.

## Persist the working client

Add a distinct `atlassian-bitbucket` stdio server using `npx`, the pinned package, the v2 URL,
`--transport http-only`, the metadata file argument, and `--silent`. Set its
`MCP_REMOTE_CONFIG_DIR` environment entry to the absolute cache directory. Store paths and client
options in configuration; leave credentials in the OAuth cache.
The persistent transport may remain silent. If it needs interactive reauthorization, use the
standalone recovery flow above so the user receives its sign-in link.

For Codex, the CLI can add the server after the standalone connection has passed:

```bash
codex mcp add atlassian-bitbucket \
  --env "MCP_REMOTE_CONFIG_DIR=$ROVO_BITBUCKET_OAUTH_CACHE" -- \
  npx --yes mcp-remote@0.15.1 https://mcp.atlassian.com/v2/mcp \
  --transport http-only \
  --static-oauth-client-metadata "@$ROVO_BITBUCKET_OAUTH_CACHE/client-metadata.json" \
  --silent
```

Rovo Dev uses the corresponding `command`, `args`, and `env` entry in `~/.rovodev/mcp.json`.
Check existing names and preserve unrelated settings. In this dotfiles configuration, a separate
runtime server survives hydration; `atlassian-native` is managed as HTTP, so do not repurpose that
entry for stdio. Do not run whole-repository hydration merely to add a runtime server.

Read back the configuration and test a fresh connection using those exact settings. Verify
resources, discovery, and one requested repository read after reconnecting. Report if the host
must reload its MCP connections before the new server becomes available in its tool list.

## Organization checks after scoped OAuth

If properly scoped OAuth still lacks access, inspect the organization's Atlassian MCP server
permissions under **Connectors → Atlassian MCP server → Permissions** and its Bitbucket read
permission. Check existing workspace linkage and the user's repository access. Do not enable
write permissions for a read task.
[MCP permission controls](https://support.atlassian.com/security-and-access-policies/docs/configure-atlassian-mcp-server-permissions/)

Workspace linking requires the appropriate workspace and organization administrators. It is a
separate ownership change: Atlassian documents that admins cannot currently unlink or transfer
the workspace afterward. Do not choose or link an inferred organization as an auth repair.
[Workspace linkage](https://support.atlassian.com/bitbucket-cloud/kb/linking-your-bitbucket-cloud-workspace-to-an-atlassian-organization/)
