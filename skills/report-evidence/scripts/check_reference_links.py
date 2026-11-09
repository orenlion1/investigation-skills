#!/usr/bin/env python3
"""Inventory visible reference occurrences; exit nonzero on incomplete link coverage.

This checks authored links, not network accessibility or browser acceptance. Inputs
and output contain source identities: keep investigation manifests/receipts private.
"""
import argparse
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import sys
from urllib.parse import unquote, urlsplit


SCHEMA = 'reference-links/v1'
IDENTIFIER = re.compile(r'\b(?:[0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}|I[A-Z0-9]{12}|E[1-9][0-9]*)\b')
BLOCKS = {'p', 'div', 'tr', 'li', 'br', 'hr', 'td', 'th'}


def validate_manifest(data):
    if not isinstance(data, dict) or data.get('schema') != SCHEMA or data.get('reviewed') is not True:
        raise ValueError('reference-links/v1 requires an explicitly reviewed source inventory')
    refs = data.get('references')
    if not isinstance(refs, list) or not refs:
        raise ValueError('nonempty references inventory required')
    seen = set()
    for ref in refs:
        if (not isinstance(ref, dict) or not all(isinstance(ref.get(k), str) and ref[k].strip()
                for k in ('id', 'type', 'identity', 'source'))
                or ref['id'] in seen or ref.get('provenance') not in
                ('verified', 'unavailable', 'unverified')):
            raise ValueError('invalid or duplicate reference identity/provenance')
        seen.add(ref['id'])
        labels = ref.get('labels')
        if (not isinstance(labels, list) or not labels or
                not all(isinstance(label, str) and label.strip() == label and label for label in labels)
                or len(set(labels)) != len(labels)):
            raise ValueError('references need unique, nonempty visible labels')
        if ref.get('section') is not None and not isinstance(ref['section'], str):
            raise ValueError('reference section must be a literal heading')
        if ref['provenance'] == 'verified' and not isinstance(ref.get('url'), str):
            raise ValueError('verified provenance requires a source-derived URL')
        if ref.get('url') is not None and not isinstance(ref['url'], str):
            raise ValueError('URL must be a string or null')
    return refs


class VisibleHTML(HTMLParser):
    """Keep a link and a location for every visible character, including split labels."""
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.chars = []
        self.stack = []
        self.section = 'Document'
        self.heading = None
        self.anchors = set()

    def emit(self, value, href=None):
        ignored = any(tag in ('script', 'style', 'pre') for tag, _ in self.stack)
        if ignored:
            return
        if href is None:
            href = next((url for tag, url in reversed(self.stack) if tag == 'a'), None)
        loc = 'line %s' % self.getpos()[0]
        self.chars.extend((char, href, self.section, loc) for char in value)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if attrs.get('id'):
            self.anchors.add(attrs['id'])
        if tag in BLOCKS or re.fullmatch('h[1-6]', tag):
            self.emit('\n')
        if re.fullmatch('h[1-6]', tag):
            self.heading = len(self.chars)
        if attrs.get('data-type') in ('media', 'media-inline'):
            identity = attrs.get('data-id', attrs.get('data-media-id', ''))
            collection = attrs.get('data-collection', attrs.get('data-media-collection', ''))
            self.emit(attrs.get('data-alt', ''), 'media:%s@%s' % (identity, collection))
        if tag not in ('br', 'hr', 'img', 'input', 'meta', 'link', 'source', 'wbr'):
            self.stack.append((tag, attrs.get('href') if tag == 'a' else None))

    def handle_endtag(self, tag):
        if re.fullmatch('h[1-6]', tag) and self.heading is not None:
            title = ''.join(c[0] for c in self.chars[self.heading:]).strip()
            self.section = title or self.section
            self.chars[self.heading:] = [(c, u, self.section, loc)
                                        for c, u, _, loc in self.chars[self.heading:]]
            # Confluence's documented short evidence headings produce same-page anchors.
            if re.fullmatch(r'E[1-9][0-9]*', title):
                self.anchors.add(title)
            self.heading = None
        for index in range(len(self.stack) - 1, -1, -1):
            if self.stack[index][0] == tag:
                del self.stack[index:]
                break
        if tag in BLOCKS or re.fullmatch('h[1-6]', tag):
            self.emit('\n')

    def handle_data(self, value):
        self.emit(value)


def html_document(text):
    parser = VisibleHTML()
    parser.feed(text)
    parser.close()
    return parser.chars, parser.anchors


