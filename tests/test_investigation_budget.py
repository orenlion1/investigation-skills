"""Exercise the soft checkpoint CLI with observed wall and wait boundaries."""
import json
from pathlib import Path
import subprocess
import sys
import unittest

HELPER = Path(__file__).resolve().parents[1] / 'skills/open-edit-close-execute/scripts/investigation_budget.py'
START = '2026-01-01T12:00:00Z'


class InvestigationBudgetTests(unittest.TestCase):
    def run_budget(self, *args):
        return subprocess.run([sys.executable, str(HELPER), '--started', START, *args],
                              capture_output=True, text=True)

    def test_soft_boundary_and_continuation_remain_successful(self):
        for now, due in [('12:09:59', False), ('12:10:00', True), ('12:26:00', True)]:
            result = self.run_budget('--observed', '2026-01-01T' + now + 'Z')
            self.assertEqual(result.returncode, 0, result.stderr)
            data = json.loads(result.stdout)
            self.assertEqual(data['checkpoint_due'], due)
            self.assertIsNone(data['non_wait_wall_seconds'])
        result = self.run_budget('--observed', '2026-01-01T12:26:00Z',
                                 '--checkpoint', '2026-01-01T12:10:00Z')
        self.assertFalse(json.loads(result.stdout)['checkpoint_due'])

    def test_waits_union_without_restarting_clock_or_summing_parallel_work(self):
        result = self.run_budget('--observed', '2026-01-01T12:12:00Z',
                                 '--wait', 'editor', START, '2026-01-01T12:05:00Z',
                                 '--wait', 'authentication', '2026-01-01T12:04:00Z',
                                 '2026-01-01T12:06:00Z', '--wait-coverage', 'complete')
        self.assertEqual(result.returncode, 0, result.stderr)
        data = json.loads(result.stdout)
        self.assertEqual(data['elapsed_seconds'], 720)
        self.assertEqual(data['observed_wait_seconds'], 360)
        self.assertEqual(data['non_wait_wall_seconds'], 360)
        self.assertTrue(data['checkpoint_due'])
        self.assertEqual(data['wait_seconds_by_kind']['editor'], 300)

    def test_invalid_boundaries_fail_clearly(self):
        for args in [('--observed', '2026-01-01T11:59:59Z'),
                     ('--observed', '2026-01-01T12:10:00'),
                     ('--checkpoint', '2026-01-01T11:59:00Z'),
                     ('--checkpoint', '2026-01-01T12:09:00Z')]:
            result = self.run_budget(*args)
            self.assertEqual(result.returncode, 2)
            self.assertIn('error:', result.stderr)
