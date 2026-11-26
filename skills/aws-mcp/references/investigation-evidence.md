# Resource validation and evidence handoff

Use after the identity and bounded resource-access checks in [AWS MCP](../SKILL.md).
Working access starts investigation reads; it does not validate existing hypotheses.

## Validate material findings

1. Map each AWS-related claim or competing explanation to a discriminating resource read:
   deployment/configuration history, workload lifecycle, audit logs, metrics, or service logs.
   Search the authorized account, Regions, resource filters and incident window through MCP.
   A Grafana observation, repository configuration or successful STS call does not substitute
   for that resource evidence. If a relevant read cannot run, name its exact gap.
2. Discover identifiers and available operations before querying. Start with narrow metadata;
   expand only along the symptom's dependency path, within the existing scope. For EKS,
   discover the cluster's actual control-plane log groups and whether Kubernetes audit records
   are available. CloudTrail and Kubernetes audit logs describe different API surfaces;
   an empty CloudTrail search cannot exclude a Kubernetes change. Do not enable logging.
3. On an explicit account/profile correction, update the task's selected field through
   Profile Manager, preserving omitted fields, and read it back. Repeat CLI/MCP identity and
   the bounded resource read for that selection; keep previous-account evidence identified.
   Never try other accounts merely because a search is empty or denied.
4. Retain selected responses, query text/parameters, exact time bounds and timezone, filters,
   pagination/caps, observation time and errors. Empty, truncated, denied and unavailable
   results are distinct. Report the tested hypothesis, result and remaining uncertainty.

## Generate exploration code when needed

Use an available live MCP tool directly when sufficient. When bounded discovery or repeated
queries need code, generate and review a small reproducible driver using that connection's
actual schema. Review every operation and any script before executing it; enforce the
selected profile, explicit Region, expected account/role, query bounds and read-only controls.
The driver must call MCP for diagnostic resource reads; local CLI/SDK reads are not MCP proof.
Keep queries and selected results in caller-resolved evidence paths without credentials or
unnecessary payloads. Reuse a verified driver before making another one.

In this repository, [the bounded explorer](../../../scripts/aws_mcp_explore.py) accepts a saved
TASK, explicit profile/Region and expected account/role, a reviewed JSON command plan, and a
fresh evidence output. Inspect its help, plan validation and transport compatibility before
use. It uses AWS API MCP with read-only enforcement; follow the
[connection setup](mcp-connection-setup.md) for server selection and protection requirements.
An unavailable operation is a capability gap, never a reason to disable read-only protections.

## Interpret the audited operation

Preserve event time, API surface/verb, kind, namespace, resource name, changed field/value,
actor, user agent and response status when present. Distinguish request payload from a
successful response and from later observed workload behavior. Interpret absent fields as
unknown; an audit request is not a complete resource snapshot.

For example, a successful Kubernetes PATCH to a StatefulSet's
`spec.template.metadata.annotations`, setting `kubectl.kubernetes.io/restartedAt` to a
timestamp, has a payload **consistent with a rollout restart**. Say so, then correlate the
pod delete/create and process-start records when available. A `kubectl` user agent does not
capture the exact CLI command or prove who initiated it beyond the recorded principal.
AWS CloudWatch can hold Kubernetes audit evidence; its storage location does not turn the
operation into an AWS infrastructure patch. Do not infer an image upgrade from a restart:
pre-restart image tag/digest, replacement requested tag, replacement running digest, and
deployed source revision are separate facts requiring their own evidence.

## Hand off and verify

Return the source record and retrievable query/result references with normalized event times,
resource identity, field changes, evidence identifiers and explicitly bounded interpretation.
[Report Authoring](../../report-authoring/SKILL.md) owns collection attribution and required
event coverage in reports; [Diagramming Style](../../diagramming-style/SKILL.md) owns rendering.
Name these receiving owners in investigation plans as well as completed results; a list of
query steps without the report/graph handoff is incomplete. Do not leave material AWS
findings only in a tool transcript. Check that the handoff can
support the report's claims without a new search or an unstated account/timezone assumption.
