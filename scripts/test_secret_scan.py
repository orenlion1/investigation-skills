"""Exercise the real secret gate in disposable repositories using synthetic values."""
import os
from pathlib import Path
import random
import shlex
import shutil
import string
import subprocess
import tempfile
import unittest


SCAN = Path(__file__).resolve().with_name('scan-secrets.sh')


class SecretScanTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='secret-scan-selftest-')
        self.addCleanup(self.temp.cleanup)
        self.repo = Path(self.temp.name) / 'repo'
        self.git('init', '-q', str(self.repo), cwd=self.temp.name)
        self.git('config', 'user.name', 'Secret Scan Fixture')
        self.git('config', 'user.email', 'fixture@example.invalid')
        (self.repo / 'README.md').write_text('Clean fixture.\n')
        self.commit()

    def git(self, *args, cwd=None):
        return subprocess.run(
            ['git', '-c', 'core.hooksPath=/dev/null', '-c', 'commit.gpgsign=false', *args],
            cwd=cwd or self.repo, check=True, capture_output=True, text=True)

    def commit(self):
        self.git('add', '.')
        self.git('commit', '-qm', 'Scanner fixture')

    def scan(self, repo=None, env=None):
        return subprocess.run(['bash', str(SCAN), str(repo or self.repo)],
                              env=env, capture_output=True, text=True)

    def test_clean_history_passes(self):
        self.assertEqual(self.scan().returncode, 0)

    def test_merge_only_credential_is_scanned(self):
        original = self.git('branch', '--show-current').stdout.strip()
        self.git('checkout', '-qb', 'fixture-side')
        (self.repo / 'side.txt').write_text('Public side.\n')
        self.commit()
        self.git('checkout', original)
        (self.repo / 'main.txt').write_text('Public main.\n')
        self.commit()
        self.git('merge', '--no-commit', '--no-ff', 'fixture-side')
        fake = 'ghp_' + ''.join(random.Random(4821).choices(
            string.ascii_letters + string.digits, k=36))
        (self.repo / 'fixture.txt').write_text('token = ' + repr(fake) + '\n')
        self.commit()
        # Deleting the merge-only content must not hide its reachable blob.
        (self.repo / 'fixture.txt').unlink()
        self.git('add', '-A')
        self.git('commit', '-qm', 'Public later revision')
        result = self.scan()
        self.assertEqual(result.returncode, 1)
        self.assertNotIn(fake, result.stdout + result.stderr)

    def test_credentials_in_deleted_paths_are_scanned_without_disclosure(self):
        fake = 'ghp_' + ''.join(random.Random(4822).choices(
            string.ascii_letters + string.digits, k=36))
        path = self.repo / ('quoted\n"' + fake + '.txt')
        path.write_text('Public content.\n')
        self.commit()
        path.unlink()
        self.git('add', '-A')
        self.git('commit', '-qm', 'Public later revision')
        result = self.scan()
        self.assertEqual(result.returncode, 1)
        self.assertNotIn(fake, result.stdout + result.stderr)

    def test_blob_only_tag_credentials_are_scanned(self):
        fake = 'ghp_' + ''.join(random.Random(4823).choices(
            string.ascii_letters + string.digits, k=36))
        path = self.repo / 'uncommitted.txt'
        path.write_text('token = ' + repr(fake) + '\n')
        oid = self.git('hash-object', '-w', str(path)).stdout.strip()
        self.git('tag', 'blob-fixture', oid)
        path.unlink()
        result = self.scan()
        self.assertEqual(result.returncode, 1)
        self.assertNotIn(fake, result.stdout + result.stderr)

    def test_credentials_in_ref_names_are_scanned(self):
        fake = 'ghp_' + ''.join(random.Random(4824).choices(
            string.ascii_letters + string.digits, k=36))
        self.git('branch', fake)
        result = self.scan()
        self.assertEqual(result.returncode, 1)
        self.assertNotIn(fake, result.stdout + result.stderr)

    def test_deleted_secret_fails_without_logging_value_or_honoring_suppressions(self):
        # Construct a fake credential only in the temporary fixture, never in project history.
        fake = 'ghp_' + ''.join(random.Random(8741).choices(
            string.ascii_letters + string.digits, k=36))
        path = self.repo / 'fixture.py'
        path.write_text('token = ' + repr(fake) + '  # gitleaks:allow\n')
        self.commit()
        secret_commit = self.git('rev-parse', 'HEAD').stdout.strip()
        path.unlink()
        (self.repo / '.gitleaks.toml').write_text('[allowlist]\npaths = [".*"]\n')
        (self.repo / '.gitleaksignore').write_text(
            secret_commit + ':fixture.py:github-pat:1\n')
        self.commit()
        result = self.scan()
        self.assertEqual(result.returncode, 1)
        self.assertNotIn(fake, result.stdout + result.stderr)

    def test_missing_scanner_fails_closed(self):
        result = self.scan(env={**os.environ, 'GITLEAKS_BIN': str(self.repo / 'missing')})
        self.assertNotEqual(result.returncode, 0)

    def test_shallow_checkout_fails_closed(self):
        shallow = Path(self.temp.name) / 'shallow'
        self.git('clone', '--quiet', '--depth', '1', self.repo.as_uri(), str(shallow))
        result = self.scan(repo=shallow)
        self.assertEqual(result.returncode, 2)
        self.assertIn('complete history', result.stderr)

    def test_detached_pull_request_head_is_scanned(self):
        self.git('checkout', '--detach')
        fake = 'ghp_' + ''.join(random.Random(9173).choices(
            string.ascii_letters + string.digits, k=36))
        (self.repo / 'fixture.py').write_text('token = ' + repr(fake) + '\n')
        self.commit()
        result = self.scan()
        self.assertEqual(result.returncode, 1)
        self.assertNotIn(fake, result.stdout + result.stderr)

    def test_credentials_in_historical_commit_messages_fail_without_disclosure(self):
        fake = 'ghp_' + ''.join(random.Random(3821).choices(
            string.ascii_letters + string.digits, k=36))
        self.git('commit', '--allow-empty', '-qm', 'token = ' + fake + ' # gitleaks:allow')
        (self.repo / 'README.md').write_text('Clean later revision.\n')
        self.commit()
        result = self.scan()
        self.assertEqual(result.returncode, 1)
        self.assertNotIn(fake, result.stdout + result.stderr)

    def test_credentials_in_annotated_tag_messages_fail_without_disclosure(self):
        fake = 'ghp_' + ''.join(random.Random(3822).choices(
            string.ascii_letters + string.digits, k=36))
        self.git('tag', '-a', 'fixture', '-m', 'token = ' + fake)
        result = self.scan()
        self.assertEqual(result.returncode, 1)
        self.assertNotIn(fake, result.stdout + result.stderr)

    def test_credentials_in_nested_tag_messages_fail_without_inner_ref(self):
        fake = 'ghp_' + ''.join(random.Random(3823).choices(
            string.ascii_letters + string.digits, k=36))
        self.git('tag', '-a', 'inner', '-m', 'token = ' + fake + ' # gitleaks:allow')
        self.git('tag', '-a', 'middle', 'inner', '-m', 'Public middle annotation')
        self.git('tag', '-a', 'outer', 'middle', '-m', 'Public outer annotation')
        self.git('tag', '-d', 'inner', 'middle')
        (self.repo / '.gitleaks.toml').write_text('[allowlist]\npaths = [".*"]\n')
        (self.repo / '.gitleaksignore').write_text('*\n')
        self.commit()
        result = self.scan()
        self.assertEqual(result.returncode, 1)
        self.assertNotIn(fake, result.stdout + result.stderr)

    def test_detached_commit_message_credentials_are_scanned(self):
        self.git('checkout', '--detach')
        fake = 'ghp_' + ''.join(random.Random(3824).choices(
            string.ascii_letters + string.digits, k=36))
        self.git('commit', '--allow-empty', '-qm', 'token = ' + fake)
        result = self.scan()
        self.assertEqual(result.returncode, 1)
        self.assertNotIn(fake, result.stdout + result.stderr)

    def test_clean_nested_tags_pass(self):
        self.git('tag', '-a', 'inner', '-m', 'Public inner annotation')
        self.git('tag', '-a', 'outer', 'inner', '-m', 'Public outer annotation')
        self.git('tag', '-d', 'inner')
        result = self.scan()
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_metadata_scanner_failure_blocks_without_logging_diagnostics(self):
        real_scanner = shutil.which(os.environ.get('GITLEAKS_BIN', 'gitleaks'))
        self.assertIsNotNone(real_scanner)
        shim = Path(self.temp.name) / 'scanner'
        diagnostic = 'synthetic-sensitive-diagnostic'
        shim.write_text('#!/usr/bin/env bash\n'
                        'if [ "$1" = dir ]; then\n'
                        '  echo ' + diagnostic + ' >&2\n'
                        '  exit 2\n'
                        'fi\n'
                        'exec ' + shlex.quote(real_scanner) + ' "$@"\n')
        shim.chmod(0o700)
        result = self.scan(env={**os.environ, 'GITLEAKS_BIN': str(shim)})
        self.assertEqual(result.returncode, 2)
        self.assertNotIn(diagnostic, result.stdout + result.stderr)


if __name__ == '__main__':
    unittest.main(verbosity=2)
