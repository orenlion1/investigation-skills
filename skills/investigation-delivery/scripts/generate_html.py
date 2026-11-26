#!/usr/bin/env python3
"""Render report content to HTML without requiring a delivered Markdown artifact."""
import argparse
import hashlib
from html import escape
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import sys
from urllib.parse import urlsplit

from markdown_it import MarkdownIt


ANCHOR = re.compile(r'<a\s+(?:id|name)=[\"\']([\w.:-]+)[\"\']\s*>', re.I)
EMPTY_ANCHOR = re.compile(r'<a\s+(?:id|name)=[\"\']([\w.:-]+)[\"\']\s*>\s*</a>', re.I)
HTML_THEMES = ('light', 'dark', 'system')
DARK_STYLE = 'body {color: #eaecf0; background: #101828} a {color: #84caff} pre {background: #1d2939}'
STYLE = '''body {font: 1rem/1.6 system-ui, sans-serif; color: #182230;
background: #fff; max-width: 72rem; margin: auto; padding: 2rem; overflow-wrap: anywhere}
a {color: #165caa} img {max-width: 100%; height: auto}
pre {overflow: auto; padding: 1rem; background: #f2f4f7}
table {border-collapse: collapse; display: block; overflow-x: auto}
th, td {border: 1px solid #98a2b3; padding: .5rem; text-align: left}
blockquote {border-left: .25rem solid #98a2b3; margin-left: 0; padding-left: 1rem}
'''
PRINT_STYLE = '@media print {body {max-width: none; padding: 0; color: #182230; background: #fff} pre {white-space: pre-wrap}}'


class FigureHTML(HTMLParser):
    """Allow theme-aware report figures without accepting active HTML or CSS."""
    ATTRIBUTES = {'div': {'class'}, 'picture': set(),
                  'source': {'media', 'srcset', 'type'},
                  'img': {'src', 'alt', 'width', 'height', 'loading'}}
    VOID = {'source', 'img'}

    def __init__(self, theme="system"):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self.theme = theme

    def handle_starttag(self, tag, attrs):
        if tag not in self.ATTRIBUTES:
            raise ValueError('unsupported raw HTML element')
        seen = set()
        for name, value in attrs:
            if name not in self.ATTRIBUTES[tag] or name in seen or value is None:
                raise ValueError('unsupported or duplicate figure attribute')
            seen.add(name)
            if name in ('src', 'srcset'):
                # A theme source selects one URL; descriptors/lists require separate support.
                if (not value or any(c.isspace() or ord(c) < 32 or ord(c) == 127 for c in value)
                        or urlsplit(value).scheme.lower() not in ('', 'https', 'http')
                        or '\\' in value or ',' in value):
                    raise ValueError('unsupported figure URL')
            if name in ('width', 'height') and not re.fullmatch(r'[1-9][0-9]*', value):
                raise ValueError('figure dimensions must be positive integers')
            if name == 'loading' and value not in ('lazy', 'eager'):
                raise ValueError('unsupported image loading policy')
            if name == 'class' and not re.fullmatch(r'[\w -]+', value):
                raise ValueError('unsupported figure class')
        if tag == 'source' and self.theme != 'system':
            rewritten = []
            for key, value in attrs:
                if key == 'media' and 'prefers-color-scheme' in value.lower():
                    match = re.fullmatch(r'\(prefers-color-scheme:\s*(light|dark)\)', value, re.I)
                    if not match:
                        raise ValueError('fixed themes require a single color-scheme source condition')
                    value = 'all' if match[1].lower() == self.theme else 'not all'
                rewritten.append((key, value))
            attrs = rewritten
        self.parts.append('<' + tag + ''.join(' ' + key + '="' + escape(value, quote=True) + '"'
                                            for key, value in attrs) + '>')

    def handle_endtag(self, tag):
        if tag not in self.ATTRIBUTES or tag in self.VOID:
            raise ValueError('unsupported raw HTML closing element')
        self.parts.append('</' + tag + '>')

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in self.VOID:
            self.handle_endtag(tag)

    def handle_data(self, data):
        self.parts.append(escape(data))

    def handle_decl(self, decl):
        raise ValueError('raw HTML declarations are unsupported')


