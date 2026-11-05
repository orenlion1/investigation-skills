# Sub-Agent Brief and Manifest Templates

Copy these templates verbatim. The resolved block and output contract are identical in
every brief of a run; only Store, Integration skill, and Store-specific questions change.
Placeholders in angle brackets are the only editable text.

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

## Manifest template

Record as a LOG artifact through Workflow Artifact Naming (default `logs/`); keep it
local and untracked.

```json
{
  "task": "<task path>",
  "launch_mode": "parallel | sequential | disabled",
  "degradation_reason": "<empty unless sequential/disabled>",
  "environment": "<environment>",
  "window": {"start": "<ISO-8601>", "end": "<ISO-8601>", "timezone": "<IANA>"},
  "branches": [
    {
      "store": "<store>",
      "integration_skill": "<skill>",
      "agent_id": "<harness agent identifier, or 'inline'>",
      "launched_at": "<ISO-8601>",
      "iterations": 0,
      "blocker": ""
    }
  ],
  "iteration_rounds": 0,
  "returned_to_user": ""
}
```

## Conformity checklist

- One brief per resolved store; at most one Atlassian brief.
- Resolved blocks byte-identical across briefs.
- All branches launched before any result is awaited (parallel mode), or the
  degradation declared in manifest and report.
- Follow-ups routed by continuing the existing branch agent; `iterations`
  incremented; three rounds maximum.
- Manifest written for every run, including disabled runs.
