"""HTML-only Confluence attachment packaging, independent of Markdown/PDF files."""
import base64
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
GENERATOR = ROOT / 'skills/publish-it/scripts/generate_html.py'
PACKAGER = ROOT / 'skills/publish-it/scripts/package_confluence_html.py'
PNG = base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+j4xkAAAAASUVORK5CYII=')


class Tags(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.tags = []
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        self.tags.append((tag, dict(attrs)))


class ConfluenceHtmlPackageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.assets = self.root / 'assets'
        self.assets.mkdir()
        for name in ('light.png', 'dark.png'):
            (self.assets / name).write_bytes(PNG)
        self.source = self.root / 'report.html'
        self.output = self.root / 'report-confluence.html'

    def run_package(self):
        return subprocess.run([sys.executable, str(PACKAGER), '--source', str(self.source),
                               '--output', str(self.output), '--asset-root', str(self.assets)],
                              capture_output=True, text=True)

    def generate(self, theme):
        content = ('# Report\n\n<picture><source media="(prefers-color-scheme: dark)" '
                   'srcset="assets/dark.png"><img src="assets/light.png" alt="CPU"></picture>\n\n'
                   'Figure 1. Caption and [source](https://example.com/evidence).\n')
        subprocess.run([sys.executable, str(GENERATOR), '--output', str(self.source),
                        '--title', 'Report', '--theme', theme], input=content,
                       text=True, capture_output=True, check=True)

    def test_html_only_packaging_preserves_all_three_themes_and_embeds_both_variants(self):
        for theme in ('light', 'dark', 'system'):
            with self.subTest(theme=theme):
                self.generate(theme)
                original = self.source.read_bytes()
                result = self.run_package()
                self.assertEqual(result.returncode, 0, result.stderr)
                receipt = json.loads(result.stdout)
                self.assertEqual(receipt['theme'], theme)
                self.assertEqual(receipt['source_sha256'], hashlib.sha256(original).hexdigest())
                self.assertEqual(receipt['html_sha256'], hashlib.sha256(self.output.read_bytes()).hexdigest())
                self.assertEqual(len(receipt['embedded_images']), 2)
                tags = Tags(self.output.read_text()).tags
                figure_urls = [attrs[key] for tag, attrs in tags
                               for key in ('src', 'srcset') if tag in ('img', 'source') and key in attrs]
                self.assertEqual(len(figure_urls), 2)
                for url in figure_urls:
                    self.assertEqual(base64.b64decode(url.split(',', 1)[1]), PNG)
                self.assertIn('Figure 1. Caption', self.output.read_text())
                self.assertIn('href="https://example.com/evidence"', self.output.read_text())
                self.assertEqual(self.source.read_bytes(), original)
                self.assertFalse(list(self.root.glob('*.md')))
                self.assertFalse(list(self.root.glob('*.pdf')))
                self.source.unlink()
                self.output.unlink()

    def test_missing_remote_or_escaping_image_fails_without_output(self):
        outside = self.root / 'outside.png'
        outside.write_bytes(PNG)
        for url in ('assets/missing.png', 'https://example.com/figure.png', 'outside.png'):
            self.source.write_text('<html data-theme="light"><img src="' + url + '"></html>')
            self.assertNotEqual(self.run_package().returncode, 0, url)
            self.assertFalse(self.output.exists())

    def test_active_html_and_external_css_are_rejected(self):
        for body in ('<script>alert(1)</script>', '<img src="assets/light.png" onerror="alert(1)">',
                     '<style>@import "https://example.com/style.css";</style>'):
            self.source.write_text('<html data-theme="light">' + body + '</html>')
            self.assertNotEqual(self.run_package().returncode, 0)
            self.assertFalse(self.output.exists())

    def test_unsupported_markup_and_alternate_fetch_attributes_are_rejected(self):
        for body in ('<svg><a><animate attributeName="href" values="javascript:alert(1)"></animate></a></svg>',
                     '<img src="assets/light.png" srcset="https://example.com/remote.png">',
                     '<video poster="https://example.com/remote.png"></video>',
                     '<a href="https://example.com" ping="https://example.com/track">evidence</a>',
                     r'<style>@\69mport "https://example.com/style.css";</style>'):
            with self.subTest(body=body):
                if self.output.exists():
                    self.output.unlink()
                self.source.write_text('<html data-theme="light">' + body + '</html>')
                self.assertNotEqual(self.run_package().returncode, 0)
                self.assertFalse(self.output.exists())

    def test_generated_table_alignment_is_preserved_without_allowing_active_styles(self):
        self.source.write_text('<html data-theme="light"><table><tr><td style="text-align:right">1</td></tr></table></html>')
        self.assertEqual(self.run_package().returncode, 0)
        self.assertIn('style="text-align:right"', self.output.read_text())
        self.output.unlink()
        self.source.write_text('<html data-theme="light"><td style="background:url(https://example.com/image.png)">1</td></html>')
        self.assertNotEqual(self.run_package().returncode, 0)
        self.assertFalse(self.output.exists())

    def test_local_links_remain_explicit_mapping_work_and_existing_output_is_preserved(self):
        self.source.write_text('<html data-theme="system"><a href="prior.md#E1">Prior</a></html>')
        result = self.run_package()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)['local_links_requiring_publication_mapping'], ['prior.md#E1'])
        before = self.output.read_bytes()
        self.assertNotEqual(self.run_package().returncode, 0)
        self.assertEqual(self.output.read_bytes(), before)


if __name__ == '__main__':
    unittest.main()
