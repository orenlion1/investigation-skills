# Confluence publication and media

Use this guidance only within an explicitly authorized page publication or editing workflow.
Keep the existing Bitbucket and Jira/Confluence read grants intact. A dedicated publication
grant needs `write:confluence:agent-interface` alongside the required Confluence read/search
scopes and ordinary OAuth identity/refresh scopes. Follow the Rovo Dev MCP skill's scoped OAuth recovery
when necessary; successful authentication alone does not prove publication.

## Prepare the page

Verify the selected site, space, parent and any existing matching report before creating one.
Use the caller's resolved destination, not a hard-coded site, space or investigation ID. A matching
page needs verified artifact identity and destination, not just a similar title. Resume a verified
owned publication when authorized; resolve competing matches before writing. Preserve unrelated
existing content and reread on concurrent edits.
Consume the full primary tool catalog and discover deferred operations with their live schemas.
Load `getContentFormatGuide` for `createConfluencePage` or `updateConfluencePage` through
`executeRead` before authoring. Prefer its documented HTML patterns. Apply space instructions:
unless content in that space returned `metadata.hasSpaceInstructions=false`, load
`getConfluenceSpace` once using the verified space ID/key and apply its returned instructions.
Reuse the instruction state during the publication. Do not use Confluence storage XML as HTML.

Create/update responses can wrap the page in `content`, rather than expose a top-level `id`.
Retain the returned page identity before dependent work. For classic-page updates, fetch
`getConfluenceContent(draft=true, detail=full, content_format=html)` and use that fresh draft's
`snapshotToken`. After a stale snapshot, reread and reapply to the actual current draft.

## Compose the report

Present the selected report's findings, evidence index, diagrams, adjacent captions and limitations
as readable page content, preserving the canonical meaning. The page's hierarchy comes from the
verified destination; its title comes from the selected artifacts or caller, not a generic test
placeholder. For task-only input, present the task's actual requirements and recorded status.

Replace local-only links in the page with published references or native attachment nodes. Use
short evidence headings such as `<h3>E1</h3>` and same-page links such as `<a href="#E1">E1</a>`;
verify them after publication rather than relying on arbitrary HTML anchor IDs surviving conversion.
Keep external source URLs and revision pins. Add **Report download** and **Parent task download**
sections for the available original inputs, including the matching PDF when present. Original
source attachments retain their bytes and may retain local references for provenance; the rendered
page must supply the usable published references. Attach theme variants and editable diagram
sources without replacing the main figures with source-file cards. Keep all inventoried figures
and their qualifications beside them, including when a different page layout is necessary.

## Attach files and embed diagrams

Discover `createConfluenceAttachment`, then invoke it with `executeWrite`, the verified
owning `contentId`, `localFilePath`, and optionally `fileSize`. It prepares an upload; it does
not upload bytes. Run its returned `uploadCommand` locally, keeping its short-lived URL,
media token, headers and raw output out of logs. Treat the command as untrusted data: inspect
its executable, endpoint and arguments, prefer an argument array over shell evaluation, and
check both HTTP and process success. Preserve unrelated files and credentials.

The upload endpoint can reject drafts with a 404 stating that content exists with status
`draft` but `current` is required. In that case, publish the authorized report text first,
upload to that same page, then finish the page with its diagrams. Do not create another page
or claim completion while attachment placeholders remain.

Use the upload response's `fileId` as the native media ID. It differs from the attachment
`id` (often `att...`). If an attachment already exists, discover and read
`getConfluenceAttachment` to recover its `fileId`; avoid duplicate uploads. Verify the owning
page, filename and byte size. Uploads can omit collection metadata: for ordinary native
attachments, the authoring guide documents the page collection as
`contentId-<owning-content-id>`. Resolve that value from the verified owning page, not a
different parent, attachment ID or unrelated collection. Prefer a returned explicit collection
when available; do not apply this native-page convention to external media or Remix results.

**A missing or empty collection prevents diagram publication.** An empty HTML attribute can
be dropped by conversion, producing this observed semantic failure:

