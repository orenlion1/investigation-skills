"""Offline fixture checks for imported skill provenance and version pins."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
CHECKER = ROOT / 'scripts/check-vendored-imports.py'


class VendoredImports(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        (self.root / 'policy').mkdir()
        self.pin = self.root / 'policy/vendored-imports.json'
        self.skill = self.add_skill('imported', '0.2.36')
        self.policy = {'schema': 'vendored-imports/v1', 'skills': {
            'skills/imported': {'upstream_repository': 'https://github.com/example/upstream',
                                'commit': 'a' * 40, 'version': '0.2.36'}}}
        self.save()

    def add_skill(self, name, version):
        directory = self.root / 'skills' / name
        directory.mkdir(parents=True)
        skill = directory / 'SKILL.md'
        metadata = '' if version is None else f'metadata:\n  version: "{version}"\n'
        skill.write_text(f'---\nname: {name}\ndescription: Fixture\n{metadata}---\n# Fixture\n')
        return skill

    def save(self):
        self.pin.write_text(json.dumps(self.policy))

    def run_check(self):
        return subprocess.run([sys.executable, str(CHECKER), '--repository', str(self.root)],
                              capture_output=True, text=True)

    def assert_fails(self, *messages):
        result = self.run_check()
        self.assertEqual(result.returncode, 1, result.stderr)
        for message in messages:
            self.assertIn(message, result.stderr)

    def test_pinned_skill_passes_without_network_or_sibling(self):
        self.add_skill('native', None)
        result = self.run_check()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('1 imported skill', result.stdout)

    def test_version_mismatch_names_both_values(self):
        self.skill.write_text(self.skill.read_text().replace('0.2.36', '0.2.32'))
        self.assert_fails('skills/imported', '0.2.32', '0.2.36')

    def test_missing_pin_fails_closed(self):
        self.pin.unlink()
        self.assert_fails('vendored-imports.json')

    def test_unreadable_pin_fails_closed(self):
        specification = importlib.util.spec_from_file_location('vendored_checker', CHECKER)
        checker = importlib.util.module_from_spec(specification)
        specification.loader.exec_module(checker)
        with mock.patch.object(Path, 'read_text', side_effect=PermissionError('denied')), \
                mock.patch.object(sys, 'argv', [str(CHECKER), '--repository', str(self.root)]), \
                mock.patch('sys.stderr') as stderr:
            self.assertEqual(checker.main(), 1)
            self.assertIn('denied', str(stderr.write.call_args_list))

    def test_invalid_utf8_pin_fails_closed(self):
        self.pin.write_bytes(b'\xff')
        self.assert_fails('pin')

    def test_nonregular_pin_fails_closed(self):
        self.pin.unlink()
        self.pin.mkdir()
        self.assert_fails('regular file')

    def test_symlink_pin_fails_closed(self):
        target = self.root / 'saved.json'
        self.pin.rename(target)
        self.pin.symlink_to(target)
        self.assert_fails('regular file')

    def test_malformed_pins_fail_closed(self):
        for content in ('{bad', '[]', '{}', '{"schema":"vendored-imports/v1","skills":{}}',
                        '{"schema":"bad","skills":{},"skills":{}}'):
            with self.subTest(content=content):
                self.pin.write_text(content)
                self.assert_fails('pin')

    def test_invalid_pin_fields_fail_closed(self):
        for field, value in [('commit', 'main'), ('version', ''),
                             ('upstream_repository', '../sibling')]:
            with self.subTest(field=field):
                original = self.policy['skills']['skills/imported'][field]
                self.policy['skills']['skills/imported'][field] = value
                self.save()
                self.assert_fails(field)
                self.policy['skills']['skills/imported'][field] = original

    def test_unpinned_versioned_skill_is_discovered(self):
        self.add_skill('new-import', '1.0.0')
        self.assert_fails('skills/new-import', 'pin')

    def test_missing_pinned_skill_fails_closed(self):
        self.skill.unlink()
        self.assert_fails('SKILL.md')

    def test_removed_metadata_version_fails_closed(self):
        self.skill.write_text('---\nname: imported\n---\n')
        self.assert_fails('skills/imported', 'version')

    def test_ambiguous_or_invalid_frontmatter_fails_closed(self):
        for metadata in ('metadata:\n  version: "0.2.36"\n  version: "0.2.36"\n',
                         'metadata: {version: "0.2.36"}\n',
                         'metadata:\n  version: "0.2.36"\nmetadata:\n',
                         'metadata:\n  version: ["0.2.36"]\n'):
            with self.subTest(metadata=metadata):
                self.skill.write_text('---\nname: imported\n'+metadata+'---\n')
                self.assert_fails('metadata')

    def test_symlink_skill_fails_closed(self):
        target = self.root / 'saved.md'
        self.skill.rename(target)
        self.skill.symlink_to(target)
        self.assert_fails('regular file')

    def test_real_repository_passes(self):
        result = subprocess.run([sys.executable, str(CHECKER)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('2 imported skill', result.stdout)


if __name__ == '__main__':
    unittest.main()
