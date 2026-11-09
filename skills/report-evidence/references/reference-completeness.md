# Material reference completeness

This contract belongs to Report Evidence and is reused by Publish It. It checks required
relationships that existing-link validation cannot see. It does not rerun an investigation,
change evidence windows, revise incident causality or refresh historical token cutoffs.

## Build and review the source inventory

Read the entire selected report, including reconciliation prose, tables, evidence-index entries
and captions. Record every material incident, historical investigation, backing chat, conversation,
Slack reply and cross-report evidence identity; enumerate every visible label/alias. Resolve the
expected URL from inspected source evidence and retain its object/version/query scope. Keep an
investigation identity distinct from its backing chat; label a backing-chat destination explicitly.
Do not fabricate object paths or fragments when provenance is missing or inaccessible.

Create a private manifest under caller-resolved workflow asset paths. Minimal example:

```json
{
  "schema": "reference-links/v1",
  "reviewed": true,
  "references": [
    {
      "id": "prior-cleanup-evidence",
      "type": "cross-report-evidence",
      "identity": "page 123 evidence E4",
      "labels": ["cleanup OOM evidence", "E4"],
      "section": "Historical reconciliation",
      "url": "https://example.atlassian.net/wiki/spaces/TEST/pages/123#E4",
      "provenance": "verified",
      "source": "inspected page 123 version 2, heading E4; retained source record"
    }
  ]
}
```

`section` is optional and literal: use it to disambiguate identical E labels in different sections.
Never globally map E4 across unrelated reports. For a short contextual alias in addition to global
labels, use `scoped_labels: [{"label": "conversation", "section": "Historical reconciliation"}]`.
This keeps an unrelated phrase such as "conversation usage" outside that object's population.
Use the longest complete visible identity phrase so a name and its adjacent ID count as one
occurrence rather than two overlapping references. The helper recognizes native E headings and the report convention `E13 - …` (including bold
Markdown evidence entries) as logical evidence sections across text and PDF. Other PDF locations
use `page N`, so a scoped HTML/Markdown
inventory may require a separately reviewed PDF manifest retaining the same canonical reference IDs
and destinations. Reconcile those per-format occurrence inventories explicitly; do not substitute
unique-URL membership for occurrence parity. Do not weaken scope to hide unresolved references.

`provenance` is `verified`, `unavailable` or `unverified`. The source field names the actual retained
provenance; a string or boolean in a manifest cannot independently establish that it was inspected.
Set `reviewed: true` only after comparing the registry with the complete visible source. The helper
finds all registered labels and flags unregistered UUIDs, alert-group IDs and E identifiers. Other
semantic references and aliases require human/agent source review: this detector is conservative,
not an exhaustive natural-language classifier. Register and resolve its candidates; do not dismiss
an unresolved candidate as nonmaterial without recording the exact occurrence and reason.

Report-owned declaration headings, quoted source/code and native internal PDF destinations require
separate review when outside the helper's supported URI-reference extraction. Unsupported results
remain incomplete. Never label an unverified extraction path as passed, or claim that scanning only
the registry establishes whole-report reference completeness.

## Run before delivery and before publication writes

