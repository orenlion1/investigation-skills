"""Deterministic prompt preparation; no live Grafana request is made."""
import json
from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'skills/rhyming-incident-search/scripts/prepare_assistant_search.py'


class AssistantPreparationTests(unittest.TestCase):
    def setUp(self):
        self.endpoint = {'id': 'match', 'kind': 'grafana-assistant-search',
                         'target': 'service-a', 'context': 'history-ops'}
        self.shared = {'incident': 'incident-example elevated latency', 'symptoms': 'HTTP 503',
                       'services_environment': 'service-a production',
                       'incident_window': {'start': '2026-11-09T12:00:00Z',
                                           'end': '2026-11-09T13:00:00Z', 'timezone': 'UTC'},
                       'historical_window': {'start': '2026-11-02T12:00:00Z',
                                             'end': '2026-11-09T12:00:00Z', 'timezone': 'UTC'},
                       'matching_criteria': 'symptoms, components, mechanisms, mitigations',
                       'permitted_terms_redactions': 'service-a; remove personal data'}

    def prepare(self, **overrides):
        data = dict(endpoints=[self.endpoint], shared=self.shared,
                    assistant_enabled=True, existing_branches=[])
        data.update(overrides)
        result = subprocess.run([sys.executable, str(SCRIPT)], input=json.dumps(data),
                                text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout)

    def test_command_has_complete_brief_and_exact_context(self):
        result = self.prepare()
        args = result['executions'][0]['arguments']
        self.assertEqual(args[:3], ['gcx', 'assistant', 'prompt'])
        self.assertEqual(args[4:], ['--context', 'history-ops', '--json', '--no-stream', '--timeout', '300'])
        for value in ['incident-example', 'HTTP 503', 'production', '2026-11-02', 'UTC', 'service-a',
                      'contradictions', 'hypotheses', 'read-only', 'Do not create investigations',
                      'source link', 'limitations']:
            self.assertIn(value, args[3])
        self.assertEqual(result['endpoints'][0]['role'], 'owner')

    def branch(self, **overrides):
        branch = dict(reference='assistant-main', context='history-ops', scope='service-a',
                      shared=self.shared, prompt_sent=False, initial_prompt='Investigate incident-example')
        branch.update(overrides)
        return branch

    def test_share_existing_initial_prompt_keep_endpoint_rows(self):
        endpoints = [self.endpoint, dict(self.endpoint, id='match-two')]
        result = self.prepare(endpoints=endpoints, existing_branches=[self.branch()])
        self.assertEqual(len(result['executions']), 1)
        execution = result['executions'][0]
        self.assertEqual(execution['owner_reference'], 'assistant-main')
        self.assertIn('Investigate incident-example', execution['arguments'][3])
        self.assertEqual([row['endpoint_id'] for row in result['endpoints']], ['match', 'match-two'])
        self.assertEqual({row['role'] for row in result['endpoints']}, {'consumer'})
        self.assertEqual({row['execution_reference'] for row in result['endpoints']}, {execution['reference']})

    def test_different_context_or_scope_does_not_share(self):
        for branch in [self.branch(context='other'), self.branch(scope='service-b'),
                       self.branch(shared=dict(self.shared, incident='incident-other'))]:
            result = self.prepare(existing_branches=[branch])
            self.assertEqual(result['executions'][0]['owner_reference'], 'match')
        result = self.prepare(endpoints=[self.endpoint, dict(self.endpoint, id='other', context='other')])
        self.assertEqual(len(result['executions']), 2)

    def test_late_arrival_never_sends_second_prompt(self):
        result = self.prepare(existing_branches=[self.branch(prompt_sent=True)])
        self.assertEqual(result['executions'], [])
        self.assertEqual(result['endpoints'][0]['status'], 'unavailable')
        self.assertIn('already sent', result['endpoints'][0]['limitation'])

    def test_disabled_and_history_never_prepare_prompt(self):
        history = dict(self.endpoint, id='history', kind='grafana-assistant-conversations')
        result = self.prepare(endpoints=[self.endpoint, history], assistant_enabled=False)
        self.assertEqual(result['executions'], [])
        self.assertEqual([x['status'] for x in result['endpoints']], ['disabled', 'history-only'])
        self.assertEqual(self.prepare(endpoints=[history])['executions'], [])

    def test_two_endpoints_without_existing_branch_use_one_owner(self):
        result = self.prepare(endpoints=[self.endpoint, dict(self.endpoint, id='second')])
        self.assertEqual(len(result['executions']), 1)
        self.assertEqual([x['role'] for x in result['endpoints']], ['owner', 'consumer'])

    def test_ambiguous_ownership_rejects_entire_preparation(self):
        data = dict(endpoints=[self.endpoint], shared=self.shared, assistant_enabled=True,
                    existing_branches=[self.branch(), self.branch(reference='other-owner')])
        result = subprocess.run([sys.executable, str(SCRIPT)], input=json.dumps(data),
                                text=True, capture_output=True)
        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stdout, '')

    def test_invalid_inputs_fail_without_command_or_echo(self):
        for shared in [dict(self.shared, incident=''),
                       dict(self.shared, incident_window={'start': 'yesterday'}),
                       dict(self.shared, historical_window=dict(self.shared['historical_window'], timezone='Invalid/Zone'))]:
            data = dict(endpoints=[self.endpoint], shared=shared, assistant_enabled=True)
            result = subprocess.run([sys.executable, str(SCRIPT)], input=json.dumps(data),
                                    text=True, capture_output=True)
            self.assertEqual(result.returncode, 2)
            self.assertEqual(result.stdout, '')
            self.assertNotIn('incident-example', result.stderr)
