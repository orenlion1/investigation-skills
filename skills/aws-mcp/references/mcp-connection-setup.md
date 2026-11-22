# AWS MCP connection setup

Use when the selected profile needs a profile-bound MCP connection that the host
does not already expose. The safeguards in [SKILL.md](../SKILL.md) apply.

- Configure a narrowly scoped profile-bound connection through the host's
  supported configuration mechanism and a verified released proxy version.
  Preserve other connections and defaults.
- The official proxy supports `--profile` and `--region`; use an official
  endpoint in the resolved allowed Region, such as
  `https://aws-mcp.us-east-1.api.aws/mcp`.
- Inspect proxy `--help` for compatible read-only controls.
- Reconnect through the host when needed.

Consult current installed help and official sources for version-sensitive setup:

- [AWS MCP setup](https://docs.aws.amazon.com/agent-toolkit/latest/userguide/getting-started-aws-mcp-server.html)
- [MCP profile routing](https://docs.aws.amazon.com/agent-toolkit/latest/userguide/multi-account-access.html)
- [Official MCP proxy](https://github.com/aws/mcp-proxy-for-aws)
- [SSO login](https://docs.aws.amazon.com/cli/latest/reference/sso/login.html)
- [Console login](https://docs.aws.amazon.com/cli/latest/reference/login/)
