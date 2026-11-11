# Repository Inspection Brief

Use for each parent-resolved repository unit under the
[repository workflow](../SKILL.md#repository-resolution-and-scheduling). The parent supplies
all placeholders. Keep the resolved block and output contract byte-identical to the store
brief template for this run. The shared delegation machinery and manifest schema remain in
[the delegation contract](delegation-contract.md); this file owns repository-specific identity
and questions only.

```markdown
# Investigation brief: <canonical repository>

## Repository
- Repository: <canonical identity and every configured alias>
- Provider: <github | bitbucket>
- Integration: <approved GitHub tooling | rovo-dev-mcp>
- Provider scope: <verified account/workspace scope and narrower task limits>
- Inspected revision: <exact revision, or unresolved with reason>
- Inspection owner: <parent-assigned ownership reference>
- Excluded work: <other repository owners and remaining store work>

## Resolved block (identical across all briefs in this run)
- Environment: <environment>
- Effective Resources: <complete parent-resolved resources, including every repository and explicit user overrides>
- Time window: <start> .. <end>
- Timezone: <IANA timezone>
- Task questions: <the task's questions, verbatim>
- Constraints: read-only; only the objects above; AWS stays within
  us-east-1/eu-central-1; no mutations, acknowledgments, messages, or publication.

## Repository-specific questions
- <the task's relevant source questions for this repository>
- Trace relevant implementation and consumers within the assigned provider scope.
- Return exact commit, file, lines and retrievable references for material source claims.
- Distinguish inspected source from deployed-revision evidence; identify unavailable provenance.
- Report denied/unsupported/ambiguous reads individually. Route cross-repository questions to
  the parent rather than repeating another owner's work or scheduling new inspection units.

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

The parent's linked repository manifest uses the caller-owned fields documented in the skill.
Every distinct repository and every unresolved input retains an outcome. The parent correlates
and verifies returned evidence before making cross-repository causal claims.
