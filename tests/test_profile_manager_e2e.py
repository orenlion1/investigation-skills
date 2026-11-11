"""Walk the documented profile-manager chain end to end against a real Git repository.

The unit suite in test_profile_manager.py checks each command in isolation. This
module instead follows SKILL.md's documented order in one pass — ignore, create,
add, load, remove, delete — and asserts the artifacts each step leaves behind, so
a regression in the ordering guards or in the task rewrite fails here even when
every command still works on its own.

It reads the repository's own templates/TASK.md, so a change to that template's
Resources section that the derived schema cannot express fails this test too.
"""
import json
import os
import re
import shlex
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
HELPER = ROOT / 'skills' / 'profile-manager' / 'scripts' / 'profile_env.py'
TEMPLATE = ROOT / 'templates' / 'TASK.md'
UNMANAGED = 'DEPLOY_TOKEN="do-not-touch"'


class EndToEndChainTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name) / 'repository'
        (self.root / 'templates').mkdir(parents=True)
        (self.root / 'docs' / 'tasks').mkdir(parents=True)
        (self.root / 'templates' / 'TASK.md').write_text(
            TEMPLATE.read_text(encoding='utf-8'), encoding='utf-8')
        self.store = self.root / '.env'
        self.task = self.root / 'docs' / 'tasks' / 'TASK.md'
        self.git('init')

    def git(self, *arguments, check=True):
        return subprocess.run(['git', '-C', str(self.root), *arguments],
                              capture_output=True, text=True, check=check)

    def helper(self, *arguments):
        return subprocess.run([sys.executable, '-B', str(HELPER),
                               '--repository-root', str(self.root), *arguments],
                              capture_output=True, text=True, check=False)

    def ok(self, *arguments):
        result = self.helper(*arguments)
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout) if result.stdout.startswith('{') else result.stdout

    def fails(self, *arguments):
        result = self.helper(*arguments)
        self.assertEqual(result.returncode, 2, result.stdout)
        return result.stderr

    def ignore_lines(self):
        path = self.root / '.gitignore'
        return path.read_text(encoding='utf-8').splitlines() if path.exists() else []

    def test_documented_chain_from_an_unignored_repository(self):
        """ignore, create, add, load into a task, remove, delete — in that order."""
        (self.root / '.gitignore').write_text('# pre-existing\nnode_modules/\n', encoding='utf-8')

        with self.subTest('schema comes from the task template'):
            fields = {field['field'] for field in self.ok('schema')['fields']}
            self.assertEqual(fields, {'REPO', 'SLACK_CHANNEL', 'AWS_ACCOUNT', 'AWS_REGION',
                                      'GRAFANA_CONTEXT', 'ALERT', 'ALERT_UID', 'PUBLISH', 'RHYMING_ENDPOINTS', 'RHYMING_HISTORICAL_WINDOW_DAYS', 'GENERATE_PDF'})

        with self.subTest('no store is written while Git does not ignore it'):
            self.assertIn('not ignored by Git',
                          self.fails('set', '--profile', 'payments',
                                     '--field', 'REPO=payments-service'))
            self.assertFalse(self.store.exists())

        with self.subTest('ignore adds coverage and Git confirms it'):
            ignored = self.ok('ignore')
            self.assertTrue(ignored['verified'])
            self.assertIn('.env', self.ignore_lines())
            self.assertIn('# pre-existing', self.ignore_lines())
            self.assertEqual(self.git('check-ignore', '.env').returncode, 0)

        with self.subTest('init creates an owner-only store'):
            created = self.ok('init')
            self.assertTrue(created['created'])
            self.assertEqual(oct(self.store.stat().st_mode & 0o777), '0o600')
            self.store.write_text('# unrelated local settings\n' + UNMANAGED + '\n',
                                  encoding='utf-8')
            # A store made by hand — cp .env.example .env — arrives world-readable.
            self.store.chmod(0o644)

        with self.subTest('set adds the profile and preserves unmanaged lines'):
            added = self.ok('set', '--profile', 'payments',
                            '--field', 'REPO=payments-service',
                            '--field', 'SLACK_CHANNEL=#payments-oncall',
                            '--field', 'ALERT=Checkout latency',
                            '--field', 'ALERT_UID=ab12cd34')
            self.assertEqual(added['added'],
                             ['ALERT', 'ALERT_UID', 'GENERATE_PDF', 'REPO', 'RHYMING_HISTORICAL_WINDOW_DAYS', 'SLACK_CHANNEL'])
            contents = self.store.read_text(encoding='utf-8')
            self.assertIn("PROFILE__PAYMENTS__REPO='payments-service'", contents)
            self.assertIn(UNMANAGED, contents)
            self.assertEqual(oct(self.store.stat().st_mode & 0o777), '0o600')

        with self.subTest('list and show report status without unmanaged values'):
            listed = self.ok('list')
            self.assertEqual(listed['profiles'], ['payments'])
            self.assertTrue(listed['ignored'])
            self.assertFalse(listed['tracked'])
            self.assertNotIn('do-not-touch', json.dumps(listed))
            shown = self.ok('show', '--profile', 'payments')
            self.assertEqual(shown['fields']['REPO'], 'payments-service')
            self.assertIn('PUBLISH', shown['missing_fields'])
            self.assertNotIn('do-not-touch', json.dumps(shown))

        self.task.write_text(TEMPLATE.read_text(encoding='utf-8'), encoding='utf-8')

        with self.subTest('dry-run load writes nothing'):
            before = self.task.read_text(encoding='utf-8')
            preview = self.ok('load', '--profile', 'payments',
                              '--task', 'docs/tasks/TASK.md', '--dry-run')
            self.assertEqual(preview['resources'][0],
                             '- Repo (Bitbucket/Github): `payments-service`')
            self.assertEqual(self.task.read_text(encoding='utf-8'), before)

        with self.subTest('load fills Resources and leaves other sections intact'):
            loaded = self.ok('load', '--profile', 'payments', '--task', 'docs/tasks/TASK.md')
            self.assertTrue(loaded['verified'])
            body = self.task.read_text(encoding='utf-8')
            self.assertIn('## Resources\n\n'
                          '- Repo (Bitbucket/Github): `payments-service`\n'
                          '- Slack channel: `#payments-oncall`\n'
                          '- Alert: `Checkout latency`; UID `ab12cd34`\n', body)
            self.assertNotIn('<enter repo name>', body)
            self.assertNotIn('- AWS account:', body)
            self.assertIn('## Acceptance Tests', body)
            self.assertIn('## Problem', body)

        with self.subTest('a second load preserves supplied resources unless replacing'):
            self.assertIn('already supplies payments-service',
                          self.fails('load', '--profile', 'payments',
                                     '--task', 'docs/tasks/TASK.md'))

        with self.subTest('Git never tracks the store'):
            self.git('add', '-A')
            self.assertEqual(self.git('ls-files').stdout.count('.env'), 0)
            self.assertNotIn('.env', self.git('status', '--short').stdout)

        with self.subTest('remove deletes only that profile'):
            removed = self.ok('remove', '--profile', 'payments')
            self.assertEqual(removed['remaining_profiles'], [])
            contents = self.store.read_text(encoding='utf-8')
            self.assertNotIn('PROFILE__PAYMENTS__', contents)
            self.assertIn(UNMANAGED, contents)

        with self.subTest('remove-env protects unmanaged keys, then deletes on --force'):
            self.assertIn('unmanaged keys (DEPLOY_TOKEN)', self.fails('remove-env'))
            self.assertTrue(self.store.exists())
            self.assertTrue(self.ok('remove-env', '--force')['deleted'])
            self.assertFalse(os.path.lexists(self.store))

    def test_chain_when_the_repository_already_ignores_the_store(self):
        """The shape this repository is in: .gitignore already covers .env."""
        (self.root / '.gitignore').write_text('.env\n.env.*\n!.env.example\n', encoding='utf-8')
        before = self.ignore_lines()

        covered = self.ok('ignore')
        self.assertTrue(covered['already_ignored'])
        self.assertEqual(covered['appended'], [])
        self.assertEqual(self.ignore_lines(), before)

        self.ok('init')
        self.ok('set', '--profile', 'investigation-skills',
                '--field', 'REPO=investigation-skills',
                '--field', 'AWS_ACCOUNT=team-readonly',
                '--field', 'AWS_REGION=us-east-1')
        shown = self.ok('show', '--profile', 'investigation-skills')
        self.assertEqual(shown['fields']['AWS_REGION'], 'us-east-1')
        self.task.write_text(TEMPLATE.read_text(encoding='utf-8'), encoding='utf-8')
        self.assertTrue(self.ok('load', '--profile', 'investigation-skills',
                                '--task', 'docs/tasks/TASK.md')['verified'])
        self.assertIn('- Repo (Bitbucket/Github): `investigation-skills`',
                      self.task.read_text(encoding='utf-8'))
        self.assertIn('- AWS account: `team-readonly`\n- AWS region: `us-east-1`',
                      self.task.read_text(encoding='utf-8'))
        self.ok('remove', '--profile', 'investigation-skills')
        self.assertEqual(self.ok('list')['profiles'], [])
        self.assertTrue(self.ok('remove-env')['deleted'])


    def test_readme_environment_application_and_composition_commands(self):
        """Execute the actual documented synthetic commands and compare rendered output."""
        readme = (ROOT / 'README.md').read_text()
        example = readme.split('<!-- profile-composition-example:start -->')[1].split(
            '<!-- profile-composition-example:end -->')[0]
        self.task.write_text(TEMPLATE.read_text())
        for block in re.findall(r'```sh\n(.*?)```', example, re.S):
            for line in block.replace('\\\n', ' ').splitlines():
                if not line.strip():
                    continue
                args = shlex.split(line)
                self.assertEqual(args[:3], ['python3', '-B',
                                           'skills/profile-manager/scripts/profile_env.py'])
                self.assertEqual(args[3:5], ['--repository-root', '.'])
                self.ok(*args[5:])
        shown = self.ok('show', '--profile', 'prod-us-app-alpha')['fields']
        self.assertEqual(len(json.loads(shown['REPO'])), 3)
        self.assertEqual(shown['AWS_REGION'], 'us-east-1')
        expected = readme.split('The effective task Resources are:')[1].split('```markdown\n')[1].split('```')[0]
        loaded = self.task.read_text().split('## Resources')[1]
        expected_bullets = [line for line in expected.splitlines() if line.startswith('- ')]
        self.assertEqual([line for line in loaded.splitlines() if line.startswith('- ')], expected_bullets)
        self.assertEqual(self.git('ls-files', '.env').stdout, '')


if __name__ == '__main__':
    unittest.main()