Use Python 3.10+ in an isolated environment. Install only the pinned requirements from this complete
skill folder; reuse a compatible environment when present. Markdown parsing uses markdown-it-py
(MIT); PDF text/URI geometry uses PyMuPDF (AGPL-3.0 or its commercial license). These dependencies
retain their licenses and are not relicensed under this repository's MIT license. No npm package
or host installer is required. Repository test and tagged-release CI install the same requirements.

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r skills/report-evidence/scripts/requirements.txt
.venv/bin/python skills/report-evidence/scripts/check_reference_links.py --manifest references.json --artifact report.md --artifact report.pdf --artifact report.html --output coverage.json
```

Resolve actual private manifest/receipt paths through Workflow Artifact Naming before writing.
Example filenames above are command arguments, not defaults that override repository configuration.
Never put real investigation manifests, reports or receipts in public source commits.

The helper parses visible Markdown (including reference-style links and tables), HTML anchors and
native media labels, and PDF character positions with URI annotations. It requires the complete
visible label to have one destination; a URL in another paragraph or elsewhere on the PDF page
cannot cover an unlinked occurrence. PDF rows include page and character geometry. HTML/Markdown
rows retain a section, rendered line location and occurrence sequence; they do not claim original
Markdown source-line equivalence. Preformatted source blocks are not treated as narrative references.

Exit codes: `0` means all extracted registered occurrences matched; `1` means unresolved coverage;
`2` means configuration/extraction was unavailable. A passing receipt alone never proves that the
registry was complete, a URL was reachable, or an external anchor landed successfully. All three
checks are required separately. Never continue publication after a nonzero preflight.

Keep the JSON receipt: artifact names/hashes, manifest hash, reference type/text/source identity,
section, locator, occurrence sequence, expected and actual link, status and exact unresolved count.
`linked` means authored destination match only. Other statuses distinguish missing links, wrong
targets, broken fragments, local-only links, unregistered/ambiguous references, unavailable/unverified
sources, absent registered references and cross-format occurrence-count mismatch. Count occurrences
and unique expected destinations separately. Use receipts only for their exact input hashes; rerun
after any source, companion, manifest or composed-page change. `verify_freshness` is available to
callers that consume a prior receipt; stale or unresolved receipts fail.

For Confluence, only a title-path suffix normalization preserving the origin, space/page ID, query
and fragment is accepted. An altered page ID or removed/changed evidence fragment fails. External
fragment existence still requires the source read and browser acceptance; equality of two authored
URLs does not establish a working destination.

## Publication and read-back

Require source-reference completeness before the first external write, even when attachments,
hashes and all existing URLs pass other checks. For native-media slots whose IDs depend on upload,
retain the separate packaging dependency and rerun the complete composed-page check after the
verified IDs/collections are known. Native media uses the actual file ID and nonempty owning
collection, not an attachment ID guessed to be a file ID. For an inventoried native download label,
use its source-derived representation `media:FILE_ID@COLLECTION`; verify ownership and metadata
through the publication procedure as well. Missing labels or collections are incomplete.

Read back published HTML from the exact same page identity and published version, run the occurrence
check again and reconcile canonical identities/fragments and counts with the preflight. Verify every
native figure/file with its adjacent caption and evidence links. Download the selected original
Markdown and refreshed PDF, verify SHA-256 equality and prove they derive from the same saved source;
a pair of unrelated current hashes cannot establish freshness. Record generation provenance and
retain old cutoffs. Reject stale companions or local-only page links.

Use the supported browser to open each required object, land on evidence anchors, load native media
and preview the files. A tool launch, HTML href, media ID or successful upload is not visual acceptance.
Record authentication/capability failures and exact unfinished checks without calling them passing.
Publication-only work cannot repair such a gap by silently rerunning the historical investigation.

## Retained regressions and diagnosis

Tests must cover a linked and unlinked occurrence sharing one target, wrong targets, broken fragments,
native attachments, unavailable provenance, allowed Confluence title normalization, actual PDF URI
annotations and stale receipt detection. Include the bounded 12-target historical population:
2 Grafana history destinations, 3 prior alert groups, 6 external evidence anchors and 1 Slack reply.
Use sanitized identities in public fixtures; preserve authentic pre-fix evidence privately.

Derive historical omission counts from retained pre-fix artifacts, not the number of corrected targets.
Record a newly introduced target separately from an occurrence that was already linked elsewhere.
Separate demonstrated assembly omissions, traced workflow/code causes and remaining hypotheses;
state precisely which artifacts, versions and reference population were audited and what remains
unexamined. A missing-reference gate added here is not proof that all historical publication paths
have been audited or that every existing report is repaired.
