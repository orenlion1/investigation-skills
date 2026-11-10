---
name: aws-mcp
description: Authenticate a supplied AWS profile with browser sign-in when needed, wait for completion, verify AWS MCP access, and investigate root causes through scoped AWS resource queries. Use when handling AWS MCP connectivity, expired sessions, and read-only AWS troubleshooting.
---

# AWS MCP Authentication and Investigation

## Overview

Accept an AWS profile, such as `production-readonly`, for authentication or a read-only
root-cause investigation. The example profile is not a default. Keep profile login,
CLI identity, MCP identity, resource access, and diagnostic findings separate.

Example agent requests:

```text
Use $aws-mcp with profile production-readonly to authenticate in us-east-1.
Use $aws-mcp with profile production-readonly to investigate ECS service <service>
in us-east-1 between <start> and <end> UTC; open sign-in if needed and wait.
```

When this skill runs as part of an investigation, use the root
[soft delivery budget](../open-edit-close-execute/references/investigation-delivery.md)
from request receipt; carry its original start into this work and check it at control boundaries.
Reuse verified setup and shared evidence; preserve this skill's required coverage and gates.

## When to Use

- Authenticating a supplied AWS profile and verifying AWS MCP access.
- Recovering an expired or broken AWS MCP session.
- Read-only AWS root-cause investigation through scoped resource queries.

## Resolve profile and Region

Use the supplied profile or the profile explicitly resolved for the active task.
If missing, ask for it; local profile names from `aws configure list-profiles` can
help selection. Never silently select `default`, a billing profile, or another account.
Check `aws --version` and inspect only selected non-secret configuration fields:
Region, SSO session/Region, role ARN, source profile, and login method. Do not dump
credentials, credential-process output, token caches, or complete AWS config files.
Inspect override variable names and credential presence without exposing values;
resolve credential/endpoint/profile conflicts before live requests.

Resolve the resource Region from the request or verified selected-profile metadata.
Ask if missing or ambiguous. Before **every** regional call, including login and
MCP setup, enforce the repository allowlist: `us-east-1` and `eu-central-1` only.
This also applies to the configured IAM Identity Center SSO Region. An SSO Region
outside the allowlist blocks that login; do not override it to make login succeed.
Use global calls only when necessary, without discovering or enabling other Regions.

Use task-local variables and explicit arguments; preserve defaults and unrelated
settings. The following placeholders must be replaced with resolved values:

```bash
AWS_TASK_PROFILE='<selected-profile>'
AWS_TASK_REGION='<selected-allowed-region>'
case "$AWS_TASK_REGION" in
  us-east-1|eu-central-1) ;;
  *) printf '%s\n' 'Blocked: resolve an allowed AWS Region first.' >&2; exit 1 ;;
esac
aws sts get-caller-identity --profile "$AWS_TASK_PROFILE" \
  --region "$AWS_TASK_REGION" --output json --no-cli-pager
```

Missing tools are setup work under repository Required Dependencies: reuse working
installations, otherwise use
documented user-scoped installers and verify versions. `aws login` needs AWS CLI
2.32.0 or later. Report installed/updated tools, sources, and runtime changes.

## Open sign-in and wait

Reuse valid credentials and automatic refresh. When the user requests authentication
or the task requires renewal, start the selected profile's supported flow within
that authorization without asking for duplicate permission. A status-only or
explicit no-login request stops at the diagnostic result.

- **IAM Identity Center:** after validating its configured SSO Region, run
  `aws sso login --profile "$AWS_TASK_PROFILE" --region "$AWS_TASK_REGION"`.
  Respect both modern `sso_session` and legacy SSO profiles; do not migrate them.
- **Console login:** for an existing login-session profile, or an explicitly
  requested console-login setup, run
  `aws login --profile "$AWS_TASK_PROFILE" --region "$AWS_TASK_REGION"`.
  This may update the selected profile; never overwrite a different authentication
  method or create a missing profile merely to repair a session.
- **Assume-role/source-profile, credential process, MFA, or other federation:**
  follow the configured credential owner's renewal flow. Trace only the required
  source profile and validate its Regions. Do not replace it with console login,
  create access keys, or change role trust/permissions. Ask for the missing setup
  choice when the credential owner or login method cannot be determined.

Run the login client in a tracked interactive session. It normally opens the browser;
if opening fails, use the platform URL opener (on macOS, `open`) with the exact
authorization-start URL issued by that live client, passed as an argument safely.
Promptly provide that validated link as **Sign in to AWS**, naming the profile and
the check that will resume. Validate it against the selected AWS/SSO provider; do
not fabricate a URL. Share only the intended start link and sanitized status, never
raw debug output, tokens, codes, cookies, or callback URLs. Keep transient links out
of saved files. Do not choose `aws login --remote` just to obtain a link: it requires
manual authorization-code entry. Let the client own credentials and callbacks.

Keep the same client and callback listener alive while the user completes sign-in
and consent. Poll the tracked process in short waits and provide progress updates;
do not treat browser opening, elapsed time, or a user message as completed login.
Proceed only after the client exits successfully and the same explicit-profile STS
check succeeds. If cancelled, expired, or failed, report the sanitized blocker and
stop dependent reads. Do not reuse a dead link or start repeated competing flows.
An explicit permission denial with valid credentials needs permission diagnosis,
not repeated login.

