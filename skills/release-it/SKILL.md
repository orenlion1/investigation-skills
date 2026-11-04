---
name: release-it
description: Release investigation-skills on GitHub. Use when the user says run release-it or requests a new repository release. Validate version metadata, complete the protected PR and annotated tag workflow, verify exact-SHA CI, and publish curated GitHub release notes.
---

# Release It

## Overview

Adapted from the agent-tasks release-plugin workflow and release contract.
Use only for `orenlion1/investigation-skills`, verified from the repository remote,
with `VERSION`, `package.json`, `scripts/release.py`, and `VERSIONING.md` present.

Read [the release contract](../../VERSIONING.md) completely and follow it as the
source of truth. An explicit release request authorizes the entire documented
release lifecycle without a second permission request, within the caller's scope.

Verify clean synchronized main, GitHub identity/authentication, existing tags/releases,
and protection before preparation. Preserve unrelated edits; use the contract's
first-release exception only when no stable tags or releases exist. Otherwise
save the prior tag and choose the next patch or explicit greater stable version.
Run the bumper's check mode before mutation and all `scripts/check.sh` gates.

Review the complete diff, push the preparation branch, and use the protected squash
PR path with required Tests, Skill Quality Gate, Secret scan, and Institutional data
checks and `--match-head-commit` bound to the reviewed head. Run the local
`bash scripts/check-disclosure.sh` gate before uploading commits or tags.
Reread checks and protection immediately before merge. Verify the merged revision,
rerun gates there, and create one annotated tag on that exact synchronized main SHA.
Require its remote peeled SHA and successful push-triggered Verify Release,
Secret scan, and Institutional data checks
to match before creating a draft GitHub Release.

Curate generated notes from actual changes, publish, then read back the exact tag,
title, changelog link, body, publication timestamp, and non-draft/non-prerelease
state. Report the PR, merge/tag SHAs, workflow URL, release URL, tests, and gaps.
This repository ships source skills; do not run agent-tasks plugin installers or
claim native-host parity. Never publish to npm, force-push, bypass protection, move
a tag, overwrite an existing release, or discard local artifacts to repair a failure.

Stop the affected release step on version drift, target conflicts, changed PR head,
failed checks, blocked protection, mismatched tag/workflow SHA, or failed publication
read-back. Resolve through normal protected work and immutable forward versions;
never lower a gate or claim completion from a queued workflow or tag push alone.

## When to Use

- The user says `run release-it`.
- An explicit request for a new GitHub release of this repository.
- Never for Confluence publication or unrelated repositories.

## Common Rationalizations

- "Local tests passed; CI is a formality." Only a successful push-triggered Verify Release run on the exact tagged SHA counts.
- "Tag now, verify later." The annotated tag is created only on the verified, synchronized main revision.
- "Yesterday's checks still stand." A changed head invalidates prior check evidence; reread checks and protection immediately before merge.

## Red Flags

- A red, absent, or wrong-SHA release CI run before publishing.
- A tag that does not match the merged, synchronized main commit.
- Skipping the published-release read-back or the bumper's check mode.
- Weakened branch protection to force a merge.

## Verification

- All [VERSIONING.md](../../VERSIONING.md) gates passed: version agreement, protected exact-head merge, annotated tag peeled-SHA match, successful exact-SHA release CI.
- The published GitHub Release was read back and its notes, tag, and target SHA verified.
