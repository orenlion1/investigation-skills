# Sub-Agent Brief Template

Copy this template verbatim. The resolved block and output contract are identical in
every brief of a run; only Store, Integration skill, and Store-specific questions change.
Placeholders in angle brackets are the only editable text.

The manifest schema, the launch-mode vocabulary and the harness mechanics are not here: they
belong to the [shared delegation contract](delegation-contract.md), which every delegating skill
in this catalog uses. This file owns only the store brief and the store conformity checklist.

## Brief template

```markdown
# Investigation brief: <store>

## Store
- Store: <Grafana | AWS | Atlassian | Slack>
- Integration skill: <gcx-cli | aws-mcp | rovo-dev-mcp | slack-mcp>
- Resolved identity: <context / profile+Region / workspace objects / channel>

## Resolved block (identical across all briefs in this run)
- Environment: <environment>
- Time window: <start> .. <end>
- Timezone: <IANA timezone>
- Task questions: <the task's questions, verbatim>
- Constraints: read-only; only the objects above; AWS stays within
  us-east-1/eu-central-1; no mutations, acknowledgments, messages, or publication.

## Store-specific questions
- <question 1>
- <question 2>

## Output contract
Return exactly these sections:
- Findings: one entry per observation — claim; object identity; retrievable
  reference (URL, ID, or query); timestamp or query scope.
- Limitations: what was not examined and why.
- Failed or denied queries: verbatim, sanitized.
- Follow-ups: questions for OTHER stores that your findings raise, each naming
  the target store.
Do not draw cross-store conclusions; do not mutate anything.
```

## Conformity checklist

- One brief per resolved store; at most one Atlassian brief.
- Resolved blocks byte-identical across briefs.
- All branches launched before any result is awaited, or the degradation declared in
  the manifest and the report, under the [shared delegation contract](delegation-contract.md).
- Follow-ups routed by continuing the existing branch agent, and three follow-up rounds
  maximum — this skill's own bound, not the contract's.
- A manifest written for every run, including disabled runs, with one row per resolved
  store carrying `store` and `integration_skill`.
