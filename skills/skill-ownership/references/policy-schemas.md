# Policy Schemas

Each policy file lives in the adopting repository's `policy/` directory. Start from the
matching file in `templates/policy/`.

| File | Required | Check | Purpose |
| --- | --- | --- | --- |
| `root-contract.json` | Always | `root-contract`, `skill-validation` | Root files, line budget, clause, section allowlist, routing coverage |
| `skill-ownership-pin.json` | Always, downstream | `pin` | Which upstream release the carried copy came from |
| `skill-size-baseline.json` | Optional | `size-ratchet` | Recorded `SKILL.md` sizes |
| `delegation-contract.json` | Optional | `delegation-contract` | One shared definition of delegation machinery |
| `vendored-imports.json` | Optional | `vendored-imports` | Pins for skills imported from other repositories |

## root-contract.json

Schema `root-contract/v1`. `files` lists at least two root files that must stay
byte-identical. `max_lines` is the line budget. `ownership_clause` is matched verbatim after
whitespace is collapsed. `allowed_sections` is the allowlist of level-two headings and
`required_sections` its mandatory subset. `skills_dir` names the catalog. `minimum` declares
how many sections and skills a run must have checked, so an empty scan cannot pass.

The optional `docs` key adds README and diagram checks: required README sections, complete
diagram sets, and a routing diagram that mentions every routed skill.

## skill-ownership-pin.json

Schema `skill-ownership-pin/v1` with exactly these keys:

| Key | Value |
| --- | --- |
| `upstream_repository` | Plain `https` URL of the upstream repository |
| `commit` | Full 40-character lowercase commit of the release |
| `version` | The release's `VERSION`; must equal the carried `metadata.version` |
| `local_adaptations` | List of `{path, reason}` for files inside the carried skill that differ on purpose |

The carried `SKILL.md` declares its release as one quoted `metadata.version` and no other
`metadata` key. Where the copy came from lives only in the pin.

## skill-size-baseline.json

Schema `skill-size-baseline/v1`: a map from skill path to `SKILL.md` size in bytes. Written
by `ratchet --record`; edit it by hand only to remove a retired skill.
