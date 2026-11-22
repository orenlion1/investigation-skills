# Economization

A skill's `SKILL.md` is loaded whenever the skill is used; its references load on demand.
Economizing means paying the always-loaded cost only for what every use needs.

## Practices

- State each rule once. If a reference holds the detail, the skill file links to it.
- Move what a reader rarely needs (setup, edge cases, long examples, tables of options) into
  a reference named for its topic.
- Keep the path to action short: what the skill does, when to use it, the commands, the
  verification.
- Write every description to one shape: one quoted line that says what the skill does, then
  a trigger beginning `Use when`, `Use for` or `Use only`.
- Prefer deleting a sentence to shortening it.

## Guardrails

| Check | Fails when |
| --- | --- |
| `size-ratchet` | A `SKILL.md` is larger than its recorded baseline, or a skill has no entry |
| `duplication` | A paragraph or list item of 80 or more normalized characters appears in both a `SKILL.md` and one of its references |
| `links` | A relative link or heading anchor under the catalog does not resolve |
| `description-shape` | A description is unquoted, multi-line, outside 40 to 500 characters, has no trigger, or does not end with a period |
| `preserve` | A rewrite lost a code span, a code line, or a bounded number, and the removal is not declared |

The ratchet is not a cap. It records where each skill is and stops silent growth; a skill
that needs more always-loaded text says so with `ratchet --record` in a reviewable change.

## Proving a rewrite lost nothing

```sh
python3 skills/skill-ownership/scripts/ownership.py preserve --repository . \
  --base <revision> --skill skills/<name>
```

The check compares the skill at `<revision>` with the working tree across `SKILL.md` and
every reference, so text moved into a reference still counts as kept. Declare a deliberate
removal in a `token-removals/v1` file passed with `--removals`; a declaration for a token
that was not lost fails, so the file cannot go stale.

These lints are literal. They do not detect a paraphrase or judge whether a sentence earns
its place; review does.
