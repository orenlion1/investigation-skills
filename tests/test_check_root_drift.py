"""Fixture coverage for the root-drift checker: each failure mode plus the real tree."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
CHECKER = REPOSITORY_ROOT / 'scripts/check-root-drift.py'


def load_checker():
    specification = importlib.util.spec_from_file_location('root_drift_checker', CHECKER)
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module


CLAUSE = 'This document routes requests to their owners. The limit holds.'

ROOT_TEXT = """# Repository Policy

This document routes requests to their owners.
The limit holds.

## Routing

| Request | Owning skill |
| --- | --- |
| Alpha work | [Alpha](skills/alpha/SKILL.md) |
| Beta work | [Beta](skills/beta/SKILL.md) |

## Skill Quality Gate

Run the gate.
"""

POLICY = {
    'schema': 'root-contract/v1',
    'files': ['AGENTS.md', 'CLAUDE.md'],
    'max_lines': 20,
    'ownership_clause': CLAUSE,
    'allowed_sections': ['Routing', 'Skill Quality Gate'],
    'required_sections': ['Routing', 'Skill Quality Gate'],
    'routing_section': 'Routing',
    'skills_dir': 'skills',
    'minimum': {'sections': 2, 'skills': 2},
    'docs': {
        'readme': 'README.md',
        'readme_required_sections': [],
        'diagram_dir': 'diagrams',
        'diagram_suffixes': ['.dot'],
        'routing_diagram': {'enabled': False, 'dot': 'diagrams/DIAGRAM-routing.dot'},
        'minimum': {'diagram_sets': 1, 'readme_diagram_references': 1},
    },
}


class RootDriftFixture(unittest.TestCase):
    def setUp(self):
        self.checker = load_checker()
        self.tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tempdir.cleanup)
        self.root = Path(self.tempdir.name)
        for skill in ('alpha', 'beta'):
            (self.root / 'skills' / skill).mkdir(parents=True)
            (self.root / 'skills' / skill / 'SKILL.md').write_text('# skill\n', encoding='utf-8')
        self.write_roots(ROOT_TEXT)
        (self.root / 'policy').mkdir()
        self.policy_path = self.root / 'policy' / 'root-contract.json'
        self.policy_path.write_text(json.dumps(POLICY), encoding='utf-8')

    def write_roots(self, text, claude=None):
        (self.root / 'AGENTS.md').write_text(text, encoding='utf-8')
        (self.root / 'CLAUDE.md').write_text(claude if claude is not None else text,
                                             encoding='utf-8')

    def run_check(self):
        policy = self.checker.load_policy(self.policy_path)
        return self.checker.check(self.root, policy)

    def test_conforming_fixture_passes(self):
        self.assertEqual(self.run_check(), [])

    def test_reintroduced_workflow_section_fails(self):
        self.write_roots(ROOT_TEXT + '\n## Report Evidence\n\nFull workflow text.\n')
        errors = self.run_check()
        self.assertTrue(any('Report Evidence' in e and 'allowlist' in e for e in errors),
                        errors)

    def test_oversize_root_file_fails(self):
        self.write_roots(ROOT_TEXT + '\n' * 30 + 'tail\n')
        errors = self.run_check()
        self.assertTrue(any('budget' in e for e in errors), errors)

    def test_missing_routing_row_fails(self):
        (self.root / 'skills' / 'gamma').mkdir()
        errors = self.run_check()
        self.assertTrue(any('skills/gamma' in e for e in errors), errors)

    def test_parity_break_fails(self):
        self.write_roots(ROOT_TEXT, claude=ROOT_TEXT + 'extra line\n')
        errors = self.run_check()
        self.assertTrue(any('byte-identical' in e for e in errors), errors)

    def test_missing_required_section_fails(self):
        self.write_roots(ROOT_TEXT.replace('## Skill Quality Gate\n\nRun the gate.\n', ''))
        errors = self.run_check()
        self.assertTrue(any('required section missing' in e for e in errors), errors)

    def test_reworded_ownership_clause_fails(self):
        self.write_roots(ROOT_TEXT.replace('The limit holds.', 'The owner wins.'))
        errors = self.run_check()
        self.assertTrue(any('ownership clause verbatim' in e for e in errors), errors)

    def test_missing_ownership_clause_fails(self):
        self.write_roots(ROOT_TEXT.replace(
            'This document routes requests to their owners.\nThe limit holds.\n\n', ''))
        errors = self.run_check()
        self.assertTrue(any('ownership clause verbatim' in e for e in errors), errors)

    def test_rewrapped_ownership_clause_passes(self):
        self.write_roots(ROOT_TEXT.replace('owners.\nThe limit', 'owners. The\nlimit'))
        self.assertEqual(self.run_check(), [])

    def test_content_beside_ownership_clause_fails(self):
        self.write_roots(ROOT_TEXT.replace('## Routing', 'Always run step one first.\n\n## Routing'))
        errors = self.run_check()
        self.assertTrue(any('beside the ownership clause' in e for e in errors), errors)

    def test_missing_title_fails(self):
        self.write_roots(ROOT_TEXT.replace('# Repository Policy\n\n', ''))
        errors = self.run_check()
        self.assertTrue(any('level-one title' in e for e in errors), errors)

    def test_routing_row_for_missing_skill_fails(self):
        self.write_roots(ROOT_TEXT.replace(
            '| Beta work |', '| Ghost work | [Ghost](skills/ghost/SKILL.md) |\n| Beta work |'))
        errors = self.run_check()
        self.assertTrue(any('skills/ghost' in e and 'no SKILL.md' in e for e in errors), errors)

    def test_link_to_missing_root_section_fails(self):
        (self.root / 'docs').mkdir()
        (self.root / 'docs' / 'note.md').write_text(
            'See [gate](../AGENTS.md#skill-quality-gate) and '
            '[gone](../CLAUDE.md#templated-tasks).\n', encoding='utf-8')
        errors = self.run_check()
        self.assertEqual([e for e in errors if 'links to a section' in e],
                         ['docs/note.md links to a section the root files do not have: '
                          'CLAUDE.md#templated-tasks'])

    def test_policy_without_ownership_clause_is_rejected(self):
        policy = {k: v for k, v in POLICY.items() if k != 'ownership_clause'}
        self.policy_path.write_text(json.dumps(policy), encoding='utf-8')
        with self.assertRaises(ValueError):
            self.checker.load_policy(self.policy_path)

    def test_self_audit_fails_below_declared_minimums(self):
        policy = dict(POLICY)
        policy['minimum'] = {'sections': 5, 'skills': 5}
        self.policy_path.write_text(json.dumps(policy), encoding='utf-8')
        errors = self.run_check()
        self.assertTrue(any('checked only' in e and 'sections' in e for e in errors), errors)
        self.assertTrue(any('checked only' in e and 'skills' in e for e in errors), errors)


class RootDriftRealTree(unittest.TestCase):
    def test_real_repository_passes(self):
        checker = load_checker()
        policy = checker.load_policy(REPOSITORY_ROOT / 'policy' / 'root-contract.json')
        self.assertEqual(checker.check(REPOSITORY_ROOT, policy), [])


if __name__ == '__main__':
    unittest.main()
