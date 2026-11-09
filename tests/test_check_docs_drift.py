"""Fixture coverage for the docs-drift checker: each failure mode plus the real tree."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
CHECKER = REPOSITORY_ROOT / 'scripts/check-docs-drift.py'


def load_checker():
    specification = importlib.util.spec_from_file_location('docs_drift_checker', CHECKER)
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module


README_TEXT = """# Fixture

## Skill philosophy

The model.

![view](diagrams/DIAGRAM-flow-light.png)
[Editable](diagrams/DIAGRAM-flow.dot)
"""

ROOT_TEXT = """# Repository Policy

## Routing

| Request | Owning skill |
| --- | --- |
| Alpha work | [Alpha](skills/alpha/SKILL.md) |
"""

DOCS_POLICY = {
    'schema': 'root-contract/v1',
    'files': ['AGENTS.md', 'CLAUDE.md'],
    'max_lines': 20,
    'allowed_sections': ['Routing'],
    'required_sections': ['Routing'],
    'routing_section': 'Routing',
    'skills_dir': 'skills',
    'minimum': {'sections': 1, 'skills': 1},
    'docs': {
        'readme': 'README.md',
        'readme_required_sections': ['Skill philosophy'],
        'diagram_dir': 'diagrams',
        'diagram_suffixes': ['.dot', '-light.png'],
        'routing_diagram': {'enabled': True, 'dot': 'diagrams/DIAGRAM-flow.dot'},
        'minimum': {'diagram_sets': 1, 'readme_diagram_references': 2},
    },
}


class DocsDriftFixture(unittest.TestCase):
    def setUp(self):
        self.checker = load_checker()
        self.tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tempdir.cleanup)
        self.root = Path(self.tempdir.name)
        diagrams = self.root / 'diagrams'
        diagrams.mkdir()
        (diagrams / 'DIAGRAM-flow.dot').write_text('digraph { "skills/alpha" }',
                                                   encoding='utf-8')
        (diagrams / 'DIAGRAM-flow-light.png').write_bytes(b'png')
        (self.root / 'README.md').write_text(README_TEXT, encoding='utf-8')
        (self.root / 'CLAUDE.md').write_text(ROOT_TEXT, encoding='utf-8')
        (self.root / 'policy').mkdir()
        self.policy_path = self.root / 'policy' / 'root-contract.json'
        self.policy_path.write_text(json.dumps(DOCS_POLICY), encoding='utf-8')

    def run_check(self):
        docs = self.checker.load_docs_policy(self.policy_path)
        return self.checker.check(self.root, docs, 'CLAUDE.md')

    def test_conforming_fixture_passes(self):
        self.assertEqual(self.run_check(), [])

    def test_incomplete_diagram_set_fails(self):
        (self.root / 'diagrams' / 'DIAGRAM-flow-light.png').unlink()
        errors = self.run_check()
        self.assertTrue(any('incomplete diagram set' in e for e in errors), errors)

    def test_readme_missing_diagram_reference_fails(self):
        (self.root / 'README.md').write_text(
            README_TEXT.replace('DIAGRAM-flow-light.png', 'DIAGRAM-gone-light.png'),
            encoding='utf-8')
        errors = self.run_check()
        self.assertTrue(any('missing diagram file' in e for e in errors), errors)

    def test_readme_missing_required_section_fails(self):
        (self.root / 'README.md').write_text(
            README_TEXT.replace('## Skill philosophy', '## Something else'),
            encoding='utf-8')
        errors = self.run_check()
        self.assertTrue(any('required section: Skill philosophy' in e for e in errors), errors)

    def test_routing_diagram_missing_skill_fails(self):
        (self.root / 'diagrams' / 'DIAGRAM-flow.dot').write_text('digraph { other }',
                                                                 encoding='utf-8')
        errors = self.run_check()
        self.assertTrue(any('does not mention the routed skill: alpha' in e for e in errors),
                        errors)

    def test_self_audit_fails_below_declared_minimums(self):
        policy = json.loads(self.policy_path.read_text(encoding='utf-8'))
        policy['docs']['minimum'] = {'diagram_sets': 3, 'readme_diagram_references': 9}
        self.policy_path.write_text(json.dumps(policy), encoding='utf-8')
        errors = self.run_check()
        self.assertTrue(any('diagram sets' in e and 'checked only' in e for e in errors),
                        errors)
        self.assertTrue(any('README diagram references' in e for e in errors), errors)


class DocsDriftRealTree(unittest.TestCase):
    def test_real_repository_passes(self):
        checker = load_checker()
        docs = checker.load_docs_policy(REPOSITORY_ROOT / 'policy' / 'root-contract.json')
        self.assertEqual(checker.check(REPOSITORY_ROOT, docs, 'CLAUDE.md'), [])


if __name__ == '__main__':
    unittest.main()
