#!/usr/bin/env python3
"""Fail closed when workflow content accretes in the root routing files.

Enforces policy/root-contract.json: the declared root files stay byte-identical,
within the line budget, open with one title and the verbatim ownership clause and
nothing else, contain only allowlisted level-two sections, and their routing table
reaches every directory under skills/ and names no skill that is missing. Every
Markdown link in the repository that targets a root-file section must resolve.
Self-auditing: the run fails
when it checked fewer sections or skills than the policy declares, so an empty
scan can never pass silently.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

HEADING = re.compile(r'^## (.+?)\s*$', re.MULTILINE)
TITLE = re.compile(r'^# \S')
ANY_HEADING = re.compile(r'^#{1,6} (.+?)\s*$', re.MULTILINE)
ROUTING_LINK = re.compile(r'\]\(skills/([a-z0-9]+(?:-[a-z0-9]+)*)/SKILL\.md\)')


def read_regular(path: Path) -> str:
    if path.is_symlink() or not path.is_file() or path.stat().st_size > 1024 * 1024:
        raise ValueError(f'{path}: expected a readable regular file under 1 MiB')
    return path.read_text(encoding='utf-8')


def load_policy(path: Path) -> dict:
    policy = json.loads(read_regular(path))
    required_keys = {'schema', 'files', 'max_lines', 'ownership_clause', 'allowed_sections',
                     'required_sections', 'routing_section', 'skills_dir', 'minimum'}
    if not isinstance(policy, dict) or not required_keys <= set(policy):
        raise ValueError('policy must declare schema, files, max_lines, ownership_clause, '
                         'allowed_sections, required_sections, routing_section, skills_dir, '
                         'minimum')
    if policy['schema'] != 'root-contract/v1':
        raise ValueError(f'unsupported policy schema: {policy["schema"]!r}')
    if (not isinstance(policy['files'], list) or len(policy['files']) < 2
            or not all(isinstance(f, str) and f for f in policy['files'])):
        raise ValueError('policy files must list at least two root files')
    if not isinstance(policy['max_lines'], int) or policy['max_lines'] < 1:
        raise ValueError('policy max_lines must be a positive integer')
    clause = policy['ownership_clause']
    if not isinstance(clause, str) or not clause or clause != ' '.join(clause.split()):
        raise ValueError('policy ownership_clause must be a nonempty single-spaced sentence run')
    for key in ('allowed_sections', 'required_sections'):
        if (not isinstance(policy[key], list) or not policy[key]
                or not all(isinstance(s, str) and s for s in policy[key])):
            raise ValueError(f'policy {key} must be a nonempty list of section titles')
    if not set(policy['required_sections']) <= set(policy['allowed_sections']):
        raise ValueError('required_sections must be a subset of allowed_sections')
    minimum = policy['minimum']
    if (not isinstance(minimum, dict) or set(minimum) != {'sections', 'skills'}
            or not all(isinstance(minimum[k], int) and minimum[k] >= 1 for k in minimum)):
        raise ValueError('policy minimum must declare positive integer sections and skills')
    return policy


def check_preamble(text: str, name: str, clause: str) -> list[str]:
    """The text above the first section is one title plus the ownership clause, verbatim.

    Line wrapping is free; wording is not. Anything extra is unowned content that the
    section allowlist cannot see, so it fails too.
    """
    match = HEADING.search(text)
    lines = (text[:match.start()] if match else text).splitlines()
    if not lines or not TITLE.match(lines[0]):
        return [f'{name} must open with a single level-one title']
    body = ' '.join(' '.join(lines[1:]).split())
    if body == clause:
        return []
    if clause in body:
        return [f'{name} has content beside the ownership clause above the first section '
                f'(policy belongs in an allowlisted section, workflow in a skill)']
    return [f'{name} must carry the ownership clause verbatim above the first section: '
            f'{clause}']


def slug(heading: str) -> str:
    """GitHub's heading anchor: lowercase, punctuation dropped, spaces to hyphens."""
    kept = ''.join(ch for ch in heading.lower() if ch.isalnum() or ch in ' -_')
    return kept.replace(' ', '-')


