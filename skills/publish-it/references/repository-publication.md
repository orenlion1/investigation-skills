# Repository publication

Use this guidance only within an explicitly authorized publication whose effective destination
list names a repository. It delivers the packaged investigation artifacts to a GitHub or
Bitbucket repository as one publication branch and one pull request. The package, the
[reference gate](../../report-evidence/references/reference-completeness.md) and the evidence
rules are the ones [Publish It](../SKILL.md) already applied; this procedure adds only what a
repository destination needs.

## Resolve the destination

Resolve and record, before any write:

- **Provider and repository.** From the entry's host: a GitHub repository, or a Bitbucket
  workspace and repository. A short name needs verified provider context; never guess one.
- **Base branch.** The branch named in the entry (`/tree/<branch>/…` on GitHub,
  `/src/<branch>/…` on Bitbucket), otherwise the repository's default branch read from the
  provider.
- **Directory.** The directory named in the entry, otherwise the destination repository's
  documented location for investigation reports. There is no fallback directory: when neither
  exists, the destination is incomplete and [Publish It](../SKILL.md#destinations) returns its
  missing-destination feedback instead of choosing a location.
- **Visibility and access.** Read the repository's visibility and confirm, with one bounded
  read, that the current identity can push a branch and open a pull request.

Use the caller's resolved destination, not a hard-coded organization, workspace or repository.
Stop this destination, and report the exact blocker, when the repository cannot be identified,
access is missing, or the directory resolves outside the repository.

A **public** repository needs the user's explicit confirmation of that visibility in the current
conversation before the first push: investigation reports describe live systems. Without it,
record the destination as blocked and continue with the others.

## Access and tooling

- GitHub: approved GitHub tooling with the user's existing access.
- Bitbucket: [Rovo Dev MCP](../../rovo-dev-mcp/SKILL.md) for authentication, discovery and pull
  request operations its live tool schemas offer; Git over the user's existing authenticated
  remote for the branch push.

Use the commit identity already configured for that remote. Do not change global Git
configuration, store credentials, or embed tokens in remote URLs, commit messages or evidence.

## Lay out the files

Work in a fresh clone or worktree of the destination repository outside the caller's working
tree, on the branch `publish/<slug>` created from the base branch, where `<slug>` is the
verified artifact slug from [Workflow Artifact Naming](../../workflow-artifact-naming/SKILL.md).

Place the package under `<directory>/<slug>/`, keeping the report's own relative layout so its
figures and cited assets resolve without edits:

| Packaged artifact | Path under `<directory>/<slug>/` |
| --- | --- |
| Report Markdown | `REPORT-<slug>.md` |
| Selected matching PDF (Generate PDF `enabled` only) | `REPORT-<slug>.pdf` |
| Parent TASK | `TASK-<slug>.md` |
| Diagrams, theme variants, editable sources, cited local evidence | The report-relative paths they already have, such as `assets/<slug>/…` |

Commit original bytes. Where a relative link in the report would not resolve in this layout —
typically the link to the parent TASK — add a `README.md` in the same directory that links the
report, the PDF and the TASK, rather than rewriting the original; disclose any derivative that
was unavoidable. Commit only inventoried files: no task or log directories, credential caches,
transcripts or unreferenced files. A task-only publication commits the TASK and a `README.md`
stating its actual scope.

## Resume instead of duplicating

Before creating anything, look for an existing `publish/<slug>` branch or an open pull request
from it. A match with verified artifact identity is the same publication: add a new commit to
that branch and reuse its pull request. Never force-push, rewrite published history, or open a
second pull request for the same slug and base. Resolve a branch with unrelated content, or a
same-named directory already on the base branch with a different artifact identity, with the user
before writing. A republished revision is a new commit that replaces the files in place.

## Publish

1. Run the destination repository's own documented pre-commit and pre-push checks. Never skip
   hooks, bypass branch protection, or relax a secret or disclosure scan to make a push succeed;
   a rejection is this destination's blocker.
2. Commit with a message naming the investigation title and slug.
3. Push `publish/<slug>`. Never push to the base, default or any protected branch.
4. Open one pull request into the base branch. Its description states what was published, the
   source revision and evidence window recorded in the report, the file inventory, and any gaps.
   Do not add reviewers, labels or mentions the user did not ask for.
5. Stop there. Merging, approving, enabling auto-merge, and deleting the branch remain
   separately authorized.

When the provider tooling cannot open the pull request, keep the pushed branch, record the
destination as partial, and return the branch plus the exact remaining operation.

## Read back

Verify from the provider, not from the local clone:

- the pushed commit on `publish/<slug>` contains exactly the inventoried files, and each
  file's hash matches the package manifest;
- the report renders in the provider's Markdown view with its figures and adjacent captions,
  and its relative links resolve on that branch;
- the pull request is open, unmerged, targets the resolved base branch, and contains only the
  publication's files.

Record the repository, base branch, publication branch, commit, pull request URL, file hashes
and check results in the publication manifest. A check the provider or an authentication gap
prevented stays incomplete rather than passing.
