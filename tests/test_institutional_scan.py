"""Exercise disclosure controls against real disposable Git objects."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCANNER = ROOT / 'scripts/scan-institutional-data.py'
POLICY = ROOT / 'security/disclosure-policy.json'


class InstitutionalScanTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='disclosure-fixture-')
        self.addCleanup(self.temp.cleanup)
        self.repo = Path(self.temp.name) / 'repo'
        self.git('init', '-q', str(self.repo), cwd=self.temp.name)
        self.git('config', 'user.name', 'Disclosure Fixture')
        self.git('config', 'user.email', 'fixture@example.invalid')
        self.write('README.md', 'Public example.\n')
        self.commit()

    def git(self, *args, cwd=None):
        return subprocess.run(
            ['git', '-c', 'core.hooksPath=/dev/null', '-c', 'commit.gpgsign=false', *args],
            cwd=cwd or self.repo, check=True, capture_output=True)

    def write(self, name, data):
        path = self.repo / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data if isinstance(data, bytes) else data.encode())

    def commit(self, message='Public fixture'):
        self.git('add', '-A')
        self.git('commit', '-qm', message)

    def scan(self, *args, repo=None, policy=POLICY):
        return subprocess.run(
            [sys.executable, str(SCANNER), '--repository', str(repo or self.repo),
             '--policy', str(policy), *args], capture_output=True, text=True, timeout=30)

    def test_public_source_and_reserved_examples_pass(self):
        self.write('example.md', '\n'.join([
            'https://docs.github.com/en/actions', 'fixture@example.invalid',
            'https://example.atlassian.net', 'https://example.invalid/service',
            'https://d1\\.awsstatic\\.com/icons',
            'SHA-256 signatures and UTF-16 text',
            '40065251+orenlion1@users.noreply.github.com']))
        self.commit()
        result = self.scan()
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_unborn_repository_supports_staged_preflight(self):
        unborn = Path(self.temp.name) / 'unborn'
        self.git('init', '-q', str(unborn))
        (unborn / 'README.md').write_text('Public source.\n')
        self.git('add', '.', cwd=unborn)
        self.assertEqual(self.scan('--staged', repo=unborn).returncode, 0)
        self.assertNotEqual(self.scan(repo=unborn).returncode, 0)

    def test_deleted_data_and_side_branch_are_not_hidden(self):
        self.git('checkout', '-qb', 'fixture-side')
        self.write('incident.md', 'person' + '@' + 'institution.invalid-corp.com')
        self.commit()
        (self.repo / 'incident.md').unlink()
        self.commit()
        self.git('checkout', '-')
        result = self.scan()
        self.assertEqual(result.returncode, 1)
        self.assertIn('email', result.stdout)
        self.assertNotIn('institution.invalid-corp.com', result.stdout + result.stderr)

    def test_detached_head_cannot_hide_data(self):
        self.git('checkout', '--detach')
        self.write('note.md', 'contact' + '@' + 'private-hospital.org')
        self.commit()
        self.assertEqual(self.scan().returncode, 1)

    def test_noncommit_tag_requires_review(self):
        # A blob-only tag is not part of a commit tree; require explicit review.
        self.write('public.txt', 'Public blob fixture.\n')
        oid = self.git('hash-object', '-w', 'public.txt').stdout.decode().strip()
        self.git('tag', 'blob-fixture', oid)
        self.assertNotEqual(self.scan().returncode, 0)

    def test_sensitive_paths_and_unknown_hosts_and_identifiers_fail(self):
        fixtures = [('docs/report.md', 'Public text.'), ('logs/evidence.txt', 'Public text.'),
                    ('.env', 'PLAIN=value'), ('note.md', 'https://' + 'tenant.atlassian.net'),
                    ('note.md', 'https://' + 'tenant.grafana.net'),
                    ('note.md', 'https://' + 'private-hospital.org/api'),
                    ('note.md', 'https://' + 'user:password' + '@' + 'github.com/private'),
                    ('note.md', 'AWS account: ' + '123456' + '789012'),
                    ('note.md', 'CASE-' + '3471')]
        for path, content in fixtures:
            with self.subTest(path=path, content=content):
                self.write(path, content)
                self.git('add', '-f', path)
                result = self.scan('--staged')
                self.assertEqual(result.returncode, 1)
                self.assertNotIn(content, result.stdout + result.stderr)
                self.git('reset', '-q', 'HEAD', '--', path)
                (self.repo / path).unlink()

    def test_fingerprints_catch_case_and_separator_variants_without_disclosure(self):
        policy = json.loads(POLICY.read_text())
        canonical = 'syntheticinstitution'
        policy['blocked_fingerprints'] = [{
            'length': len(canonical), 'sha256': hashlib.sha256(canonical.encode()).hexdigest()}]
        private_policy = Path(self.temp.name) / 'policy.json'
        private_policy.write_text(json.dumps(policy))
        self.write('note.md', 'SYNTHETIC-Institution clinical details')
        self.git('add', '.')
        result = self.scan('--staged', policy=private_policy)
        self.assertEqual(result.returncode, 1)
        self.assertIn('institution-fingerprint', result.stdout)
        self.assertNotIn('SYNTHETIC', result.stdout + result.stderr)

    def test_commit_and_tag_metadata_are_scanned(self):
        self.write('note.md', 'Public text.\n')
        self.commit('Customer ticket CASE-' + '3471')
        self.assertEqual(self.scan().returncode, 1)
        self.git('commit', '--amend', '-qm', 'Public fixture')
        self.git('tag', '-a', 'fixture', '-m', 'contact' + '@' + 'private-hospital.org')
        result = self.scan()
        self.assertEqual(result.returncode, 1)
        self.assertIn('email', result.stdout)

    def test_binary_symlink_submodule_and_oversize_fail_closed(self):
        self.write('evidence.png', b'\x89PNG\x00private payload')
        self.git('add', '.')
        self.assertEqual(self.scan('--staged').returncode, 1)
        self.git('reset', '-q', 'HEAD')
        (self.repo / 'evidence.png').unlink()
        os.symlink('/outside/private-data', self.repo / 'link')
        self.git('add', '.')
        self.assertEqual(self.scan('--staged').returncode, 1)
        self.git('reset', '-q', 'HEAD')
        (self.repo / 'link').unlink()
        head = self.git('rev-parse', 'HEAD').stdout.decode().strip()
        self.git('update-index', '--add', '--cacheinfo', '160000,' + head + ',external')
        self.assertEqual(self.scan('--staged').returncode, 1)
        self.git('reset', '-q', 'HEAD')
        self.write('huge.txt', b'x' * (2 * 1024 * 1024 + 1))
        self.git('add', '.')
        self.assertEqual(self.scan('--staged').returncode, 1)

    def test_path_disclosure_is_redacted_even_for_workflow_commands(self):
        name = '::error::person' + '@' + 'private-hospital.org.md'
        self.write(name, 'Public text.\n')
        self.git('add', '.')
        result = self.scan('--staged')
        self.assertEqual(result.returncode, 1)
        self.assertNotIn(name, result.stdout + result.stderr)
        self.assertNotIn('::error::', result.stdout + result.stderr)

    def test_missing_policy_and_shallow_clone_fail_closed(self):
        self.assertNotEqual(self.scan(policy=Path(self.temp.name) / 'missing').returncode, 0)
        shallow = Path(self.temp.name) / 'shallow'
        self.git('clone', '-q', '--depth', '1', self.repo.as_uri(), str(shallow))
        result = self.scan(repo=shallow)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('complete history', result.stderr)


if __name__ == '__main__':
    unittest.main()
