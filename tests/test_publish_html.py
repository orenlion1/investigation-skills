"""Exercise HTML generation, including delivery without a Markdown artifact."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import test_profile_manager as profiles

ROOT = Path(__file__).resolve().parents[1]
GENERATOR = ROOT / 'skills/publish-it/scripts/generate_html.py'
CONTENT = '''# Example investigation

[Evidence](#E1) and [findings](#findings).

<a id="E1"></a>

## Findings

| Signal | Result |
| --- | --- |
| Errors | None |

![Flow](assets/flow.svg)

Figure 1. Verified flow.

## Findings

```text
<literal example>
```
'''


class HtmlGeneratorTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.output = self.root / 'REPORT-example.html'

    def generate(self, content=CONTENT, *arguments):
        return subprocess.run([sys.executable, str(GENERATOR), '--output', str(self.output),
                               '--title', 'Example <investigation>', *arguments],
                              input=content, text=True, capture_output=True)

    def test_stdin_produces_html_without_markdown_or_pdf_and_preserves_references(self):
        result = self.generate()
        self.assertEqual(result.returncode, 0, result.stderr)
        receipt = json.loads(result.stdout)
        self.assertEqual(receipt['source_sha256'], hashlib.sha256(CONTENT.encode()).hexdigest())
        self.assertEqual(receipt['html_sha256'], hashlib.sha256(self.output.read_bytes()).hexdigest())
        html = self.output.read_text()
        for expected in ('<!doctype html>', '<title>Example &lt;investigation&gt;</title>',
                         'id="E1"', 'href="#E1"', 'id="findings"', 'id="findings-1"',
                         '<table>', 'src="assets/flow.svg"', 'Figure 1. Verified flow.',
                         '&lt;literal example&gt;'):
            self.assertIn(expected, html)
        self.assertEqual(list(self.root.iterdir()), [self.output])

    def test_theme_picture_and_wrappers_preserve_figures_and_markdown_captions(self):
        content = ('<div class="figure-pair">\n\n<picture>'
                   '<source media="(prefers-color-scheme: dark)" srcset="assets/dark.png">'
                   '<img src="assets/light.png" alt="CPU &amp; state"></picture>\n\n'
                   '**Figure 1.** Evidence remains adjacent.\n\n</div>')
        result = self.generate(content)
        self.assertEqual(result.returncode, 0, result.stderr)
        html = self.output.read_text()
        for expected in ('<div class="figure-pair">', '<picture>', 'srcset="assets/dark.png"',
                         'src="assets/light.png"', 'alt="CPU &amp; state"',
                         '<strong>Figure 1.</strong> Evidence remains adjacent.'):
            self.assertIn(expected, html)

    def test_raw_figure_urls_and_attributes_cannot_execute_code(self):
        for raw in ('<img src="javascript:alert(1)">',
                    '<source srcset="javascript:alert(1)">',
                    '<img src="java&#10;script:alert(1)">',
                    '<div style="background:url(javascript:alert(1))">',
                    '<img src="safe.png" src="javascript:alert(1)">'):
            self.assertEqual(self.generate(raw).returncode, 2, raw)
            self.assertFalse(self.output.exists())

    def test_html_theme_selects_page_and_picture_policy(self):
        content = ('<picture><source media="(prefers-color-scheme: dark)" srcset="assets/dark.png">'
                   '<img src="assets/light.png" alt="CPU"></picture>')
        for theme in ('light', 'dark', 'system'):
            result = self.generate(content, '--theme', theme)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(result.stdout)['theme'], theme)
            html = self.output.read_text()
            self.assertIn('data-theme="' + theme + '"', html)
            if theme == 'system':
                self.assertIn('media="(prefers-color-scheme: dark)"', html)
            else:
                self.assertIn('media="' + ('all' if theme == 'dark' else 'not all') + '"', html)
                self.assertNotIn('@media (prefers-color-scheme: dark)', html)
            self.output.unlink()
        self.assertNotEqual(self.generate(content, '--theme', 'invalid').returncode, 0)
        self.assertFalse(self.output.exists())

    def test_saved_source_is_preserved_and_output_cannot_overwrite(self):
        source = self.root / 'REPORT-example.md'
        source.write_text(CONTENT)
        result = self.generate('', '--source', str(source))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(source.read_text(), CONTENT)
        before = self.output.read_bytes()
        self.assertEqual(self.generate('# Different').returncode, 2)
        self.assertEqual(self.output.read_bytes(), before)

    def test_unsupported_active_html_fails_before_creating_output(self):
        for content in ('<script>alert(1)</script>', '<img src=x onerror="alert(1)">',
                        '<a id="bad" onclick="alert(1)"></a>'):
            result = self.generate(content)
            self.assertEqual(result.returncode, 2, result.stdout)
            self.assertFalse(self.output.exists())

    def test_duplicate_anchor_and_moved_source_are_rejected(self):
        result = self.generate('<a id="E1"></a>\n\n<a id="E1"></a>')
        self.assertEqual(result.returncode, 2)
        source = self.root / 'nested' / 'report.md'
        source.parent.mkdir()
        source.write_text(CONTENT)
        self.assertEqual(self.generate('', '--source', str(source)).returncode, 2)
        self.assertFalse(self.output.exists())

    def test_profile_html_only_generates_no_disabled_deliverables(self):
        fixture = profiles.ProfileStoreTests('runTest')
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        fixture.ignore_and_init()
        fixture.ok('set', '--profile', 'html-only', '--field', 'REPO=service-a',
                   '--field', 'GENERATE_MARKDOWN=disabled', '--field', 'GENERATE_PDF=disabled',
                   '--field', 'GENERATE_HTML=enabled')
        task = fixture.root / 'TASK.md'
        task.write_text('## Resources\n')
        loaded = fixture.ok('load', '--profile', 'html-only', '--task', str(task))
        self.assertTrue(loaded['verified'])
        for label, choice in (('Markdown', 'disabled'), ('PDF', 'disabled'), ('HTML', 'enabled')):
            self.assertIn('- Generate ' + label + ': `' + choice + '`', task.read_text())
        result = self.generate()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(self.output.is_file())
        self.assertEqual(list(self.root.glob('*.md')), [])
        self.assertEqual(list(self.root.glob('*.pdf')), [])


if __name__ == '__main__':
    unittest.main()