def render(content, title, theme="system"):
    """Keep authored links and safe evidence anchors; reject unsupported raw HTML."""
    if theme not in HTML_THEMES:
        raise ValueError('unsupported HTML theme')
    parser = MarkdownIt('commonmark', {'html': True}).enable(['table', 'strikethrough'])
    anchors = set()

    def raw_html(tokens, index, options, env):
        raw = tokens[index].content.strip()
        match = EMPTY_ANCHOR.fullmatch(raw) or ANCHOR.fullmatch(raw)
        if match:
            identity = match[1]
            if identity in anchors:
                raise ValueError('duplicate explicit HTML anchor')
            anchors.add(identity)
            return '<a id="' + escape(identity, quote=True) + '"></a>'
        if raw.lower() == '</a>':
            return ''
        if raw.startswith('<!--') and raw.endswith('-->'):
            return ''
        if raw.lower() in ('<br>', '<br/>', '<br />', '<hr>', '<hr/>', '<hr />'):
            return raw.lower()
        figure = FigureHTML(theme)
        figure.feed(raw)
        figure.close()
        return ''.join(figure.parts)

    parser.renderer.rules['html_inline'] = raw_html
    parser.renderer.rules['html_block'] = raw_html
    tokens = parser.parse(content)
    # Validate raw HTML and reserve explicit IDs before assigning heading IDs.
    for token in tokens:
        for child in [token] + (token.children or []):
            if child.type in ('html_inline', 'html_block'):
                child.meta['safe_html'] = raw_html([child], 0, {}, {})
    parser.renderer.rules['html_inline'] = lambda ts, i, opts, env: ts[i].meta['safe_html']
    parser.renderer.rules['html_block'] = parser.renderer.rules['html_inline']
    for index, token in enumerate(tokens):
        if token.type == 'heading_open':
            children = tokens[index + 1].children or []
            label = ''.join(child.content for child in children
                            if child.type in ('text', 'code_inline', 'image'))
            slug = re.sub(r'[^\w\- ]', '', label.lower()).replace(' ', '-') or 'section'
            identity, suffix = slug, 0
            while identity in anchors:
                suffix += 1
                identity = slug + '-' + str(suffix)
            anchors.add(identity)
            token.attrSet('id', identity)
    body = parser.renderer.render(tokens, parser.options, {})
    style = STYLE
    if theme == 'dark':
        style += DARK_STYLE
    elif theme == 'system':
        style += '@media (prefers-color-scheme: dark) {' + DARK_STYLE + '}'
    style += PRINT_STYLE
    scheme = 'light dark' if theme == 'system' else theme
    return ('<!doctype html>\n<html lang="en" data-theme="' + theme + '"><head><meta charset="utf-8">\n'
            '<meta name="color-scheme" content="' + scheme + '">\n'
            '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
            '<title>' + escape(title) + '</title>\n<style>' + style + '</style>\n'
            '</head><body><main>\n' + body + '</main></body></html>\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, help='Optional saved Markdown input; otherwise read stdin')
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--title', required=True)
    parser.add_argument('--theme', choices=HTML_THEMES, default='system')
    args = parser.parse_args()
    try:
        if args.output.suffix.lower() != '.html':
            raise ValueError('output must have the .html extension')
        if args.source:
            if args.source.is_symlink() or not args.source.is_file():
                raise ValueError('source must be a regular non-symlink file')
            if args.source.resolve().parent != args.output.resolve().parent:
                raise ValueError('saved source and HTML must share a directory to preserve relative links')
            source = args.source.read_bytes()
        else:
            source = sys.stdin.buffer.read()
        document = render(source.decode('utf-8'), args.title, args.theme)
        # Exclusive creation also refuses existing files and dangling symlinks.
        with args.output.open('x', encoding='utf-8') as handle:
            handle.write(document)
        saved = args.output.read_bytes()
        print(json.dumps({'output': str(args.output), 'theme': args.theme, 'source_sha256': hashlib.sha256(source).hexdigest(),
                          'html_sha256': hashlib.sha256(saved).hexdigest(), 'bytes': len(saved)}))
    except (OSError, UnicodeError, ValueError) as error:
        print('error: ' + str(error), file=sys.stderr)
        return 2
    return 0


if __name__ == '__main__':
    sys.exit(main())
