#!/usr/bin/env python3
"""Deterministic, dependency-free validation of every skill package in a catalog.

Each skill directory holds a regular SKILL.md with closed frontmatter, a kebab-case name
equal to its directory, a bounded description without angle brackets, and no scaffold
placeholder. An empty catalog fails: a scan that found nothing proves nothing.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

MAX_SKILL_BYTES = 1_048_576
NAME_PATTERN = re.compile(r'^[a-z0-9]+(?:-[a-z0-9]+)*$')
PLACEHOLDER = re.compile(r'\[TODO(?:[:\]])|\bTBD\b|\bYOUR_[A-Z_]+\b', re.IGNORECASE)


def unquote(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
        return value[1:-1]
    return value


def validate(skill_dir: Path) -> str | None:
    """Return the first violation in one skill package, or None when it is valid."""
    skill_file = skill_dir / 'SKILL.md'
    if not skill_dir.is_dir() or skill_dir.is_symlink():
        return f'skill directory must be a real directory: {skill_dir}'
    if not skill_file.is_file() or skill_file.is_symlink():
        return f'SKILL.md must be a regular non-symlink file: {skill_file}'
    size = skill_file.stat().st_size
    if size < 1 or size > MAX_SKILL_BYTES:
        return f'SKILL.md size is outside 1..{MAX_SKILL_BYTES} bytes: {size}'
    source = skill_file.read_text(encoding='utf-8')
    lines = source.splitlines()
    if not lines or lines[0] != '---':
        return f'SKILL.md lacks opening YAML frontmatter: {skill_file}'
    try:
        closing_index = lines.index('---', 1)
    except ValueError:
        return f'SKILL.md lacks closing YAML frontmatter: {skill_file}'
    fields: dict[str, str] = {}
    for line in lines[1:closing_index]:
        if not line.strip() or line.startswith((' ', '\t', '#')):
            continue
        if ':' not in line:
            return f'invalid frontmatter line in {skill_file}: {line}'
        key, value = line.split(':', 1)
        fields[key.strip()] = unquote(value.strip())
    name = fields.get('name', '')
    description = fields.get('description', '')
    if not NAME_PATTERN.fullmatch(name):
        return f'invalid or missing skill name: {name or "<missing>"}'
    if name != skill_dir.name:
        return f'skill name {name!r} does not match directory {skill_dir.name!r}'
    if not description:
        return f'missing description: {skill_file}'
    if len(description) > 1024:
        return f'description exceeds 1024 characters: {skill_file}'
    if '<' in description or '>' in description:
        return f'description contains unsupported angle brackets: {skill_file}'
    if PLACEHOLDER.search(source):
        return f'scaffold placeholder remains in {skill_file}'
    return None


def check(repository: Path, skills_dir: str = 'skills') -> tuple[list[str], int]:
    """Validate every skill under the catalog; return violations and the number checked."""
    catalog = repository / skills_dir
    if catalog.is_symlink() or not catalog.is_dir():
        return [f'skill catalog must be a real directory: {catalog}'], 0
    directories = sorted(p for p in catalog.iterdir()
                         if not p.name.startswith('.') and (p.is_dir() or p.is_symlink()))
    if not directories:
        return [f'no skills found under {catalog}'], 0
    errors = [error for error in map(validate, directories) if error]
    return errors, len(directories)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repository', type=Path, default=Path.cwd())
    parser.add_argument('--skills-dir', default='skills')
    args = parser.parse_args()
    errors, count = check(args.repository, args.skills_dir)
    for error in errors:
        print(f'error: {error}', file=sys.stderr)
    if errors:
        return 1
    print(f'skill validation: {count} skill package(s) valid — PASSED')
    return 0


if __name__ == '__main__':
    sys.exit(main())
