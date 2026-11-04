# Investigation Skills

A root cause is rarely visible in one place. The latency spike is in Grafana,
the throttling and the stack trace are in AWS, the deploy that preceded both is
in a pull request, and the first customer symptom is a Slack thread. Reading
each store is easy; relating them is the work — and when that work happens in a
chat session, the conclusion survives and the reasoning that produced it does
not.

This repository keeps it. Describe the problem once in a task file; your coding
agent queries the resources in scope, draws the relationships between their
signals, narrows to a cause and a resolution, and writes the result up as a
report in which every material claim is pinned to the evidence behind it.
Publishing that report is what turns one person's investigation into something
the next lifecycle step — and the rest of the team — can build on.

The workflow is agent-driven. Anything shown as `text` below is something you
say to your coding agent while this repository is open — not a shell command.
The agent follows the repository [policy](AGENTS.md) and the [skills](#skills)
it routes to.

## Why use it

- **One entry point.** `open task` produces a structured draft; saving and
  closing the editor runs it. No per-investigation prompt engineering.
- **Correlation, not just collection.** Metrics, logs, traces, AWS resource
  state, code, tickets, and conversation are pulled onto one time window, so the
  relationships between signals — not just the signals — are what you reason
  about.
- **The systems you already use.** AWS, Grafana, Slack, Bitbucket, Jira, and
  Confluence are reached through scoped read-only skills — only the ones your
  task actually names.
- **Evidence you can audit.** Reports keep inspected source, observed runtime
  behavior, inference, and proposal apart, and link material claims to a
  revision-pinned evidence index.
- **Deliverables, not notes.** Markdown and PDF with consistent diagrams,
  captions, stated limitations, and token accounting; optional one-command
  publication to Confluence.
- **Work that compounds.** A published report is the input to the next step of
  the incident lifecycle and the record a teammate extends, instead of a
  transcript that expires with the session.
- **Authorization stays with you.** A task describes work. It never grants
  permission to commit, update a ticket, deploy, or publish.

## Requirements

A coding agent that reads [AGENTS.md](AGENTS.md) or [CLAUDE.md](CLAUDE.md), a
working CodeGraph installation, and Python 3. Each integration's tooling and
sign-in live in its own skill. A missing required dependency is setup work
rather than a blocker — see
[Required Dependencies](AGENTS.md#required-dependencies).

## Quick start

1. **Open a draft.** Ask the agent:

   ```text
   open task
   ```

   It copies [templates/TASK.md](templates/TASK.md) to a `docs/tasks/TASK.md`
   draft and opens it in a waiting editor. An existing draft is preserved, not
   replaced.

2. **Fill it in.** Give the task a title, the problem, at least one observable
   acceptance test, and at least one real resource — repository, Slack channel,
   AWS profile, Grafana context, or alert. Individual fields are optional;
   placeholders and examples do not count as resources. The template also takes
   a Publish parent page, which records the intended destination with the
   investigation; publication itself stays a separate, authorized step.

3. **Save and close the editor.** That alone starts execution. Once any
   supplied checks pass, the agent names the task from its title, runs its
   saved requirements, and produces the reports. **No separate `run`
   instruction is needed.**

To revisit an existing investigation, supply its actual path:

```text
edit task docs/tasks/TASK-example-service-investigation.md
```

Existing tasks keep their filenames. To stop before execution, ask for **edit
only**; for a new draft, **initialization only** stops at the same boundary.

## How an investigation runs

Once the task is running, the agent works through the same arc whatever the
resources in scope are:

1. **Gather.** The saved task names what is in scope. Each resource is queried
   read-only through its own skill, with the account, context, Region, object
   identity, and time window resolved before the call rather than guessed.
2. **Relate.** Signals are aligned on one explicit time window and timezone, so
   an alert transition, a log burst, a throttled dependency, a deploy, and the
   customer report that followed sit on a single timeline instead of in four
   tools.
3. **Narrow.** Candidate causes are tested against that evidence rather than
   asserted. Code, a schema, or a class name proves what the source says, not
   what production did; the paths and consumers that matter are traced before a
   behavioral conclusion is drawn.
4. **Write up.** The report captures the findings, the reasoning that connects
   them, diagrams of the flows and dependencies involved, and the resolution or
   proposed change — separating what the evidence verifies from what it only
   suggests, and recording the questions still open and what would answer them.
5. **Publish.** The report becomes a page the team can read, cite, and extend.

Step 5 is where the value is captured. Because the evidence index is pinned to
the exact revision, observation window, and objects that produced it, a later
reader can tell what was verified, what has changed since, and what was never
tested. That makes the report a working input rather than a summary: the
postmortem starts from a confirmed timeline, the corrective-action ticket names
a specific defect, the next investigation begins from what has already been
ruled out, and a teammate reads the page instead of reconstructing the
reasoning.

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="diagrams/DIAGRAM-investigation-workflow-dark.png">
  <img alt="Open and edit an investigation task, save and close the task editor to start execution, investigate using aws-mcp, gcx-cli, slack-mcp, and rovo-dev-mcp as needed, produce Markdown and PDF reports, then Publish to the configured parent page." src="diagrams/DIAGRAM-investigation-workflow-light.png">
</picture>

**Figure 1 — Lifecycle and integrations.** The same arc as a flow. Solid arrows
are activity handoffs; dashed arrows are the integrations Investigate calls as
the task requires, in no fixed order. The artifacts progress from `TASK.md` to
the saved task, findings and evidence, and the reports. Publish uses the parent
page configured in the task.

[Editable diagram](diagrams/DIAGRAM-investigation-workflow.dot) ·
[Light SVG](diagrams/DIAGRAM-investigation-workflow-light.svg) ·
[Dark SVG](diagrams/DIAGRAM-investigation-workflow-dark.svg)

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="diagrams/DIAGRAM-investigation-skill-routing-dark.png">
  <img alt="Investigation activities route to task initialization skills, selected resource skills, and report naming, token usage, and diagramming skills." src="diagrams/DIAGRAM-investigation-skill-routing-light.png">
</picture>

**Figure 2 — Skill routing.** The same lifecycle expanded into the skill that
owns each step. Dashed arrows mean invocation; peer placement implies no
ordering. Listing a skill does not make its resource field mandatory.

[Editable routing diagram](diagrams/DIAGRAM-investigation-skill-routing.dot) ·
[Light SVG](diagrams/DIAGRAM-investigation-skill-routing-light.svg) ·
[Dark SVG](diagrams/DIAGRAM-investigation-skill-routing-dark.svg) ·
[Source notes and regeneration](diagrams/DIAGRAM-investigation-workflow.md)

The repository owns the template, draft creation, final naming, execution, and
reporting. The [Open/Edit/Close/Execute](skills/open-edit-close-execute/SKILL.md)
skill owns the waiting-editor barrier that triggers them: saving alone, or a
timeout, never counts as closure. In VS Code the waiting command is
`code --reuse-window --wait "<task-path>"`; the
[editor contract](skills/open-edit-close-execute/references/open-edit-close-execute.md)
covers other editors and how closure is confirmed when it cannot be tracked.

Grafana alert investigations pause before any live query: the agent first
proposes a parallel Grafana Assistant and `investigate-alert` plan and waits for
your explicit authorization. See the
[alert investigation entry point](AGENTS.md#grafana-investigation-entry-point).

## What you get

| Path | Purpose |
| --- | --- |
| [templates/TASK.md](templates/TASK.md) | Reusable task template; copied when starting a new task. |
| `docs/tasks/TASK.md` | Local temporary task draft; ignored by Git. |
| `docs/tasks/TASK-{slug}.md` | Local finalized task, named from its saved title; ignored by Git. |
| `docs/reports/REPORT-{slug}.md` and `.pdf` | Local investigation deliverables; ignored by Git. |
| `docs/reports/assets/{slug}/` | Local supporting report assets. |
| `logs/` | Local investigation logs and supporting evidence; ignored by Git. |
| [diagrams/](diagrams/) | Committed documentation diagrams and editable source. |
| [skills/](skills/) | Self-contained skill packages and their references or helpers. |

Investigation output stays local: `docs/tasks/`, `docs/reports/*`, `logs/`, and
`outputs/` are ignored, while the task template stays tracked. Findings about
live systems are not committed here, so the published page — not this checkout —
is the shared copy. Custom destinations need their own tracking decision. Paths
are resolved before any write, and an existing draft or a destination collision
is preserved for you to resolve rather than overwritten or suffixed.

## Publish to Confluence

Configure the publication destination in the task's Resources section:

```text
Publish: <Parent page>
```

For example, `Publish: Confluence page "Investigations"`. Use the parent page's URL
or ID when its title is ambiguous. The saved task supplies this destination to
[Publish It](skills/publish-it/SKILL.md); an explicit `--parent` can also name it:

```text
publish it --task docs/tasks/TASK-example.md --report docs/reports/REPORT-example.md --parent <Confluence parent URL>
```

It resolves related artifacts, publishes the report with its diagrams and
evidence, and attaches the original report and parent task as downloads — so a
reader gets the narrative on the page and the inputs underneath it, and can
reopen the task the findings came from. A task-only or report-only request uses
verified companion files when they exist and reports any that are missing.

Publishing presents the investigation as it was recorded: it does not rerun it
or refresh its evidence window, which is what makes the page citable later.
Republish a revised report rather than editing the page away from its evidence.

## Skills

| Skill | Responsibility |
| --- | --- |
| [Open/Edit/Close/Execute](skills/open-edit-close-execute/SKILL.md) | Wait for editor closure and supplied checks, then continue within scope. |
| [Workflow Artifact Naming](skills/workflow-artifact-naming/SKILL.md) | Resolve artifact identity, format, filename, and destination. |
| [Release It](skills/release-it/SKILL.md) | Prepare and verify protected GitHub releases. |
| [Publish It](skills/publish-it/SKILL.md) | Publish tasks and reports to Confluence with diagrams, evidence and verified downloads. |
| [Token Usage](skills/token-usage/SKILL.md) | Derive scoped report duration and token totals from local conversation records. |
| [Diagramming Style](skills/diagramming-style/SKILL.md) | Create and verify readable diagrams in light and dark themes. |
| [Rovo Dev MCP](skills/rovo-dev-mcp/SKILL.md) | Authenticate and perform scoped Atlassian resource reads. |
| [Grafana CLI](skills/gcx-cli/SKILL.md) | Install gcx and its Claude/Codex skills, refresh before commands, authenticate a selected context, and investigate through scoped queries. |
| [Slack MCP](skills/slack-mcp/SKILL.md) | Establish and verify scoped Slack access. |
| [AWS MCP](skills/aws-mcp/SKILL.md) | Authenticate a selected AWS profile, wait for browser sign-in, and investigate root causes through scoped AWS MCP queries. |
| [AWS architecture diagrams](skills/aws-architecture-diagrams/SKILL.md) | Document AWS architecture with the bundled diagram conventions. |

## Where the rules live

This README is the entry point. Each rule has exactly one owner, so follow the
link rather than a summary:

| Topic | Owner |
| --- | --- |
| Task lifecycle, resources, naming, continuation | [Templated Tasks](AGENTS.md#templated-tasks) |
| Evidence, citations, and stated limitations | [Report Evidence](AGENTS.md#report-evidence) |
| Artifact paths and destinations | [Workflow Artifact Naming](skills/workflow-artifact-naming/SKILL.md) |
| Report duration and token accounting | [Token Usage](skills/token-usage/SKILL.md) |
| Diagram style, theming, and consistency | [Diagramming Style](skills/diagramming-style/SKILL.md) |
| Atlassian connectivity probes | [Rovo Dev MCP](skills/rovo-dev-mcp/SKILL.md) |
| Grafana investigation entry point | [AGENTS.md](AGENTS.md#grafana-investigation-entry-point) |
| Skill and eval quality gate | [Skill Quality Gate](AGENTS.md#skill-quality-gate) |
| Publication security and disclosure | [SECURITY.md](SECURITY.md) |
| Release contract | [VERSIONING.md](VERSIONING.md) |

[AGENTS.md](AGENTS.md) and [CLAUDE.md](CLAUDE.md) are byte-identical; change
repository policy in both.

## Local validation

Run the same checks CI runs, from the repository root:

```sh
bash scripts/check.sh
```

That validates release metadata, compiles the scripts, skills, and tests, runs
the repository and diagramming test suites, confirms the two policy files match,
and rejects whitespace errors. Changes to any skill or eval case additionally
need `bash scripts/run-skill-quality-gate.sh`.

Keep the CodeGraph index current and local:

```sh
codegraph status
codegraph sync
```

To regenerate both workflow views — adaptive SVGs, fixed light and dark
exports, and overlap checks:

```sh
bash scripts/render-workflow-diagram.sh
```

Then inspect the rendered README in both GitHub themes alongside the exported
images. The [Validate workflow](.github/workflows/validate.yml) runs the
required `Tests` check on pull requests, merge queues, and `main`; authorized
changes land through a protected squash pull request.

## Security

Investigation output is deliberately untracked, and the repository gates what
can be committed: a full-history credential scan plus an institutional-data
policy that rejects private artifacts, institution fingerprints, corporate email
addresses, unreviewed hosts, and identifying account or ticket values — without
logging matched content. Before any first upload, when CI cannot help yet:

```sh
bash scripts/check-disclosure.sh
```

[SECURITY.md](SECURITY.md) has the coverage, policy review, required checks, and
the local pre-push hook.

## Versioning and releases

[VERSION](VERSION) is the repository release version. Ask your agent to
`run release-it` to invoke the [Release It skill](skills/release-it/SKILL.md),
which prepares a protected pull request, validates the exact merged revision,
pushes an annotated SemVer tag, verifies its workflow, and publishes curated
release notes. [VERSIONING.md](VERSIONING.md) holds the contract.

## License

[MIT License](LICENSE). External tools retain their own licenses.
