"""Exercise the portable resolver through its public command-line interface."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


RESOLVER = (Path(__file__).resolve().parents[1] / 'skills' /
            'workflow-artifact-naming' / 'scripts' / 'resolve_artifact_names.py')


class ResolverTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name) / 'repository'
        self.root.mkdir()

    def run_resolver(self, *arguments):
        return subprocess.run(
            [sys.executable, str(RESOLVER), '--repository-root', str(self.root),
             *arguments], capture_output=True, text=True, check=False)

    def resolve(self, *arguments):
        result = self.run_resolver(*arguments)
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout)

    def configure(self, content):
        (self.root / 'workflow-artifact-naming.json').write_text(content, encoding='utf-8')

    def test_default_report_is_read_only(self):
        result = self.resolve('--title', 'Scheduled Maintenance', '--type', 'REPORT')
        self.assertEqual(result['path'], 'docs/reports/REPORT-scheduled-maintenance.md')
        self.assertEqual(result['location_source'], 'default')
        self.assertEqual(list(self.root.iterdir()), [])

    def test_configured_sibling_and_explicit_destination_precedence(self):
        self.configure(json.dumps({'schema': 'workflow-artifact-naming/v1',
                                   'locations': {'REPORT': '../reports'}}))
        configured = self.resolve('--slug', 'maintenance', '--type', 'REPORT')
        self.assertEqual(configured['path'], '../reports/REPORT-maintenance.md')
        self.assertEqual(configured['location_source'], 'configuration')
        explicit = self.resolve('--slug', 'maintenance', '--type', 'REPORT',
                                '--destination', 'outputs')
        self.assertEqual(explicit['path'], 'outputs/REPORT-maintenance.md')
        self.assertEqual(explicit['location_source'], 'explicit')
        self.assertFalse((self.root.parent / 'reports').exists())
        self.assertFalse((self.root / 'outputs').exists())

    def test_invalid_configuration_is_rejected_even_with_override(self):
        self.configure('{"schema": "workflow-artifact-naming/v1", "locations": {}, "locations": {}}')
        result = self.run_resolver('--slug', 'maintenance', '--type', 'REPORT',
                                   '--destination', 'outputs')
        self.assertEqual(result.returncode, 2)
        self.assertIn('duplicate configuration key', result.stderr)
        self.assertFalse((self.root / 'outputs').exists())

    def test_invalid_slug_is_rejected(self):
        for slug in ('../escape', 'UPPERCASE', ''):
            with self.subTest(slug=slug):
                result = self.run_resolver('--slug', slug, '--type', 'TASK')
                self.assertEqual(result.returncode, 2)
        self.assertEqual(list(self.root.iterdir()), [])

    def test_child_log_and_asset_names(self):
        ticket = 'EXAMPLE-' + '123'
        child = self.resolve('--slug', 'maintenance', '--type', 'LOG', '--ticket', ticket)
        self.assertEqual(child['path'], f'logs/LOG-maintenance-{ticket}.md')
        asset = self.resolve('--slug', 'maintenance', '--type', 'CHART',
                             '--asset', '--extension', 'svg')
        self.assertEqual(asset['path'], 'logs/assets/maintenance/CHART-maintenance.svg')
        self.assertEqual(list(self.root.iterdir()), [])

    def test_legacy_title_normalization(self):
        result = self.resolve('--title', 'İFoo CAFÉ', '--type', 'TASK')
        self.assertEqual(result['filename'], 'TASK-ifoo-caf.md')


if __name__ == '__main__':
    unittest.main()
