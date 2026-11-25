import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import live_eval_spend as spend  # noqa: E402

SHIM = ROOT / 'scripts' / 'live-evals-runner' / 'claude'
STUB = '''#!/usr/bin/env python3
import json, os, sys, uuid
from pathlib import Path
sys.stdin.read()
cost = os.environ.get('STUB_COST')
folder = Path(os.environ['LIVE_EVAL_PROJECTS']) / 'stub-project'
folder.mkdir(parents=True, exist_ok=True)
records = [{'type': 'assistant', 'message': {'model': 'stub-model'}}]
if cost:
    records += [{'totalCostUSD': float(cost) / 2}, {'totalCostUSD': float(cost)}]
(folder / (uuid.uuid4().hex + '.jsonl')).write_text(''.join(json.dumps(r) + '\\n' for r in records))
print('stub output ' + ' '.join(sys.argv[1:]))
'''


class LiveEvalSpendTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.real = self.tmp / 'real-claude'
        self.real.write_text(STUB)
        self.real.chmod(0o755)
        self.ledger = self.tmp / 'ledger.jsonl'
        self.env = {**os.environ, 'LIVE_EVAL_REAL_CLAUDE': str(self.real), 'LIVE_EVAL_LEDGER': str(self.ledger),
                    'LIVE_EVAL_PROJECTS': str(self.tmp / 'projects')}
        # These tests exercise the unisolated path; CI runners set GITHUB_ACTIONS themselves.
        for name in ('GITHUB_ACTIONS', 'LIVE_EVAL_ISOLATION_USER'):
            self.env.pop(name, None)

    def call(self, *args, cost='0.25', budget=None):
        env = {**self.env, 'STUB_COST': cost}
        if budget is not None:
            env['LIVE_EVAL_JOB_BUDGET_USD'] = str(budget)
        return subprocess.run([sys.executable, str(SHIM), *args], input='prompt', capture_output=True, text=True, env=env)

    def test_records_session_cost_and_passes_output_through(self):
        result = self.call('-p', '--output-format', 'stream-json')
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout.strip(), 'stub output -p --output-format stream-json '
                         '--strict-mcp-config --disallowedTools WebFetch WebSearch')
        entries = spend.read_ledger(self.ledger)
        self.assertEqual(entries[0]['cost_usd'], 0.25)
        self.assertEqual(entries[0]['role'], 'executor')
        self.assertEqual(entries[0]['models'], ['stub-model'])
        self.call('-p')
        self.assertEqual(spend.read_ledger(self.ledger)[1]['role'], 'grader')
        self.assertEqual(spend.totals(spend.read_ledger(self.ledger))['total_usd'], 0.5)

    def test_refuses_once_the_next_call_could_exceed_the_budget(self):
        self.assertEqual(self.call('-p', budget=0.6).returncode, 0)
        self.assertEqual(self.call('-p', budget=0.6).returncode, 0)
        refused = self.call('-p', budget=0.6)
        self.assertEqual(refused.returncode, spend.REFUSED_EXIT)
        self.assertIn('budget reached', refused.stderr)
        self.assertEqual(refused.stdout, '')
        self.assertEqual(len(spend.read_ledger(self.ledger)), 2)

    def test_unknown_cost_stops_further_calls(self):
        self.assertEqual(self.call('-p', cost='').returncode, 0)
        self.assertIsNone(spend.read_ledger(self.ledger)[0]['cost_usd'])
        refused = self.call('-p')
        self.assertEqual(refused.returncode, spend.REFUSED_EXIT)
        self.assertIn('recorded no cost', refused.stderr)

    def test_month_sum_and_summary_artifact(self):
        self.call('-p', '--output-format', 'stream-json', cost='0.1')
        self.call('-p', cost='0.3')
        out = self.tmp / 'spend' / 'spend.json'
        self.assertEqual(spend.main(['summary', '--ledger', str(self.ledger), '--output', str(out),
                                     '--skill', 'demo', '--model', 'stub-model', '--run-id', '1']), 0)
        record = json.loads(out.read_text())
        self.assertEqual(record['by_role'], {'executor': 0.1, 'grader': 0.3})
        blob = io.BytesIO()
        with zipfile.ZipFile(blob, 'w') as archive:
            archive.writestr('spend.json', out.read_text())
        self.assertEqual(spend.sum_spend_zips([blob.getvalue(), blob.getvalue()]), (0.8, 2))


    def test_budget_is_allotted_by_eval_count(self):
        self.assertEqual(spend.allot(50, {'a': 17, 'b': 1, 'c': 2}), {'a': 42.5, 'b': 2.5, 'c': 5.0})
        self.assertEqual(spend.allot(-1, {'a': 3}), {'a': 0.0})

    def test_oidc_token_is_minted_per_call_and_minting_variables_are_withheld(self):
        import http.server, threading
        seen = []
        failed = []

        class Issuer(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                if not failed:
                    # The first request fails as GitHub's token service sometimes does.
                    failed.append(True)
                    self.send_response(503); self.end_headers(); return
                seen.append((self.path, self.headers.get('Authorization')))
                body = json.dumps({'value': 'token-%d' % len(seen)}).encode()
                self.send_response(200); self.end_headers(); self.wfile.write(body)

            def log_message(self, *args):
                pass

        server = http.server.HTTPServer(('127.0.0.1', 0), Issuer)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        self.addCleanup(server.shutdown)
        probe = self.tmp / 'probe-claude'
        probe.write_text("""#!/usr/bin/env python3
import json, os, sys
from pathlib import Path
sys.stdin.read()
path = os.environ.get('ANTHROPIC_IDENTITY_TOKEN_FILE')
print(json.dumps({'token': Path(path).read_text() if path else None,
                  'leaked': [k for k in os.environ if k.startswith('ACTIONS_ID_TOKEN_REQUEST')]}))
""")
        probe.chmod(0o755)
        env = {**self.env, 'LIVE_EVAL_REAL_CLAUDE': str(probe), 'LIVE_EVAL_OIDC_AUDIENCE': 'https://api.example.invalid',
               'ACTIONS_ID_TOKEN_REQUEST_URL': 'http://localhost:%d/token?api-version=2.0' % server.server_port,
               'ACTIONS_ID_TOKEN_REQUEST_TOKEN': 'request-token-not-real'}
        outputs = []
        for _ in range(2):
            # The probe records no cost, which would stop the next call; start each call afresh.
            self.ledger.unlink(missing_ok=True)
            result = subprocess.run([sys.executable, str(SHIM), '-p'], input='x', capture_output=True, text=True, env=env)
            self.assertEqual(result.returncode, 0, result.stderr)
            outputs.append(json.loads(result.stdout))
        self.assertEqual([o['token'] for o in outputs], ['token-1', 'token-2'])
        self.assertEqual([o['leaked'] for o in outputs], [[], []])
        self.assertIn('audience=https%3A%2F%2Fapi.example.invalid', seen[0][0])
        self.assertEqual(seen[0][1], 'Bearer request-token-not-real')
        self.assertFalse(list(Path(tempfile.gettempdir()).glob('live-eval-oidc-*/identity-token')))

    def test_oidc_without_id_token_permission_refuses_the_call(self):
        env = {**self.env, 'LIVE_EVAL_OIDC_AUDIENCE': 'https://api.example.invalid', 'STUB_COST': '0.1'}
        env.pop('ACTIONS_ID_TOKEN_REQUEST_URL', None)
        result = subprocess.run([sys.executable, str(SHIM), '-p'], input='x', capture_output=True, text=True, env=env)
        self.assertEqual(result.returncode, spend.REFUSED_EXIT)
        self.assertIn('id-token: write', result.stderr)


class GitHubReadTests(unittest.TestCase):
    def test_transient_artifact_and_network_errors_retry_without_changing_auth(self):
        errors = [spend.urllib.error.HTTPError('https://api.github.com/test', 503, 'unavailable', {}, None),
                  spend.urllib.error.URLError('connection reset')]
        for error in errors:
            with self.subTest(error=type(error).__name__):
                response = MagicMock()
                response.__enter__.return_value.read.return_value = b'zip bytes'
                with patch.object(spend.urllib.request, 'urlopen', side_effect=[error, response]) as get, \
                        patch.object(spend.time, 'sleep') as sleep:
                    self.assertEqual(spend.github('test', 'not-a-real-token', raw=True), b'zip bytes')
                self.assertEqual(get.call_count, 2)
                sleep.assert_called_once_with(2)
                for call in get.call_args_list:
                    request = call.args[0]
                    self.assertEqual(request.unredirected_hdrs['Authorization'], 'Bearer not-a-real-token')
                    self.assertNotIn('Authorization', request.headers)

    def test_permanent_permission_failure_is_not_retried(self):
        error = spend.urllib.error.HTTPError('https://api.github.com/test', 403, 'forbidden', {}, None)
        with patch.object(spend.urllib.request, 'urlopen', side_effect=error) as get, \
                patch.object(spend.time, 'sleep') as sleep:
            with self.assertRaises(spend.urllib.error.HTTPError):
                spend.github('test', 'not-a-real-token')
        self.assertEqual(get.call_count, 1)
        sleep.assert_not_called()

    def test_retry_exhaustion_propagates_unknown_spend_instead_of_returning_zero(self):
        error = spend.urllib.error.HTTPError('https://api.github.com/test', 503, 'unavailable', {}, None)
        with patch.object(spend.urllib.request, 'urlopen', side_effect=error) as get, \
                patch.object(spend.time, 'sleep') as sleep:
            with self.assertRaises(spend.urllib.error.HTTPError):
                spend.github('test', 'not-a-real-token')
        self.assertEqual(get.call_count, 5)
        self.assertEqual([c.args[0] for c in sleep.call_args_list], [2, 4, 8, 16])

if __name__ == '__main__':
    unittest.main()
