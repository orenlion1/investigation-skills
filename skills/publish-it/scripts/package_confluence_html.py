#!/usr/bin/env python3
"""Package verified HTML with embedded raster figures for Confluence download.

This prepares a local attachment; it does not upload or compose native Confluence media.
"""
import argparse
import base64
import hashlib
from html import escape
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import sys
from urllib.parse import unquote, urlsplit


MAX_IMAGE_BYTES = 20 * 1024 * 1024
# Deliberately limited to semantic report markup and embedded raster pictures.
REPORT_TAGS = set(('html head meta title style body main h1 h2 h3 h4 h5 h6 p a '
                   'strong em s del code pre blockquote ul ol li table thead tbody '
                   'tr th td div picture source img br hr').split())
GLOBAL_ATTRIBUTES = {'id', 'class', 'title', 'lang'}
TAG_ATTRIBUTES = {
    'html': {'data-theme'}, 'meta': {'charset', 'name', 'content'},
    'a': {'href', 'name'}, 'ol': {'start'},
    'th': {'style', 'colspan', 'rowspan'}, 'td': {'style', 'colspan', 'rowspan'},
    'img': {'src', 'alt', 'width', 'height', 'loading'},
    'source': {'media', 'srcset', 'type'},
}


def image_type(data):
    for magic, mime in ((b'\x89PNG\r\n\x1a\n', 'image/png'), (b'\xff\xd8\xff', 'image/jpeg'),
                        (b'GIF87a', 'image/gif'), (b'GIF89a', 'image/gif')):
        if data.startswith(magic):
            return mime
    if data.startswith(b'RIFF') and data[8:12] == b'WEBP':
        return 'image/webp'
    raise ValueError('figure must be PNG, JPEG, GIF or WebP; render other formats first')


class PackageHTML(HTMLParser):
    def __init__(self, source, roots):
        super().__init__(convert_charrefs=False)
        self.source, self.roots = source, roots
        self.parts, self.images, self.local_links = [], {}, []
        self.theme, self.in_style = None, False

    def embed(self, value):
        if value.startswith('data:'):
            match = re.fullmatch(r'data:(image/(?:png|jpeg|gif|webp));base64,([A-Za-z0-9+/=]+)', value)
            if not match or len(value) > MAX_IMAGE_BYTES * 2:
                raise ValueError('unsupported embedded figure')
            data = base64.b64decode(match[2], validate=True)
            if image_type(data) != match[1] or len(data) > MAX_IMAGE_BYTES:
                raise ValueError('invalid embedded figure')
            return value
        url = urlsplit(value)
        if url.scheme or url.netloc or url.query or url.fragment:
            raise ValueError('figure must name an approved local file; remote images are not fetched')
        path = (self.source.parent / unquote(url.path)).resolve(strict=True)
        if not any(path.is_relative_to(root) for root in self.roots):
            raise ValueError('figure escapes approved asset roots')
        if not path.is_file() or path.stat().st_size > MAX_IMAGE_BYTES:
            raise ValueError('figure is not a bounded regular file')
        data = path.read_bytes()
        mime = image_type(data)
        self.images[value] = {'sha256': hashlib.sha256(data).hexdigest(), 'bytes': len(data), 'mime': mime}
        return 'data:' + mime + ';base64,' + base64.b64encode(data).decode('ascii')

    def handle_starttag(self, tag, attrs):
        if tag not in REPORT_TAGS:
            raise ValueError('active HTML and external styles are unsupported')
        if len({key for key, _ in attrs}) != len(attrs):
            raise ValueError('duplicate HTML attributes')
        values = dict(attrs)
        if set(values) - GLOBAL_ATTRIBUTES - TAG_ATTRIBUTES.get(tag, set()):
            raise ValueError('unsupported report HTML attribute')
        if any(key.startswith('on') or key == 'http-equiv' for key in values):
            raise ValueError('active HTML attributes are unsupported')
        if 'style' in values and not (tag in ('th', 'td') and re.fullmatch(
                r'text-align:\s*(?:left|right|center|start|end);?', values['style'], re.I)):
            raise ValueError('only table-cell text alignment is supported in inline styles')
        if tag == 'html':
            self.theme = values.get('data-theme')
        if tag == 'style':
            self.in_style = True
        for key in ('href', 'src'):
            if key in values and not (tag == 'img' and key == 'src'):
                value = values[key] or ''
                if (any(ord(c) < 32 for c in value)
                        or urlsplit(value).scheme.lower() not in ('', 'http', 'https', 'mailto')):
                    raise ValueError('unsupported URL scheme')
        if tag == 'a' and values.get('href'):
            target = urlsplit(values['href'])
            if not target.scheme and not target.netloc and target.path:
                self.local_links.append(values['href'])
        key = 'src' if tag == 'img' else 'srcset' if tag == 'source' else None
        if key:
            if not values.get(key):
                raise ValueError('figure is missing its image URL')
            values[key] = self.embed(values[key])
            self.parts.append('<' + tag + ''.join(' ' + name + ('="' + escape(value, quote=True) + '"'
                               if value is not None else '') for name, value in values.items()) + '>')
        else:
            self.parts.append(self.get_starttag_text())

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in ('img', 'source', 'br', 'hr', 'meta'):
            self.handle_endtag(tag)

    def handle_endtag(self, tag):
        if tag not in REPORT_TAGS:
            raise ValueError('unsupported report HTML closing element')
        if tag == 'style':
            self.in_style = False
        self.parts.append('</' + tag + '>')

    def handle_data(self, data):
        if self.in_style and re.search(r'@import|url\s*\(|\\|/\*', data, re.I):
            raise ValueError('external CSS resources are unsupported')
        self.parts.append(data)

    def handle_entityref(self, name):
        self.parts.append('&' + name + ';')

    def handle_charref(self, name):
        self.parts.append('&#' + name + ';')

    def handle_decl(self, decl):
        if decl.lower() != 'doctype html':
            raise ValueError('unsupported HTML declaration')
        self.parts.append('<!' + decl + '>')

    def handle_comment(self, data):
        self.parts.append('<!--' + data + '-->')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--asset-root', type=Path, action='append', required=True)
    args = parser.parse_args()
    try:
        if args.source.is_symlink() or not args.source.is_file():
            raise ValueError('source must be a regular non-symlink HTML file')
        if args.source.suffix.lower() != '.html' or args.output.suffix.lower() != '.html':
            raise ValueError('source and output must use .html')
        roots = [root.resolve(strict=True) for root in args.asset_root]
        if not all(root.is_dir() for root in roots):
            raise ValueError('asset roots must be directories')
        source = args.source.read_bytes()
        package = PackageHTML(args.source.resolve(), roots)
        package.feed(source.decode('utf-8'))
        package.close()
        if package.theme not in ('light', 'dark', 'system'):
            raise ValueError('HTML theme metadata is required; verify or generate the selected export first')
        result = ''.join(package.parts).encode('utf-8')
        with args.output.open('xb') as handle:
            handle.write(result)
        print(json.dumps({'source': str(args.source), 'output': str(args.output), 'theme': package.theme,
                          'source_sha256': hashlib.sha256(source).hexdigest(),
                          'html_sha256': hashlib.sha256(args.output.read_bytes()).hexdigest(),
                          'embedded_images': package.images,
                          'local_links_requiring_publication_mapping': sorted(set(package.local_links))}))
    except (OSError, UnicodeError, ValueError) as error:
        print('error: ' + str(error), file=sys.stderr)
        return 2
    return 0


if __name__ == '__main__':
    sys.exit(main())
