"""Exercise the profile store helper through its public command-line interface."""
import importlib.util
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


def load_helper():
    specification = importlib.util.spec_from_file_location('profile_env', HELPER)
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module


# Assert against the helper's own setting constants rather than repeating their spelling.
PROFILE_ENV = load_helper()
ENABLED, DISABLED = PROFILE_ENV.ENABLED, PROFILE_ENV.DISABLED
TOGGLE_ERROR = PROFILE_ENV.TOGGLE_ERROR.lstrip('; ')
TOGGLES = tuple(PROFILE_ENV.CONTROL_DEFAULTS)


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

    def test_grafana_assistant_schema_and_profile_roundtrip(self):
        fields = {entry['field']: entry for entry in self.ok('schema')['fields']}
        self.assertEqual(fields['GRAFANA_ASSISTANT']['enum'], [ENABLED, DISABLED])
        self.assertEqual(fields['GRAFANA_ASSISTANT']['default'], ENABLED)
        self.assertFalse(fields['GRAFANA_ASSISTANT']['resource'])
        self.ignore_and_init()
        self.ok('set', '--profile', 'ops', '--field', 'GRAFANA_CONTEXT=ops')
        self.assertEqual(self.ok('show', '--profile', 'ops')['fields']['GRAFANA_ASSISTANT'],
                         ENABLED)
        self.ok('set', '--profile', 'ops', '--field', 'GRAFANA_ASSISTANT=disabled')
        self.assertIn('- Grafana Assistant: `disabled`', self.ok('render', '--profile', 'ops'))
        self.ok('set', '--profile', 'ops', '--field', 'REPO=service-a')
        self.assertEqual(self.ok('show', '--profile', 'ops')['fields']['GRAFANA_ASSISTANT'],
                         DISABLED)
        self.ok('set', '--profile', 'ops', '--field', 'GRAFANA_ASSISTANT=')
        self.assertNotIn('GRAFANA_ASSISTANT', self.ok('show', '--profile', 'ops')['fields'])
        self.assertEqual(self.ok('show', '--profile', 'ops')['effective_grafana_assistant'],
                         ENABLED)

    def test_grafana_assistant_legacy_default_validation_and_no_resource(self):
        self.ignore_and_init()
        self.store.write_text("UNMANAGED='keep'\nPROFILE__OPS__GRAFANA_CONTEXT='ops'\n")
        before = self.store.read_bytes()
        self.assertEqual(self.ok('show', '--profile', 'ops')['effective_grafana_assistant'],
                         ENABLED)
        self.assertIn('- Grafana Assistant: `enabled`', self.ok('render', '--profile', 'ops'))
        self.assertEqual(self.store.read_bytes(), before)
        for bad in ('false', 'False', 'off', 'no', 'disable'):
            self.assertIn(TOGGLE_ERROR, self.fails('set', '--profile', 'ops',
                          '--field', 'GRAFANA_ASSISTANT=' + bad))
            self.assertEqual(self.store.read_bytes(), before)
        self.assertIn('no actual resource', self.fails('set', '--profile', 'only',
                      '--field', 'GRAFANA_ASSISTANT=disabled'))
        self.assertEqual(self.store.read_bytes(), before)
        self.store.write_text("PROFILE__OPS__GRAFANA_CONTEXT='ops'\n"
                              "PROFILE__OPS__GRAFANA_ASSISTANT='off'\n")
        task = self.root / 'TASK.md'; task.write_text('## Resources\n')
        for command in ('show', 'render', 'endpoints', 'load'):
            extra = ('--task', str(task)) if command == 'load' else ()
            self.assertIn(TOGGLE_ERROR,
                          self.fails(command, '--profile', 'ops', *extra))
        self.assertEqual(task.read_text(), '## Resources\n')

    def test_grafana_assistant_task_and_command_precedence_are_idempotent(self):
        self.ignore_and_init()
        self.ok('set', '--profile', 'ops', '--field', 'GRAFANA_CONTEXT=ops')
        task = self.root / 'TASK.md'
        task.write_text('## Resources\n- Grafana Assistant: disabled\n- Fan-out: disabled\n')
        self.ok('load', '--profile', 'ops', '--task', str(task))
        self.assertIn('- Grafana Assistant: `disabled`', task.read_text())
        self.assertIn('- Fan-out: `disabled`', task.read_text())
        first = task.read_bytes()
        self.ok('load', '--profile', 'ops', '--task', str(task), '--replace')
        self.assertEqual(task.read_bytes(), first)
        self.ok('load', '--profile', 'ops', '--task', str(task), '--replace',
                '--field', 'GRAFANA_ASSISTANT=enabled')
        self.assertIn('- Grafana Assistant: `enabled`', task.read_text())
        self.assertEqual(self.ok('show', '--profile', 'ops')['fields']['GRAFANA_ASSISTANT'],
                         ENABLED)
        for setting in ('- Grafana Assistant: `off`',
                        '- Grafana Assistant: disabled\n- Grafana Assistant: `enabled`'):
            task.write_text('## Resources\n' + setting + '\n')
            before = task.read_bytes()
            self.fails('load', '--profile', 'ops', '--task', str(task), '--replace')
            self.assertEqual(task.read_bytes(), before)

    def test_grafana_assistant_composition_conflicts_and_override(self):
        self.ignore_and_init()
        self.ok('set', '--profile', 'one', '--field', 'REPO=service-a',
                '--field', 'GRAFANA_ASSISTANT=disabled')
        self.ok('set', '--profile', 'two', '--field', 'REPO=service-b')
        before = self.store.read_bytes()
        self.assertIn('conflicting field GRAFANA_ASSISTANT',
                      self.fails('compose', '--profile', 'one', '--profile', 'two', '--into', 'out'))
        self.assertEqual(self.store.read_bytes(), before)
        self.ok('compose', '--profile', 'one', '--profile', 'two', '--into', 'out',
                '--field', 'GRAFANA_ASSISTANT=disabled')
        self.assertEqual(self.ok('show', '--profile', 'out')['fields']['GRAFANA_ASSISTANT'],
                         DISABLED)
        self.assertTrue(self.store.read_bytes().startswith(before))

    def test_generate_pdf_roundtrip_default_and_task_override(self):
        self.ignore_and_init()
        added = self.ok('set', '--profile', 'example', '--field', 'REPO=example-service')
        self.assertEqual(added['fields']['GENERATE_PDF'], ENABLED)
        self.ok('set', '--profile', 'example', '--field', 'GENERATE_PDF=disabled')
        self.assertIn('- Generate PDF: `disabled`', self.ok('render', '--profile', 'example'))
        task = self.root / 'TASK.md'
        task.write_text('# Task Title: demo\n\n## Resources\n\n- Generate PDF: `enabled`\n')
        self.ok('load', '--profile', 'example', '--task', str(task))
        self.assertIn('- Generate PDF: `enabled`', task.read_text())
        first = task.read_bytes()
        self.ok('load', '--profile', 'example', '--task', str(task), '--replace')
        self.assertEqual(task.read_bytes(), first)
        self.assertEqual(self.ok('show', '--profile', 'example')['fields']['GENERATE_PDF'], DISABLED)

    def test_generate_pdf_legacy_invalid_and_configuration_only(self):
        self.ignore_and_init()
        self.store.write_text('UNMANAGED="keep"\nPROFILE__example__REPO="example-service"\n')
        before = self.store.read_bytes()
        shown = self.ok('show', '--profile', 'example')
        self.assertEqual(shown['effective_generate_pdf'], ENABLED)
        self.assertIn('- Generate PDF: `enabled`', self.ok('render', '--profile', 'example'))
        self.assertEqual(self.store.read_bytes(), before)
        for bad in ('true', 'False', '0', 'on', 'yes', 'enable'):
            self.assertIn(TOGGLE_ERROR, self.fails('set', '--profile', 'example',
                                                       '--field', 'GENERATE_PDF=' + bad))
            self.assertEqual(self.store.read_bytes(), before)
        self.assertIn('no actual resource', self.fails('set', '--profile', 'only',
                                                      '--field', 'GENERATE_PDF=disabled'))
        task = self.root / 'TASK.md'
        task.write_text('# Task Title: demo\n\n## Resources\n\n- Generate PDF: `false`\n')
        original = task.read_bytes()
        self.assertIn(TOGGLE_ERROR, self.fails('load', '--profile', 'example',
                                                  '--task', str(task), '--replace'))
        self.assertEqual(task.read_bytes(), original)
        task.write_text('# Task Title: demo\n\n## Resources\n\n- Generate PDF: `enabled`\n- Generate PDF: `disabled`\n')
        self.assertIn('duplicate Generate PDF', self.fails('load', '--profile', 'example',
                                                        '--task', str(task), '--replace'))

    def test_toggle_settings_share_one_enabled_disabled_contract(self):
        self.ignore_and_init()
        schema = {field['field']: field for field in self.ok('schema')['fields']}
        for toggle in TOGGLES:
            self.assertEqual(schema[toggle]['type'], 'enum')
            self.assertEqual(schema[toggle]['enum'], list(PROFILE_ENV.TOGGLE_VALUES))
            self.assertEqual(schema[toggle]['default'], ENABLED)
            self.assertFalse(schema[toggle]['resource'])
            self.ok('set', '--profile', 'example', '--field', 'REPO=example-service',
                    '--field', toggle + '=disabled')
            self.assertIn(TOGGLE_ERROR,
                          self.fails('set', '--profile', 'example', '--field', toggle + '=off'))
        self.assertEqual(schema['GENERATE_PDF']['legacy_values'], {'T': ENABLED, 'F': DISABLED})
        task = self.root / 'TASK.md'
        task.write_text('## Resources\n\n- Generate PDF: enabled\n- Grafana Assistant: enabled\n')
        self.ok('load', '--profile', 'example', '--task', str(task))
        self.assertIn('- Generate PDF: `enabled`', task.read_text())
        self.assertIn('- Grafana Assistant: `enabled`', task.read_text())

    def test_fan_out_profile_setting_default_task_override_and_unknown_controls(self):
        self.ignore_and_init()
        added = self.ok('set', '--profile', 'example', '--field', 'REPO=example-service')
        self.assertEqual(added['fields']['FAN_OUT'], ENABLED)
        self.assertEqual(self.ok('show', '--profile', 'example')['effective_fan_out'], ENABLED)
        self.ok('set', '--profile', 'example', '--field', 'FAN_OUT=disabled')
        self.assertIn('- Fan-out: `disabled`', self.ok('render', '--profile', 'example'))
        # The saved task wins over the profile; controls outside the template are preserved.
        task = self.root / 'TASK.md'
        task.write_text('## Resources\n\n- Fan-out: enabled\n- Owner: platform\n')
        self.ok('load', '--profile', 'example', '--task', str(task))
        self.assertIn('- Fan-out: `enabled`', task.read_text())
        self.assertIn('- Owner: platform', task.read_text())
        self.assertIn('no actual resource', self.fails('set', '--profile', 'only',
                                                      '--field', 'FAN_OUT=disabled'))
        # A profile stored before the setting existed resolves the default without a rewrite.
        self.store.write_text("PROFILE__OLD__REPO='example-service'\n")
        before = self.store.read_bytes()
        self.assertEqual(self.ok('show', '--profile', 'old')['effective_fan_out'], ENABLED)
        self.assertIn('- Fan-out: `enabled`', self.ok('render', '--profile', 'old'))
        self.assertEqual(self.store.read_bytes(), before)

    def test_setting_names_and_values_accept_flexible_spelling(self):
        self.ignore_and_init()
        self.ok('set', '--profile', 'example', '--field', 'REPO=example-service')
        # Names ignore case, spaces, hyphens and underscores; "=" and ":" both delimit.
        for assignment, stored in (('fan out=disabled', DISABLED), ('fan_out=ENABLED', ENABLED),
                                   ('FAN OUT: DISABLED', DISABLED), ('Fan-out:enabled', ENABLED),
                                   ('fanout: Disabled', DISABLED), (' fan out : enabled ', ENABLED)):
            result = self.ok('set', '--profile', 'example', '--field', assignment)
            self.assertEqual(result['fields']['FAN_OUT'], stored, assignment)
        self.assertIn("PROFILE__EXAMPLE__FAN_OUT='enabled'", self.store.read_text())
        # Template labels work as names, for resources as well as settings.
        result = self.ok('set', '--profile', 'example', '--field', 'generate pdf: Disabled',
                         '--field', 'grafana assistant: DISABLED',
                         '--field', 'slack channel: #example-support',
                         '--field', 'publish: https://example.atlassian.net/wiki/spaces/OPS')
        self.assertEqual(result['fields']['GENERATE_PDF'], DISABLED)
        self.assertEqual(result['fields']['GRAFANA_ASSISTANT'], DISABLED)
        self.assertEqual(result['fields']['SLACK_CHANNEL'], '#example-support')
        self.assertEqual(result['fields']['PUBLISH'], 'https://example.atlassian.net/wiki/spaces/OPS')
        # Legacy spellings translate to the same constants in any case.
        for spelling, stored in (('T', ENABLED), ('f', DISABLED), (' t ', ENABLED)):
            result = self.ok('set', '--profile', 'example', '--field', 'generate pdf:' + spelling)
            self.assertEqual(result['fields']['GENERATE_PDF'], stored)
        # "=" first keeps a value containing ":" intact; an empty colon value clears.
        self.ok('set', '--profile', 'example', '--field', 'REPO=ssh://git@example.com/org/repo.git')
        self.ok('set', '--profile', 'example', '--field', 'slack channel:')
        shown = self.ok('show', '--profile', 'example')['fields']
        self.assertEqual(shown['REPO'], 'ssh://git@example.com/org/repo.git')
        self.assertNotIn('SLACK_CHANNEL', shown)
        before = self.store.read_bytes()
        for bad in ('fan out', 'fan out disabled', 'fanned out: disabled', ': disabled',
                    'fan out: off'):
            self.fails('set', '--profile', 'example', '--field', bad)
            self.assertEqual(self.store.read_bytes(), before)
        # Load overrides and task bullets follow the same rules.
        task = self.root / 'TASK.md'
        task.write_text('## Resources\n\n- fan out: DISABLED\n- GENERATE_PDF: `Enabled`\n')
        self.ok('load', '--profile', 'example', '--task', str(task),
                '--field', 'grafana assistant: ENABLED')
        text = task.read_text()
        self.assertIn('- Fan-out: `disabled`', text)
        self.assertIn('- Generate PDF: `enabled`', text)
        self.assertIn('- Grafana Assistant: `enabled`', text)
        self.assertEqual(text.count('- Fan-out:'), 1)
        self.assertNotIn('fan out', text)

    def lint(self, *arguments):
        result = self.run_helper('lint', *arguments)
        self.assertIn(result.returncode, (0, 1), result.stderr)
        report = json.loads(result.stdout)
        return result.returncode, report, [(item['rule'], item['location'], item['fixable'])
                                           for item in report['findings']]

    def test_lint_reports_and_fixes_hand_edited_store_settings(self):
        self.ignore_and_init()
        self.ok('set', '--profile', 'team', '--field', 'REPO=example-service',
                '--field', 'FAN_OUT=' + DISABLED)
        self.assertEqual(self.lint(), (0, self.lint()[1], []))
        with self.store.open('a') as stream:
            stream.write('OTHER="keep me"\n'
                         'PROFILE__team__generate_pdf="F"\n'               # duplicate, differs
                         "PROFILE__TEAM__Fan_Out='DISABLED'\n"             # duplicate, agrees
                         'PROFILE__team__slack_channel="#example-support"\n'
                         'export PROFILE__TEAM__AWS_REGION=us-east-1\n'
                         "PROFILE__TEAM__NOT_A_FIELD='x'\n"
                         "PROFILE__TEAM__GRAFANA_CONTEXT='<enter gcx profile>'\n")
        before = self.store.read_bytes()
        status, report, rules = self.lint()
        self.assertEqual(status, 1)
        self.assertEqual(sorted(rules), sorted([
            ('conflicting-duplicate', 'store', False), ('duplicate', 'store', True),
            ('key-spelling', 'store', True), ('formatting', 'store', True),
            ('unknown-field', 'store', False), ('invalid-value', 'store', False)]))
        self.assertFalse(report['clean'])
        self.assertEqual((report['fixable'], report['unfixable'], report['fixed']), (3, 3, 0))
        # Findings name fields and lines, never stored values.
        self.assertNotIn('example-support', json.dumps(report))
        self.assertNotIn('keep me', json.dumps(report))
        # Reporting and --dry-run never write.
        self.assertEqual(self.store.read_bytes(), before)
        self.lint('--fix', '--dry-run')
        self.assertEqual(self.store.read_bytes(), before)
        status, report, _ = self.lint('--fix')
        self.assertEqual((status, report['fixed'], report['clean']), (1, 3, False))
        text = self.store.read_text()
        self.assertIn("PROFILE__TEAM__SLACK_CHANNEL='#example-support'\n", text)
        self.assertIn("PROFILE__TEAM__AWS_REGION='us-east-1'\n", text)
        self.assertEqual(text.upper().count('__FAN_OUT='), 1)
        # Unrelated lines and findings only the user can resolve are left exactly as written.
        self.assertIn('OTHER="keep me"\n', text)
        self.assertIn('PROFILE__team__generate_pdf="F"\n', text)
        self.assertIn("PROFILE__TEAM__NOT_A_FIELD='x'\n", text)
        self.assertEqual(oct(self.store.stat().st_mode & 0o777), '0o600')
        # A second pass finds only what needs a decision, and is idempotent.
        fixed = self.store.read_bytes()
        status, _, rules = self.lint('--fix')
        self.assertEqual(status, 1)
        self.assertTrue(all(not fixable for _, _, fixable in rules))
        self.assertEqual(self.store.read_bytes(), fixed)
        # --profile limits findings to that profile.
        self.assertEqual(self.lint('--profile', 'other')[2], [])

    def test_lint_updates_legacy_values_and_other_commands_ask_for_it(self):
        self.ignore_and_init()
        self.ok('set', '--profile', 'new', '--field', 'REPO=example-service')
        self.assertNotIn('lint_notice', self.ok('show', '--profile', 'new'))
        # A store written before the settings contract holds T and F.
        self.store.write_text("# profile: old\nPROFILE__OLD__GENERATE_PDF='F'\n"
                              "PROFILE__OLD__REPO='example-service'\n"
                              "\n# profile: older\nPROFILE__OLDER__GENERATE_PDF='T'\n"
                              "PROFILE__OLDER__REPO='other-service'\n")
        before = self.store.read_bytes()
        # Every other command still works, reports the store, and leaves it untouched.
        shown = self.ok('show', '--profile', 'old')
        self.assertEqual(shown['fields']['GENERATE_PDF'], DISABLED)
        notice = shown['lint_notice']
        self.assertEqual((notice['findings'], notice['fixable'], notice['needs_decision']),
                         (2, 2, 0))
        self.assertEqual(notice['rules'], ['legacy-value'])
        self.assertIn('lint profiles', notice['message'])
        self.assertIn('lint_notice', self.ok('list'))
        rendered = self.run_helper('render', '--profile', 'old')
        self.assertEqual(rendered.returncode, 0)
        self.assertIn('lint profiles', rendered.stderr)
        self.assertIn('- Generate PDF: `' + DISABLED + '`', rendered.stdout)
        self.assertEqual(self.store.read_bytes(), before)
        status, report, rules = self.lint()
        self.assertEqual((status, rules), (1, [('legacy-value', 'store', True)] * 2))
        self.assertEqual([item['canonical'] for item in report['findings']], [DISABLED, ENABLED])
        status, report, _ = self.lint('--fix')
        self.assertEqual((status, report['clean'], report['fixed']), (0, True, 2))
        self.assertEqual(self.store.read_text(),
                         "# profile: old\nPROFILE__OLD__GENERATE_PDF='" + DISABLED + "'\n"
                         "PROFILE__OLD__REPO='example-service'\n"
                         "\n# profile: older\nPROFILE__OLDER__GENERATE_PDF='" + ENABLED + "'\n"
                         "PROFILE__OLDER__REPO='other-service'\n")
        self.assertNotIn('lint_notice', self.ok('show', '--profile', 'old'))

    def test_store_lint_prompts_for_tasks_with_illegal_values_without_editing_them(self):
        self.ignore_and_init()
        self.ok('set', '--profile', 'team', '--field', 'REPO=example-service')
        self.assertNotIn('task_notice', self.lint()[1])
        tasks = self.root / 'docs' / 'tasks'
        tasks.mkdir(parents=True)
        (tasks / 'TASK.md').write_text('## Resources\n\n- Fan-out: `off`\n- generate pdf: T\n')
        (tasks / 'TASK-clean.md').write_text('## Resources\n\n- Fan-out: `' + DISABLED + '`\n')
        (tasks / 'notes.md').write_text('## Resources\n\n- Fan-out: `off`\n')
        before = (tasks / 'TASK.md').read_bytes()
        status, report, rules = self.lint('--fix')
        # The store is clean; the task findings are a prompt, not part of this lint.
        self.assertEqual((status, rules, report['clean']), (0, [], True))
        notice = report['task_notice']
        self.assertEqual(notice['tasks'], [{
            'task': 'docs/tasks/TASK.md', 'findings': 3, 'fixable': 2, 'needs_decision': 1,
            'rules': ['invalid-value', 'label-spelling', 'legacy-value']}])
        self.assertIn('lint task', notice['message'])
        self.assertIn('legal', notice['message'])
        self.assertEqual((tasks / 'TASK.md').read_bytes(), before)
        # Linting the named task fixes what it can and leaves the illegal value for the user.
        status, report, _ = self.lint('--task', 'docs/tasks/TASK.md', '--fix')
        self.assertEqual((status, report['fixed'], report['unfixable']), (1, 2, 1))
        self.assertNotIn('task_notice', report)
        self.assertEqual((tasks / 'TASK.md').read_text(),
                         '## Resources\n\n- Fan-out: `off`\n- Generate PDF: `' + ENABLED + '`\n')
        (tasks / 'TASK.md').write_text('## Resources\n\n- Fan-out: `' + DISABLED + '`\n')
        self.assertNotIn('task_notice', self.lint()[1])

    def test_lint_reports_and_fixes_hand_edited_task_settings(self):
        self.ignore_and_init()
        task = self.root / 'TASK.md'
        task.write_text('# Task Title: demo\n\n## Resources\n\n- fan out: DISABLED\n'
                        '- generate_pdf: `F`\n- Slack Channel: `#example-support`\n'
                        '- Owner: platform\n\n## Notes\n\n- fan out: untouched\n')
        before = task.read_bytes()
        status, report, rules = self.lint('--task', str(task))
        self.assertEqual(status, 1)
        self.assertEqual(sorted(rules), sorted([('label-spelling', 'task', True)] * 3
                                               + [('value-spelling', 'task', True),
                                                  ('legacy-value', 'task', True)]))
        self.assertEqual(task.read_bytes(), before)
        status, report, _ = self.lint('--task', str(task), '--fix')
        self.assertEqual((status, report['clean'], report['fixed']), (0, True, 5))
        self.assertEqual(task.read_text(),
                         '# Task Title: demo\n\n## Resources\n\n- Fan-out: `' + DISABLED + '`\n'
                         '- Generate PDF: `' + DISABLED + '`\n- Slack channel: `#example-support`\n'
                         '- Owner: platform\n\n## Notes\n\n- fan out: untouched\n')
        self.assertEqual(self.lint('--task', str(task)), (0, self.lint('--task', str(task))[1], []))
        # A value that is not a setting value needs the user and is never guessed.
        task.write_text('## Resources\n\n- Fan-out: `off`\n- Generate PDF: `' + ENABLED + '`\n'
                        '- Generate PDF: `' + DISABLED + '`\n')
        before = task.read_bytes()
        status, _, rules = self.lint('--task', str(task), '--fix')
        self.assertEqual(status, 1)
        self.assertEqual(sorted(rules), [('conflicting-duplicate', 'task', False),
                                         ('invalid-value', 'task', False)])
        self.assertEqual(task.read_bytes(), before)

    def test_generate_pdf_legacy_values_resolve_and_normalize_on_write(self):
        self.ignore_and_init()
        self.store.write_text("PROFILE__OLD__REPO='example-service'\n"
                              "PROFILE__OLD__GENERATE_PDF='F'\n")
        before = self.store.read_bytes()
        shown = self.ok('show', '--profile', 'old')
        self.assertEqual(shown['fields']['GENERATE_PDF'], DISABLED)
        self.assertEqual(shown['effective_generate_pdf'], DISABLED)
        self.assertIn('- Generate PDF: `disabled`', self.ok('render', '--profile', 'old'))
        # Reads never migrate the store.
        self.assertEqual(self.store.read_bytes(), before)
        task = self.root / 'TASK.md'
        task.write_text('## Resources\n\n- Generate PDF: `T`\n')
        self.ok('load', '--profile', 'old', '--task', str(task))
        self.assertIn('- Generate PDF: `enabled`', task.read_text())
        # A legacy value supplied on a command is stored in canonical form.
        self.assertEqual(self.ok('set', '--profile', 'new', '--field', 'REPO=repo',
                                 '--field', 'GENERATE_PDF=F')['fields']['GENERATE_PDF'], DISABLED)
        # The next update of a legacy profile rewrites its stored toggle canonically.
        self.ok('set', '--profile', 'old', '--field', 'AWS_REGION=us-east-1')
        self.assertIn("PROFILE__OLD__GENERATE_PDF='disabled'", self.store.read_text())
        self.assertNotIn("GENERATE_PDF='F'", self.store.read_text())

    def test_schema_is_derived_from_the_template_labels(self):
        schema = self.ok('schema')
        fields = {field['field']: field for field in schema['fields']}
        self.assertEqual(schema['template'], 'templates/TASK.md')
        self.assertEqual(set(fields), {'REPO', 'SLACK_CHANNEL', 'AWS_ACCOUNT', 'AWS_REGION',
                                       'GRAFANA_CONTEXT', 'ALERT', 'ALERT_UID', 'PUBLISH', 'RHYMING_ENDPOINTS', 'RHYMING_HISTORICAL_WINDOW_DAYS', 'GENERATE_PDF', 'GRAFANA_ASSISTANT', 'FAN_OUT'})
        self.assertEqual(fields['REPO']['label'], 'Repo (Bitbucket/Github)')
        self.assertEqual(fields['ALERT_UID']['requires'], 'ALERT')
        self.assertIsNone(fields['ALERT']['requires'])

    def test_schema_follows_a_changed_template_and_rejects_its_unknown_field(self):
        self.template.write_text('# Task Title:\n\n## Resources\n\n'
                                 '- Datadog dashboard: `<enter dashboard>`\n', encoding='utf-8')
        schema = self.ok('schema')
        self.assertEqual([field['field'] for field in schema['fields']], ['DATADOG_DASHBOARD'])
        self.ignore_and_init()
        self.ok('set', '--profile', 'custom', '--field', 'DATADOG_DASHBOARD=dashboard-a')
        shown = self.ok('show', '--profile', 'custom')
        self.assertIsNone(shown['effective_grafana_assistant'])
        self.assertNotIn('GRAFANA_ASSISTANT', shown['fields'])
        self.assertNotIn('Grafana Assistant:', self.ok('render', '--profile', 'custom'))
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
                                            'GRAFANA_CONTEXT': 'example', 'RHYMING_HISTORICAL_WINDOW_DAYS': '7', 'GENERATE_PDF': ENABLED, 'GRAFANA_ASSISTANT': ENABLED, 'FAN_OUT': ENABLED})
        self.assertEqual(merged['added'], ['GRAFANA_CONTEXT'])
        contents = self.store.read_text(encoding='utf-8')
        self.assertIn('# local only\nUNRELATED_TOKEN="keep me"\n', contents)
        self.assertIn("PROFILE__EXAMPLE__REPO='example-service'", contents)
        replaced = self.ok('set', '--profile', 'example', '--replace',
                           '--field', 'REPO=example-service')
        self.assertEqual(replaced['fields'], {'REPO': 'example-service', 'GENERATE_PDF': ENABLED, 'GRAFANA_ASSISTANT': ENABLED, 'FAN_OUT': ENABLED})
        self.assertEqual(replaced['cleared'], ['GRAFANA_CONTEXT', 'RHYMING_HISTORICAL_WINDOW_DAYS'])
        cleared = self.ok('set', '--profile', 'example', '--field', 'REPO=other-service',
                          '--field', 'GRAFANA_CONTEXT=')
        self.assertEqual(cleared['fields'], {'REPO': 'other-service', 'GENERATE_PDF': ENABLED, 'GRAFANA_ASSISTANT': ENABLED, 'FAN_OUT': ENABLED})
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
                                           'RHYMING_HISTORICAL_WINDOW_DAYS': '7', 'GENERATE_PDF': ENABLED, 'GRAFANA_ASSISTANT': ENABLED, 'FAN_OUT': ENABLED})
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
                          '- Slack channel: `#example-support`', '- Grafana Assistant: `enabled`',
                          '- Generate PDF: `enabled`',
                          '- Fan-out: `enabled`'])
        self.assertFalse(preview['replaced'])
        self.assertEqual(task.read_text(encoding='utf-8'), original)
        loaded = self.ok('load', '--profile', 'example', '--task', 'docs/tasks/TASK.md')
        self.assertTrue(loaded['verified'])
        body = task.read_text(encoding='utf-8')
        self.assertIn('- Repo (Bitbucket/Github): `example-service`\n'
                      '- Slack channel: `#example-support`\n', body)
        self.assertEqual([line for line in body.splitlines() if not line.startswith('- ')],
                         [line for line in original.splitlines() if not line.startswith('- ')])
        self.assertNotIn('<enter repo name>', body)
        self.assertIn('## Acceptance Tests', body)
        self.assertIn('already supplies example-service',
                      self.fails('load', '--profile', 'example', '--task', 'docs/tasks/TASK.md'))
        self.assertTrue(self.ok('load', '--profile', 'example', '--task',
                                'docs/tasks/TASK.md', '--replace')['replaced'])

    def test_load_preserves_resource_layout_and_is_repeatable(self):
        self.ignore_and_init()
        self.ok('set', '--profile', 'example', '--field', 'REPO=service-a',
                '--field', 'SLACK_CHANNEL=["#ops-a","#ops-b"]')
        task = self.root / 'TASK.md'
        original = ('# Task Title: layout\n\n## Resources\n\n'
                    'Each setting is optional.\n\n'
                    '- Repo (Bitbucket/Github): `<enter repo name>`\n'
                    '\n<!-- Keep channel guidance here. -->\n'
                    '- Slack channel: `<enter channel>`\n'
                    '- Owner: platform\n\n'
                    '<!-- Keep this footer. -->\n\n## Notes\n\nKeep me.\n')
        task.write_text(original)
        self.ok('load', '--profile', 'example', '--task', 'TASK.md')
        loaded = task.read_text()
        self.assertIn('## Resources\n\nEach setting is optional.\n\n'
                      '- Repo (Bitbucket/Github): `service-a`\n'
                      '\n<!-- Keep channel guidance here. -->\n'
                      '- Slack channel: `#ops-a`\n'
                      '- Slack channel: `#ops-b`\n', loaded)
        self.assertIn('- Owner: platform\n\n<!-- Keep this footer. -->'
                      '\n\n## Notes\n\nKeep me.\n', loaded)
        self.ok('load', '--profile', 'example', '--task', 'TASK.md', '--replace')
        self.assertEqual(task.read_text(), loaded)

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


    def test_repository_array_roundtrip_and_repeated_load(self):
        self.ignore_and_init()
        repositories = ['org/service-a', 'https://bitbucket.example/team/library']
        value = json.dumps(repositories)
        fields = self.ok('set', '--profile', 'app-alpha', '--field', 'REPO=' + value)['fields']
        self.assertEqual(fields['REPO'], value)
        self.assertEqual(self.ok('show', '--profile', 'app-alpha')['fields']['REPO'], value)
        schema = {field['field']: field for field in self.ok('schema')['fields']}
        self.assertEqual(schema['REPO']['type'], 'repository-or-array')
        self.assertEqual(schema['REPO']['max_items'], 16)
        before = self.store.read_bytes()
        rendered = self.ok('render', '--profile', 'app-alpha')
        self.assertEqual(rendered.count('- Repo (Bitbucket/Github):'), 2)
        self.assertNotIn('`[', rendered)
        task = self.root / 'TASK.md'
        task.write_text('# Task Title: case\n\n## Resources\n\n## Other\nKeep me.\n')
        self.ok('load', '--profile', 'app-alpha', '--task', str(task))
        loaded = task.read_bytes()
        self.assertIn('## Other\nKeep me.', task.read_text())
        for repo in repositories:
            self.assertIn('- Repo (Bitbucket/Github): `' + repo + '`', task.read_text())
        self.assertIn('already supplies', self.fails('load', '--profile', 'app-alpha',
                                                  '--task', str(task)))
        self.ok('load', '--profile', 'app-alpha', '--task', str(task), '--replace')
        self.assertEqual(loaded, task.read_bytes())
        self.assertEqual(before, self.store.read_bytes())

    def test_repository_array_validation_fails_without_writes_or_value_leaks(self):
        self.ignore_and_init()
        invalid = ['[\n\"a\"]', '[]', '[1]', '[null]', '[true]', '[{}]', '["a", "a"]',
                   '["a",]', '["<repo>"]', '["a`b"]', '["a\\nb"]',
                   json.dumps(['a' * 513]), json.dumps([chr(0xd800)]),
                   json.dumps(['a' + chr(0x2028) + 'b']), json.dumps(['r' + str(i) for i in range(17)]),
                   json.dumps(['r' + str(i) + 'x' * 510 for i in range(16)]),
                   json.dumps(['xox' + 'b-1234567890-abcdefabcdef']),
                   json.dumps(['https://' + 'name:private' + '@' + 'example.com/org/repo'])]
        for value in invalid:
            with self.subTest(value=value[:20]):
                before = self.store.read_bytes()
                error = self.fails('set', '--profile', 'app', '--field', 'REPO=' + value)
                self.assertIn('invalid REPO', error)
                self.assertNotIn(value, error)
                self.assertEqual(before, self.store.read_bytes())

    def test_repository_array_readers_validate_manual_values(self):
        self.ignore_and_init()
        self.store.write_text("PROFILE__APP__REPO='[1]'\n")
        task = self.root / 'TASK.md'
        task.write_text('## Resources\n')
        for args in [('show',), ('render',), ('load', '--task', str(task))]:
            self.assertIn('invalid REPO', self.fails(args[0], '--profile', 'app', *args[1:]))
        self.assertEqual(task.read_text(), '## Resources\n')

    def test_repository_replacement_clearing_and_legacy_compatibility(self):
        self.ignore_and_init()
        self.ok('set', '--profile', 'app', '--field', 'REPO=["a","b"]')
        self.ok('set', '--profile', 'app', '--field', 'REPO=legacy-service')
        self.assertEqual(self.ok('show', '--profile', 'app')['fields']['REPO'], 'legacy-service')
        self.assertIn('- Repo (Bitbucket/Github): `legacy-service`',
                      self.ok('render', '--profile', 'app'))
        self.ok('set', '--profile', 'app', '--field', 'GRAFANA_CONTEXT=ops', '--field', 'REPO=')
        self.assertNotIn('REPO', self.ok('show', '--profile', 'app')['fields'])

    def test_compose_persists_ordered_union_and_preserves_sources(self):
        self.ignore_and_init()
        self.store.write_text('# untouched\nUNMANAGED="keep me exactly"\n')
        self.ok('set', '--profile', 'prod-us', '--field', 'AWS_ACCOUNT=ops-readonly',
                '--field', 'AWS_REGION=us-east-1', '--field', 'REPO=org/shared')
        self.ok('set', '--profile', 'app-alpha',
                '--field', 'REPO=["org/service-a","org/shared","org/service-b"]')
        before = self.store.read_bytes()
        dry = self.ok('compose', '--profile', 'prod-us', '--profile', 'app-alpha',
                      '--into', 'combined', '--dry-run')
        self.assertEqual(before, self.store.read_bytes())
        self.assertEqual(json.loads(dry['fields']['REPO']),
                         ['org/shared', 'org/service-a', 'org/service-b'])
        self.ok('compose', '--profile', 'prod-us', '--profile', 'app-alpha', '--into', 'combined')
        self.assertTrue(self.store.read_bytes().startswith(before))
        shown = self.ok('show', '--profile', 'combined')['fields']
        self.assertEqual(shown['AWS_ACCOUNT'], 'ops-readonly')
        self.assertEqual(shown['AWS_REGION'], 'us-east-1')
        self.assertEqual(shown['GENERATE_PDF'], ENABLED)
        self.assertEqual(oct(self.store.stat().st_mode & 0o777), '0o600')
        target_before = self.store.read_bytes()
        self.assertIn('already exists', self.fails('compose', '--profile', 'prod-us',
                      '--profile', 'app-alpha', '--into', 'combined'))
        self.assertEqual(self.store.read_bytes(), target_before)
        self.ok('compose', '--profile', 'prod-us', '--profile', 'app-alpha',
                '--into', 'combined', '--replace')
        self.assertEqual(self.store.read_bytes(), target_before)
        task = self.root / 'TASK.md'
        task.write_text('## Resources\n- Generate PDF: `disabled`\n')
        self.ok('load', '--profile', 'combined', '--task', str(task))
        self.assertEqual(task.read_text().count('- Repo (Bitbucket/Github):'), 3)
        self.assertIn('- AWS region: `us-east-1`', task.read_text())
        self.assertIn('- Generate PDF: `disabled`', task.read_text())

    def test_compose_scalar_conflicts_are_atomic_and_sanitized(self):
        self.ignore_and_init()
        self.ok('set', '--profile', 'one', '--field', 'REPO=repo-a',
                '--field', 'GRAFANA_CONTEXT=first-private-value')
        self.ok('set', '--profile', 'two', '--field', 'REPO=repo-b',
                '--field', 'GRAFANA_CONTEXT=second-private-value')
        before = self.store.read_bytes()
        error = self.fails('compose', '--profile', 'one', '--profile', 'two', '--into', 'out')
        self.assertIn('conflicting field GRAFANA_CONTEXT', error)
        self.assertNotIn('private-value', error)
        self.assertEqual(before, self.store.read_bytes())

    def test_compose_guards_sources_and_target_and_revalidates_union(self):
        self.ignore_and_init()
        self.ok('set', '--profile', 'one', '--field', 'REPO=a')
        self.ok('set', '--profile', 'two', '--field', 'REPO=b')
        before = self.store.read_bytes()
        for sources, target in [(['one'], 'out'), (['one', 'one'], 'out'),
                                (['one', 'two'], 'one'), (['one', 'missing'], 'out')]:
            args = [item for name in sources for item in ('--profile', name)]
            self.fails('compose', *args, '--into', target, '--replace')
            self.assertEqual(before, self.store.read_bytes())
        self.ok('set', '--profile', 'one',
                '--field', 'REPO=' + json.dumps(['r' + str(i) for i in range(16)]))
        before = self.store.read_bytes()
        self.assertIn('invalid REPO', self.fails('compose', '--profile', 'one',
                      '--profile', 'two', '--into', 'out'))
        self.assertEqual(before, self.store.read_bytes())

    def test_compose_defaults_unknown_fields_and_whole_target_replacement(self):
        self.ignore_and_init()
        self.store.write_text("PROFILE__ONE__REPO='a'\nPROFILE__TWO__REPO='b'\n"
                              "PROFILE__TWO__GENERATE_PDF='F'\n")
        self.ok('compose', '--profile', 'one', '--profile', 'two', '--into', 'out')
        self.assertEqual(self.ok('show', '--profile', 'out')['fields']['GENERATE_PDF'], DISABLED)
        self.ok('set', '--profile', 'out', '--field', 'SLACK_CHANNEL=#stale')
        self.ok('compose', '--profile', 'one', '--profile', 'two', '--into', 'out', '--replace')
        self.assertNotIn('SLACK_CHANNEL', self.ok('show', '--profile', 'out')['fields'])
        with self.store.open('a') as stream:
            stream.write("PROFILE__ONE__UNKNOWN='unknown'\n")
        before = self.store.read_bytes()
        self.assertIn('unknown fields', self.fails('compose', '--profile', 'one',
                      '--profile', 'two', '--into', 'out', '--replace'))
        self.assertEqual(before, self.store.read_bytes())


    def test_compose_preserves_unmanaged_newline_bytes(self):
        self.ignore_and_init()
        self.ok('set', '--profile', 'one', '--field', 'REPO=a')
        self.ok('set', '--profile', 'two', '--field', 'REPO=b')
        prefix = b'# local settings\r\nUNMANAGED="unchanged"\r\n'
        original = prefix + self.store.read_bytes()
        self.store.write_bytes(original)
        self.ok('compose', '--profile', 'one', '--profile', 'two', '--into', 'out')
        self.assertTrue(self.store.read_bytes().startswith(original))
        self.ok('compose', '--profile', 'one', '--profile', 'two', '--into', 'out', '--replace')
        self.assertTrue(self.store.read_bytes().startswith(original))


    def test_repository_ssh_identity_is_not_a_credential(self):
        self.ignore_and_init()
        for repo in ('git@example.com:org/repo.git', 'ssh://git@example.com/org/repo.git'):
            self.ok('set', '--profile', 'app', '--field', 'REPO=' + repo)
            self.assertEqual(self.ok('show', '--profile', 'app')['fields']['REPO'], repo)
            self.assertIn('`' + repo + '`', self.ok('render', '--profile', 'app'))


    def test_compose_replaces_manually_lowercase_target_keys(self):
        self.ignore_and_init()
        self.store.write_text("PROFILE__ONE__REPO='a'\nPROFILE__TWO__REPO='b'\n"
                             "PROFILE__out__REPO='old'\nPROFILE__out__SLACK_CHANNEL='#stale'\n")
        self.ok('compose', '--profile', 'one', '--profile', 'two', '--into', 'out', '--replace')
        shown = self.ok('show', '--profile', 'out')['fields']
        self.assertEqual(json.loads(shown['REPO']), ['a', 'b'])
        self.assertNotIn('SLACK_CHANNEL', shown)
        self.assertNotIn('PROFILE__out__', self.store.read_text())


    def test_load_preserves_user_task_fields_above_injected_profile_values(self):
        self.ignore_and_init()
        self.ok('set', '--profile', 'env', '--field', 'REPO=profile-repo',
                '--field', 'SLACK_CHANNEL=#profile', '--field', 'AWS_REGION=us-east-1')
        task = self.root / 'TASK.md'
        task.write_text('## Resources\n- Slack channel: `#user`\n'
                        '- AWS region: `eu-central-1`\n- Fan-out: disabled\n')
        before = self.store.read_bytes()
        self.ok('load', '--profile', 'env', '--task', str(task), '--replace')
        self.assertIn('- Slack channel: `#user`', task.read_text())
        self.assertIn('- AWS region: `eu-central-1`', task.read_text())
        self.assertIn('- Repo (Bitbucket/Github): `profile-repo`', task.read_text())
        self.assertIn('- Fan-out: `disabled`', task.read_text())
        self.assertNotIn('`#profile`', task.read_text())
        self.assertEqual(before, self.store.read_bytes())
        first = task.read_bytes()
        self.ok('load', '--profile', 'env', '--task', str(task), '--replace')
        self.assertEqual(first, task.read_bytes())

    def test_explicit_compose_and_load_fields_win_without_changing_sources(self):
        self.ignore_and_init()
        for name in ('one', 'two'):
            self.ok('set', '--profile', name, '--field', 'REPO=' + name,
                    '--field', 'SLACK_CHANNEL=#' + name)
        before = self.store.read_bytes()
        result = self.ok('compose', '--profile', 'one', '--profile', 'two', '--into', 'out',
                         '--field', 'SLACK_CHANNEL=#user', '--field', 'REPO=chosen-repo')
        self.assertEqual(result['fields']['SLACK_CHANNEL'], '#user')
        self.assertEqual(result['fields']['REPO'], 'chosen-repo')
        self.assertTrue(self.store.read_bytes().startswith(before))
        task = self.root / 'TASK.md'
        task.write_text('## Resources\n- Slack channel: `#saved`\n- Generate PDF: `enabled`\n')
        profile_before = self.store.read_bytes()
        self.ok('load', '--profile', 'out', '--task', str(task), '--replace',
                '--field', 'SLACK_CHANNEL=#latest', '--field', 'GENERATE_PDF=disabled')
        self.assertIn('- Slack channel: `#latest`', task.read_text())
        self.assertIn('- Generate PDF: `disabled`', task.read_text())
        self.assertEqual(self.store.read_bytes(), profile_before)

    def test_invalid_or_duplicate_user_task_fields_fail_before_mutation(self):
        self.ignore_and_init()
        self.ok('set', '--profile', 'env', '--field', 'REPO=profile-repo')
        task = self.root / 'TASK.md'
        for body in ('- AWS region: `us-east-1`\n- AWS region: `eu-central-1`\n',
                     '- Slack channel: `#one`\n- Slack channel: `#one`\n',
                     '- Slack channel: malformed\n',
                     '- Repo (Bitbucket/Github): `[1]`\n'):
            task.write_text('## Resources\n' + body)
            before = task.read_bytes()
            self.fails('load', '--profile', 'env', '--task', str(task), '--replace')
            self.assertEqual(task.read_bytes(), before)
        task.write_text('## Resources\n')
        self.assertIn('unknown field', self.fails('load', '--profile', 'env', '--task', str(task),
                      '--field', 'UNKNOWN=anything'))
        self.assertEqual(task.read_text(), '## Resources\n')


    def test_near_byte_limit_repository_list_loads_repeatedly(self):
        self.ignore_and_init()
        entries = [str(i) + 'a' * (508 + (i < 3) - len(str(i))) for i in range(16)]
        value = json.dumps(entries, separators=(',', ':'))
        self.assertEqual(len(value.encode()), 8180)
        self.ok('set', '--profile', 'app', '--field', 'REPO=' + value)
        task = self.root / 'TASK.md'
        task.write_text('## Resources\n')
        self.ok('load', '--profile', 'app', '--task', str(task))
        before = task.read_bytes()
        self.ok('load', '--profile', 'app', '--task', str(task), '--replace')
        self.assertEqual(task.read_bytes(), before)


    def test_slack_channel_array_roundtrip_and_repeated_load(self):
        self.ignore_and_init()
        value = '["#ops-alpha","C000000002"]'
        self.ok('set', '--profile', 'channels', '--field', 'SLACK_CHANNEL=' + value)
        schema = {field['field']: field for field in self.ok('schema')['fields']}
        self.assertEqual(schema['SLACK_CHANNEL']['type'], 'channel-or-array')
        self.assertEqual(self.ok('show', '--profile', 'channels')['fields']['SLACK_CHANNEL'], value)
        before = self.store.read_bytes()
        rendered = self.ok('render', '--profile', 'channels')
        self.assertIn('- Slack channel: `#ops-alpha`\n- Slack channel: `C000000002`', rendered)
        task = self.root / 'TASK.md'
        task.write_text('## Resources\n')
        self.ok('load', '--profile', 'channels', '--task', str(task))
        first = task.read_bytes()
        self.ok('load', '--profile', 'channels', '--task', str(task), '--replace')
        self.assertEqual(first, task.read_bytes())
        self.assertEqual(before, self.store.read_bytes())
        self.ok('set', '--profile', 'channels', '--field', 'SLACK_CHANNEL=#legacy')
        self.assertIn('- Slack channel: `#legacy`', self.ok('render', '--profile', 'channels'))
        self.ok('set', '--profile', 'channels', '--field', 'REPO=repo', '--field', 'SLACK_CHANNEL=')
        self.assertNotIn('SLACK_CHANNEL', self.ok('show', '--profile', 'channels')['fields'])

    def test_publish_destination_array_roundtrip_load_and_task_precedence(self):
        self.ignore_and_init()
        page = 'https://example.atlassian.net/wiki/spaces/OPS/pages/123/Investigations'
        repo = 'https://github.com/example-org/example-reports'
        value = json.dumps([page, repo], separators=(',', ':'))
        self.ok('set', '--profile', 'out', '--field', 'REPO=repo', '--field', 'PUBLISH=' + value)
        schema = {field['field']: field for field in self.ok('schema')['fields']}
        self.assertEqual(schema['PUBLISH']['type'], 'destination-or-array')
        self.assertEqual(self.ok('show', '--profile', 'out')['fields']['PUBLISH'], value)
        before = self.store.read_bytes()
        self.assertIn('- Publish: `' + page + '`\n- Publish: `' + repo + '`',
                      self.ok('render', '--profile', 'out'))
        task = self.root / 'TASK.md'
        task.write_text('## Resources\n')
        self.ok('load', '--profile', 'out', '--task', str(task))
        first = task.read_bytes()
        self.ok('load', '--profile', 'out', '--task', str(task), '--replace')
        self.assertEqual(first, task.read_bytes())
        self.assertEqual(before, self.store.read_bytes())
        # Destinations the user wrote in the task replace the profile list.
        chosen = 'Confluence page "Investigations"'
        task.write_text('## Resources\n\n- Publish: `' + chosen + '`\n')
        result = self.ok('load', '--profile', 'out', '--task', str(task), '--replace')
        self.assertEqual(result['fields']['PUBLISH'], chosen)
        self.assertEqual(task.read_text().count('- Publish:'), 1)
        # A scalar remains valid, and an empty assignment clears the field.
        self.ok('set', '--profile', 'out', '--field', 'PUBLISH=' + page)
        self.assertIn('- Publish: `' + page + '`', self.ok('render', '--profile', 'out'))
        self.ok('set', '--profile', 'out', '--field', 'PUBLISH=')
        self.assertNotIn('PUBLISH', self.ok('show', '--profile', 'out')['fields'])

    def test_compose_publish_destinations_uses_ordered_union(self):
        self.ignore_and_init()
        page = 'https://example.atlassian.net/wiki/pages/viewpage.action?pageId=123'
        repo = 'https://bitbucket.example/example-workspace/example-reports'
        self.ok('set', '--profile', 'environment', '--field', 'AWS_REGION=us-east-1',
                '--field', 'PUBLISH=' + page)
        self.ok('set', '--profile', 'application', '--field', 'REPO=repo',
                '--field', 'PUBLISH=' + json.dumps([page, repo]))
        result = self.ok('compose', '--profile', 'environment', '--profile', 'application',
                         '--into', 'combined')
        self.assertEqual(json.loads(result['fields']['PUBLISH']), [page, repo])

    def test_publish_destinations_are_validated_before_any_write(self):
        self.ignore_and_init()
        self.ok('set', '--profile', 'out', '--field', 'REPO=repo')
        before = self.store.read_bytes()
        secret = 'https://' + 'user:hunter2' + '@' + 'example.atlassian.net/wiki/spaces/OPS'
        for value in ('["a","a"]', '[]', '["<Parent page>"]', secret,
                      json.dumps(['ok', secret]), json.dumps(['d%d' % i for i in range(17)])):
            error = self.fails('set', '--profile', 'out', '--field', 'PUBLISH=' + value)
            self.assertNotIn('hunter2', error)
            self.assertEqual(before, self.store.read_bytes())

    def test_compose_channels_uses_ordered_union_and_user_list_replaces_it(self):
        self.ignore_and_init()
        self.ok('set', '--profile', 'env', '--field', 'SLACK_CHANNEL=#ops')
        self.ok('set', '--profile', 'app', '--field', 'SLACK_CHANNEL=["#app","#ops"]')
        self.ok('compose', '--profile', 'env', '--profile', 'app', '--into', 'out')
        self.assertEqual(json.loads(self.ok('show', '--profile', 'out')['fields']['SLACK_CHANNEL']),
                         ['#ops', '#app'])
        self.ok('compose', '--profile', 'env', '--profile', 'app', '--into', 'chosen',
                '--field', 'SLACK_CHANNEL=["#user-one","#user-two"]')
        task = self.root / 'TASK.md'
        task.write_text('## Resources\n- Slack channel: `#saved-one`\n'
                        '- Slack channel: `#saved-two`\n')
        self.ok('load', '--profile', 'out', '--task', str(task), '--replace')
        self.assertIn('`#saved-one`', task.read_text())
        self.assertIn('`#saved-two`', task.read_text())
        self.assertNotIn('`#ops`', task.read_text())
        self.ok('load', '--profile', 'out', '--task', str(task), '--replace',
                '--field', 'SLACK_CHANNEL=["#latest-one","#latest-two"]')
        self.assertIn('`#latest-one`', task.read_text())
        self.assertNotIn('`#saved-one`', task.read_text())
        self.assertEqual(json.loads(self.ok('show', '--profile', 'chosen')['fields']['SLACK_CHANNEL']),
                         ['#user-one', '#user-two'])

    def test_slack_arrays_are_validated_before_any_write(self):
        self.ignore_and_init()
        bad = ['[]', '[1]', '[null]', '["#one","#one"]', '["<channel>"]', '["#bad`name"]',
               json.dumps(['#' + str(i) for i in range(17)]),
               json.dumps(['#' + 'x' * 512]), json.dumps([chr(0xd800)]),
               json.dumps(['#' + str(i) + 'x' * 510 for i in range(16)])]
        for value in bad:
            before = self.store.read_bytes()
            self.assertIn('invalid SLACK_CHANNEL', self.fails('set', '--profile', 'channels',
                          '--field', 'SLACK_CHANNEL=' + value))
            self.assertEqual(before, self.store.read_bytes())
        self.store.write_text("PROFILE__BAD__SLACK_CHANNEL='[1]'\n")
        self.assertIn('invalid SLACK_CHANNEL', self.fails('show', '--profile', 'bad'))
        self.assertIn('invalid SLACK_CHANNEL', self.fails('render', '--profile', 'bad'))

    def test_channel_union_limit_and_near_limit_repeated_loading(self):
        self.ignore_and_init()
        values = [str(i) + 'a' * (508 + (i < 3) - len(str(i))) for i in range(16)]
        self.ok('set', '--profile', 'one', '--field', 'SLACK_CHANNEL=' +
                json.dumps(values, separators=(',', ':')))
        self.ok('set', '--profile', 'two', '--field', 'SLACK_CHANNEL=#extra')
        before = self.store.read_bytes()
        self.assertIn('invalid SLACK_CHANNEL', self.fails('compose', '--profile', 'one',
                      '--profile', 'two', '--into', 'out'))
        self.assertEqual(before, self.store.read_bytes())
        task = self.root / 'TASK.md'
        task.write_text('## Resources\n')
        self.ok('load', '--profile', 'one', '--task', str(task))
        first = task.read_bytes()
        self.ok('load', '--profile', 'one', '--task', str(task), '--replace')
        self.assertEqual(first, task.read_bytes())


if __name__ == '__main__':
    unittest.main()