## Verify the AWS MCP connection

Discover the available AWS MCP tools and their live schemas. Prefer the official
AWS MCP Server through its SigV4 proxy for named-profile workflows. CLI login alone
does not bind a running MCP server to that profile. OAuth-only MCP sessions do not
support local AWS profile switching; do not claim a profile was selected through one.

Inspect the selected MCP connection's non-secret launch settings. A single-profile
proxy must explicitly select the requested profile. With supported multi-profile
routing, pass `aws_profile` on every auth-requiring call that exposes it and verify
the profile is allowed. `AWS_MCP_PROXY_PROFILES` overrides `--profile` and
`AWS_PROFILE`; check for conflicts. Never assume changing shell environment changes
an already-running MCP process.

When required, configure a narrowly scoped profile-bound MCP connection using the
host's supported configuration mechanism and a verified released proxy version.
Preserve other connections and defaults. The official proxy supports `--profile`
and `--region`; use an official endpoint in the resolved allowed Region, such as
`https://aws-mcp.us-east-1.api.aws/mcp`. Reconnect through the host when needed.
Use read-only credentials where available and inspect proxy `--help` for compatible
read-only controls. Tool filtering alone does not make arbitrary scripts read-only:
review every script and API operation before execution. Do not disable protections
to expose a missing tool, weaken TLS, use unsigned requests, or broaden IAM access.

Through the selected MCP connection, invoke STS `GetCallerIdentity` using the live
schema (for example, a minimal identity script if `run_script` is exposed). Compare
Account and principal/role with the explicit-profile CLI result and any expected
account. Session suffixes may differ; an unexpected account or role blocks queries.
Then perform one bounded metadata read of the requested resource through MCP.
Catalog visibility or STS success alone does not prove resource access.

If the host cannot expose or reload the required MCP connection, report exactly
what is missing and the supported reload/setup step. Do not substitute CLI/SDK
resource queries and describe them as MCP results. CLI calls here are for local
authentication and identity verification; diagnostic resource queries use AWS MCP.

## Investigate root cause through AWS MCP

Resolve symptoms, resource identifiers, account, allowed Region, and time window
with timezone. Ask only for missing scope that changes the investigation. For an
authentication-only request, stop after verified MCP identity and the bounded
resource-access probe; do not start an unrelated investigation.

Use the live tool catalog and operation schemas rather than guessing tool names.
For script tools, inspect the execution contract and permitted libraries first;
explicitly select the resource Region for every client/API. Use only reviewed read
operations and selected fields. Avoid secret values, decrypted parameters, user
data, full environment dumps, and unrelated accounts. Log/metric query initiation
may be needed for reading telemetry; do not enable logging or create infrastructure.

Follow the symptom's dependency path and test competing explanations. Examples:

| Symptom | Useful bounded evidence |
| --- | --- |
| ECS deployment failures | Service events, deployment/task state, stopped-task reasons, target health, and matching logs/metrics. |
| Lambda errors or throttling | Function configuration metadata, error/throttle metrics, and matching log events. |
| RDS latency or connection failures | Instance/cluster state, events, connection/latency metrics, and relevant network configuration. |
| Recent regression | Deployment/configuration timestamps and scoped CloudTrail events correlated with the symptom window. |

Discover actual resource/log-group/metric identifiers before querying. Bound filters,
time windows, returned fields, page counts, and log volume. Follow pagination within
the agreed scope or disclose caps and remaining cursors; empty or sampled results
do not prove absence. Handle rate limits with bounded retries. Correlate timestamps
and identifiers across configuration, events, metrics, and logs; a configuration
risk or one error string alone does not establish root cause.

Return observed facts, the supported cause or ranked hypotheses, evidence, gaps,
and the next discriminating check. State when root cause remains unconfirmed.
Recommendations do not authorize restarts, deployments, security changes, writes,
or remediation. For saved investigations, follow repository Report Evidence,
Workflow Artifact Naming, Token Usage, and required Markdown/PDF report contracts.

## Verification

Report the selected profile, verified account/principal, MCP connection, Regions,
resource IDs, observation time/window, queries, result limits, and access failures.
Distinguish login success, CLI identity, MCP identity, object access, and behavioral
evidence. Successful login is not proof of MCP access or root cause.

Consult current installed help and official sources for version-sensitive setup:

- [AWS MCP setup](https://docs.aws.amazon.com/agent-toolkit/latest/userguide/getting-started-aws-mcp-server.html)
- [MCP profile routing](https://docs.aws.amazon.com/agent-toolkit/latest/userguide/multi-account-access.html)
- [Official MCP proxy](https://github.com/aws/mcp-proxy-for-aws)
- [SSO login](https://docs.aws.amazon.com/cli/latest/reference/sso/login.html)
- [Console login](https://docs.aws.amazon.com/cli/latest/reference/login/)

## Common Rationalizations

- "Deleting leftovers is harmless cleanup." The workflow is read-only; mutations need their own authorization.
- "Any profile or Region works." Use only the supplied profile and an explicitly resolved, allowlisted Region.
- "Sign-in completed, so access is proven." Only a verified bounded read proves MCP access.

## Red Flags

- Mutating AWS calls during an investigation.
- Operations in a Region outside the allowlist, or with an unverified profile.
- Credentials, tokens, or sign-in URLs echoed into output or evidence.
