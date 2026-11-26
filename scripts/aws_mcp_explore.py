#!/usr/bin/env python3
"""Bounded AWS reads over AWS API MCP; never invokes diagnostic AWS CLI directly.

Requires Python 3.11 or newer.
Run with: uv run --with mcp==1.30.0 python scripts/aws_mcp_explore.py --help
Plans are JSON lists of reviewed AWS read commands. Responses may contain private
metadata: use an ignored evidence directory. Existing outputs are never replaced.
The child server is pinned and restricted with READ_OPERATIONS_ONLY=true.
"""
import argparse
import asyncio
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import shlex

SERVER = "awslabs.aws-api-mcp-server==1.6.1"
READS = {
    ("sts", "get-caller-identity"), ("eks", "list-clusters"),
    ("eks", "describe-cluster"), ("eks", "list-updates"),
    ("eks", "describe-update"), ("logs", "describe-log-groups"),
    ("logs", "describe-log-streams"), ("logs", "filter-log-events"),
    ("logs", "start-query"), ("logs", "get-query-results"),
    ("cloudtrail", "lookup-events"), ("ecr", "describe-images"),
    ("ecr", "describe-repositories"), ("ec2", "describe-instances"),
}


def scope(task, profile, region):
    if task.count("## Resources\n") != 1:
        raise ValueError("task requires exactly one Resources section")
    resources = task.split("## Resources\n", 1)[1].split("\n## ", 1)[0]
    for label, expected in (("AWS account", profile), ("AWS region", region)):
        values = re.findall(r"^- " + label + r": `([^`]+)`\s*$", resources, re.M)
        if values != [expected]:
            raise ValueError("selected " + label + " must match the single saved task value")


def command(raw, region):
    tokens = shlex.split(raw)
    if (len(tokens) < 3 or tokens[0] != "aws" or tuple(tokens[1:3]) not in READS
            or any(x in raw for x in (";", "\n", "\r", "`", "$", "file://", "fileb://"))):
        raise ValueError("command must be a reviewed allowlisted read")
    forbidden = ("--region", "--profile", "--endpoint", "--cli-input", "--debug",
                 "--no-sign", "--no-verify", "--ca-bundle", "--output", "--generate-cli")
    # AWS CLI accepts unambiguous option abbreviations; reject those too.
    options = [t.split("=", 1)[0] for t in tokens[3:] if t.startswith("--")]
    if (any(option.startswith(blocked) or blocked.startswith(option)
            for option in options for blocked in forbidden)
            or any(t in ("|", "&&", ">", "<", "&") for t in tokens[3:])):
        raise ValueError("command cannot override identity, region, transport or input")
    if tokens[1:3] == ["logs", "start-query"]:
        if "--query-string" not in tokens:
            raise ValueError("log queries require an explicit projection")
        query = tokens[tokens.index("--query-string") + 1]
        projection = query.rsplit("|", 1)[-1].strip()
        if not projection.startswith("display ") or "@message" in projection:
            raise ValueError("log queries must end with display of reviewed metadata fields")
    return shlex.join(tokens + ["--region", region, "--output", "json", "--no-paginate"])


def verify_identity(data, account, role):
    """Require exact account and SSO role, not strings embedded in error text."""
    records = data.get("structuredContent", {}).get("result", [])
    if data.get("isError") or len(records) != 1:
        raise ValueError("MCP identity response unavailable")
    response = records[0].get("response", {})
    if response.get("status_code") != 200 or response.get("error"):
        raise ValueError("MCP identity call failed")
    identity = json.loads(response["as_json"])
    arn = identity.get("Arn", "")
    principal = (r"arn:aws:sts::" + re.escape(account)
                 + r":assumed-role/AWSReservedSSO_" + re.escape(role)
                 + r"_[0-9a-fA-F]{16}/[^/]+")
    if identity.get("Account") != account or not re.fullmatch(principal, arn):
        raise ValueError("MCP identity does not match expected account and SSO role")


async def run(args):
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    scope(args.task.read_text(), args.profile, args.region)
    commands = json.loads(args.plan.read_text())
    if not isinstance(commands, list) or not 1 <= len(commands) <= 12:
        raise ValueError("plan must contain 1–12 read commands")
    requested_commands = commands
    commands = [command(c, args.region) for c in requested_commands]
    # Always verify server identity before executing the supplied discovery plan.
    identity = command("aws sts get-caller-identity", args.region)
    env = dict(os.environ, AWS_API_MCP_PROFILE_NAME=args.profile, AWS_PROFILE=args.profile,
               AWS_REGION=args.region, AWS_DEFAULT_REGION=args.region,
               READ_OPERATIONS_ONLY="true", AWS_API_MCP_TELEMETRY="false",
               AWS_PAGER="", FASTMCP_LOG_LEVEL="ERROR")
    for key in ("AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_SESSION_TOKEN",
                "AWS_ENDPOINT_URL", "AWS_MCP_PROXY_PROFILES"):
        if key in os.environ:
            raise ValueError("resolve credential/endpoint override before running: " + key)
    if any(key.startswith("AWS_ENDPOINT_URL_") for key in os.environ):
        raise ValueError("resolve service endpoint override before running")
    receipt = {"started_at": datetime.now(timezone.utc).isoformat(), "profile": args.profile,
               "region": args.region, "server_package": SERVER, "read_operations_only": True,
               "requested_commands": requested_commands, "results": []}
    # Exclusive, private output reserved before any remote work.
    fd = os.open(args.output, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    try:
        async with asyncio.timeout(240):
            params = StdioServerParameters(command="uvx", args=[SERVER], env=env)
            async with stdio_client(params) as (reader, writer):
                async with ClientSession(reader, writer) as session:
                    info = await session.initialize()
                    receipt["server"] = info.serverInfo.model_dump(mode="json")
                    catalog = await session.list_tools()
                    tool = next((t for t in catalog.tools if t.name == "call_aws"), None)
                    if tool is None:
                        receipt["catalog"] = [t.model_dump(mode="json") for t in catalog.tools]
                        raise ValueError("call_aws unavailable; inspect saved live catalog")
                    receipt["tool_schema"] = tool.inputSchema
                    properties = tool.inputSchema.get("properties", {})
                    if "cli_command" not in properties:
                        raise ValueError("unsupported live call_aws schema; inspect receipt")
                    for index, cli in enumerate([identity] + commands):
                        async with asyncio.timeout(65):
                            result = await session.call_tool("call_aws", {"cli_command": cli})
                        data = result.model_dump(mode="json")
                        receipt["results"].append({"command": cli, "response": data})
                        if index == 0:
                            verify_identity(data, args.expected_account, args.expected_role)
                        print("Saved result " + str(index) + (" (tool error)" if result.isError else ""), flush=True)
    except BaseException as exc:
        receipt["failure_type"] = type(exc).__name__
        raise
    finally:
        receipt["finished_at"] = datetime.now(timezone.utc).isoformat()
        with os.fdopen(fd, "w") as out:
            json.dump(receipt, out, indent=2)
            out.write("\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--task", type=Path, required=True)
    parser.add_argument("--profile", required=True)
    parser.add_argument("--region", required=True)
    parser.add_argument("--expected-account", required=True)
    parser.add_argument("--expected-role", required=True)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    asyncio.run(run(parser.parse_args()))


if __name__ == "__main__":
    main()
