"""Attachment-only local evidence validation cannot satisfy the page publication gate."""
import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


source = module('publication_source', 'skills/publish-it/scripts/validate_publication_source.py')
checker = module('reference_checker', 'skills/report-authoring/scripts/check_reference_links.py')


class PublicationSourceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.artifact = self.root / 'report.html'
        self.artifact.write_text('<p><a href="evidence.json">saved evidence</a></p>')
        self.evidence = self.root / 'evidence.json'
        self.evidence.write_text('{"finding":"retained"}')
        self.manifest = {'schema': 'reference-links/v1', 'reviewed': True, 'references': [
            {'id': 'saved', 'identity': 'saved evidence', 'type': 'supporting-evidence',
             'labels': ['saved evidence'], 'url': 'evidence.json', 'provenance': 'verified',
             'source': 'inspected saved evidence file'}]}

    def validate(self, manifest=None, roots=None):
        return source.validate(self.artifact, manifest or self.manifest,
                               roots or [self.root], checker)

    def test_local_file_authorizes_only_attachment_preparation(self):
        result = self.validate()
        self.assertEqual(result['unresolved'], 0)
        self.assertEqual(result['permission'], 'attachment-uploads-only')
        self.assertFalse(result['page_publication_allowed'])
        self.assertEqual(result['rows'][0]['original_status'], 'local-only')
        self.assertEqual(result['local_files']['saved']['bytes'], len(self.evidence.read_bytes()))
        with self.assertRaises(ValueError):
            checker.require_complete([self.artifact], self.manifest)

    def test_missing_wrong_unlinked_unverified_or_escaping_evidence_still_blocks(self):
        for mode in ('missing', 'wrong', 'unlinked', 'unverified', 'outside'):
            with self.subTest(mode=mode):
                data = copy.deepcopy(self.manifest)
                self.artifact.write_text('<p><a href="evidence.json">saved evidence</a></p>')
                roots = [self.root]
                if mode == 'missing': data['references'][0]['url'] = 'missing.json'
                if mode == 'wrong': self.artifact.write_text('<a href="other.json">saved evidence</a>')
                if mode == 'unlinked': self.artifact.write_text('<p>saved evidence</p>')
                if mode == 'unverified': data['references'][0]['provenance'] = 'unverified'
                if mode == 'outside':
                    allowed = self.root / 'allowed'; allowed.mkdir(); roots = [allowed]
                self.assertGreater(self.validate(data, roots)['unresolved'], 0)

    def test_symlink_missing_file_and_unsafe_schemes_are_not_local_proof(self):
        self.evidence.unlink()
        self.assertGreater(self.validate()['unresolved'], 0)
        target = self.root / 'target.json'; target.write_text('{}')
        self.evidence.symlink_to(target)
        self.assertGreater(self.validate()['unresolved'], 0)
        self.manifest['references'][0]['url'] = 'javascript:alert(1)'
        self.artifact.write_text('<a href="javascript:alert(1)">saved evidence</a>')
        self.assertGreater(self.validate()['unresolved'], 0)


if __name__ == '__main__':
    unittest.main()
