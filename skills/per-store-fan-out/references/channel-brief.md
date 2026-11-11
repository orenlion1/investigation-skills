# Slack Channel Inspection Brief

Use for each parent-resolved channel under the
[channel workflow](../SKILL.md#channel-resolution-and-scheduling). Keep the resolved block and
output contract byte-identical to the store/repository templates. Scheduling and manifest
machinery remain in [the shared delegation contract](delegation-contract.md); this template
owns only channel identity and questions.

```markdown
# Investigation brief: <canonical workspace/channel>

## Channel
- Channel: <canonical channel ID and every configured alias>
- Workspace: <verified workspace identity, or unresolved with reason>
- Integration skill: slack-mcp
- Inspection owner: <parent-assigned owner reference>
- Excluded work: <other channel owners and remaining store work>

## Resolved block (identical across all briefs in this run)
- Environment: <environment>
- Effective Resources: <complete parent-resolved resources, including every repository and explicit user overrides>
- Time window: <start> .. <end>
- Timezone: <IANA timezone>
- Task questions: <the task's questions, verbatim>
- Constraints: read-only; only the objects above; AWS stays within
  us-east-1/eu-central-1; no mutations, acknowledgments, messages, or publication.

## Channel-specific questions
- <task questions for this channel and its in-scope threads>
- Read only the assigned channel/workspace within the shared window and constraints.
- Return message/thread references, observation/query timestamps and query scope for each lead.
- Report denied, ambiguous or unsupported reads individually; do not infer an empty channel.
- Send cross-channel questions to the parent rather than repeating another owner's reads or
  creating additional inspection units. Do not message, acknowledge, mutate or publish.

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

Use the skill's channel-owned manifest fields; unresolved channel inputs remain visible. The
parent verifies material evidence and performs cross-channel correlation.
