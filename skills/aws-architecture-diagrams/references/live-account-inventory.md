# Inventory from a live account

Use when there is no IaC, or the IaC covers only a fraction of what is deployed.
The source is then the live account, read-only, and the diagram must be explicit
that that is what it is.

Start from a tag predicate rather than a service-by-service sweep, because it is
the only way to bound "what belongs to this system":

```bash
aws resourcegroupstaggingapi get-resources --region <region> \
  --tag-filters 'Key=<key>,Values=<v1>,<v2>'
```

Several tag keys need one request each, unioned by ARN afterwards — passing two
keys in one request applies AND, silently dropping everything that carries only
one of them. Record the resulting count and date; it is a snapshot, not a fact.

The tagging API does not return every resource type, and tags are not ownership.
So the tag query gives you the node set, and **relationships come from the APIs
that actually model them**:

| To establish | Read |
| --- | --- |
| Ingress wiring | `elbv2 describe-load-balancers`, `describe-target-groups` |
| Which paths are permitted | `ec2 describe-security-groups`, `describe-vpcs` |
| What a compute tier may call | `iam get-instance-profile`, then `get-policy-version` |
| Data-tier shape and replicas | `rds describe-db-instances`, `elasticache describe-*` |
| Async wiring | queue redrive policies, S3 notifications, event rules |

Resolve every CIDR you find to a named VPC before drawing it; an unresolved
`10.16.0.0/16` on a diagram tells a reader nothing.

Classify every edge by the evidence it rests on, per the evidence classes in
[SKILL.md](../SKILL.md).
