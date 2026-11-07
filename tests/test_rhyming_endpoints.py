"""Public CLI coverage for typed historical-search profile endpoints."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
HELPER = ROOT / 'skills/profile-manager/scripts/profile_env.py'


class RhymingEndpointTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / 'templates').mkdir()
        (self.root / 'templates/TASK.md').write_text((ROOT / 'templates/TASK.md').read_text())
        subprocess.run(['git', 'init', '-q', str(self.root)], check=True)
        (self.root / '.gitignore').write_text('.env\n')
        self.store = self.root / '.env'
        self.store.write_text('UNMANAGED="keep this exactly"\n')
        self.endpoints = [
            {'id': 'past', 'kind': 'grafana-investigations', 'target': 'service-a', 'context': 'ops'},
            {'id': 'assistant', 'kind': 'grafana-assistant-conversations', 'target': 'service-a', 'context': 'ops'},
            {'id': 'wiki', 'kind': 'confluence', 'target': 'https://example.atlassian.net/wiki/spaces/OPS/pages/123'},
            {'id': 'chat', 'kind': 'slack', 'target': 'C0123456789'},
            {'id': 'code', 'kind': 'repository', 'target': 'https://github.com/example/service-a', 'provider': 'github'},
        ]

    def cli(self, *args, ok=True):
        result = subprocess.run([sys.executable, '-B', str(HELPER), '--repository-root',
                                 str(self.root), *args], text=True, capture_output=True)
        self.assertEqual(result.returncode, 0 if ok else 2, result.stderr)
        return result

    def set_endpoints(self, value, ok=True, *extra):
        encoded = value if isinstance(value, str) else json.dumps(value, separators=(',', ':'))
        return self.cli('set', '--profile', 'ops', '--field', 'RHYMING_ENDPOINTS=' + encoded,
                        *extra, ok=ok)

    def test_all_kinds_round_trip_and_task_load(self):
        self.set_endpoints(self.endpoints)
        result = json.loads(self.cli('endpoints', '--profile', 'ops').stdout)
        self.assertEqual(result['endpoints'], self.endpoints)
        self.assertIn('UNMANAGED="keep this exactly"\n', self.store.read_text())
        self.assertEqual(self.store.stat().st_mode & 0o777, 0o600)
        task = self.root / 'TASK.md'
        task.write_text('# Task Title: Test\n\n## Resources\n\n- Repo: `<enter repo>`\n')
        self.cli('load', '--profile', 'ops', '--task', str(task))
        self.assertIn('- Rhyming endpoints: `', task.read_text())
        value = task.read_text().split('- Rhyming endpoints: `')[1].split('`')[0]
        self.assertEqual(json.loads(value), self.endpoints)

    def test_legacy_profile_returns_no_endpoints(self):
        self.cli('set', '--profile', 'ops', '--field', 'REPO=service-a')
        self.assertEqual(json.loads(self.cli('endpoints', '--profile', 'ops').stdout)['endpoints'], [])

    def test_schema_exposes_structured_constraints(self):
        fields = {x['field']: x for x in json.loads(self.cli('schema').stdout)['fields']}
        self.assertEqual(fields['RHYMING_ENDPOINTS']['type'], 'endpoint-array')
        self.assertEqual(len(fields['RHYMING_ENDPOINTS']['kinds']), 5)

    def test_invalid_structures_never_write(self):
        invalid = ['{', '{}', '[]', '[null]', '[{"id":"x","id":"y"}]',
                   self.endpoints + [self.endpoints[0]],
                   [dict(self.endpoints[0], kind='unknown')],
                   [{'id': 'x', 'kind': 'grafana-investigations', 'target': 'service-a'}],
                   [dict(self.endpoints[-1], provider='bitbucket')],
                   [dict(self.endpoints[0], context='')],
                   [dict(self.endpoints[0], extra='unrecognized')],
                   self.endpoints * 4]
        for value in invalid:
            with self.subTest(value=value):
                before = self.store.read_bytes()
                self.set_endpoints(value, ok=False)
                self.assertEqual(self.store.read_bytes(), before)

    def test_unsafe_targets_and_credentials_are_rejected_without_echo(self):
        for target in ['http://example.atlassian.net/wiki/123',
                       'https://' + 'user:password@' + 'example.atlassian.net/wiki/123',
                       'https://example.atlassian.net/wiki/123?token=secret',
                       'https://example.atlassian.net/wiki/123#secret',
                       'https://' + '127.0.0.1/wiki/123', 'https://example.atlassian.net/other/123',
                       '$(touch /tmp/no)', '`malicious`', '<placeholder>',
                       'https://example.atlassian.net/wiki/%0a123']:
            with self.subTest(target=target):
                result = self.set_endpoints([dict(self.endpoints[2], target=target)], ok=False)
                self.assertNotIn(target, result.stderr)
        self.set_endpoints([dict(self.endpoints[0], context='ghp_' + 'A' * 30)], ok=False)

    def test_invalid_handwritten_store_cannot_be_shown_rendered_loaded_or_probed(self):
        self.store.write_text('PROFILE__OPS__RHYMING_ENDPOINTS=\'[{"id":"bad"}]\'\n')
        for command in ['show', 'render', 'endpoints']:
            self.cli(command, '--profile', 'ops', ok=False)
        task = self.root / 'TASK.md'; task.write_text('## Resources\n')
        self.cli('load', '--profile', 'ops', '--task', str(task), ok=False)
        self.assertEqual(task.read_text(), '## Resources\n')

    def test_limits_are_field_specific_and_dry_run_preserves_store(self):
        before = self.store.read_bytes()
        self.set_endpoints(self.endpoints, True, '--dry-run')
        self.assertEqual(self.store.read_bytes(), before)
        self.cli('set', '--profile', 'ops', '--field', 'REPO=' + 'a' * 513, ok=False)
        self.set_endpoints('[' + ' ' * 8192 + ']', ok=False)

    def test_multiple_same_provider_endpoints_remain_distinct(self):
        two = [self.endpoints[0], dict(self.endpoints[0], id='past-two', target='service-b')]
        self.set_endpoints(two)
        self.assertEqual(len(json.loads(self.cli('endpoints', '--profile', 'ops').stdout)['endpoints']), 2)
