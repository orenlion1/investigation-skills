"""Exercise the real secret gate in disposable repositories using synthetic values."""
import os
from pathlib import Path
import random
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


if __name__ == '__main__':
    unittest.main(verbosity=2)