def check_anchors(repository: Path, names: list[str], text: str) -> list[str]:
    """A section that moved to its owning skill must not keep inbound links."""
    anchors = {slug(heading) for heading in ANY_HEADING.findall(text)}
    link = re.compile(r'\]\((?:\.{1,2}/)*(' + '|'.join(re.escape(n) for n in names)
                      + r')#([^)\s]+)\)')
    errors = []
    for path in sorted(repository.rglob('*.md')):
        relative = path.relative_to(repository)
        if any(part.startswith('.') for part in relative.parts) or path.is_symlink():
            continue
        try:
            content = read_regular(path)
        except (OSError, ValueError) as error:
            errors.append(str(error))
            continue
        for name, anchor in link.findall(content):
            if anchor not in anchors:
                errors.append(f'{relative} links to a section the root files do not have: '
                              f'{name}#{anchor}')
    return errors


def check(repository: Path, policy: dict) -> list[str]:
    errors: list[str] = []
    files = [repository / name for name in policy['files']]
    contents = {}
    for path in files:
        try:
            contents[path.name] = read_regular(path)
        except (OSError, ValueError) as error:
            errors.append(str(error))
    if errors:
        return errors

    first_name = policy['files'][0]
    first = contents[first_name]
    for name in policy['files'][1:]:
        if contents[name] != first:
            errors.append(f'{name} is not byte-identical to {first_name}')

    line_count = first.count('\n') + (0 if first.endswith('\n') or not first else 1)
    if line_count > policy['max_lines']:
        errors.append(f'{first_name} has {line_count} lines; budget is {policy["max_lines"]}')

    errors.extend(check_preamble(first, first_name, policy['ownership_clause']))
    errors.extend(check_anchors(repository, policy['files'], first))

    sections = HEADING.findall(first)
    allowed = set(policy['allowed_sections'])
    for section in sections:
        if section not in allowed:
            errors.append(f'section not in the allowlist (workflow content belongs in a '
                          f'skill): ## {section}')
    for section in policy['required_sections']:
        if section not in sections:
            errors.append(f'required section missing: ## {section}')
    if len(sections) < policy['minimum']['sections']:
        errors.append(f'checked only {len(sections)} sections; policy declares at least '
                      f'{policy["minimum"]["sections"]}')

    skills_dir = repository / policy['skills_dir']
    skills = sorted(p.name for p in skills_dir.iterdir()
                    if p.is_dir() and not p.name.startswith('.')) if skills_dir.is_dir() else []
    if not skills:
        errors.append(f'no skills found under {skills_dir}')
    routed = set(ROUTING_LINK.findall(first))
    for skill in skills:
        if skill not in routed:
            errors.append(f'skill has no routing-table row: skills/{skill}')
    for skill in sorted(routed):
        if not (skills_dir / skill / 'SKILL.md').is_file():
            errors.append(f'routing row names a skill with no SKILL.md: skills/{skill}')
    if len(skills) < policy['minimum']['skills']:
        errors.append(f'checked only {len(skills)} skills; policy declares at least '
                      f'{policy["minimum"]["skills"]}')
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repository', type=Path, default=Path.cwd())
    parser.add_argument('--policy', type=Path, default=None)
    args = parser.parse_args()
    policy_path = args.policy or args.repository / 'policy' / 'root-contract.json'
    try:
        policy = load_policy(policy_path)
        errors = check(args.repository, policy)
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f'error: {error}', file=sys.stderr)
        return 1
    for error in errors:
        print(f'error: {error}', file=sys.stderr)
    if errors:
        return 1
    print(f'root contract: {len(policy["files"])} file(s), line budget '
          f'{policy["max_lines"]}, ownership clause, sections and routing coverage '
          f'verified — PASSED')
    return 0


if __name__ == '__main__':
    sys.exit(main())
