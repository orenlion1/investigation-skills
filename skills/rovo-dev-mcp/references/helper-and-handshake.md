# Helper and handshake reference

Rarely needed detail for the bundled `scripts/rovo-bitbucket-mcp.mjs` helper and for operating
without it. Routine use is in [SKILL.md](../SKILL.md#quick-start).

## Helper options and safeguards

- Besides `--oauth-cache PATH` and `--oauth-scope SCOPE`, the helper accepts `--env PATH`,
  `--mcp-config PATH`, and `--url URL`. It has no project, repository, or workspace default.
- Every authentication source is restricted to the exact official v2 endpoint or its `?tools=all`
  catalog variant. Other URLs are rejected before environment files, credential configuration,
  OAuth caches, or Keychain credentials are read.
- Each MCP request, including response-body reading, has a 30-second deadline; a multi-request
  command can take longer overall.
- OAuth cache entries are opened without following symlinks, then validated and read through the
  same file descriptor; runtimes without that filesystem protection fail closed.

## Credential order without `--oauth-cache`

1. `ATLASSIAN_MCP_AUTH_HEADER`, containing a complete `Basic` or `Bearer` header.
2. `MCP_OAUTH_TOKEN`, used as a Bearer token from the process environment.
3. `ATLASSIAN_MCP_AUTH`, or `ATLASSIAN_MCP_USER` plus `ATLASSIAN_MCP_TOKEN`, encoded as
   Base64 `user:token` for Basic authentication.
4. A matching endpoint's `Authorization` header in `~/.rovodev/mcp.json`, or `--mcp-config PATH`.
   Environment placeholders must resolve before this header can be used.
5. The macOS Keychain service `rovodev-oauth`, maintained by Rovo Dev. Expired credentials with
   an `expires_at` value are skipped.

An explicit `--env PATH` loads these authentication variables, including `MCP_OAUTH_TOKEN`,
without overriding non-empty process values. It does not search project directories. A matching
configured Basic header precedes the Keychain token, so refreshing the Keychain alone may not
change the credential actually sent. Inspect only the selected source, scheme, scopes, and expiry.

## Native MCP handshake

When operating without the helper:

1. Connect to `https://mcp.atlassian.com/v2/mcp` with HTTP transport and the configured
   `Authorization` header.
2. Send `Content-Type: application/json` and `Accept: application/json, text/event-stream`, then
   send `initialize` with MCP protocol version `2025-03-26`.
3. Capture and reuse the `Mcp-Session-Id` response header.
4. Send `notifications/initialized`.
5. Call `getAccessibleAtlassianResources` and select the intended site before product operations.
6. Call `tools/list` repeatedly while `nextCursor` is present.
7. Invoke listed primary reads directly using their live schemas. For deferred reads, call
   `discover`, then use the returned operation through `executeRead`.
