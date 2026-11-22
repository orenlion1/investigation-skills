# Sync

A downstream repository carries `skills/skill-ownership/` and records where it came from in
`policy/skill-ownership-pin.json`. Sync keeps the two in step with an upstream release.

## Report

```sh
python3 skills/skill-ownership/scripts/ownership.py sync --repository .
```

Read-only. It reads the upstream release tags, checks that the pin's commit is the commit
of the pinned release, and prints the carried release, the latest release, the files that
changed between them, and any carried file that differs from its pinned release without
being declared. `--format json` gives the same facts to a tool.

| Exit code | Meaning |
| --- | --- |
| 0 | Current, and the carried copy matches its pinned release |
| 3 | Behind the latest release |
| 4 | Undeclared drift from the pinned release |
| 1 | The report could not be produced (for example, an unreachable upstream) |

`--upstream` reads releases from another location, such as an SSH URL or a local clone,
when the pin's `https` URL needs credentials the environment does not have. It does not
change the pin.

## Apply

```sh
python3 skills/skill-ownership/scripts/ownership.py sync --repository . --apply [--to 0.2.0]
```

Apply replaces the carried directory with the target release (the latest by default) and
rewrites the pin's `commit` and `version` in the same change. It then stops: review the
working tree and deliver it through the repository's normal path. Sync never commits,
pushes, or merges.

Apply refuses to run when a carried file differs from the pinned release without a
declaration, when the target is older than the carried release, or when the carried
directory or a file in it is a symlink.

## First adoption

With no pin and no carried copy, apply creates both:

```sh
python3 skills/skill-ownership/scripts/ownership.py sync --repository . --apply \
  --upstream <url-or-path> [--upstream-url <canonical-https-url>]
```

The script is not in the repository yet at that point, so run it from a checkout of the
upstream release. `--upstream-url` records the canonical `https` URL in the new pin when
`--upstream` is not one.

## Local adaptations

A repository may keep a carried file different on purpose. Declare it in the pin:

```json
"local_adaptations": [{"path": "references/evals.md", "reason": "Names our own gate."}]
```

Paths are relative to the carried skill. A declared file is never overwritten or deleted by
apply, and is reported as preserved. If `SKILL.md` is declared, apply still updates its
`metadata.version` value, and nothing else in it.

## What sync never touches

Anything outside the carried directory and the pin file: continuous integration, other
policy files and their minimums, the size baseline, the root files, and other skills. A
release that needs one of those changed says so in its notes; the change is the adopting
repository's own to make and review.
