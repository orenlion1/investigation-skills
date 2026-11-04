# DOT conventions for AWS-style diagrams

## Palette

These are the AWS architecture colours. Use them for boundaries and text; let
the icons carry the service colour.

| Purpose | Colour |
| --- | --- |
| Text, account boundary | `#232F3E` (squid ink) |
| Region boundary | `#00A4A6` |
| VPC / private grouping | `#8C4FFF` |
| Data and storage grouping | `#3B48CC` |
| Compute grouping | `#ED7100` |
| Edge / global grouping | `#7AA116` |
| Edges and edge labels | `#545B64` |
| Attention, external ownership, disabled | `#FF9900` on `#FFF7E8` |

## Graph, node, and edge defaults

```dot
graph [rankdir=LR, bgcolor="white", pad=0.4, nodesep=0.4, ranksep=1.0,
       fontname="Arial", fontsize=20, fontcolor="#232F3E",
       label="Title\nSubtitle naming the evidence", labelloc=t, labeljust=l,
       splines=spline, compound=true, newrank=true];
node [shape=plain, fontname="Arial", fontsize=10, fontcolor="#232F3E"];
edge [fontname="Arial", fontsize=9, color="#545B64", fontcolor="#545B64",
      penwidth=1.3, arrowsize=0.7];
```

`rankdir=LR` suits request flows. Use the default top-to-bottom for sequences.

## Nodes are HTML tables, not shapes

`shape=plain` with an HTML-like label puts the icon above the text and lets the
icon keep its own aspect ratio and colour.

```dot
api [label=<<TABLE BORDER="0" CELLBORDER="0" CELLPADDING="3">
  <TR><TD><IMG SRC="icons/Res_AWS-Lambda_Lambda-Function_48.png"/></TD></TR>
  <TR><TD><B>acme-orders-api</B></TD></TR>
  <TR><TD><FONT POINT-SIZE="9" COLOR="#545B64">Lambda function</FONT></TD></TR>
  <TR><TD><FONT POINT-SIZE="9">Re-verifies the token</FONT></TD></TR>
</TABLE>>];
```

Four rows, in this order:

1. the icon;
2. the **real AWS name** in bold — what you would search the console for;
3. the **resource type** in grey `#545B64` at 9pt — "Lambda function",
   "DynamoDB table", "S3 bucket";
4. the one purpose line a reader cannot infer, omitted when they can.

A node is a label, not a paragraph: break a long name with `<BR/>` rather than
letting one row set the column width. Write an account id as `<account>`
(escaped `&lt;account&gt;` inside the HTML label), and never put a secret,
token, ARN, or endpoint in a diagram.

## Which icon: `Arch_` or `Res_`

The icon package ships **Architecture icons** (`Arch_*`) for services and
**Resource icons** (`Res_*`) for specific resource types. Use the resource icon
whenever the node is a resource and AWS publishes one:

| Node is | Icon |
| --- | --- |
| A DynamoDB table | `Res_Amazon-DynamoDB_Table_48.png` |
| An S3 bucket | `Res_Amazon-Simple-Storage-Service_Bucket_48.png` |
| A Lambda function | `Res_AWS-Lambda_Lambda-Function_48.png` |
| A service with no distinct resource icon | `Arch_<Service>_48.png` |

The icon is reinforcement. The text has to identify the resource on its own,
because an icon is not readable in greyscale, at thumbnail size, or by a screen
reader.

For something owned by another team, deliberately disabled, or otherwise not
what it appears, give the table a border:

```dot
[label=<<TABLE BORDER="1" COLOR="#FF9900" BGCOLOR="#FFF7E8" CELLBORDER="0" CELLPADDING="5"> … </TABLE>>]
```

Two icons in one node (`<TR><TD><IMG/></TD><TD><IMG/></TD></TR>` with
`COLSPAN="2"` beneath) is right when a single concept is genuinely delivered by
a pair of services. It is wrong as a way to save space.

## Boundaries nest

Account contains Region contains VPC contains subnets — and only the ones the
source establishes. Solid for the account, dashed for Region and other logical
scopes.

```dot
subgraph cluster_account {
  label="AWS account"; labelloc=t; labeljust=l;
  color="#232F3E"; penwidth=2.0; style="rounded"; margin=16;
  fontname="Arial"; fontsize=12; fontcolor="#232F3E";

  subgraph cluster_region {
    label="Region  us-east-1"; labelloc=t; labeljust=l;
    color="#00A4A6"; penwidth=1.8; style="rounded,dashed"; margin=14;
    …
  }
}
```

