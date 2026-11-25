# HTML-only Confluence publication

Use this mode for an authorized Confluence publication when the request selects “HTML only”,
or the saved report settings select HTML and disable Markdown/PDF. This is report-format
selection: the available original parent TASK and cited evidence remain supporting attachments
under the shared provenance rules. An explicit instruction excluding those attachments narrows
that inventory; record the omission instead of claiming the originals were attached.

## Selection and input

Accept an existing verified `.html` report without a Markdown or PDF companion. Use explicit
paths and generation receipts to identify its source revision and theme; do not choose a recent
same-name file. The request may select light, dark or system behavior, overriding the saved
HTML theme for this publication. Reuse the selected export when its hashes and theme match;
generate a missing variant only from available verified canonical content with
[HTML generation](html-generation.md). An HTML-only input is sufficient for packaging. If its
theme cannot be verified or changed faithfully, report that exact limitation; never require a
new Markdown/PDF deliverable as a workaround.

“HTML only” overrides the report upload selection for this publication, even when a task still
has Markdown/PDF generation enabled. Record this explicit selection separately from the frozen
report's historical format metadata. It does not edit profiles, tasks, existing exports, evidence
windows or accounting cutoffs. No Markdown/PDF report is generated, uploaded, previewed or
required by validation; preserve older copies locally. Future defaults change only when requested
through Profile Manager. A persistent HTML-only selection uses its existing fields:

```text
GENERATE_HTML=enabled
GENERATE_MARKDOWN=disabled
GENERATE_PDF=disabled
HTML_THEME=system
```

For example, the skill invocation can be expressed as:

```text
publish it --report docs/reports/REPORT-example.html --parent <Confluence parent URL> HTML only, light mode
```

## Readable page and portable download

Deliver both a readable native Confluence report and a labeled HTML download. Publishing a file
card alone is partial delivery. The source HTML supplies the full findings, tables, evidence,
figures/captions, limitations and accounting. Compose that content using the live Confluence
format guide; replace local image references with native media IDs and owning-page collections,
and local evidence/cross-report links with verified page or selected HTML-attachment targets.
A disabled Markdown/PDF report cannot become an upload dependency through a relative link.

The standalone document's `html`/`head` wrapper, CSS, media queries and data images belong to
the downloaded HTML; do not assume Confluence's HTML-to-native conversion retains them. Native
page content uses supported semantic formatting and the viewer's Confluence theme.
[Atlassian documents independent viewer light/dark choices](https://support.atlassian.com/confluence-cloud/docs/apply-a-theme-to-a-site/).
No site/space/user theme changes, new apps, arbitrary scripts or custom CSS installation are
needed or authorized by this publication mode.

For the HTML download, use the Python standard-library
[attachment packager](../scripts/package_confluence_html.py) after resolving a new derivative
path through Workflow Artifact Naming. It accepts HTML directly and embeds local PNG/JPEG/GIF/WebP
figures and picture sources, preserving the export's light/dark/system behavior and source bytes:

```sh
python3 skills/publish-it/scripts/package_confluence_html.py --source /resolved/REPORT-example.html --output /resolved/REPORT-example-confluence.html --asset-root /verified/report-assets
```

Repeat `--asset-root` for separately authorized roots. Missing, escaping or remote images fail
before output creation; no remote image fetch is attempted. Render other image types through
Diagramming Style before packaging. Keep the original HTML unchanged as provenance. Clearly label
the embedded derivative, retain its input/output/figure hashes, and attach both original and
portable HTML when they differ. Both are HTML report downloads, with distinct roles.

The packager reports remaining local links as explicit mapping work; its successful exit does
not pass publication preflight. Resolve those links using inspected destination/media identities
in a disclosed hosted derivative and rerun reference checks. The shared attachment-only source validator may verify exact local files before upload creates
their hosted targets. Missing source files still block uploads. Unresolved hosted mappings block
page writes until returned attachment identities are verified. Never silently remove links or guess URLs.

## Light/dark behavior on Confluence

The export's `HTML_THEME` controls the HTML download only. Never select native media
from the fixed export's fallback `<img>` or rewritten `<source media="all/not all">`:
that discards the other theme and leaves white graphs on a dark Confluence canvas.

Native automatic switching requires both live guide support and browser proof against
Confluence's own preference (which can differ from the OS preference). The current native
media contract selects one file ID; CSS and `picture` do not provide native switching.
When unsupported, use [the native figure composer](../scripts/confluence_figures.py):
`render_theme_pair(light_attachment, dark_attachment, page_id=verified_page_id)` returns
supported native Dark graph / Light graph tabs with Dark first. Resolve both attachment
identities from the verified inventory, independently of download theme. Retain the complete
caption and evidence immediately after each pair. Tabs are explicit manual choices, not
automatic profile switching. If tabs are unsupported on the host, use two labeled visible
native figures instead; do not hide a theme in a collapsed attachment-only fallback.

Preserve fixed light/dark exports unchanged. Missing native variants require a faithful
palette-only render from verified source or an explicit incomplete result. Attaching a dark
file alone is insufficient: verify it in the main report. Record unsupported automatic
switching as incomplete even when manual theme choices and portable HTML work correctly.

## Verify independently

Apply the shared reference gate to selected source HTML, every downloadable HTML derivative and
the composed/published page, with the same source identity and cutoff. HTML-only preflight passes
HTML artifacts directly to Report Authoring, using its Markdown/HTML requirements file; it does
not import or install PDF tooling. Check all material occurrences, including rewritten local
references, rather than only unique URLs.

Before publication, inspect the selected download locally under light and dark host preferences,
with network access disabled for embedded figures. After publication, read the exact published
page/version back, verify native figures and captions in both viewer themes, and download each
HTML attachment to compare its SHA-256 and reopen it with embedded figures offline. Test required
anchors and evidence destinations separately. An unavailable Confluence preview is a distinct
capability result; never promise that Cloud executes arbitrary HTML attachments inline.
Record page/media ownership, selected formats/theme, original versus derivative hashes,
reference results, native theme behavior, download behavior and any gaps. Reuse the same page
identity on resumption; the surrounding Confluence procedure owns upload and write/read-back.
