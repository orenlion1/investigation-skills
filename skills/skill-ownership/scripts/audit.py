#!/usr/bin/env python3
"""Audit a repository against the skill ownership principle. Read-only.

The audit classifies each level-two section of the root files as a route, residual
policy, or workflow content that belongs in a skill, and lists unrouted skills, routes
without a skill, oversized skills and broken links. The classification is a heuristic
proposal for a reviewer; enforcement stays with the section allowlist in the root
contract. Nothing here writes to the target repository.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import guardrails

CLAUSE = ('This document routes requests to their owners. Each owner holds its workflow, '
          'guidance, and verification; follow the owner rather than restating or overriding it '
          'here. Everything else here is policy that no owner covers, and where such a policy '
          'limits an owner, the limit holds.')
DEFAULT_ROOT_FILES = ('AGENTS.md', 'CLAUDE.md')
ROOT_POLICY = 'policy/root-contract.json'
ADVISORY_SKILL_BYTES = 16 * 1024
SECTION = re.compile(r'^## (.+?)\s*$', re.MULTILINE)
ROUTING_LINK = re.compile(r'\]\((?:\./)?([A-Za-z0-9_./-]+)/([a-z0-9]+(?:-[a-z0-9]+)*)/SKILL\.md\)')
ORDERED_ITEM = re.compile(r'^\s*\d+[.)]\s+')
BULLET = re.compile(r'^\s*[-*+]\s+(\S+)')
# Verbs that open an instruction. A bullet that starts with one tells the reader how to do
# something, which is what a skill owns.
IMPERATIVES = frozenset('''add apply batch bind build check commit copy create delete deploy edit
fetch include insert install keep merge open preserve publish push read record redact report
re-read rerun resolve review run save select set stage start stop tag test update use verify
wait write'''.split())
CLASS_LABELS = {'route': 'route', 'residual-policy': 'residual policy',
                'workflow': 'workflow content that belongs in a skill'}


def classify(body: str, routed_here: bool) -> tuple[str, list[str]]:
    """Return a section's class and the signals that decided it."""
    if routed_here:
        return 'route', ['links skills from a table']
    prose = guardrails.split_code(body)[0]
    fenced_blocks = sum(1 for line in body.splitlines() if guardrails.FENCE.match(line)) // 2
    ordered = sum(1 for line in prose if ORDERED_ITEM.match(line))
    imperative = sum(1 for line in prose
                     if (match := BULLET.match(line))
                     and match.group(1).strip('`*_:,.').lower() in IMPERATIVES)
    signals = []
    if ordered >= 3:
        signals.append(f'{ordered} numbered steps')
    if imperative >= 3:
        signals.append(f'{imperative} imperative bullets')
    if fenced_blocks and (ordered or imperative):
        signals.append(f'{fenced_blocks} command block(s) beside steps')
    if signals:
        return 'workflow', signals
    return 'residual-policy', ['states a limit or rule without steps']


def root_settings(repository: Path) -> tuple[list[str], str, str]:
    """Root files, ownership clause and skills directory: from the policy when present."""
    policy_path = repository / ROOT_POLICY
    if policy_path.is_file():
        policy = json.loads(guardrails.read_regular(policy_path))
        if isinstance(policy, dict):
            files = policy.get('files')
            if isinstance(files, list) and files and all(isinstance(f, str) for f in files):
                return (files, policy.get('ownership_clause') or CLAUSE,
                        policy.get('skills_dir') or 'skills')
    return ([name for name in DEFAULT_ROOT_FILES if (repository / name).is_file()],
            CLAUSE, 'skills')


def audit(repository: Path) -> dict:
    repository = Path(repository)
    files, clause, skills_dir = root_settings(repository)
    if not files:
        raise ValueError(f'no root file found in {repository}: expected '
                         + ' or '.join(DEFAULT_ROOT_FILES))
    contents = [guardrails.read_regular(repository / name) for name in files]
    text = contents[0]
    matches = list(SECTION.finditer(text))
    preamble = text[:matches[0].start()] if matches else text
    preamble_body = ' '.join(' '.join(preamble.splitlines()[1:]).split())

    routed, sections = set(), []
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        body = text[match.end():end]
        links = {name for base, name in ROUTING_LINK.findall(body) if base == skills_dir}
        table_links = {name for line in body.splitlines() if line.lstrip().startswith('|')
                       for base, name in ROUTING_LINK.findall(line) if base == skills_dir}
        routed |= links
        section_class, signals = classify(body, bool(table_links))
        sections.append({'title': match.group(1), 'class': section_class, 'signals': signals,
                         'lines': len([line for line in body.splitlines() if line.strip()])})

    skills = [d.name for d in guardrails.skill_dirs(repository, skills_dir)]
    baseline = None
    baseline_path = repository / guardrails.BASELINE_RELATIVE
    if baseline_path.is_file():
        baseline = guardrails.load_baseline(baseline_path)
    oversized = []
    for skill, size in guardrails.current_sizes(repository, skills_dir).items():
        limit = baseline.get(skill) if baseline is not None else ADVISORY_SKILL_BYTES
        if limit is not None and size > limit:
            oversized.append({'skill': skill, 'bytes': size, 'limit': limit,
                              'against': 'recorded baseline' if baseline is not None
                              else 'advisory threshold (no baseline recorded)'})
    return {
        'schema': 'skill-ownership-audit/v1',
        'root_files': files,
        'clause_present': preamble_body == clause,
        'root_files_identical': all(content == text for content in contents[1:]),
        'sections': sections,
        'unrouted_skills': [f'{skills_dir}/{name}' for name in skills if name not in routed],
        'routes_without_skill': [f'{skills_dir}/{name}' for name in sorted(routed)
                                 if name not in skills],
        'oversized_skills': oversized,
        'broken_links': guardrails.link_errors(repository, skills_dir),
    }


def finding_count(report: dict) -> int:
    return (sum(1 for s in report['sections'] if s['class'] == 'workflow')
            + (not report['clause_present']) + (not report['root_files_identical'])
            + len(report['unrouted_skills']) + len(report['routes_without_skill'])
            + len(report['oversized_skills']) + len(report['broken_links']))


def render_markdown(report: dict) -> str:
    lines = ['# Skill ownership audit', '',
             'Read-only. The section classes are a heuristic proposal for review, not a verdict.',
             '', f'Root files: {", ".join(report["root_files"])}', '',
             f'- Ownership clause opens the root file verbatim: '
             f'{"yes" if report["clause_present"] else "no"}',
             f'- Root files are byte-identical: '
             f'{"yes" if report["root_files_identical"] else "no"}', '',
             '## Root-file sections', '', '| Section | Class | Lines | Why |',
             '| --- | --- | --- | --- |']
    for section in report['sections']:
        lines.append(f'| {section["title"]} | {CLASS_LABELS[section["class"]]} | '
                     f'{section["lines"]} | {"; ".join(section["signals"])} |')

    def listing(title, items):
        lines.extend(['', f'## {title}', ''])
        lines.extend([f'- {item}' for item in items] or ['- None.'])

    listing('Unrouted skills', report['unrouted_skills'])
    listing('Routes without a skill', report['routes_without_skill'])
    listing('Oversized skills', [f'{o["skill"]}: {o["bytes"]} bytes, over {o["limit"]} '
                                 f'({o["against"]})' for o in report['oversized_skills']])
    listing('Broken links', report['broken_links'])
    count = finding_count(report)
    lines.extend(['', f'{count} finding(s).' if count else 'No findings.'])
    return '\n'.join(lines) + '\n'
