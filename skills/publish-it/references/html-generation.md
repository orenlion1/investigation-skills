# HTML generation and packaging

Generate HTML is independent of Generate Markdown and Generate PDF. Resolve the saved choices
under the [report format contract](../../open-edit-close-execute/references/investigation-delivery.md#report-formats).
The default is `disabled`: create and attach no standalone HTML, and exclude historical HTML
without deleting it. Confluence page composition and read-back HTML remain required for page
publication regardless of this setting. A setting alone never authorizes external writes.

When `enabled`, generate a portable HTML report from the same canonical investigation content.
An explicit publication request with this saved selection authorizes this format conversion;
it never authorizes refreshed findings, evidence windows or accounting. Existing verified HTML
from that same content may be reused. Do not reuse stale same-name output or overwrite a collision.
An HTML-only input is sufficient; do not require or synthesize a delivered Markdown/PDF companion.
For a PDF-only input without canonical text, inspect and faithfully convert it with suitable
PDF tooling, disclose conversion limitations, and verify the resulting HTML before publication.

## Appearance

Resolve `HTML theme` from the saved task/profile under
[Profile Manager's contract](../../profile-manager/references/profile-store.md#html-theme).
Pass the effective value to the helper with `--theme`; omission retains system-following output.
The fixed modes set the page color scheme and theme-aware picture selection, so a light export
uses light diagrams even in a dark browser, and vice versa. System mode retains media queries.
No JavaScript or browser storage is needed. Fixed mode supports single `prefers-color-scheme`
source conditions; unsupported compound theme conditions fail rather than selecting a guessed image.
Images without theme variants retain their original bytes; inspect their readability in the chosen mode.

Keep existing exports and frozen report source intact. For an explicitly requested additional
variant, resolve a descriptive `light` or `dark` suffix through Workflow Artifact Naming.
Record the theme and input/output hashes in its receipt. Verify fixed modes under both host
preferences, and system mode under each, checking canvas colors, selected pictures and captions.

## Generator

Use Python 3.10+ with [pinned Markdown rendering dependencies](../scripts/requirements.txt),
installed through `python -m pip install -r skills/publish-it/scripts/requirements.txt` in a
compatible user-scoped virtual environment. No PDF runtime is needed for HTML generation.
The helper uses the [markdown-it-py token and rendering API](https://github.com/executablebooks/markdown-it-py/blob/master/docs/using.md).
Resolve the title, slug and `.html` output through Workflow Artifact Naming before running:

```sh
python skills/publish-it/scripts/generate_html.py --title 'Investigation title' --theme light --output /resolved/REPORT-slug-light.html
```

Supply the canonical content on stdin using a structured process input, keeping private content
out of command arguments and shell interpolation. This internal Markdown representation does
not require a `.md` report file. If Markdown is also selected, `--source /resolved/REPORT-slug.md`
reads its saved bytes instead; the HTML must share its directory so relative links stay valid.
With stdin, author relative links for the resolved output directory. Output creation is exclusive;
regeneration writes to a newly resolved staging location, never over an existing artifact.

The renderer preserves tables, fenced code, links, image paths, captions and safe empty evidence
anchors (`<a id="E1"></a>`), figure wrappers and theme-aware `picture`/`source`/`img`
markup. Figure URLs and attributes are allowlisted; scripts, event handlers, inline styles and
unsupported source lists fail before output creation. Headings receive deterministic unique IDs. Raw executable HTML and
unsupported HTML markup fail before output creation; convert unsupported formatting faithfully
and disclose any derivative, rather than silently dropping content. No URLs are fetched and no
remote scripts, fonts or style sheets are added. The JSON receipt records canonical input and
HTML SHA-256 hashes; it is generation evidence, not reference or browser acceptance.

## Validate and publish

Keep linked diagrams and cited local assets in their verified relative layout. This is a portable
HTML-plus-assets package; it is not a promise that one downloaded file embeds every image.
Include dependencies in repository packages. For Confluence, follow the
[HTML-only packaging and theme procedure](confluence-html-only.md), embedding raster figures
in a disclosed portable download and verifying published attachment references. Preserve original
HTML bytes separately. Never rewrite source links to guessed hosted destinations.

Run Report Authoring on the selected HTML, and visually check readability, tables, every diagram
and adjacent caption, internal anchors and external references. If any selected output is missing,
stale or unverified, stop dependent publication writes. Add the HTML, assets and source/hash
receipt to the bounded publication inventory. Verify downloaded HTML hashes for each destination;
repository read-back also checks HTML-relative asset paths. Hosted preview availability stays a
separate result from successful file download. Confluence-native media still needs its own checks.
