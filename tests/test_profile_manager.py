"""Exercise the profile store helper through its public command-line interface."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
HELPER = ROOT / 'skills' / 'profile-manager' / 'scripts' / 'profile_env.py'
TEMPLATE = ROOT / 'templates' / 'TASK.md'


class ProfileStoreTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name) / 'repository'
        (self.root / 'templates').mkdir(parents=True)
        self.template = self.root / 'templates' / 'TASK.md'
        self.template.write_text(TEMPLATE.read_text(encoding='utf-8'), encoding='utf-8')
        self.store = self.root / '.env'
        self.git('init')

    def git(self, *arguments):
        return subprocess.run(['git', '-C', str(self.root), *arguments],
                              capture_output=True, text=True, check=True)

    def run_helper(self, *arguments):
        return subprocess.run([sys.executable, '-B', str(HELPER),
                               '--repository-root', str(self.root), *arguments],
                              capture_output=True, text=True, check=False)

    def ok(self, *arguments):
        result = self.run_helper(*arguments)
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout) if result.stdout.startswith('{') else result.stdout

    def fails(self, *arguments):
        result = self.run_helper(*arguments)
        self.assertEqual(result.returncode, 2, result.stdout)
        return result.stderr

    def ignore_and_init(self):
        self.ok('ignore')
        self.ok('init')

    def test_generate_pdf_roundtrip_default_and_task_override(self):
        self.ignore_and_init()
        added = self.ok('set', '--profile', 'example', '--field', 'REPO=example-service')
        self.assertEqual(added['fields']['GENERATE_PDF'], 'T')
        self.ok('set', '--profile', 'example', '--field', 'GENERATE_PDF=F')
        self.assertIn('- Generate PDF: `F`', self.ok('render', '--profile', 'example'))
        task = self.root / 'TASK.md'
        task.write_text('# Task Title: demo\n\n## Resources\n\n- Generate PDF: `T`\n')
        self.ok('load', '--profile', 'example', '--task', str(task))
        self.assertIn('- Generate PDF: `T`', task.read_text())
        first = task.read_bytes()
        self.ok('load', '--profile', 'example', '--task', str(task), '--replace')
        self.assertEqual(task.read_bytes(), first)
        self.assertEqual(self.ok('show', '--profile', 'example')['fields']['GENERATE_PDF'], 'F')

    def test_generate_pdf_legacy_invalid_and_configuration_only(self):
        self.ignore_and_init()
        self.store.write_text('UNMANAGED="keep"\nPROFILE__example__REPO="example-service"\n')
        before = self.store.read_bytes()
        shown = self.ok('show', '--profile', 'example')
        self.assertEqual(shown['effective_generate_pdf'], 'T')
        self.assertIn('- Generate PDF: `T`', self.ok('render', '--profile', 'example'))
        self.assertEqual(self.store.read_bytes(), before)
        for bad in ('true', 't', 'False', '0', ' T'):
            self.assertIn('expected T or F', self.fails('set', '--profile', 'example',
                                                       '--field', 'GENERATE_PDF=' + bad))
            self.assertEqual(self.store.read_bytes(), before)
        self.assertIn('no actual resource', self.fails('set', '--profile', 'only',
                                                      '--field', 'GENERATE_PDF=F'))
        task = self.root / 'TASK.md'
        task.write_text('# Task Title: demo\n\n## Resources\n\n- Generate PDF: `false`\n')
        original = task.read_bytes()
        self.assertIn('expected T or F', self.fails('load', '--profile', 'example',
                                                  '--task', str(task), '--replace'))
        self.assertEqual(task.read_bytes(), original)
        task.write_text('# Task Title: demo\n\n## Resources\n\n- Generate PDF: `T`\n- Generate PDF: `F`\n')
        self.assertIn('duplicate Generate PDF', self.fails('load', '--profile', 'example',
                                                        '--task', str(task), '--replace'))

    def test_schema_is_derived_from_the_template_labels(self):
        schema = self.ok('schema')
        fields = {field['field']: field for field in schema['fields']}
        self.assertEqual(schema['template'], 'templates/TASK.md')
        self.assertEqual(set(fields), {'REPO', 'SLACK_CHANNEL', 'AWS_ACCOUNT', 'AWS_REGION',
                                       'GRAFANA_CONTEXT', 'ALERT', 'ALERT_UID', 'PUBLISH', 'RHYMING_ENDPOINTS', 'RHYMING_HISTORICAL_WINDOW_DAYS', 'GENERATE_PDF'})
        self.assertEqual(fields['REPO']['label'], 'Repo (Bitbucket/Github)')
        self.assertEqual(fields['ALERT_UID']['requires'], 'ALERT')
        self.assertIsNone(fields['ALERT']['requires'])

    def test_schema_follows_a_changed_template_and_rejects_its_unknown_field(self):
        self.template.write_text('# Task Title:\n\n## Resources\n\n'
                                 '- Datadog dashboard: `<enter dashboard>`\n', encoding='utf-8')
        schema = self.ok('schema')
        self.assertEqual([field['field'] for field in schema['fields']], ['DATADOG_DASHBOARD'])
        self.ignore_and_init()
        self.assertIn('unknown field REPO',
                      self.fails('set', '--profile', 'example', '--field', 'REPO=example-service'))

    def test_store_is_refused_until_git_ignores_it(self):
        self.assertIn('not ignored by Git',
                      self.fails('set', '--profile', 'example', '--field', 'REPO=example-service'))
        self.assertFalse(self.store.exists())
        self.assertIn('not ignored by Git', self.fails('init'))
        ignored = self.ok('ignore')
        self.assertTrue(ignored['verified'])
        self.assertIn('.env', (self.root / '.gitignore').read_text(encoding='utf-8').splitlines())
        created = self.ok('init')
        self.assertTrue(created['created'])
        self.assertEqual(created['mode'], '0o600')
        self.assertEqual(oct(self.store.stat().st_mode & 0o777), '0o600')

    def test_ignore_is_idempotent_and_dry_run_writes_nothing(self):
        self.assertEqual(self.ok('ignore', '--dry-run')['appended'][1], '.env')
        self.assertFalse((self.root / '.gitignore').exists())
        self.ok('ignore')
        repeated = self.ok('ignore')
        self.assertTrue(repeated['already_ignored'])
        self.assertEqual(repeated['appended'], [])

    def test_set_merges_fields_and_preserves_unmanaged_lines(self):
        self.ignore_and_init()
        with self.store.open('a', encoding='utf-8') as stream:
            stream.write('# local only\nUNRELATED_TOKEN="keep me"\n')
        self.ok('set', '--profile', 'example', '--field', 'REPO=example-service')
        merged = self.ok('set', '--profile', 'example', '--field', 'GRAFANA_CONTEXT=example')
        self.assertEqual(merged['fields'], {'REPO': 'example-service',
                                            'GRAFANA_CONTEXT': 'example', 'RHYMING_HISTORICAL_WINDOW_DAYS': '7', 'GENERATE_PDF': 'T'})
        self.assertEqual(merged['added'], ['GRAFANA_CONTEXT'])
        contents = self.store.read_text(encoding='utf-8')
        self.assertIn('# local only\nUNRELATED_TOKEN="keep me"\n', contents)
        self.assertIn("PROFILE__EXAMPLE__REPO='example-service'", contents)
        replaced = self.ok('set', '--profile', 'example', '--replace',
                           '--field', 'REPO=example-service')
        self.assertEqual(replaced['fields'], {'REPO': 'example-service', 'GENERATE_PDF': 'T'})
        self.assertEqual(replaced['cleared'], ['GRAFANA_CONTEXT', 'RHYMING_HISTORICAL_WINDOW_DAYS'])
        cleared = self.ok('set', '--profile', 'example', '--field', 'REPO=other-service',
                          '--field', 'GRAFANA_CONTEXT=')
        self.assertEqual(cleared['fields'], {'REPO': 'other-service', 'GENERATE_PDF': 'T'})
        self.assertIn('UNRELATED_TOKEN="keep me"', self.store.read_text(encoding='utf-8'))

    def test_dependent_field_requires_its_primary_field(self):
        self.ignore_and_init()
        self.assertIn('ALERT_UID requires ALERT',
                      self.fails('set', '--profile', 'example', '--field', 'ALERT_UID=abc123'))
        self.ok('set', '--profile', 'example', '--field', 'ALERT=Checkout latency',
                '--field', 'ALERT_UID=abc123')
        self.assertIn('- Alert: `Checkout latency`; UID `abc123`',
                      self.ok('render', '--profile', 'example'))

    def test_placeholder_example_and_credential_values_are_refused(self):
        self.ignore_and_init()
        self.assertIn('placeholders and examples are not resources',
                      self.fails('set', '--profile', 'example', '--field', 'PUBLISH=<Parent page>'))
        self.assertIn('looks like a credential',
                      self.fails('set', '--profile', 'example',
                                 '--field', 'PUBLISH=' + 'xoxb' + '-1234567890-abcdefabcdef'))
        self.assertIn('single quote',
                      self.fails('set', '--profile', 'example', '--field', "REPO=it's-a-repo"))
        self.assertFalse(self.store.read_text(encoding='utf-8'))

    def test_list_and_show_report_status_without_leaking_unmanaged_values(self):
        self.ignore_and_init()
        with self.store.open('a', encoding='utf-8') as stream:
            stream.write('UNRELATED_TOKEN="keep me"\n')
        self.ok('set', '--profile', 'example', '--field', 'REPO=example-service')
        self.ok('set', '--profile', 'other-team', '--field', 'GRAFANA_CONTEXT=other')
        listed = self.ok('list')
        self.assertEqual(listed['profiles'], ['example', 'other-team'])
        self.assertTrue(listed['ignored'])
        self.assertFalse(listed['tracked'])
        self.assertNotIn('keep me', json.dumps(listed))
        shown = self.ok('show', '--profile', 'example')
        self.assertEqual(shown['fields'], {'REPO': 'example-service',
                                           'RHYMING_HISTORICAL_WINDOW_DAYS': '7', 'GENERATE_PDF': 'T'})
        self.assertIn('PUBLISH', shown['missing_fields'])
        self.assertEqual(shown['unknown_fields'], [])
        self.assertNotIn('keep me', json.dumps(shown))
        self.assertIn('is not in the store', self.fails('show', '--profile', 'absent'))

    def test_remove_deletes_one_profile_and_keeps_the_rest(self):
        self.ignore_and_init()
        self.ok('set', '--profile', 'example', '--field', 'REPO=example-service')
        self.ok('set', '--profile', 'other-team', '--field', 'GRAFANA_CONTEXT=other')
        preview = self.ok('remove', '--profile', 'example', '--dry-run')
        self.assertEqual(preview['remaining_profiles'], ['other-team'])
        self.assertIn('PROFILE__EXAMPLE__REPO', self.store.read_text(encoding='utf-8'))
        removed = self.ok('remove', '--profile', 'example')
        self.assertEqual(removed['remaining_profiles'], ['other-team'])
        contents = self.store.read_text(encoding='utf-8')
        self.assertNotIn('EXAMPLE', contents)
        self.assertIn("PROFILE__OTHER_TEAM__GRAFANA_CONTEXT='other'", contents)
        self.assertIn('is not in the store', self.fails('remove', '--profile', 'example'))

    def test_remove_env_protects_unmanaged_keys_until_forced(self):
        self.ignore_and_init()
        self.ok('set', '--profile', 'example', '--field', 'REPO=example-service')
        with self.store.open('a', encoding='utf-8') as stream:
            stream.write('UNRELATED_TOKEN="keep me"\n')
        self.assertIn('unmanaged keys (UNRELATED_TOKEN)', self.fails('remove-env'))
        self.assertTrue(self.store.exists())
        preview = self.ok('remove-env', '--force', '--dry-run')
        self.assertFalse(preview['deleted'])
        self.assertEqual(preview['unmanaged_keys'], ['UNRELATED_TOKEN'])
        self.assertTrue(self.store.exists())
        deleted = self.ok('remove-env', '--force')
        self.assertTrue(deleted['deleted'])
        self.assertFalse(self.store.exists())
        self.assertIn('does not exist', self.fails('remove-env'))

    def test_tracked_or_symlinked_store_is_refused(self):
        self.ignore_and_init()
        self.ok('set', '--profile', 'example', '--field', 'REPO=example-service')
        self.git('add', '-f', '.env')
        self.assertIn('tracked by Git',
                      self.fails('set', '--profile', 'example', '--field', 'REPO=other-service'))
        self.assertIn('tracked by Git', self.fails('remove', '--profile', 'example'))
        self.git('rm', '--cached', '-q', '.env')
        target = self.root / '.env.real'
        self.store.rename(target)
        os.symlink(target.name, self.store)
        self.assertIn('regular non-symlink file', self.fails('list'))

    def test_load_fills_task_resources_and_protects_supplied_values(self):
        self.ignore_and_init()
        self.ok('set', '--profile', 'example', '--field', 'REPO=example-service',
                '--field', 'SLACK_CHANNEL=#example-support')
        task = self.root / 'docs' / 'tasks' / 'TASK.md'
        task.parent.mkdir(parents=True)
        task.write_text(self.template.read_text(encoding='utf-8'), encoding='utf-8')
        original = task.read_text(encoding='utf-8')
        preview = self.ok('load', '--profile', 'example', '--task', 'docs/tasks/TASK.md',
                          '--dry-run')
        self.assertEqual(preview['resources'],
                         ['- Repo (Bitbucket/Github): `example-service`',
                          '- Slack channel: `#example-support`', '- Generate PDF: `T`'])
        self.assertFalse(preview['replaced'])
        self.assertEqual(task.read_text(encoding='utf-8'), original)
        loaded = self.ok('load', '--profile', 'example', '--task', 'docs/tasks/TASK.md')
        self.assertTrue(loaded['verified'])
        body = task.read_text(encoding='utf-8')
        self.assertIn('## Resources\n\n- Repo (Bitbucket/Github): `example-service`\n'
                      '- Slack channel: `#example-support`\n', body)
        self.assertNotIn('<enter repo name>', body)
        self.assertIn('## Acceptance Tests', body)
        self.assertIn('already supplies example-service',
                      self.fails('load', '--profile', 'example', '--task', 'docs/tasks/TASK.md'))
        self.assertTrue(self.ok('load', '--profile', 'example', '--task',
                                'docs/tasks/TASK.md', '--replace')['replaced'])

    def test_load_requires_an_actual_resource_and_an_existing_section(self):
        self.ignore_and_init()
        self.ok('set', '--profile', 'empty', '--field', 'REPO=example-service')
        self.ok('set', '--profile', 'empty', '--replace', '--field', 'REPO=')
        self.assertEqual(self.ok('list')['profiles'], [])
        self.assertIn('is not in the store',
                      self.fails('render', '--profile', 'empty'))
        task = self.root / 'TASK.md'
        task.write_text('# Task Title: no resources\n', encoding='utf-8')
        self.ok('set', '--profile', 'example', '--field', 'REPO=example-service')
        self.assertIn('exactly one "## Resources" section',
                      self.fails('load', '--profile', 'example', '--task', 'TASK.md'))
        self.assertIn('task does not exist',
                      self.fails('load', '--profile', 'example', '--task', 'absent/TASK.md'))

    def test_malformed_managed_key_fails_closed(self):
        self.ignore_and_init()
        self.store.write_text("PROFILE__BROKEN='value'\n", encoding='utf-8')
        self.assertIn('not PROFILE__NAME__FIELD', self.fails('list'))

    def test_store_is_tightened_while_other_files_keep_their_mode(self):
        self.ok('ignore')
        (self.root / '.gitignore').chmod(0o644)
        self.store.write_text('UNRELATED_TOKEN="keep me"\n', encoding='utf-8')
        self.store.chmod(0o644)
        self.ok('set', '--profile', 'example', '--field', 'REPO=example-service')
        self.assertEqual(oct(self.store.stat().st_mode & 0o777), '0o600')
        self.assertIn('UNRELATED_TOKEN="keep me"', self.store.read_text(encoding='utf-8'))
        self.store.chmod(0o644)
        self.ok('remove', '--profile', 'example')
        self.assertEqual(oct(self.store.stat().st_mode & 0o777), '0o600')
        # The .gitignore and the task are ordinary repository files, not the store.
        self.assertEqual(oct((self.root / '.gitignore').stat().st_mode & 0o777), '0o644')
        self.ok('set', '--profile', 'example', '--field', 'REPO=example-service')
        task = self.root / 'TASK.md'
        task.write_text(self.template.read_text(encoding='utf-8'), encoding='utf-8')
        task.chmod(0o644)
        self.ok('load', '--profile', 'example', '--task', 'TASK.md')
        self.assertEqual(oct(task.stat().st_mode & 0o777), '0o644')

    def test_profile_name_and_field_syntax_are_validated(self):
        self.ignore_and_init()
        self.assertIn('lowercase kebab-case',
                      self.fails('set', '--profile', 'Example', '--field', 'REPO=example-service'))
        self.assertIn('FIELD=value',
                      self.fails('set', '--profile', 'example', '--field', 'REPO'))
        self.assertIn('at least one FIELD=value', self.fails('set', '--profile', 'example'))


if __name__ == '__main__':
    unittest.main()
