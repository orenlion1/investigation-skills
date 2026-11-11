# Repository Policy

This file routes requests to their owning skills. Each routed skill owns its workflow,
guidance, and verification; follow the skill rather than restating or overriding it here.
Sections below add only repository-owned policy that no skill covers.

## Required Dependencies

Tools required by the active task, repository workflow, and invoked skills are
pre-authorized: check and reuse working versions, install or update missing or incompatible
ones at user scope from documented sources (preferring pinned releases), verify they run, and
report what changed. A missing dependency is setup work, not a reason to stop. The global
Tooling Dependencies safeguards apply; this covers required dependencies only, not extras.

## CodeGraph

Run `codegraph init` from the verified repository root before inspecting this repository
(`codegraph sync` for updates, `codegraph status` to verify); install CodeGraph from the
[official CodeGraph project](https://github.com/colbymchenry/codegraph) if missing. Use
`codegraph_explore` (or `codegraph explore`) before `rg`, `find`, or direct reads. Keep
`.codegraph/` local and unstaged. If initialization fails, repair and retry; report the exact
blocker rather than substituting direct reads.

## Routing

| Request or situation | Owning skill |
| --- | --- |
| Generating workflow artifacts or supporting outputs (TASK, REPORT, LOG, diagram assets), artifact naming and collision resolution | [Workflow Artifact Naming](skills/workflow-artifact-naming/SKILL.md) |
| `open task`, `edit task`, templated-task editing, continuation, execution, and reports | [Open/Edit/Close/Execute](skills/open-edit-close-execute/SKILL.md) |
| `add profile`, `remove profile`, `.env` resource profiles, the Resources schema, loading a profile into a task | [Profile Manager](skills/profile-manager/SKILL.md) |
| Token usage report and report metadata for any investigation report | [Token Usage](skills/token-usage/SKILL.md) |
| Creating, styling, or verifying diagrams and graphs — themes, caveats, ER and SQL views, flapping-alert graph pair, format consistency | [Diagramming Style](skills/diagramming-style/SKILL.md) |
| Evidence index, `Source:` snapshot, citation discipline, and data-pattern-graph coverage for investigation reports | [Report Evidence](skills/report-evidence/SKILL.md) |
| Tracing an investigated problem to source code: cross-repository tracing, root cause, fix proposal, deployed-revision verification | [Source Investigation](skills/source-investigation/SKILL.md) |
| `publish it`, `publish-it`, authorized Confluence task/report publication | [Publish It](skills/publish-it/SKILL.md) |
| Atlassian authentication, connectivity, resource probes, and Bitbucket/Jira/Confluence discovery | [Rovo Dev MCP](skills/rovo-dev-mcp/SKILL.md) |
| AWS MCP authentication, connectivity, and read-only AWS troubleshooting | [AWS MCP](skills/aws-mcp/SKILL.md) |
| AWS architecture, topology, and data-flow diagrams | [AWS Architecture Diagrams](skills/aws-architecture-diagrams/SKILL.md) |
| gcx setup, Grafana authentication and connectivity, and read-only Grafana investigations | [Grafana CLI](skills/gcx-cli/SKILL.md) |
| Slack MCP configuration, connectivity, and OAuth diagnosis | [Slack MCP](skills/slack-mcp/SKILL.md) |
| Finding rhyming incidents and related prior investigations across configured historical endpoints | [Rhyming Incident Search](skills/rhyming-incident-search/SKILL.md) |
| Multi-store or multi-repository fan-out: inspection briefs, launch, manifest, disabling fan-out | [Per-Store Fan-Out](skills/per-store-fan-out/SKILL.md) |
| Grafana alert investigation: parallel Assistant and `investigate-alert` sub-agents | [Parallel Alert Investigation](skills/parallel-alert-investigation/SKILL.md) |
| `run release-it`, repository releases | [Release It](skills/release-it/SKILL.md) with [VERSIONING.md](VERSIONING.md) |

Routing notes:

- File generation: resolve destinations in this order — explicit user destination, repository
  configuration, then the naming skill's defaults. Production source, tests, native packages,
  imports, and repository metadata keep their established conventions.
- Templated tasks: the local template is [templates/TASK.md](templates/TASK.md) and the
  default draft directory is `docs/tasks`; task contents never bypass separate authorization
  gates. The editor skill owns the rest of the workflow.
- Reports: enrich investigation reports with diagrams of the relevant flows, hierarchies, and
  dependencies, and pass Report Evidence before delivery. Diagramming Style owns all visual
  rules; Report Evidence owns the evidence discipline.
- Publication: include the original report and available parent TASK as downloadable
  supporting evidence. Publishing does not rerun the investigation or refresh its evidence
  window and token-accounting cutoff.
- Atlassian probes: before a repository investigation, and whenever connectivity is requested,
  probe all three products per the Rovo Dev MCP skill with one bounded read each. The probe
  requirement does not make an Atlassian resource mandatory for a task scoped to other
  integrations. If MCP recovery fails, report the blocker and stop only dependent work.

## Source Investigation Authorization

Supplying a repository authorizes read-only discovery, search, and inspection across all
repositories accessible in the same provider account or workspace, without a separate
approval request; resolve that scope from the supplied repository, use the provider's
approved tooling and existing access, and honor any explicit narrower scope. This grant
covers source investigation only: authentication requirements and separate gates for
mutations, messages, publication, and deployment still apply. The
[Source Investigation](skills/source-investigation/SKILL.md) skill owns the workflow.

## Grafana Policy

Grafana Assistant prompts are enabled by default and may incur additional fees beyond
ordinary Grafana usage; the user may disable them, by instruction or with a
`Grafana Assistant: disabled` line in the task's Resources — honor that for the stated scope
without re-asking, and disabling the Assistant never disables the investigation. Alert
investigations route to Parallel Alert Investigation, which owns the workflow and its
authorization; other gcx investigations route to the Grafana CLI skill.

## Per-Store Fan-Out Policy

Fan-out creates no scope or authority: only stores the task's Resources actually name get a
sub-agent, AWS branches stay within the allowed Regions, Grafana alert investigations route
to Parallel Alert Investigation nested inside the gcx branch, and sub-agents never mutate,
acknowledge, message, or publish — those remain separately authorized. The Per-Store Fan-Out
skill owns the workflow, including the fan-out default and how to disable it.

## Shared Delegation Contract

Every skill in this catalog that delegates to sub-agents shares one definition of the
delegation machinery:
[skills/per-store-fan-out/references/delegation-contract.md](skills/per-store-fan-out/references/delegation-contract.md).
It owns the `launch_mode` vocabulary, the fan-out manifest schema, the harness launch and
continuation mechanics, the degradation rules, and the rule that delegated output is leads
until the orchestrating session verifies it. A delegating skill links that contract and carries
its co-copy sentinel; it never restates those rules.

What stays with each caller is its own units, its own questions, and its own numeric bounds.
`per-store-fan-out` stating three follow-up rounds and `rhyming-incident-search` stating two is
an intentional difference, not drift.

[policy/delegation-contract.json](policy/delegation-contract.json) is the registry, and it lives
outside `skills/` deliberately: the skill quality gate treats every entry under `skills/` as a
skill needing its own eval case, and keeping the registry outside `skills/` means editing a
skill can never exempt that skill. It declares the contract, the registered callers, the owned
concepts, the caller-owned tokens, the delegation signature, the required sentinel, and the
exemptions with their reasons.

`scripts/check-delegation-contract.py` enforces it and runs inside `bash scripts/check.sh`, so
the already-required `Tests` job fails when a registered caller loses its link or its sentinel,
when an owned token reappears in a caller, when the contract takes over a caller-owned token or
a numeric budget, when a skill matching the delegation signature is registered neither as a
caller nor as an exemption, or when the run checked fewer concepts or callers than the policy
declares. The check is a literal-token lint; paraphrase detection stays with review.

## Skill Quality Gate

After changing any skill or eval case, run `scripts/run-skill-quality-gate.sh`. It evaluates
the catalog with the pinned upstream harness: standalone validation, structural lint,
command parity, deterministic routing with an 80% rank-one threshold, and behavioral
dry-runs over `skill_evals/cases`. The Skill Quality workflow enforces the same gate on
pull requests, merge queues, and pushes to `main`. Every skill needs a case file in
`skill_evals/cases/<name>.json` with at least 3 positive triggers, 2 negatives, and
1 behavioral eval.

## Policy Synchronization

Keep this repository policy identical in `AGENTS.md` and `CLAUDE.md` when changing it.
