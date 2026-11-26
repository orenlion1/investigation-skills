# Skill naming evaluation

Read this reference during audit and refactor. Use Claude's
[naming conventions](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices#naming-conventions)
to evaluate names, rather than treating a syntactically valid name as proof of quality.

## Automated rules

`check` fails on naming errors. `audit` adds `naming_findings` to its existing
`skill-ownership-audit/v1` JSON and lists them in Markdown. Each finding has `rule`, `path`,
`severity`, `reason`, and `source`. Existing fields retain their meaning; the total finding
count includes naming errors and advisories. Audit still exits zero when it can produce a
report, even when findings exist. Both commands are offline and use the same naming rules.

| Rule | Severity | Evaluation | Source |
| --- | --- | --- | --- |
| NAME000 | error | Audit cannot read unambiguous frontmatter; no name evaluation is claimed | [Skill structure](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview#skill-structure) |
| NAME001 | error | A nonempty lowercase ASCII kebab-case name, with digits permitted; no leading, trailing, or consecutive hyphens | [Name field](https://agentskills.io/specification#name-field) |
| NAME002 | error | At most 64 characters | [Skill structure](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview#skill-structure) |
| NAME003 | error | No reserved words `anthropic` or `claude` | [Skill structure](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview#skill-structure) |
| NAME004 | error | The declared name equals its parent directory | [Name field](https://agentskills.io/specification#name-field) |
| NAME101 | advisory | Exact names `helper`, `utils`, `tools`, `documents`, `data`, or `files` merit a specificity review | [Naming conventions](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices#naming-conventions) |

Reserved-word matching is this checker's explicit interpretation of "words": compare complete
hyphen-delimited components, including a name consisting of just the word. Thus `claude-tools`
fails, while `claudette-tools` does not. The source does not specify substring matching.
The name grammar already excludes XML tags. The existing frontmatter reader supports the
catalog's simple scalar fields, not arbitrary YAML; duplicate top-level fields fail rather
than letting the last name hide an earlier violation.

Vague-name matching is exact: `data-analysis` gets no automatic advisory merely for containing
`data`. Neither absence of an advisory nor passing required checks proves a name is meaningful.

## Agent review

For every skill, read its name, description, routing row, and capability together:

1. Does the name identify the capability specifically enough to distinguish neighboring skills?
2. Is the naming pattern consistent within related skills? Explain any inconsistency using
   concrete names and capabilities; do not infer grammatical form from an `-ing` suffix.
3. Does each automated advisory apply in context? Record a reason to retain the name or suggest
   a more specific alternative. Review unflagged names too: the example list is not exhaustive.

Claude suggests gerunds such as `processing-pdfs`, and also accepts noun phrases such as
`pdf-processing` and action names such as `process-pdfs`. All three pass automated checks;
choosing among them is a contextual review decision, never an automatic grammar failure.
Report semantic judgments with evidence separately from deterministic check results.

The scripts never rename skills. Before an authorized rename, map updates to routing rows,
links, eval identifiers, pins, and other callers; verify those references after the change.
