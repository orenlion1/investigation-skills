import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'scripts/select_live_eval_cases.py'


class LiveEvalSelectionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.cases = self.root / 'cases'
        self.cases.mkdir()
        self.alpha = {'skill_name': 'alpha', 'trigger': {'positive': ['keep']},
                      'evals': [{'id': n, 'prompt': 'prompt ' + str(n),
                                 'expectations': ['must stay unchanged']} for n in [1, 2, 3]]}
        (self.cases / 'alpha.json').write_text(json.dumps(self.alpha))
        (self.cases / 'beta.json').write_text(json.dumps({'skill_name': 'beta', 'evals': [{'id': 1}]}))
        self.out = self.root / 'selected'
        self.original = {p.name: p.read_bytes() for p in self.cases.iterdir()}

    def call(self, skill='all', ids=''):
        return subprocess.run([sys.executable, str(SCRIPT), '--cases-dir', str(self.cases),
                               '--output-dir', str(self.out), '--skill', skill,
                               '--case-ids', ids], capture_output=True, text=True)

    def test_default_preserves_full_catalog_and_private_permissions(self):
        result = self.call()
        self.assertEqual(result.returncode, 0, result.stderr)
        data = json.loads(result.stdout)
        self.assertEqual(data['evals'], {'alpha': 3, 'beta': 1})
        self.assertEqual({p.name: p.read_bytes() for p in self.out.iterdir()}, self.original)
        self.assertEqual(self.out.stat().st_mode & 0o777, 0o700)
        self.assertTrue(all(p.stat().st_mode & 0o777 == 0o600 for p in self.out.iterdir()))

    def test_selected_cases_preserve_order_prompts_and_other_catalog_files(self):
        result = self.call('alpha', '3, 1')
        self.assertEqual(result.returncode, 0, result.stderr)
        data = json.loads(result.stdout)
        self.assertEqual(data['evals'], {'alpha': 2})
        self.assertEqual(data['selected_ids'], {'alpha': [1, 3]})
        selected = json.loads((self.out / 'alpha.json').read_text())
        self.assertEqual(selected, {**self.alpha, 'evals': [self.alpha['evals'][0], self.alpha['evals'][2]]})
        self.assertEqual((self.out / 'beta.json').read_bytes(), self.original['beta.json'])
        self.assertEqual({p.name: p.read_bytes() for p in self.cases.iterdir()}, self.original)
        self.assertEqual(len(data['source_sha256']['alpha']), 64)

    def test_single_skill_without_ids_keeps_all_its_cases(self):
        result = self.call('alpha')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)['evals'], {'alpha': 3})
        self.assertEqual((self.out / 'alpha.json').read_bytes(), self.original['alpha.json'])

    def test_invalid_unknown_or_duplicate_ids_fail_before_output(self):
        for ids in ['0', '-1', '1.5', '1,1', '1,', '9', '1;echo no', 'True']:
            with self.subTest(ids=ids):
                self.assertNotEqual(self.call('alpha', ids).returncode, 0)
                self.assertFalse(self.out.exists())
        self.assertEqual({p.name: p.read_bytes() for p in self.cases.iterdir()}, self.original)

    def test_ids_require_one_known_skill(self):
        for skill, ids in [('all', '1'), ('unknown', ''), ('../alpha', '1')]:
            with self.subTest(skill=skill):
                self.assertNotEqual(self.call(skill, ids).returncode, 0)
                self.assertFalse(self.out.exists())

    def test_existing_output_and_symlink_source_are_rejected(self):
        self.out.mkdir()
        self.assertNotEqual(self.call().returncode, 0)
        self.assertEqual(list(self.out.iterdir()), [])
        self.out.rmdir()
        (self.cases / 'alpha.json').unlink()
        (self.cases / 'alpha.json').symlink_to(self.cases / 'beta.json')
        self.assertNotEqual(self.call().returncode, 0)
        self.assertFalse(self.out.exists())

    def test_duplicate_or_invalid_catalog_ids_are_rejected(self):
        for values in [[1, 1], [True], [0], []]:
            with self.subTest(values=values):
                (self.cases / 'alpha.json').write_text(json.dumps({'evals': [{'id': n} for n in values]}))
                self.assertNotEqual(self.call('alpha', '1').returncode, 0)
                self.assertFalse(self.out.exists())


if __name__ == '__main__':
    unittest.main()
