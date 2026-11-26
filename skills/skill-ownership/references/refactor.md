# Refactor Workflow

Refactoring changes the target repository, so it needs that repository's own authorization
and review path. The scripts report and check; they never rewrite prose.

1. Run `audit` and read every section it lists. Correct any class the heuristic got wrong.
2. Record the starting point: note the revision you will compare against.
3. Open both root files with one title and the clause, verbatim. Wrapping is free; wording
   is not. Nothing else may sit above the first section.
4. Build the routing table: one row per skill, each linking `skills/<name>/SKILL.md`. Every
   skill directory needs a row, and every row needs a skill.
5. Move each workflow section into its owner. Prefer an existing skill; create one when no
   skill owns the work. Leave a route, and at most a limiting sentence, behind.
6. Review skill names using the naming reference linked from SKILL.md; update routes and
   other references together for any authorized rename. Give every skill an eval case,
   including ones you created.
7. Copy the policy templates you need into `policy/`, fill them with the repository's own
   values, and list the surviving sections in the root contract's allowlist.
8. Run `preserve --base <revision> --skill skills/<name>` for each skill that received moved
   text. Declare a removal only when the token was retired on purpose.
9. Run `check`. Raise each policy `minimum` to the real count once it passes.
10. Record the size baseline with `ratchet --record` and add the checks to continuous
    integration beside the gates the repository already has.

Never weaken an existing gate to make adoption pass. A gate that conflicts with the
principle is a finding to raise, not a rule to delete.