def pdf_document(path):
    import pymupdf
    chars = []
    with pymupdf.open(path) as doc:
        if doc.needs_pass:
            raise ValueError('encrypted PDF cannot establish coverage')
        for page in doc:
            uris = [(link['from'], link['uri']) for link in page.get_links() if 'uri' in link]
            for block in page.get_text('rawdict', sort=True)['blocks']:
                for line in block.get('lines', []):
                    for span in line['spans']:
                        for char in span['chars']:
                            rect = pymupdf.Rect(char['bbox'])
                            center = (rect.tl + rect.br) / 2
                            targets = {uri for bounds, uri in uris if bounds.contains(center)}
                            href = next(iter(targets)) if len(targets) == 1 else None
                            loc = 'page %s bbox %s' % (page.number + 1, tuple(char['bbox']))
                            chars.append((char['c'], href, 'page %s' % (page.number + 1), loc))
                    chars.append(('\n', None, 'page %s' % (page.number + 1), loc if chars else 'empty'))
            chars.append(('\n', None, 'page %s' % (page.number + 1), 'page end'))
    if not any(c.strip() for c, _, _, _ in chars):
        raise ValueError('PDF has no extractable text; coverage remains unverified')
    return chars, set()


def destination(url):
    """Normalize only Confluence page title suffixes, preserving origin/query/fragment."""
    parsed = urlsplit(url)
    path = parsed.path
    if parsed.hostname and parsed.hostname.endswith('.atlassian.net'):
        match = re.fullmatch(r'(/wiki/spaces/[^/]+/pages/[0-9]+)(?:/[^/]*)?/?', path)
        if match:
            path = match[1]
    return (parsed.scheme.lower(), parsed.netloc.lower(), path, parsed.query,
            unquote(parsed.fragment))


def link_status(ref, href, anchors):
    provenance = ref['provenance']
    if provenance != 'verified':
        return provenance + '-source'
    expected = ref['url']
    if not href:
        return 'missing'
    if expected.startswith('media:'):
        return 'linked' if href == expected and expected.split('@')[-1] else 'wrong-target'
    if href.startswith('#'):
        if unquote(href[1:]) not in anchors:
            return 'broken-fragment'
    elif urlsplit(href).scheme not in ('http', 'https'):
        return 'local-only'
    if not expected.startswith('#') and urlsplit(expected).scheme not in ('http', 'https'):
        return 'unverified-source'
    actual_id, expected_id = destination(href), destination(expected)
    if actual_id == expected_id:
        return 'linked'
    if actual_id[:4] == expected_id[:4]:
        return 'broken-fragment'
    return 'wrong-target'


def inventory(chars, anchors, data, artifact):
    refs = validate_manifest(data)
    text = ''.join(c[0] for c in chars)
    # Whitespace may wrap within a label in PDF/HTML. Retain original locations.
    labels = {label for ref in refs for label in ref['labels']}
    patterns = [re.escape(label).replace(r'\ ', r'\s+') for label in labels]
    pattern = re.compile(r'(?<!\w)(?:' + '|'.join(sorted(patterns, key=len, reverse=True)) + r')(?!\w)')
    matches = list(pattern.finditer(text))
    known_ranges = [(m.start(), m.end()) for m in matches]
    unknown = [m for m in IDENTIFIER.finditer(text)
               if not any(start <= m.start() and m.end() <= end for start, end in known_ranges)]
    rows, found = [], set()
    for match in sorted(matches + unknown, key=lambda m: m.start()):
        label = re.sub(r'\s+', ' ', match.group())
        section, loc = chars[match.start()][2:]
        candidates = [r for r in refs if label in r['labels'] and
                      (not r.get('section') or r['section'] == section)]
        urls = {c[1] for c in chars[match.start():match.end()] if c[0].strip()}
        href = next(iter(urls)) if len(urls) == 1 else None
        ref = candidates[0] if len(candidates) == 1 else None
        found.update(r['id'] for r in candidates)
        status = (link_status(ref, href, anchors) if ref else
                  'ambiguous-reference' if candidates else 'unregistered-reference')
        rows.append({'artifact': str(artifact), 'section': section, 'locator': loc,
                     'occurrence': len(rows) + 1, 'reference': ref['id'] if ref else None,
                     'type': ref['type'] if ref else 'unregistered', 'text': match.group(),
                     'identity': ref['identity'] if ref else None,
                     'source': ref['source'] if ref else None,
                     'expected': ref.get('url') if ref else None, 'actual': href,
                     'status': status})
    for ref in refs:
        if ref['id'] not in found:
            rows.append({'artifact': str(artifact), 'section': ref.get('section', 'Document'),
                         'locator': 'not found', 'occurrence': None, 'reference': ref['id'],
                         'type': ref['type'], 'text': None, 'identity': ref['identity'],
                         'source': ref['source'], 'expected': ref.get('url'), 'actual': None,
                         'status': 'reference-absent'})
    return rows


