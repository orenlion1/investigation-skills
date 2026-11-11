"""Synthetic end-to-end accounting and presentation regressions."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import unittest

import test_token_usage as fixtures

SCRIPTS = fixtures.SCRIPT.parent


def renderer():
    spec = importlib.util.spec_from_file_location('usage_renderer', SCRIPTS / 'render_token_usage.py')
    module = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(SCRIPTS))
    try:
        spec.loader.exec_module(module)
    finally:
        sys.path.pop(0)
    return module


class TokenReportingTests(unittest.TestCase):
    def setUp(self):
        self.fixture = fixtures.TokenUsageTests('runTest')
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)

    def checkpoint(self):
        f = self.fixture
        data = {'schema': 'investigation-accounting-cutoff/v1', 'task_artifact': fixtures.TASK,
                'thread_id': 'root', 'turn_id': 'turn', 'purpose': 'report-generation-cutoff',
                'observed_at': '2026-10-16T10:00:10.007886Z'}
        path = f.root / 'cutoff.json'; path.write_text(json.dumps(data))
        proof = {'kind': 'checkpoint', 'path': str(path),
                 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}
        manifest = f.manifest()
        manifest['window'].update(to=data['observed_at'], end=proof)
        return data, path, manifest

    def test_observed_checkpoint_preserves_fractional_cutoff_without_native_event(self):
        _, path, manifest = self.checkpoint()
        result = fixtures.collector.collect(manifest)
        self.assertEqual(result['window']['to'], '2026-10-16T10:00:10.007886Z')
        self.assertEqual(result['window']['elapsed_seconds'], 10.007886)
        self.assertEqual(result['window']['evidence']['end']['kind'], 'checkpoint')
        self.assertNotIn(str(path), json.dumps(result))
        self.assertEqual(result['usage']['tokens']['total_tokens'], 110)

    def test_checkpoint_rejects_wrong_task_turn_hash_and_timestamp(self):
        original, path, manifest = self.checkpoint()
        for field, value in (('task_artifact', 'docs/tasks/TASK-other.md'),
                             ('turn_id', 'unbound'), ('observed_at', '2026-10-16T10:00:09Z')):
            with self.subTest(field=field):
                data = {**original, field: value}; path.write_text(json.dumps(data))
                manifest['window']['end']['sha256'] = hashlib.sha256(path.read_bytes()).hexdigest()
                with self.assertRaises(ValueError):
                    fixtures.collector.collect(manifest)
        path.write_text(json.dumps(original))
        with self.assertRaises(ValueError):
            fixtures.collector.collect(manifest)

    def test_cutoff_recorder_captures_now_exclusively(self):
        path = self.fixture.root / 'observed.json'
        args = [sys.executable, str(SCRIPTS / 'record_accounting_cutoff.py'),
                '--task-artifact', fixtures.TASK, '--thread-id', 'root', '--turn-id', 'turn',
                '--output', str(path)]
        result = subprocess.run(args, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        data = json.loads(path.read_text())
        self.assertEqual(data['purpose'], 'report-generation-cutoff')
        self.assertIsNotNone(fixtures.collector.timestamp(data['observed_at']))
        self.assertEqual(json.loads(result.stdout)['sha256'], hashlib.sha256(path.read_bytes()).hexdigest())
        before = path.read_bytes()
        self.assertNotEqual(subprocess.run(args, capture_output=True).returncode, 0)
        self.assertEqual(before, path.read_bytes())
        self.assertEqual(path.stat().st_mode & 0o777, 0o600)

    def test_renderer_uses_collected_values_and_session_model_rows(self):
        f = self.fixture
        f.records.insert(3, fixtures.record('turn_context', {'turn_id': 'turn', 'model': 'example-model'}, 1))
        data = fixtures.collector.collect(f.manifest())
        sections = renderer().render(data, 'Example', 'Source scope', '2026-10-16')
        self.assertIn('Total recorded tokens: 110', sections['subheading'])
        self.assertIn('Total recorded tokens: 110', sections['details'])
        self.assertIn('| root | example-model | 110 | 1 |', sections['details'])
        self.assertIn('Cached input (input subset): 50', sections['details'])
        self.assertIn('Reasoning output (output subset): 5', sections['details'])
        self.assertTrue(sections['details'].rstrip().endswith('| root | example-model | 110 | 1 |'))
        for omitted in ('coverage', 'sha256', 'source_line', 'Method', str(f.root)):
            self.assertNotIn(omitted, sections['details'])

    def test_renderer_preserves_partial_subtotal_and_genuine_empty_telemetry(self):
        f = self.fixture
        manifest = f.manifest(); manifest['expected_threads'] = ['absent-child']
        partial = fixtures.collector.collect(manifest)
        section = renderer().render(partial)['details']
        self.assertIn('Total recorded tokens: 110', section)
        self.assertNotIn('complete', section)
        f.records.pop(3)
        empty = fixtures.collector.collect(f.manifest())
        self.assertIn('Total recorded tokens: unavailable', renderer().render(empty)['details'])

    def test_renderer_rejects_failed_collection_tampered_total_and_duration(self):
        data = fixtures.collector.collect(self.fixture.manifest())
        bad = copy.deepcopy(data); bad['usage']['tokens']['total_tokens'] = 999
        wrong_duration = copy.deepcopy(data); wrong_duration['window']['elapsed_seconds'] = 11
        for result in ({'schema': 'investigation-token-usage-error/v1', 'status': 'failed',
                        'code': 'user_request_required'}, bad, wrong_duration):
            with self.subTest(result=result):
                with self.assertRaises(ValueError):
                    renderer().render(result)

    def test_renderer_keeps_unknown_fields_unavailable_and_explicit_zero(self):
        f = self.fixture
        f.records[3]['payload']['usage'] = fixtures.counts(0, 0)
        f.records[3]['payload']['usage']['reasoning_output_tokens'] = None
        data = fixtures.collector.collect(f.manifest())
        sections = renderer().render(data, 'Example', 'Scope', '2026-10-16')
        self.assertIn('Total recorded tokens: 0', sections['subheading'])
        self.assertIn('| root | unavailable | 0 | 1 |', sections['details'])
        self.assertNotIn('Reasoning output', sections['details'])

    def test_checkpoint_rejects_symlinks_and_future_evidence(self):
        original, path, manifest = self.checkpoint()
        alias = path.with_name('linked.json'); alias.symlink_to(path)
        manifest['window']['end']['path'] = str(alias)
        with self.assertRaisesRegex(ValueError, 'unsafe_checkpoint'):
            fixtures.collector.collect(manifest)
        alias.unlink()
        data = {**original, 'observed_at': '2999-01-01T00:00:00Z'}
        path.write_text(json.dumps(data)); manifest['window']['to'] = data['observed_at']
        manifest['window']['end'].update(path=str(path), sha256=hashlib.sha256(path.read_bytes()).hexdigest())
        with self.assertRaisesRegex(ValueError, 'checkpoint_in_future'):
            fixtures.collector.collect(manifest)

    def test_renderer_groups_models_within_their_own_sessions(self):
        f = self.fixture
        f.records.insert(3, fixtures.record('turn_context', {'turn_id': 'turn', 'model': 'model-a'}, 1))
        f.records[-1:-1] = [fixtures.record('turn_context', {'turn_id': 'turn', 'model': 'model-b'}, 3),
                            fixtures.response(response_id='second', second=4)]
        manifest = f.manifest()
        child = [fixtures.record('session_meta', {'id': 'child', 'parent_thread_id': 'root'}),
                 fixtures.start('child-turn', parent='turn', root='turn', second=1),
                 fixtures.response('child', 'child-turn', 'child-response', 5)]
        manifest['sources'].append(f.source(child, 'child'))
        data = fixtures.collector.collect(manifest)
        section = renderer().render(data)['details']
        self.assertIn('Total recorded tokens: 330', section)
        for expected in ('| root | model-a | 110 | 1 |', '| root | model-b | 110 | 1 |',
                         '| child | unavailable | 110 | 1 |'):
            self.assertIn(expected, section)
        self.assertNotIn('| child | model-', section)

    def test_saved_json_renderer_cli_matches_api_and_rejects_invalid_fallback(self):
        data = fixtures.collector.collect(self.fixture.manifest())
        path = self.fixture.root / 'accounting.json'; path.write_text(json.dumps(data))
        args = [sys.executable, str(SCRIPTS / 'render_token_usage.py'), '--accounting', str(path), '--format', 'json']
        result = subprocess.run(args, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout), renderer().render(data))
        path.write_text('{"schema":"investigation-token-usage-error/v1","code":"PRIVATE"}')
        result = subprocess.run(args, capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(result.stdout, '')
        self.assertNotIn('PRIVATE', result.stderr)
        self.assertNotIn(str(path), result.stderr)


if __name__ == '__main__':
    unittest.main()
