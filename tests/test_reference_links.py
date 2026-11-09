"""Reader-visible regression tests; all identities and destinations are synthetic."""
import importlib.util
import tempfile
import subprocess
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    'reference_links', ROOT / 'skills/report-evidence/scripts/check_reference_links.py')
links = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(links)

URL = 'https://example.grafana.net/alerting/groups/ABCDEFGHIJKLM'


def manifest(label='ABCDEFGHIJKLM', url=URL):
    return {'schema': 'reference-links/v1', 'reviewed': True,
            'references': [{'id': 'incident', 'type': 'alert-group',
                            'identity': 'ABCDEFGHIJKLM', 'labels': [label],
                            'url': url, 'provenance': 'verified',
                            'source': 'inspected source object'}]}


class ReferenceLinksTests(unittest.TestCase):
    def audit(self, text, fmt='markdown', data=None):
        return links.audit_text(text, fmt, data or manifest(), 'report.' + fmt)

    def test_link_elsewhere_does_not_cover_plain_occurrence(self):
        rows = self.audit(f'# Reconciliation\n[ABCDEFGHIJKLM]({URL})\n\nABCDEFGHIJKLM')
        self.assertEqual([r['status'] for r in rows], ['linked', 'missing'])
        self.assertEqual(rows[1]['section'], 'Reconciliation')
        self.assertNotEqual(rows[0]['occurrence'], rows[1]['occurrence'])

    def test_reference_style_and_styled_labels(self):
        rows = self.audit(f'[ABCDEFGHIJKLM][prior]\n\n[prior]: {URL}')
        self.assertEqual([r['status'] for r in rows], ['linked'])
        rows = self.audit(f'<p><a href="{URL}"><b>ABCDEFG</b>HIJKLM</a> ABCDEFGHIJKLM</p>', 'html')
        self.assertEqual([r['status'] for r in rows], ['linked', 'missing'])

    def test_bold_evidence_entry_is_a_section_without_becoming_a_reference(self):
        data = manifest('E4', 'https://example.atlassian.net/wiki/spaces/TEST/pages/123#E4')
        data['references'][0]['section'] = 'E13'
        rows = self.audit('<a id="e13"></a>\n**E13 - Prior search.** [E4](%s)' % data['references'][0]['url'], data=data)
        self.assertEqual([r['status'] for r in rows], ['linked'])
        self.assertEqual(rows[0]['section'], 'E13')

    def test_wrong_object_and_broken_fragment(self):
        expected = 'https://example.atlassian.net/wiki/spaces/TEST/pages/123/Report#E4'
        data = manifest('E4', expected)
        for actual, status in [(expected.replace('/123/', '/124/'), 'wrong-target'),
                               (expected.replace('#E4', '#E5'), 'broken-fragment'),
                               (expected.split('#')[0], 'broken-fragment')]:
            self.assertEqual(self.audit(f'[E4]({actual})', data=data)[0]['status'], status)

    def test_title_normalization_keeps_page_and_fragment(self):
        data = manifest('E4', 'https://example.atlassian.net/wiki/spaces/TEST/pages/123#E4')
        self.assertEqual(self.audit('[E4](https://example.atlassian.net/wiki/spaces/TEST/pages/123/Old+title#E4)', data=data)[0]['status'], 'linked')
        self.assertEqual(self.audit('[E4](https://other.example/wiki/spaces/TEST/pages/123#E4)', data=data)[0]['status'], 'wrong-target')

    def test_unavailable_source_is_not_missing_or_valid(self):
        data = manifest(); data['references'][0].update(url=None, provenance='unavailable')
        self.assertEqual(self.audit('ABCDEFGHIJKLM', data=data)[0]['status'], 'unavailable-source')

    def test_unregistered_identity_is_not_silently_omitted(self):
        rows = self.audit('ABCDEFGHIJKLM and 12345678-1234-1234-1234-123456789abc')
        self.assertIn('unregistered-reference', [r['status'] for r in rows])

    def test_native_attachment_checks_media_identity_and_collection(self):
        data = manifest('Evidence download', 'media:file-a@contentId-123')
        html = '<div data-type="media" data-id="file-a" data-collection="contentId-123" data-alt="Evidence download"></div>'
        self.assertEqual(self.audit(html, 'html', data)[0]['status'], 'linked')
        self.assertEqual(self.audit(html.replace('contentId-123', ''), 'html', data)[0]['status'], 'wrong-target')

    def test_unknown_provenance_and_absent_labels_fail(self):
        data = manifest(); data['references'][0]['provenance'] = 'unverified'
        self.assertEqual(self.audit(f'[ABCDEFGHIJKLM]({URL})', data=data)[0]['status'], 'unverified-source')
        self.assertEqual(self.audit('nothing here')[0]['status'], 'reference-absent')
        with self.assertRaises(ValueError):
            self.audit('nothing', data={'schema': 'reference-links/v1', 'reviewed': True, 'references': []})

    def test_local_only_and_ambiguous_labels_fail(self):
        self.assertEqual(self.audit('[ABCDEFGHIJKLM](file:///tmp/evidence)')[0]['status'], 'local-only')
        data = manifest(); other = dict(data['references'][0], id='other', url=URL+'/other')
        data['references'].append(other)
        self.assertEqual(self.audit('ABCDEFGHIJKLM', data=data)[0]['status'], 'ambiguous-reference')

    def test_pdf_annotations_belong_to_each_visible_occurrence(self):
        import pymupdf
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'report.pdf'
            doc = pymupdf.open(); page = doc.new_page()
            page.insert_text((72, 72), 'ABCDEFGHIJKLM')
            page.insert_text((72, 110), 'ABCDEFGHIJKLM')
            rect = page.search_for('ABCDEFGHIJKLM')[0]
            page.insert_link({'kind': pymupdf.LINK_URI, 'from': rect, 'uri': URL})
            doc.save(path); doc.close()
            rows = links.audit_file(path, manifest())
            self.assertEqual([r['status'] for r in rows], ['linked', 'missing'])
            self.assertIn('page 1', rows[1]['locator'])

    def test_cli_preflight_fails_even_when_an_existing_link_is_correct(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'report.md'; path.write_text(f'[ABCDEFGHIJKLM]({URL}) ABCDEFGHIJKLM')
            source = Path(tmp) / 'references.json'; source.write_text(json.dumps(manifest()))
            output = Path(tmp) / 'coverage.json'
            result = subprocess.run([__import__('sys').executable, SPEC.origin,
                                     '--manifest', str(source), '--artifact', str(path),
                                     '--output', str(output)], capture_output=True)
            self.assertEqual(result.returncode, 1)
            self.assertEqual(json.loads(output.read_text())['unresolved'], 1)
            path.write_text(f'[ABCDEFGHIJKLM]({URL})')
            result = links.require_complete([path], manifest())
            self.assertEqual(result['occurrences'], 1)
            self.assertEqual(result['unique_destinations'], 1)
            self.assertEqual(len(result['artifacts'][0]['sha256']), 64)
            links.verify_freshness(result, [path])
            path.write_text('changed after validation')
            with self.assertRaises(ValueError):
                links.verify_freshness(result, [path])

    def test_cross_format_occurrence_loss_fails_even_with_correct_links(self):
        with tempfile.TemporaryDirectory() as tmp:
            md = Path(tmp) / 'report.md'; html = Path(tmp) / 'report.html'
            md.write_text(f'[ABCDEFGHIJKLM]({URL}) [ABCDEFGHIJKLM]({URL})')
            html.write_text(f'<a href="{URL}">ABCDEFGHIJKLM</a>')
            receipt = links.build_receipt([md, html], manifest())
            self.assertIn('occurrence-count-mismatch', [r['status'] for r in receipt['rows']])
            with self.assertRaises(ValueError):
                links.require_complete([md, html], manifest())

    def test_partial_label_link_does_not_cover_full_reference(self):
        rows = self.audit(f'<p><a href="{URL}">ABCDEFG</a>HIJKLM</p>', 'html')
        self.assertEqual(rows[0]['status'], 'missing')

    def test_contextual_alias_does_not_capture_unrelated_conversation_text(self):
        data = manifest('prior conversation')
        data['references'][0]['scoped_labels'] = [{'label': 'conversation', 'section': 'History'}]
        rows = self.audit('# Accounting\nconversation usage\n\n# History\nconversation\n\n' +
                          f'[prior conversation]({URL})', data=data)
        self.assertEqual([r['status'] for r in rows], ['missing', 'linked'])
        self.assertEqual([r['section'] for r in rows], ['History', 'History'])

    def test_twelve_target_regression_population_counts_occurrences_separately(self):
        # Same object classes and 12-target population as the historical report;
        # fabricated identities and reserved domains avoid publishing private evidence.
        refs = []
        for i, kind in enumerate(['history'] * 2 + ['alert-group'] * 3 +
                                 ['external-evidence'] * 6 + ['slack-reply']):
            label = 'Reference %s' % i
            refs.append({'id': str(i), 'type': kind, 'identity': str(i), 'labels': [label],
                         'url': 'https://example.com/objects/%s#evidence' % i,
                         'provenance': 'verified', 'source': 'synthetic regression'})
        data = {'schema': 'reference-links/v1', 'reviewed': True, 'references': refs}
        text = '\n\n'.join('[%s](%s)\n\n%s' % (r['labels'][0], r['url'], r['labels'][0])
                           for r in refs)
        rows = self.audit(text, data=data)
        self.assertEqual(len(rows), 24)
        self.assertEqual(sum(r['status'] == 'missing' for r in rows), 12)
        self.assertEqual(len({r['expected'] for r in rows}), 12)