def audit_text(text, fmt, data, artifact):
    if fmt == 'markdown':
        from markdown_it import MarkdownIt
        markdown = MarkdownIt('commonmark').enable('table')
        # Parse unsafe schemes too so they fail as local/unsupported destinations,
        # rather than disappearing from the audit. Nothing here opens a URL.
        markdown.validateLink = lambda url: True
        text = markdown.render(text)
    elif fmt != 'html':
        raise ValueError('unsupported text format')
    chars, anchors = html_document(text)
    return inventory(chars, anchors, data, artifact)


def audit_file(path, data):
    path = Path(path)
    if path.suffix.lower() == '.pdf':
        return inventory(*pdf_document(path), data, path.name)
    formats = {'.md': 'markdown', '.html': 'html', '.htm': 'html'}
    if path.suffix.lower() not in formats:
        raise ValueError('supported artifacts are Markdown, HTML and PDF')
    return audit_text(path.read_text(encoding='utf-8'), formats[path.suffix.lower()], data, path.name)


def build_receipt(paths, data):
    rows, artifacts = [], []
    for path in map(Path, paths):
        before = path.read_bytes()
        current = audit_file(path, data)
        if path.read_bytes() != before:
            raise ValueError('artifact changed during validation')
        rows.extend(current)
        artifacts.append({'name': path.name, 'sha256': hashlib.sha256(before).hexdigest()})
    if not artifacts or len({a['name'] for a in artifacts}) != len(artifacts):
        raise ValueError('require artifacts with unique filenames')
    counts = {}
    for artifact in artifacts:
        counts[artifact['name']] = {ref['id']: sum(
            row['reference'] == ref['id'] and row['occurrence'] is not None
            for row in rows if row['artifact'] == artifact['name'])
            for ref in data['references']}
    if len({json.dumps(value, sort_keys=True) for value in counts.values()}) != 1:
        rows.append({'artifact': 'cross-format', 'section': 'Document', 'locator': 'inventory',
                     'occurrence': None, 'reference': None, 'type': 'coverage', 'text': None,
                     'identity': None, 'source': None, 'expected': None, 'actual': None,
                     'status': 'occurrence-count-mismatch'})
    return {'schema': 'reference-link-coverage/v1', 'artifacts': artifacts,
            'manifest_sha256': hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest(),
            'occurrences': sum(r['occurrence'] is not None for r in rows),
            'unique_destinations': len({r['expected'] for r in rows if r['expected']}),
            'unresolved': sum(r['status'] != 'linked' for r in rows), 'rows': rows,
            'verification': 'authored links only; destination navigation and browser acceptance separate'}


def verify_freshness(receipt, paths):
    observed = {Path(path).name: hashlib.sha256(Path(path).read_bytes()).hexdigest()
                for path in paths}
    expected = {entry['name']: entry['sha256'] for entry in receipt['artifacts']}
    if observed != expected or receipt['unresolved']:
        raise ValueError('stale or incomplete artifact coverage receipt')


def require_complete(paths, data):
    receipt = build_receipt(paths, data)
    if receipt['unresolved']:
        raise ValueError('%s unresolved reference occurrences' % receipt['unresolved'])
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--artifact', action='append', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True,
                        help='private coverage receipt; overwrite only the selected owned receipt')
    args = parser.parse_args()
    inputs = [args.manifest, *args.artifact]
    if args.output.is_symlink() or args.output.resolve() in {path.resolve() for path in inputs}:
        print('Coverage output must be a separate owned regular file.', file=sys.stderr)
        return 2
    try:
        receipt = build_receipt(args.artifact, json.loads(args.manifest.read_text()))
        args.output.write_text(json.dumps(receipt, indent=2) + '\n')
        print('%s occurrences, %s destinations, %s unresolved; authored-link coverage only' %
              (receipt['occurrences'], receipt['unique_destinations'], receipt['unresolved']))
        return int(bool(receipt['unresolved']))
    except (ValueError, OSError, ImportError, KeyError) as error:
        # Invalidate a prior receipt at this caller-selected output on extraction failure.
        try:
            args.output.write_text(json.dumps({'schema': 'reference-link-coverage/v1',
                                              'status': 'unavailable', 'unresolved': None}) + '\n')
        except OSError:
            pass
        # No raw source values or URLs in console diagnostics.
        print('Reference validation unavailable (%s); no passing receipt established.' %
              type(error).__name__, file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
