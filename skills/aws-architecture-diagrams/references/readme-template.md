# README template for a diagrams directory

Adapt this into `<diagrams>/README.md`. The provenance paragraph is not
optional: it is what lets a later reader judge whether the picture is still
true.

````markdown
# AWS-style architecture diagrams

These diagrams use the visual conventions of AWS reference architecture
diagrams: official AWS service icons, nested account/Region boundaries, a white
canvas, AWS palette accents, concise service labels.

**Every node and edge is traced to `<the source>`.** No service, boundary,
Region, or connection is drawn to make a picture look complete. Where something
is deployed but disabled, or owned by another team, the node says so.

## Sources and outputs

| Diagram | What it shows | Editable source | SVG | PNG |
|---|---|---|---|---|
| System context | Authenticated request path | `system-context-aws.dot` | `system-context-aws.svg` | `system-context-aws.png` |
| Scheduled work | Timers and event-driven functions | `async-data-flow-aws.dot` | `async-data-flow-aws.svg` | `async-data-flow-aws.png` |

## Render

From this directory, so the relative icon paths resolve:

```bash
dot -Tsvg system-context-aws.dot -o system-context-aws.svg
dot -Tpng -Gdpi=180 system-context-aws.dot -o system-context-aws.png
```

## Keeping them true

When a change adds, removes, or rewires an AWS resource, update the `.dot`
source and re-render both outputs in the same change. A stale architecture
diagram is worse than no diagram, because it is believed.

## Icons

The icons under `icons/` are official AWS Architecture Icons from
<https://aws.amazon.com/architecture/icons/>, downloaded on `<DATE>` from the
`<PACKAGE>` package. AWS states these assets may be used in architecture
diagrams; AWS trademark and icon terms continue to apply. The diagram
composition is project-authored and is not an AWS endorsement.
````

## Two sections worth adding when they apply

**What the edge styles mean.** Where the diagrams mix evidence classes, give the
reader a key — each style, what it claims, and what confirmed it:

| Edge style | Meaning | Evidence |
| --- | --- | --- |
| Grey solid | AWS reports the resources as wired together | ELBv2 target groups |
| Blue solid | A security-group rule permits the path | `ec2:DescribeSecurityGroups` |
| Orange dashed | An IAM policy grants the call, traffic not observed | `iam:GetPolicyVersion` |

**What is deliberately not drawn, and why.** A reader who notices a missing
component will assume you forgot. A short section naming what has no diagram and
why — no route of its own, no stored state, already covered elsewhere — converts
an apparent gap into a decision, and stops the next person adding a near
duplicate.

**Both themes, if the set has them.** State in the README that each `<stem>.dot`
produces four files — `<stem>.svg`, `<stem>.png`, and the `<stem>-dark` pair —
and that the `.dot` carries the light palette while the dark outputs are derived
at render time. Without that sentence the next person edits a `-dark` file
directly and loses the change on the next render.
