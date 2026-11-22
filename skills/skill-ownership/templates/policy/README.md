# Policy templates

Copy a template to the downstream repository's `policy/` directory and replace every value
with that repository's own. A check runs only for a policy file that exists; the root
contract is always required.

| Template | Becomes | Enforced by |
| --- | --- | --- |
| `root-contract.json` | `policy/root-contract.json` | `root-contract`, `skill-validation` |
| `root-contract-docs.json` | the optional `docs` key inside `policy/root-contract.json` | `docs-contract` |
| `delegation-contract.json` | `policy/delegation-contract.json` | `delegation-contract` |
| `vendored-imports.json` | `policy/vendored-imports.json` | `vendored-imports` |
| `skill-ownership-pin.json` | `policy/skill-ownership-pin.json` (always required downstream) | `pin` |

Raise each `minimum` to the real count once the repository passes, so a scan that silently
checks less than it should fails instead of passing.
