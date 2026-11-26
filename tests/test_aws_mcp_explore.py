"""Boundary checks for the read-only investigation client (no AWS calls)."""
import importlib.util
import json
from pathlib import Path
import unittest

SPEC = importlib.util.spec_from_file_location(
    "aws_mcp_explore", Path(__file__).parents[1] / "scripts/aws_mcp_explore.py")
explorer = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(explorer)


class ExplorerTests(unittest.TestCase):
    def test_log_queries_require_final_metadata_projection(self):
        for query in ("fields jsonParse(@message) as e | fields e.verb", "display @message"):
            with self.assertRaises(ValueError):
                explorer.command("aws logs start-query --query-string " + __import__('shlex').quote(query), "eu-central-1")
        explorer.command("aws logs start-query --query-string 'fields @timestamp | display @timestamp'", "eu-central-1")

    def test_identity_requires_structured_exact_account_and_role(self):
        def result(account, role):
            identity = {"Account": account, "Arn": "arn:aws:sts::" + account + ":assumed-role/AWSReservedSSO_" + role + "_0123456789abcdef/user"}
            return {"structuredContent": {"result": [{"response": {
                "status_code": 200, "error": None, "as_json": json.dumps(identity)}}]}}
        # Clearly synthetic values; keep account-like literals out of public fixtures.
        account, other_account = "0" * 12, "1" * 12
        explorer.verify_identity(result(account, "operations"), account, "operations")
        for data in (result(other_account, "operations"), result(account, "developer"),
                     result(account, "operations_admin"),
                     {"isError": True, "content": account + " operations"}):
            with self.assertRaises(ValueError):
                explorer.verify_identity(data, account, "operations")

    def test_requires_the_task_profile_and_region(self):
        task = "## Resources\n- AWS account: `prod`\n- AWS region: `eu-central-1`\n"
        self.assertEqual(explorer.scope(task, "prod", "eu-central-1"), None)
        for profile, region in [("default", "eu-central-1"), ("prod", "us-east-1")]:
            with self.assertRaises(ValueError):
                explorer.scope(task, profile, region)

    def test_duplicate_scope_fails_closed(self):
        task = "## Resources\n- AWS account: `prod`\n- AWS account: `other`\n- AWS region: `eu-central-1`\n"
        with self.assertRaises(ValueError):
            explorer.scope(task, "prod", "eu-central-1")

    def test_refuses_mutations_region_overrides_and_file_loading(self):
        for command in ["aws eks delete-cluster --name x", "aws eks list-clusters --region us-east-1",
                        "aws eks describe-cluster --cli-input-json file:///tmp/input",
                        "aws eks list-clusters; aws s3 ls", "aws eks list-clusters --endpoint-url https://example.com"]:
            with self.assertRaises(ValueError, msg=command):
                explorer.command(command, "eu-central-1")

    def test_adds_authorized_region_and_preserves_quoted_query(self):
        result = explorer.command("aws eks list-clusters --query 'clusters'", "eu-central-1")
        self.assertEqual(result, "aws eks list-clusters --query clusters --region eu-central-1 --output json --no-paginate")

    def test_refuses_abbreviated_identity_and_transport_overrides(self):
        for option in ("--prof other", "--reg us-east-1", "--endp https://example.com",
                       "--cli-in {}", "--no-sig", "--no-ver"):
            with self.assertRaises(ValueError, msg=option):
                explorer.command("aws eks list-clusters " + option, "eu-central-1")


if __name__ == "__main__":
    unittest.main()
