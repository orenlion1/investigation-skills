---
name: aws-architecture-diagrams
description: "Create evidence-backed AWS-style architecture, topology, system-context and data-flow diagrams in Mermaid, Graphviz DOT, or both. Use when AWS architecture visuals are requested. Choose the format by renderer, audience, icon fidelity and layout control; neither is preferred by default."
---
<!-- source: self; self-authored: self; managed-by: https://github.com/orenlion1/dotfiles; sync-from: https://github.com/orenlion1/dotfiles; dotfiles-sync-date: 2026-08-30; dotfiles-sync-commit: 42a3e852aa9d6786e9e7f27e3fc77790fea09ffd -->

# AWS-style architecture diagrams

## Overview

Produce diagrams that follow [AWS reference architecture diagram](https://aws.amazon.com/architecture/reference-architecture-diagrams/)
conventions: accurate service names, labelled account/Region/VPC boundaries,
short flow labels, and an uncluttered canvas. "AWS-style" describes those
conventions; it does not by itself require official AWS icons or Graphviz.

Mermaid and Graphviz DOT are peer authoring formats. Use one when it satisfies
the complete delivery contract and both when distinct audiences or artifacts
make the additional maintenance worthwhile.

## When to Use

Use this skill for evidence-backed AWS architecture, topology, system-context,
or data-flow diagrams. Do not use it for a non-AWS visual or when a table alone
communicates the requested facts more clearly.

## Common Rationalizations

- "AWS-style means DOT" ignores Mermaid renderers that meet the actual contract.
- "Both formats are safer" creates synchronization cost without two named consumers.
- "The service probably connects here" is not evidence for an edge.

## Red Flags

Stop and resolve unsupported resources or relationships, an ambiguous target renderer,
missing icon rights or assets, conflicting source evidence, or a requested Region outside
the authorized scope before drawing or querying live infrastructure.

## The rule that outranks the aesthetics

**Draw only what the source establishes.** Every node, edge, boundary, Region,
and protocol must trace to something real — Terraform, CloudFormation, CDK,
deployed configuration, or an owner's written statement.

- Never add a service, connection, Availability Zone, VPC, or Region because the
  picture looks unbalanced without it. If the source does not establish a
  boundary, leave it out; an honest sparse diagram beats a decorative complete one.
- When something is deployed but disabled, say so on the node
  (`WEB_PUSH_ENABLED=false`, "Deployed, release-disabled") rather than drawing it
  as live, and mark what another team owns.
- State the provenance in the diagram itself — a subtitle naming the source, such
  as *"traced to `<iac-dir>/*.tf` at `<revision>`"* or *"live read-only inventory,
  `<date>`"* — and repeat it in a header comment in the DOT source.

## Establish the architecture from source

Inventory what actually exists before drawing anything. Find the directory this
project keeps its IaC in — `infra/`, `terraform/`, `deploy/`, a CDK app — rather
than assuming a layout:

```bash
iac_dir=infra   # whatever this repository actually uses
grep -hoE '^resource "aws_[a-z0-9_]+"' "$iac_dir"/*.tf | sort | uniq -c | sort -rn
```

Then pull the specifics that make edges real **and the names that go on the
nodes**: function names, table names, bucket names, event rules and their
schedules, S3 notifications, authorizers, and any cross-account or cross-stack
grant. Resolve names through their variables and locals to the value actually
deployed. Note the Region from the variable that sets it, not from assumption.

When there is no IaC, or it covers only part of the estate, the source is the
live account, read-only, and the diagram must say so: follow
[references/live-account-inventory.md](references/live-account-inventory.md).

### Say which kind of evidence each edge rests on

Never draw a line because two resources share a naming prefix. Separate the
classes visually and define them in the diagram and its prose:

- **Wiring AWS itself reports** — a target group's targets, a replica's source.
  The strongest class.
- **A path something permits** — a security-group rule, a bucket policy. A call
  *may* happen, not that it does. Note when a rule is CIDR-scoped rather than
  security-group-scoped: it authorises an entire range, not the one workload
  the arrow leaves.
- **A grant an identity holds** — an IAM policy statement. Same caution, plus
  the grant is not the effective permission until SCPs, permission boundaries,
  and resource policies are evaluated.
- **Inference from naming or tags** — draw dashed, label with the uncertainty,
  or leave it out. Never solid.

Absence is a finding worth drawing: when a role that "obviously" talks to a
queue holds no `sqs:*` action at all, a node saying so forecloses the wrong
assumption where a missing arrow leaves it open.

## Name the resource, not just the service

A service icon alone identifies nothing a reader can find in the console. Every
node states three facts:

1. **What it is called in AWS.** The real deployed name — `acme-orders-events`,
   not a friendly alias like "Orders". Write an account id as `<account>` rather
   than the digits; never put a secret, token, or endpoint in a diagram.
2. **What type of resource it is.** Written out, in grey, under the name:
   "DynamoDB table", "S3 bucket", "Lambda function", "API Gateway HTTP API",
   "WAFv2 web ACL", "SES v2 email identity".
3. **What it is for.** One line, and only where a reader could not infer it.

For Graphviz output, use a **resource icon** where AWS publishes one (such as
`Res_Amazon-DynamoDB_Table`) and a **service (`Arch_`) icon** for everything
else. The icon reinforces the identity; it must never be the only thing carrying
it, because an icon is not readable in greyscale, at thumbnail size, or by a
screen reader.

## Choose the format from the requirements

There is no global winner and no default format. Honor an explicitly requested
source format unless it conflicts with another acceptance criterion. Otherwise
compare the actual delivery needs:

| Requirement | Mermaid tends to fit better | Graphviz DOT tends to fit better |
| --- | --- | --- |
| Repository review | Inline Markdown rendering, compact textual diffs | Reviewable text source plus separately rendered artifacts |
| Diagram type | Sequence, flow, state, dependency, and straightforward architecture views | Dense topology, nested boundaries, and graphs needing deliberate edge routing |
| AWS visuals | AWS-style names, boundaries, colors, or renderer-provided icon packs | Exact repo-local AWS-published icon assets |
| Layout | Renderer-managed responsive layout and theme adaptation | Precise ranks, ports, clusters, spacing, and fixed composition |
| Delivery | Documentation that should render where it is written | Controlled SVG/PNG for decks, documents, and presentation surfaces |
| Tooling | Target renderer already supports the required Mermaid syntax and version | Graphviz and the required local assets are available in the build or authoring environment |

- Tabular content stays a Markdown table rather than becoming a picture.
- For an ordered participant exchange, Mermaid `sequenceDiagram` is usually the
  natural fit — a diagram-type advantage, not a general preference for Mermaid.
- Mermaid supports [architecture diagrams and configurable icon
  packs](https://mermaid.js.org/syntax/architecture.html), but a hosted renderer
  cannot be assumed to provide repo-local AWS assets, custom pack registration,
  or the same Mermaid version as a controlled local renderer. Graphviz loads
  [local image assets directly](https://graphviz.org/docs/attrs/image/), so it is
  the dependable choice when exact icon assets and fixed exported composition are
  acceptance criteria, not merely because the request says "AWS-style".
- Count the costs on both sides: Mermaid can vary across renderer versions,
  available icon packs, and host themes; DOT adds a rendering step and generated
  artifacts that must remain synchronized with the editable source.
- If renderer support, icon fidelity, fixed composition, or expected output files
  would materially change the result and the request is ambiguous, clarify the
  delivery contract. Otherwise select the format that satisfies the known
  requirements with the least project-specific machinery.
- When Mermaid is selected, the evidence, provenance, resource-naming, and
  accessibility rules above still apply; validate the source in its target
  renderer and skip the Graphviz workflow.

### When both formats are justified

Produce Mermaid and DOT only when each artifact has a named consumer or
acceptance criterion, such as inline repository review plus exact AWS-icon
presentation output. For an unusually dense complete-system map that needs exact
AWS icons, fixed composition, or port-level connector placement, DOT plus its
SVG and PNG can serve as the presentation and AWS-icon artifact, with a Mermaid
rendering as the maintainable, inline-reviewable companion when that is also
required. A focused flow without those DOT-specific requirements may need
Mermaid alone.

Neither source is canonical by default; name one authoritative only when the
user or repository policy explicitly assigns that role. Derive both from the
same verified resource-and-relationship inventory, carry the same provenance,
and check that nodes, edges, boundaries, Regions, ownership, and uncertainty
agree. A format may add presentation-specific structure without changing the
architecture it claims.

## Mermaid workflow

Read [references/mermaid-workflow.md](references/mermaid-workflow.md) before
starting; it holds the type choices, icon-pack command, and checks.

1. **Select the Mermaid diagram type** and confirm the target renderer supports
   that syntax and any icon pack.
2. **Encode the verified inventory** with full resource names and types in
   text, evidenced boundaries only, and visible annotations for permitted or
   inferred relationships.
3. **Render and inspect in the target environment** at the intended width and
   theme; a `?` icon fallback is a failed render.
4. **Deliver the required artifacts**: inline Mermaid, or deterministic SVG/PNG
   with a documented reproduction command.

## Graphviz workflow

Read [references/graphviz-workflow.md](references/graphviz-workflow.md) before
starting; it holds the commands, helper contract, and checks for every step.

1. **Get the official icons.** Discover the current asset package URL, copy only
   the 48px PNGs actually used into `<diagrams>/icons/` under their original
   filenames, and never recolor, redraw, stretch, or substitute a generic glyph.
2. **Write the DOT source** per
   [references/dot-conventions.md](references/dot-conventions.md): palette, node
   tables, icon choice, cluster nesting, edge classes, connector ports, two-theme
   publishing, and layout fixes.
3. **Render** SVG and PNG from the diagram directory; embed the icons when the
   SVG must stand alone.
4. **Look at the result — this step is not optional.** Graphviz will produce a
   valid file that is unreadable; inspect the PNG and the SVG in the destination
   preview, fix, and rerender.
5. **Write the README** from
   [references/readme-template.md](references/readme-template.md): each diagram,
   its editable source, rendered outputs, render commands, and icon provenance.

## One concern per diagram

When a single graph gets dense, split it by concern and cross-reference in the
header comments:

- **System context** — the authenticated request path: user, edge, API,
  functions, the state they reach.
- **Scheduled and event-driven** — timers, queues, event rules, and the
  functions they wake.
- **Topology** — VPC, Availability Zones, subnets, gateways, where those exist.
- **Sequence or compliance flow** — an ordered path, numbered only when the
  order matters.

Two legible diagrams always beat one crowded one. Split before compromising on
label size.

## Verification

Verify source provenance, resource names and types, boundaries, Regions, edge evidence,
ownership, and uncertainty against the inventory. Render every delivered source in its
target environment, visually inspect it at delivery scale, validate required SVG/PNG files,
and compare semantic parity when both Mermaid and DOT are delivered.

When a change alters AWS structure, update every delivered editable source and
rerender its required outputs together — a stale diagram is worse than none,
because it is believed. That synchronization is part of this verification.
