# The Ownership Principle

One owner per rule. The clause that opens the root files defines a model with three
classes, and every level-two section of a root file belongs to exactly one.

| Class | What it is | Where it lives |
| --- | --- | --- |
| Route | A row that sends a request or situation to the skill that owns it | The routing table in the root file |
| Residual policy | A rule no skill covers, usually a limit on what skills may do | An allowlisted root-file section |
| Workflow content | Steps, commands, or guidance for doing a piece of work | The owning skill, never the root file |

## Telling the classes apart

- A section that answers "who handles this?" is a route.
- A section that answers "what is never allowed, or always required, whoever handles it?" is
  residual policy. The clause gives it force: where it limits an owner, the limit holds.
- A section that answers "how do I do this?" is workflow content. Numbered steps, bullets
  that open with a verb, and command blocks are the usual signs.

A residual policy may point at an owner, and a route may carry a short note. Neither may
restate what the owner already says: the second copy is the one that drifts.

## What an owner holds

A skill owns its workflow, its guidance, and its verification. It has a clear interface (the
`description` a router matches) and its own tests (an eval case). Anything about how the
work is done changes in the skill and nowhere else.

## Repository-specific rules about a shared skill

A repository sometimes needs a rule that differs from a skill it distributes or imports.
That rule is residual policy when it only limits the owner, and it stays in the root file.
When it is a procedure of its own, it becomes a repository-local skill with its own route,
so the shared skill keeps its defaults for everyone else.
