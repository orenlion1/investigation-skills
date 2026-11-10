---
name: slack-mcp
description: Inspect Slack MCP configuration, diagnose OAuth or permission errors, discover available Slack capabilities, and validate connectivity with bounded workspace or profile reads. Use when asked to check a Slack connection or troubleshoot MCP access; keep message composition and broader Slack workflows with their owning task.
---
<!-- source: self; self-authored: self; managed-by: https://github.com/orenlion1/dotfiles; sync-from: https://github.com/orenlion1/dotfiles; dotfiles-sync-date: 2026-10-15; dotfiles-sync-commit: b79db3e29956b7262bf1b990471eb3844c854df2 -->

# Slack MCP

## Overview

Identify the Slack connection being tested, inspect its authentication and available tools, and
prove access with a minimal read. Distinguish configured settings, reachable transport,
authenticated MCP initialization, tool discovery, and successful Slack data access.

When this skill runs as part of an investigation, use the root
[soft delivery budget](../open-edit-close-execute/references/investigation-delivery.md)
from request receipt; carry its original start into this work and check it at control boundaries.
Reuse verified setup and shared evidence; preserve this skill's required coverage and gates.

## When to Use

Use for Slack MCP setup inspection, authentication troubleshooting, capability discovery, or a
read requested as proof of access. Broader Slack work retains its original scope and authorization.

## Select and Inspect the Connection

For a named server, validate that exact connection. For a general Slack connectivity request,
inspect the configured direct server and any available hosted connector separately. For an
ordinary Slack read, select an available authenticated route and identify it in the result.

- The official direct endpoint is `https://mcp.slack.com/mcp`, using Streamable HTTP. Slack does
  not support legacy SSE transport or Dynamic Client Registration. Do not replace an existing
  server or register another app merely to test it.
- In Codex, inspect the Slack entry under `mcp_servers` in `~/.codex/config.toml`; this workstation
  uses the alias `codex-slack-mcp`. Discover the actual name instead of assuming that alias exists
  on another host. OAuth client ID and callback settings identify the configured flow; their
  presence does not prove login. Inspect other clients only when they are in the requested scope.
- A hosted Slack connector, such as tools under `mcp__codex_apps__slack_*`, has its own connection
  and authorization. Its success cannot establish that a direct local MCP entry works. Do not
  copy its credentials into the direct server or silently substitute it for a failed named route.
- Report only the source path, server name, sanitized endpoint, enabled state, authentication
  status, and presence of required OAuth fields. Strip URL userinfo, query strings, and fragments.
  Do not print whole config files, token caches, authorization headers, client secrets, callback
  state, or authorization codes. Preserve unrelated MCP entries and client-owned settings.

For Codex, check the installed CLI before using authentication commands. This status filter
avoids printing transport headers or environment values from the JSON response:

```bash
codex --version
codex mcp list --json | python3 -c 'import json,sys; print(json.dumps([{k:s.get(k) for k in ("name","enabled","auth_status")} for s in json.load(sys.stdin) if "slack" in s.get("name", "").lower()], indent=2))'
codex mcp login --help
```

## Authentication and Recovery

Slack requires an approved registered app identity and user authorization. Check the selected
connection first; reuse working authentication and successful automatic refresh without another
login prompt. When interactive OAuth authorization is required, start the selected client's
supported flow within the task's authorization, honoring any applicable prerequisite login
barrier. For a configured Codex server, use the exact command with its discovered alias:

```bash
codex mcp login codex-slack-mcp
```

Replace the alias as needed. Attempt to open the browser and promptly provide the active client's
authorization-start URL as a clickable **Sign in to Slack** link, even if browser opening was
attempted. Name the connection and the read that will resume; do not assume a window appeared or
wait silently for timeout. Verify the link belongs to the selected flow's provider, preserve its
state/PKCE parameters, and keep the same client/callback listener alive while the user signs in.
Capture and filter output before forwarding it; share only that intended link and sanitized
status, never raw logs. Keep transient links out of repository files and reports.

For a hosted connector, use that host's actual Slack Connect/Reconnect link or control; a local
server's login does not renew the hosted grant. If no link is exposed or the flow cannot run here,
explain the limitation and identify the actual host control or provide the supported local command
with the discovered alias. Never invent a URL, start competing flows, or select manual
callback-entry mode just to obtain a link. If a flow exits, expires, or is cancelled, say its link
is no longer usable; do not reuse it. A warranted retry needs a fresh supported flow.

