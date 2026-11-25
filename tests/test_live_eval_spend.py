import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
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

    def call(self, *args, cost='0.25', budget=None):
        env = {**self.env, 'STUB_COST': cost}
        if budget is not None:
            env['LIVE_EVAL_JOB_BUDGET_USD'] = str(budget)
        return subprocess.run([sys.executable, str(SHIM), *args], input='prompt', capture_output=True, text=True, env=env)

    def test_records_session_cost_and_passes_output_through(self):
        result = self.call('-p', '--output-format', 'stream-json')
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout.strip(), 'stub output -p --output-format stream-json')
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


if __name__ == '__main__':
    unittest.main()