Anything outside the account — a user, the internet, another team's stack —
lives outside every cluster. That placement is the diagram's way of saying "not
ours", so do not tuck an external system inside the account box for tidiness.

## Edges

Solid for the primary flow, dashed for control, trust, configuration, and
observability. Short lowercase labels: `HTTPS`, `presign PUT`, `ObjectCreated`,
`JWT authorizer`. Number steps only when order is part of the claim.

Where a diagram mixes kinds of evidence, give each kind its own visual class and
say what the classes mean in a header comment and in the accompanying prose:

```dot
/* wiring a live API confirms */
nlb -> alb [label="web-nlb-443-alb\nTCP 443; target type alb"];

/* a security-group rule permits this path */
edge [color="#3B48CC", fontcolor="#3B48CC"];
web -> rds [label="TCP 1433"];

/* an IAM policy grants this call; traffic was not observed */
edge [color="#ED7100", fontcolor="#ED7100", style=dashed];
web -> secret [label="secretsmanager:GetSecretValue"];
```

Edge attribute statements are positional — they apply to every edge declared
after them — so group edges by class and set the attributes once.

## Publishing in two themes

A white canvas is a glaring slab in a dark-only UI, which is where a lot of
people now read. If a diagram set needs both themes, **derive the dark variant
at render time from the light source. Do not keep a second `.dot`.** A forked
pair drifts the moment someone edits one side, and the drift is invisible until
a reader trusts the stale one.

A small generator that string-substitutes a role-based palette is enough:

| Role | Light | Dark |
| --- | --- | --- |
| Canvas | `white` | `#0D1117` |
| Primary text, account boundary | `#232F3E` | `#E6EDF3` |
| Secondary text, edges | `#545B64` | `#9BA7B4` |
| Region | `#00A4A6` | `#2DD4D6` |
| VPC | `#7AA116` | `#A3D227` |
| Ingress / messaging | `#8C4FFF` | `#B18AFF` |
| Compute | `#ED7100` | `#FF9A3C` |
| Data / storage | `#3B48CC` | `#7C86F0` |
| Security | `#C7131F` | `#FF6B6B` |
| External / unowned | `#879196` | `#8B949E` |

For that substitution to be total, every colour in the source has to come from
the palette. Two things escape it, and both are silent:

**Tint fills.** A pale highlight such as the `BGCOLOR="#FFF7E8"` callout above
is nearly white. Left unmapped it burns a hole in the dark canvas, and it will
not show up in any warning — only by looking. Give every tint a dark surface
counterpart (`#FFF7E8` → `#2A2113`, `#F7FAEF` → `#172013`).

**Icons.** AWS publishes the coloured service and resource glyphs for light
backgrounds only. In practice they read acceptably on dark, because the strokes
are saturated — but verify that by rendering, not by assuming. The
General-Icons set is the real trap: it ships explicit `_Light`/`_Dark` pairs,
and the light `Res_Users` glyph is a mid-grey that vanishes completely. Carry
the `_Dark` counterpart and swap it with the palette.

Then look at **both** renders. A theme map that is correct for eight diagrams
can still be missing the one colour the ninth uses.

## When the layout fights you

**A node renders outside its cluster.** Too many long cross-cluster edges are
pulling it out. Reduce edges, or split the diagram by concern.

**An edge label sits on a cluster border.** Graphviz places the label at the
edge midpoint with no awareness of boundaries, so a long edge crossing two
clusters will drop its label on one of them. Raising `ranksep` sometimes moves
it and shortening the label sometimes helps, but the reliable fix is to stop
drawing that edge in that diagram. If two or three edges have to travel the
whole width of the graph, they are usually a second diagram trying to get out.

**Labels collide or vanish.** `splines=ortho` does not support edge labels at
all — Graphviz warns and drops them. Either use `splines=spline` (usually
right) or switch to `xlabel`, accepting looser placement.

**The graph is far taller than it is wide.** Too many nodes on one rank chain.
Split by concern first. Then try raising `nodesep`, or `{rank=same; a; b;}` for
genuine siblings.

**Clusters overlap or edges cut through them.** Add `newrank=true`; increase
cluster `margin`; and check for an edge that crosses a boundary it should not.

Do not fix legibility by shrinking font sizes. If it does not fit at these
sizes, it is two diagrams.

## Render

```bash
dot -Tsvg name-aws.dot -o name-aws.svg
dot -Tpng -Gdpi=180 name-aws.dot -o name-aws.png
```

Icon paths are resolved against the working directory of the `dot` process,
not against the DOT file, so always render from the diagram directory.