Let the client manage its secure credential storage and browser callback; never ask for passwords,
tokens, authorization codes, or callback URLs in chat. The authorization-start link is distinct
from those secrets. Let the user complete the secure prompt and consent.
An explicit status-only or no-login request takes precedence: report the missing authentication
and next step without prompting or starting consent.

Wait for the user to complete login before dependent reads; unrelated skill work may continue.
Then recheck that same connection's authentication, refresh its MCP connection if needed,
rediscover tools, and retry the bounded read. Do not treat the user's completion message or a
stored OAuth status as proof that the read works. If login is declined, cancelled, or unavailable,
leave validation pending and report the blocker. If revalidation still fails, report its actual
error without repeatedly prompting for login or switching providers. Check app approval, client
identity, callback registration, and required scopes for the relevant failure. Do not change
redirect URIs, toggle app-wide PKCE, register via unsupported DCR, or broaden scopes as a shortcut.

Consult [Slack's MCP authentication and scope contract](https://docs.slack.dev/ai/slack-mcp-server/)
and [client setup guidance](https://docs.slack.dev/ai/slack-mcp-server/connect-to-harnesses/)
for the selected client. Use installed CLI help when a documentation example differs from the
current client. [Slack PKCE configuration](https://docs.slack.dev/authentication/using-pkce/)
belongs to deliberate app setup, not a read-only diagnosis.

## Validate Connectivity

1. Confirm the selected route is enabled and has usable authentication. An unauthenticated
   `401` with a Bearer challenge proves endpoint reachability only. Do not claim initialization,
   tool availability, or Slack access from that response.
2. For direct MCP, complete `initialize` and `notifications/initialized`, negotiate the protocol,
   and retain required session headers through the host's MCP client. Discover `tools/list` and
   follow every `nextCursor`. For hosted tools, inspect the tools actually exposed in this session;
   report the result as a hosted connector check, not a direct-server handshake.
3. Use a listed read-only operation and its live schema. Prefer a workspace listing capped at
   one result and/or the authenticated user's concise profile. For example, the hosted connector
   may expose `slack_list_workspaces(limit=1, include_icon=false)` and
   `slack_read_user_profile(response_format="concise")`; these are examples, not guaranteed
   names or schemas for every client. Use channel metadata or a narrowly bounded search only
   when needed for the user's requested proof. Do not read message bodies just to test login.
4. Check JSON-RPC errors, MCP `isError`, and Slack `ok:false` payloads as applicable. HTTP 200 or
   an outer "Action completed" message is insufficient without the actual successful result.
   Empty results prove query execution, not retrieval of a workspace, profile, or message.

Never send a test message, save a draft, react, join a channel, invite a user, upload a file,
create a reminder, or change a profile to prove connectivity. Those are separate mutations and
require the user's task to authorize the specific action. Reading private channels or DMs must
also respect the selected tool's consent requirements and the user's requested scope.

## Capabilities and Blockers

Use the authenticated live catalog to determine whether search, conversation/thread reads,
profiles, canvases, lists, or files are available. Match scopes to the requested operation using
Slack's current scope table; visible tools alone do not establish access to every workspace or
channel. Full thread retrieval requires the thread operation, not just a channel-history page.

- `not_logged_in`, invalid tokens, or revoked authorization: request the selected client's login
  using the recovery flow above, then revalidate after completion. Do not extract tokens from
  another app or browser session.
- `missing_scope` or permission errors: identify the operation and any explicitly returned scope
  requirement. A generic access denial is not proof of a scope defect. Preserve existing grants.
- Rate limiting: respect `Retry-After`; keep any retry bounded and disclose an incomplete check.
- Transport, protocol, or tool errors: report the sanitized error and the last successful stage.
  If the selected route cannot complete the check, stop that check. Browser, CLI, direct Slack
  Web API, or another connector results do not prove the failed MCP route works.

## Verification

Report the route, endpoint where applicable, returned workspace/identity or requested object,
successful operation, result cap, and any untested capability. A connection is validated only
to the level actually observed; distinguish a reachable endpoint from authenticated discovery
and a successful read. A single workspace sample is not an exhaustive membership or permission
inventory. Stop after the requested probe and identify any remaining authentication step.

## Common Rationalizations

- "Slack is enabled" proves configuration, not an authenticated connection.
- "The hosted connector works" does not validate the separately configured direct server.
- "A harmless test message is enough" introduces an unnecessary external write.

## Red Flags

Stop for an unexpected endpoint, ambiguous workspace, missing authorization, an unavailable
required tool, or a proposed credential transfer between clients. Report the blocker without
persisting secret material or private message content in the skill, repository, or test fixtures.
