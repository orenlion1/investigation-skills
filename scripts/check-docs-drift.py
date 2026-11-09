#!/usr/bin/env python3
"""Fail closed when README or diagram assets drift from the repository's state.

Enforces the docs block of policy/root-contract.json: every diagrams/DIAGRAM-*
set is complete (every declared suffix exists for each base name), every diagram
file README.md references exists, every policy-required README section exists,
and — when enabled — every skill routed in the root files appears in the routing
diagram's DOT source. Self-auditing: the run fails when it checked fewer diagram
sets or README references than the policy declares.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
README_DIAGRAM = re.compile(r'\(((?:[a-z0-9_-]+/)*DIAGRAM-[A-Za-z0-9._-]+)\)|'
                            r'(?:src|srcset)="((?:[a-z0-9_-]+/)*DIAGRAM-[A-Za-z0-9._-]+)"')
HEADING = re.compile(r'^#{2,3} (.+?)\s*$', re.MULTILINE)
ROUTING_LINK = re.compile(r'\]\(skills/([a-z0-9]+(?:-[a-z0-9]+)*)/SKILL\.md\)')


def read_regular(path: Path) -> str:
    if path.is_symlink() or not path.is_file() or path.stat().st_size > 4 * 1024 * 1024:
        raise ValueError(f'{path}: expected a readable regular file under 4 MiB')
    return path.read_text(encoding='utf-8')


def load_docs_policy(path: Path) -> dict:
    policy = json.loads(read_regular(path))
    if not isinstance(policy, dict) or policy.get('schema') != 'root-contract/v1':
        raise ValueError('policy must be root-contract/v1')
    docs = policy.get('docs')
    required = {'readme', 'readme_required_sections', 'diagram_dir', 'diagram_suffixes',
                'routing_diagram', 'minimum'}
    if not isinstance(docs, dict) or not required <= set(docs):
        raise ValueError('policy docs must declare readme, readme_required_sections, '
                         'diagram_dir, diagram_suffixes, routing_diagram, minimum')
    if (not isinstance(docs['diagram_suffixes'], list) or not docs['diagram_suffixes']
            or not all(isinstance(s, str) and s.startswith(('.', '-')) for s in
                       docs['diagram_suffixes'])):
        raise ValueError('docs diagram_suffixes must be a nonempty list of suffixes')
    routing = docs['routing_diagram']
    if (not isinstance(routing, dict) or set(routing) != {'enabled', 'dot'}
            or not isinstance(routing['enabled'], bool) or not isinstance(routing['dot'], str)):
        raise ValueError('docs routing_diagram must declare enabled and dot')
    minimum = docs['minimum']
    if (not isinstance(minimum, dict)
            or set(minimum) != {'diagram_sets', 'readme_diagram_references'}
            or not all(isinstance(minimum[k], int) and minimum[k] >= 1 for k in minimum)):
        raise ValueError('docs minimum must declare positive integer diagram_sets and '
                         'readme_diagram_references')
    return docs


def diagram_bases(diagram_dir: Path, suffixes: list[str]) -> set[str]:
    bases: set[str] = set()
    if not diagram_dir.is_dir():
        return bases
    for path in diagram_dir.iterdir():
        if not path.name.startswith('DIAGRAM-'):
            continue
        for suffix in sorted(suffixes, key=len, reverse=True):
            if path.name.endswith(suffix):
                bases.add(path.name[: -len(suffix)])
                break
    return bases


def check(repository: Path, docs: dict, root_file: str) -> list[str]:
    errors: list[str] = []
    diagram_dir = repository / docs['diagram_dir']
    bases = diagram_bases(diagram_dir, docs['diagram_suffixes'])
    if not bases:
        errors.append(f'no diagram sets found under {diagram_dir}')
    for base in sorted(bases):
        for suffix in docs['diagram_suffixes']:
            expected = diagram_dir / f'{base}{suffix}'
            if not expected.is_file():
                errors.append(f'incomplete diagram set {base}: missing {expected.name}')
    if len(bases) < docs['minimum']['diagram_sets']:
        errors.append(f'checked only {len(bases)} diagram sets; policy declares at least '
                      f'{docs["minimum"]["diagram_sets"]}')

    try:
        readme = read_regular(repository / docs['readme'])
    except (OSError, ValueError) as error:
        return errors + [str(error)]

    references = [group for match in README_DIAGRAM.finditer(readme)
                  for group in match.groups() if group]
    for reference in references:
        if not (repository / reference).is_file():
            errors.append(f'{docs["readme"]} references a missing diagram file: {reference}')
    if len(references) < docs['minimum']['readme_diagram_references']:
        errors.append(f'checked only {len(references)} README diagram references; policy '
                      f'declares at least {docs["minimum"]["readme_diagram_references"]}')

    headings = set(HEADING.findall(readme))
    for section in docs['readme_required_sections']:
        if section not in headings:
            errors.append(f'{docs["readme"]} is missing the required section: {section}')

    routing = docs['routing_diagram']
    if routing['enabled']:
        try:
            dot = read_regular(repository / routing['dot'])
            routed = set(ROUTING_LINK.findall(read_regular(repository / root_file)))
        except (OSError, ValueError) as error:
            return errors + [str(error)]
        if not routed:
            errors.append(f'no routed skills found in {root_file}')
        for skill in sorted(routed):
            if skill not in dot:
                errors.append(f'routing diagram {routing["dot"]} does not mention the routed '
                              f'skill: {skill}')
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repository', type=Path, default=ROOT)
    parser.add_argument('--policy', type=Path, default=None)
    parser.add_argument('--root-file', default='CLAUDE.md')
    args = parser.parse_args()
    policy_path = args.policy or args.repository / 'policy' / 'root-contract.json'
    try:
        docs = load_docs_policy(policy_path)
        errors = check(args.repository, docs, args.root_file)
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f'error: {error}', file=sys.stderr)
        return 1
    for error in errors:
        print(f'error: {error}', file=sys.stderr)
    if errors:
        return 1
    print('docs contract: diagram sets, README references and sections verified — PASSED')
    return 0


if __name__ == '__main__':
    sys.exit(main())
