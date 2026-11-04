# Publication security

This repository contains reusable skills and synthetic examples. Investigation inputs,
reports, telemetry, customer or patient records, credentials, and institutional identifiers
must stay outside published Git objects. A clean scan is evidence for the configured rules,
not proof that arbitrary prose or encoded data contains no confidential information.

## Before the first push

CI runs after GitHub receives content. Scan locally before uploading any commit, branch, or
tag. After initializing the fresh repository, enable the checked-in pre-push hook:

```sh
git config --local core.hooksPath .githooks
bash scripts/check-disclosure.sh
```

Gitleaks **8.30.1**, Git, Bash, and Python 3.10+ must be available. The hook fails when a
scanner or policy is missing; it never installs tools during a push. Do not use `--no-verify`
or relax a rule to publish a finding. The hook is supplied but is not enabled in this
directory while it has no Git metadata. The scanners read Git objects and the index, so
stage intended files again after editing; unstaged and ignored local files are not audited.
Before the initial commit, the institutional preflight can run with
`python3 scripts/scan-institutional-data.py --staged`.

## GitHub gates

[Security](.github/workflows/security.yml) runs on pull requests, merge queues, all branch
and tag pushes, and manual dispatch. It has read-only permissions, no supplied repository
secrets, disabled checkout credential persistence, full-depth fetches, SHA-pinned actions,
and a checksum-pinned standalone Gitleaks release. It uses `pull_request`, never privileged
`pull_request_target`, and uploads no scanner output or sensitive findings as artifacts.

- **Secret scan** first runs `python3 scripts/test_secret_scan.py`, then
  `bash scripts/scan-secrets.sh .`. The real-scanner tests exercise deleted credentials,
  detached heads, commit messages, direct and nested tag annotations, missing tools,
  shallow clones, and suppression attempts. The scan uses a
  temporary bare mirror, every fetched ref, and the exact detached checkout head; repository
  ignore files, inline allow comments, and custom Gitleaks configuration cannot suppress it.
  Gitleaks scans both historical patches and private temporary exports of every reachable
  commit and tag object, including intermediate annotations without their own refs.
- **Institutional data** tests the disclosure controls, then scans the index, all reachable
  commit trees, branch/ref names, and commit and annotated-tag metadata, including every
  annotation in a nested tag chain even when only its outer ref remains. It blocks private
  artifact paths even if force-added, non-public email addresses, unreviewed URL hosts,
  account and ticket identifiers, and configured institution-name fingerprints. Symlinks,
  submodules, oversize objects, and unreviewed binary content fail closed. Binary exceptions
  require an exact path and SHA-256 digest in the reviewed policy. Scanner failures omit
  matched content and paths, including filenames that could contain workflow commands.

After choosing the new GitHub destination, require **Secret scan**, **Institutional data**,
**Tests**, and **Skill Quality Gate** in its branch rules. Require code-owner review for
workflow, scanner, hook, and policy changes, disallow direct pushes and protection bypasses,
and restrict release tags. Review the destination's native secret protection and push
protection options separately. Local YAML and CODEOWNERS cannot activate hosted protections.
Do not publish a release until both security checks pass on its exact tag SHA.

## Disclosure policy

[security/disclosure-policy.json](security/disclosure-policy.json) stores the reviewed public
URL hosts, public email domains, and institution fingerprints. Reserved example domains are
allowed; add a real public host only after review. Corporate domains are not approved merely
because their website is public. Keep integration endpoints generic and examples synthetic.
The exact GitHub merge-bot email is approved for generated commit metadata; this does
not approve other addresses at its domain.

Institution fingerprints use SHA-256 of NFKC-normalized, case-folded ASCII letters/digits,
plus the normalized length. The scanner hashes sliding windows, detecting names embedded in
domains, longer identifiers, or punctuation-separated text. Fingerprints avoid committing the
literal names; they do not hide easily guessed names from dictionary attacks. Add identifiers
locally and commit only their lengths and digests. Do not submit the original values to a
public issue, PR discussion, workflow variable, test fixture, or scan log.

Private paths (`docs`, `logs`, `outputs`, `inputs`, tool caches, real environment files, key
material, and history bundles) are blocked independently of `.gitignore`. Use generic source
assets under a skill's established directories. Ordinary public text is scanned, including
tests; test fixtures assemble prohibited examples only in disposable repositories.

## Coverage and response

The gates inspect only available local/fetched refs and staged Git objects. They cannot
inspect deleted server-retained objects, other clones, GitHub PR retention, issues, wikis,
releases, Actions logs/artifacts, or ignored local evidence. Do not infer hosted cleanup
from a passing local scan. Unknown institutional names, semantic disclosures, novel secret
formats, and encoded/steganographic content still require human review. Reviewed binary
approvals are not OCR or content analysis.

If a credential reaches a remote, revoke or rotate it before history cleanup. Remove
institutional data from every affected ref and address hosted copies separately. Avoid
echoing the finding into CI logs or a public issue. Use a private reporting channel with
the repository owner; no hosted reporting channel has been configured for the new repository.
