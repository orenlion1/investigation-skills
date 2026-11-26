# HTML publication packaging

Resolve saved format choices and theme settings through
[Profile Manager](../../profile-manager/references/profile-store.md#report-formats) and the
[delivery contract](../../investigation-delivery/references/delivery-contract.md#report-formats).
Publication-specific selections follow [HTML-only Confluence](confluence-html-only.md).
Do not copy setting defaults here. A setting alone never authorizes external writes.

When standalone HTML is disabled, create and attach none, and exclude historical HTML
without deleting it. Confluence page composition and read-back HTML remain required for
page publication regardless of that setting.

Reuse selected verified HTML from the frozen canonical content. If an authorized publication
needs a missing derivative, invoke [Investigation Delivery's HTML generator](../../investigation-delivery/references/html-generation.md);
publication does not own or duplicate the rendering procedure. Conversion never refreshes
findings, evidence windows or accounting. Do not require Markdown/PDF companions for HTML-only
input, reuse stale same-name output, or overwrite collisions.

## Package and verify each destination

Keep the verified relative asset layout in repository packages. For Confluence, follow the
[HTML-only packaging and theme procedure](confluence-html-only.md), embedding raster figures
in a disclosed portable download and verifying published attachment references. Preserve
original HTML bytes separately. Never rewrite source links to guessed hosted destinations.

Run Report Authoring on the selected source and derivatives. If any selected output is missing,
stale or unverified, stop dependent publication writes. Add the HTML, assets and source/hash
receipt to the bounded publication inventory. Verify downloaded HTML hashes for each destination;
repository read-back also checks HTML-relative asset paths. Hosted preview availability stays a
separate result from successful file download. Confluence-native media still needs its own checks.