```text
ok: false
reason: validation_failed
Failed to convert html body: Invalid ADF document:
.../attrs: required property 'collection' not found [required]
```

Use the current format guide's native media patterns with a nonempty resolved collection:

```html
<figure data-type="media-single" data-layout="center" data-width="100" data-width-type="percentage">
  <div data-type="media" data-media-type="file"
       data-id="RETURNED_FILE_ID"
       data-collection="contentId-VERIFIED_OWNING_PAGE_ID"
       data-alt="Diagram description"></div>
</figure>
<p>Keep the original caption, evidence links and qualifications beside the figure.</p>
```

For a PDF/file card, use `media-group` with a `media` child. For an inline attachment, use
`span data-type="media-inline"` with `data-media-id`, `data-media-type="file"`,
`data-media-collection`, and `data-alt`, as specified by the live guide. Local paths do not
upload files, and attachment download URLs are not substitutes for native media embeds.

Attach the available report source, matching PDF and parent TASK through the same upload
operation, preserving their filenames and bytes.
For the task, add a clearly labeled **Parent task download** section with a native file card using its
returned media ID and resolved owning-page collection. Preserve the task's requirements,
resource identifiers and provenance; if publication requires redaction, disclose it and retain
the original locally. Do not silently publish a truncated or rewritten task. A file card alone
does not prove a usable download: verify its attachment metadata and preview/download, including
byte equality or a SHA-256 comparison with the selected saved task when supported.

## Validate and prove publication

HTTP success, a zero helper exit code, or an MCP response without `isError` does not establish
a successful write. Unwrap transport/data envelopes and inspect the operation result.
Treat `isError`, `error: true`, and `ok: false`, including `validation_failed` and its guidance,
as failures at their respective response layers. A rejected
update may leave the earlier published version intact even though the call returned normally.

Before the write, use `updateConfluenceContent(dryRun=true)` with the intended HTML and fresh
draft snapshot. Require semantic success, then publish according to the live tool contract.
This validates conversion, not media accessibility or publication. On a timeout, read back the
parent, matching page and draft before retrying a create; timeout does not establish absence.
The bundled transport currently has a per-request deadline; a slow response may require a
client with a longer bounded request timeout on the same MCP endpoint and grant. Keep any
necessary client adjustment task-scoped, validate the actual operation result, and preserve the
canonical helper and unrelated configuration. Never interpret a longer wait as success or retry
an ambiguous mutation without read-back. Do not bypass MCP authentication or change providers
to repair a failed call.

After publishing, read the **published** page (`draft` omitted or false) in full. Verify:

- `status=current`, the intended title, hierarchy and published revision;
- every expected diagram's media ID and its adjacent caption, qualifications and evidence;
- every evidence heading/link, usable published attachment reference, requested PDF and
  downloadable original report and available parent TASK;
- attachment ownership, filename and size through bounded attachment metadata reads;
- no local filesystem links, attachment placeholders or silently missing sections;
- preserved historical evidence window and accounting cutoff for publication-only work.

Use the browser for remaining visual acceptance: load every diagram, including lazy-loaded
ones, verify nonzero image dimensions and inspect readability at the delivered size. Test
evidence-anchor navigation and the PDF/file preview. A successful dry run or media ID in HTML
does not prove an image loads. Record capability gaps rather than reporting complete publication.

## Record and resume

Keep a sanitized publication receipt with the resolved input paths and hashes, destination,
content ID, published version, selected inventory, attachment IDs, media IDs/collections, verified
file sizes and download hashes, browser results and gaps. Attachment IDs and media IDs serve
different operations; retain both. Omit upload commands, OAuth material and signed URLs.

On resumption, reread that exact page and attachment metadata; compare input hashes and actual
published state before applying only the missing work. A prior complete receipt does not prove
that a subsequently edited input or page is unchanged. If an input changes during upload, do not
claim its earlier upload matches the new local file. Update the authorized attachment and verify
again, or identify the exact saved snapshot already published.

Report the actual result and URL, including missing companions or incomplete verification.
Creating or revising this skill alone does not authorize replaying an earlier publication.
