---
name: aws-architecture-diagrams
description: Create evidence-backed AWS-style architecture diagrams in Mermaid, Graphviz DOT, or both. Use when AWS system context, topology, architecture, or data-flow visuals are requested. Select the format from the required renderer, audience, icon fidelity, layout control, reviewability, and output artifacts; neither Mermaid nor DOT is inherently preferred.
---
<!-- source: self; self-authored: self; managed-by: https://github.com/orenlion1/dotfiles; sync-from: https://github.com/orenlion1/dotfiles; dotfiles-sync-date: 2026-08-30; dotfiles-sync-commit: 42a3e852aa9d6786e9e7f27e3fc77790fea09ffd -->

# AWS-style architecture diagrams

## Overview

Produce diagrams that follow [AWS reference architecture diagram](https://aws.amazon.com/architecture/reference-architecture-diagrams/)
conventions: accurate service names, labelled account/Region/VPC boundaries,
short flow labels, and an uncluttered canvas. "AWS-style" describes those
conventions; it does not by itself require official AWS icons or Graphviz.

Mermaid and Graphviz DOT are peer authoring formats. Mermaid often fits
inline, theme-aware, text-reviewable documentation; DOT often fits exact local
AWS icon assets, controlled composition, and presentation-ready SVG/PNG. Use
one when it satisfies the complete delivery contract and both when distinct
audiences or artifacts make the additional maintenance worthwhile.

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
deployed configuration, or an owner's written statement. A diagram is an
evidence artifact that happens to be visual.

Never add a service, connection, Availability Zone, VPC, or Region because the
picture looks unbalanced without it. If the source does not establish a
boundary, leave it out; an honest sparse diagram beats a decorative complete
one. When something is deployed but disabled, say so on the node
(`WEB_PUSH_ENABLED=false`, "Deployed, release-disabled") rather than drawing it
as if it were live, and mark what another team owns so a reader does not think
you control it.

State the provenance in the diagram itself — a subtitle naming the source, such
as *"traced to `<iac-dir>/*.tf` at `<revision>`"* or *"live read-only inventory,
`<date>`"* — and repeat it in a header comment in the DOT source.

## Name the resource, not just the service

A service icon alone does not identify anything. A magenta DynamoDB glyph
labelled "Operations" could be a table, a stream, or an index, and a reader has
no way to find it in the console. Every node states three facts:

1. **What it is called in AWS.** The real deployed name — `acme-orders-events`,
   not a friendly alias like "Orders". Write an account id as `<account>` rather
   than the digits; never put a secret, token, or endpoint in a diagram.
2. **What type of resource it is.** Written out, in grey, under the name:
   "DynamoDB table", "S3 bucket", "Lambda function", "API Gateway HTTP API",
   "WAFv2 web ACL", "SES v2 email identity".
3. **What it is for.** One line, and only where a reader could not infer it.

For Graphviz output, use a **resource icon** where AWS publishes one —
`Res_Amazon-DynamoDB_Table`, `Res_Amazon-Simple-Storage-Service_Bucket`,
`Res_AWS-Lambda_Lambda-Function` — and a **service (`Arch_`) icon** for
everything else. The icon reinforces the identity; it must never be the only
thing carrying it, because an icon is not readable in greyscale, at thumbnail
size, or by a screen reader.

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

If the requested content is actually tabular, use a Markdown table rather than
turning it into a picture. For an ordered participant exchange, Mermaid
`sequenceDiagram` is usually the natural fit; this is a diagram-type advantage,
not a general preference for Mermaid.

Mermaid supports [architecture diagrams and configurable icon
packs](https://mermaid.js.org/syntax/architecture.html), but a hosted renderer
cannot be assumed to provide repo-local AWS assets, custom pack registration,
or the same Mermaid version as a controlled local renderer. Graphviz can load
[local image assets directly](https://graphviz.org/docs/attrs/image/), so it is
the dependable choice when exact icon assets and fixed exported composition are
acceptance criteria, not merely because the request says "AWS-style".

Count the tradeoffs on both sides. Mermaid can vary across renderer versions,
available icon packs, and host themes. DOT adds a rendering step and generated
artifacts that must remain synchronized with the editable source. Select the
format whose costs match the repository and destination rather than treating
either tool's strengths as universal.

If renderer support, icon fidelity, fixed composition, or expected output files
would materially change the result and the request is ambiguous, clarify the
delivery contract. Otherwise select the format that satisfies the known
requirements with the least project-specific machinery.

When Mermaid is selected, retain the evidence, provenance, resource-naming, and
accessibility rules above, validate the source in its target renderer, and stop
before the Graphviz-specific workflow below.

### When both formats are justified

Produce Mermaid and DOT when they satisfy different real requirements, such as
inline repository review plus exact AWS-icon presentation output. Dual delivery
is not automatically better: it is justified only when both artifacts have a
named consumer or acceptance criterion.

Neither source is canonical by default. Derive both from the same verified
resource-and-relationship inventory, carry the same provenance, and check that
nodes, edges, boundaries, Regions, ownership, and uncertainty agree. A format
may add presentation-specific structure without changing the architecture it
claims. Name one format authoritative only when the user or repository policy
explicitly assigns that role.

For an unusually dense complete-system map that needs exact AWS icons, fixed
composition, or port-level connector placement, DOT plus its SVG and PNG can
serve as the presentation and AWS-icon artifact. A Mermaid rendering can serve
as the maintainable, inline-reviewable companion when that is also required.
For a focused flow without those DOT-specific requirements, Mermaid alone may
satisfy the contract. These are requirement-driven choices, not a reason to
produce both formats for every diagram.

## Mermaid workflow

### 1. Select the Mermaid diagram type

Use `architecture-beta` or a flowchart for architecture and topology, a
`sequenceDiagram` for ordered exchanges, and a state diagram only for actual
state transitions. Confirm that the target renderer supports the selected
syntax and any icon pack; do not assume GitHub, a documentation site, and a
local Mermaid CLI run the same version or configuration. When using Iconify
symbols, keep the full AWS resource name and type in text; an icon must never be
the only resource identifier.

### 2. Encode the verified inventory

Represent AWS account, Region, VPC, Availability Zone, subnet, and ownership
boundaries only when the evidence establishes them. Use full resource names and
types, short labelled edges, and visible annotations for permitted or inferred
relationships. Keep the provenance in nearby Markdown and, when the syntax
allows, in a source comment.

### 3. Render and inspect in the target environment

Use the repository's pinned Mermaid command or documentation build. Validate
the exact fenced block or `.mmd` source that will ship, then inspect the rendered
result at its intended width and theme. Check clipped labels, overlapping edges,
unsupported icons or syntax, inaccessible contrast, and semantic drift from the
verified inventory. Fix the editable source and rerender until it is readable.

Register non-built-in icon packs explicitly. For Mermaid CLI, a reproducible
AWS-symbol render can use:

```bash
mmdc --iconPacks '@iconify-json/logos' \
  -i system-context-aws.mmd -o system-context-aws.svg -b white
```

Treat a `?` fallback as a failed render, not a cosmetic degradation. Icon-pack
support can vary by Mermaid version and layout renderer; verify the actual
output visually and structurally. If one supported renderer loses registered
icons, use another supported renderer that preserves them and document the
layout tradeoff. Do not claim inline portability unless the target host also
registers the required pack.

### 4. Deliver the required artifacts

Keep Mermaid inline when that is the repository contract. When standalone SVG
or PNG outputs are required, render them deterministically with the repository's
pinned Mermaid version and document the reproduction command.

## Graphviz workflow

### 1. Establish the architecture from source

Read the IaC and inventory what actually exists before drawing anything. Find
the directory this project keeps it in — `infra/`, `terraform/`, `deploy/`, a
CDK app — rather than assuming a layout:

```bash
iac_dir=infra   # whatever this repository actually uses
grep -hoE '^resource "aws_[a-z0-9_]+"' "$iac_dir"/*.tf | sort | uniq -c | sort -rn
```

Then pull the specifics that make edges real **and the names that go on the
nodes**: function names, table names, bucket names, event rules and their
schedules, S3 notifications, authorizers, and any cross-account or cross-stack
grant. Resolve names through their variables and locals to the value actually
deployed. Note the Region from the variable that sets it, not from assumption.

### 1b. When there is no IaC, or the IaC is only part of the estate

Sometimes the thing to diagram is a running account nobody has Terraform for, or
the Terraform covers a fraction of what is deployed. Then the source is the live
account, read-only, and the diagram must be explicit that that is what it is.

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

### 1c. Say which kind of evidence each edge rests on

This matters most when reading a live account, where it is tempting to draw a
line because two resources share a naming prefix. Separate the classes visually
and define them in the diagram and its prose:

- **Wiring AWS itself reports** — a target group's targets, a replica's source.
  The strongest class; AWS is modelling the relationship for you.
- **A path something permits** — a security-group rule, a bucket policy. This
  establishes that a call *may* happen, not that it does. Note when a rule is
  CIDR-scoped rather than security-group-scoped: it authorises an entire range,
  not the one workload you drew the arrow from.
- **A grant an identity holds** — an IAM policy statement. Same caution, plus
  the grant is not the effective permission until SCPs, permission boundaries,
  and resource policies are evaluated.
- **Inference from naming or tags** — draw dashed, label with the uncertainty,
  or leave it out. Never solid.

Absence is a finding worth drawing too. When a role that "obviously" talks to a
queue turns out to hold no `sqs:*` action at all, a node saying so is more useful
than a missing arrow, because it forecloses the wrong assumption instead of
leaving it open.

### 2. Get the official icons

The asset package URL rotates, so discover it rather than hardcoding:

```bash
curl -fsSL https://aws.amazon.com/architecture/icons/ -o icons-page.html
grep -oiE 'https://d1\.awsstatic\.com/[^"]*Icon-package[^"]*\.zip' icons-page.html | head -1
```

Download, unzip, and copy only the 48px PNGs you actually use into
`<diagrams>/icons/`. Keep the original filenames — they identify the service and
the package version. Do not recolor, redraw, stretch, or substitute a generic
cloud glyph for a named service.

Record in the README where the icons came from and on what date, and note that
AWS trademark and icon terms apply and that the composition is not an AWS
endorsement.

### 3. Write the DOT source

Follow `references/dot-conventions.md` for the palette, the node table
structure, cluster nesting, and the settings that actually work in Graphviz.

For dense fan-out or scheduled/notification paths, use named HTML-table
`PORT` cells and explicit compass endpoints such as `worker:telemetry:s` or
`table:email:e`. Put endpoint meaning on the resource or its named cell where
possible. Invocation, state, logging, and alarm connectors must leave distinct
ports so downstream edges cannot appear to branch from an unrelated invoke
line. Render and inspect after every connector-layout change; syntactically
valid DOT can still communicate the wrong origin or destination.

### 4. Render

Graphviz's default SVG renderer leaves PNG icons as relative `icons/*.png`
references. That is acceptable only when the destination preserves and serves
the adjacent asset directory. For a standalone or sandbox-previewed SVG,
generate the standard SVG and run a repository-owned embedding step that
replaces only those image references with `data:` URLs while preserving
`preserveAspectRatio` and selectable text:

```bash
dot -Tsvg system-context-aws.dot -o system-context-aws.svg
node embed-svg-images.mjs system-context-aws.svg
dot -Tpng -Gdpi=180 system-context-aws.dot -o system-context-aws.png
```

Reuse an established repository helper when one exists. Otherwise create and
validate a narrowly scoped helper beside the diagrams, or keep the standard SVG
and ship its icon directory with it; never document a command for a helper that
does not exist in the delivered repository.

The embedding helper must be idempotent, validate its input, provide a
non-mutating `--check` mode, reject paths outside the diagram directory, and
verify that at least one image was embedded with no local references left.
Do not substitute `svg:cairo` without visual verification: tested Graphviz
15.1.1 output embedded the icons but applied a non-uniform `1 x 0.75` transform
that vertically compressed square AWS assets and converted text to glyph paths.
State which portability and text-accessibility contract the output satisfies.
SVG is for repositories and the web; PNG is for decks and issue threads.

### 5. Look at the result — this step is not optional

Open the rendered PNG and actually inspect it. Graphviz will produce a valid
file that is unreadable. Check:

- no node has escaped its cluster box (a node drawn outside the boundary it
  belongs to is a **correctness** bug, not a cosmetic one);
- no edge label sits on top of another label or an icon;
- no edge crosses a cluster it has no business entering;
- the aspect ratio suits the destination — a diagram three times taller than it
  is wide will be illegible on a slide;
- **the type survives the scale it will be viewed at.** This is the failure that
  gets shipped most often, because the diagram looks fine at 100% in the render
  you just opened. Check the `width` the SVG declares: at a 900px page width, a
  1900pt-wide diagram is drawn at about a third of size, so its 9pt labels land
  near 4px. Raising the font sizes alone makes it *wider* and no more readable.
  Past roughly 1200pt, switch `rankdir` to `TB` — height scrolls, width shrinks
  the type — or split the diagram;
- every icon is the service the label claims.

For a self-contained SVG, also verify that no relative icon link remains and
that embedded image data exists. For example:

```bash
xmllint --noout system-context-aws.svg
! grep -Eq '(xlink:)?href="icons/' system-context-aws.svg
grep -Eq '(xlink:)?href="data:image/png;base64' system-context-aws.svg
! grep -q 'matrix(1, 0, 0, 0.75' system-context-aws.svg
```

Open the SVG itself in the destination preview, not only the separately
rendered PNG. A PNG can look correct while the SVG silently depends on missing
relative icon files.

If it fails, fix it and render again. Common fixes are in
`references/dot-conventions.md` under "When the layout fights you".

### 6. Write the README

List each diagram, its editable source, its rendered outputs, the render
commands, and the icon provenance. See `references/readme-template.md`.

## One concern per diagram

The strongest lever on legibility is refusing to draw everything at once. When
a single graph gets dense, split it by concern and cross-reference in the
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

## Keeping them current

When a change alters AWS structure, update every delivered editable source and
rerender its required outputs together — a stale diagram is worse than none,
because it is believed. For dual-format delivery, validate semantic parity
between Mermaid and DOT as well as each renderer's output; neither format is
canonical unless the user or repository says so. Treat that synchronization
as part of this skill's verification contract.

## Verification

Verify source provenance, resource names and types, boundaries, Regions, edge evidence,
ownership, and uncertainty against the inventory. Render every delivered source in its
target environment, visually inspect it at delivery scale, validate required SVG/PNG files,
and compare semantic parity when both Mermaid and DOT are delivered.
