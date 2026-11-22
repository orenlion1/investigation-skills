#!/usr/bin/env python3
"""Economization guardrails: keep each skill's always-loaded context small and honest.

Five rules, each a literal, deterministic lint:

- size ratchet: a SKILL.md never grows past its recorded baseline without an explicit,
  reviewable `ratchet --record`; it sets no absolute cap;
- duplication: a rule is stated once, in SKILL.md or in a reference, not both;
- link integrity: every relative link and heading anchor under the catalog resolves;
- description shape: one quoted line that says what the skill does and when to use it;
- token preservation: a rewrite loses no command, flag, path, identifier or bounded number
  unless the removal is declared.

None of them detects paraphrase; review keeps that job.
"""
from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

BASELINE_RELATIVE = 'policy/skill-size-baseline.json'
BASELINE_SCHEMA = 'skill-size-baseline/v1'
REMOVALS_SCHEMA = 'token-removals/v1'
DUPLICATE_MIN_CHARS = 80
DESCRIPTION_MIN, DESCRIPTION_MAX = 40, 500
MAX_BYTES = 1024 * 1024

FENCE = re.compile(r'^\s*(```|~~~)')
INLINE_CODE = re.compile(r'`([^`\n]+)`')
LIST_ITEM = re.compile(r'^\s*(?:[-*+]|\d+[.)])\s+')
HEADING = re.compile(r'^#{1,6}\s+(.+?)\s*#*\s*$')
LINK = re.compile(r'\]\(\s*<?([^)\s>]+)>?(?:\s+"[^"]*")?\s*\)')
SCHEME = re.compile(r'^[a-zA-Z][a-zA-Z0-9+.-]*:')
EXPLICIT_ANCHOR = re.compile(r'<a\s+(?:id|name)="([^"]+)"')
TRIGGER = re.compile(r'\bUse (?:when|for|only)\b')
BOUNDED_NUMBER = re.compile(
    r'\b\d+(?:\.\d+)?\s?(?:%|(?:seconds?|minutes?|hours?|days?|rounds?|attempts?|retries|'
    r'bytes?|lines?|characters?|tokens?|KiB|MiB|GiB|KB|MB|GB)\b)')


def read_regular(path: Path) -> str:
    if path.is_symlink() or not path.is_file() or path.stat().st_size > MAX_BYTES:
        raise ValueError(f'{path}: expected a readable regular file under 1 MiB')
    return path.read_text(encoding='utf-8')


def skill_dirs(repository: Path, skills_dir: str = 'skills') -> list[Path]:
    catalog = repository / skills_dir
    if catalog.is_symlink() or not catalog.is_dir():
        return []
    return sorted(p for p in catalog.iterdir() if p.is_dir() and not p.name.startswith('.')
                  and not p.is_symlink())


def markdown_files(directory: Path) -> list[Path]:
    return sorted(p for p in directory.rglob('*.md') if p.is_file() and not p.is_symlink())


def split_code(text: str) -> tuple[list[str], list[str]]:
    """Return (prose lines, fenced code lines); a fence marker belongs to neither."""
    prose, code, fenced = [], [], False
    for line in text.splitlines():
        if FENCE.match(line):
            fenced = not fenced
            prose.append('')
            continue
        (code if fenced else prose).append(line)
    return prose, code


def squash(text: str) -> str:
    return ' '.join(text.split())


# --- size ratchet -------------------------------------------------------------------------

def current_sizes(repository: Path, skills_dir: str = 'skills') -> dict[str, int]:
    return {f'{skills_dir}/{d.name}': (d / 'SKILL.md').stat().st_size
            for d in skill_dirs(repository, skills_dir) if (d / 'SKILL.md').is_file()}


def load_baseline(path: Path) -> dict[str, int]:
    baseline = json.loads(read_regular(path))
    if (not isinstance(baseline, dict) or set(baseline) != {'schema', 'skills'}
            or baseline['schema'] != BASELINE_SCHEMA or not isinstance(baseline['skills'], dict)
            or not all(isinstance(k, str) and type(v) is int and v > 0
                       for k, v in baseline['skills'].items())):
        raise ValueError(f'{path}: expected {BASELINE_SCHEMA} with positive integer sizes')
    return baseline['skills']


def ratchet_errors(repository: Path, skills_dir: str = 'skills') -> list[str] | None:
    """None when no baseline is recorded; otherwise every skill that grew or is unrecorded."""
    path = repository / BASELINE_RELATIVE
    if not path.exists() and not path.is_symlink():
        return None
    baseline = load_baseline(path)
    sizes = current_sizes(repository, skills_dir)
    errors = []
    for skill, size in sizes.items():
        if skill not in baseline:
            errors.append(f'{skill}: no recorded baseline; run ratchet --record to admit it')
        elif size > baseline[skill]:
            errors.append(f'{skill}/SKILL.md grew from {baseline[skill]} to {size} bytes; move '
                          f'detail to a reference, or run ratchet --record to admit the growth')
    for skill in sorted(set(baseline) - set(sizes)):
        errors.append(f'{skill}: baseline entry for a skill that no longer exists')
    return errors


def record_baseline(repository: Path, skills_dir: str = 'skills') -> dict[str, int]:
    sizes = current_sizes(repository, skills_dir)
    if not sizes:
        raise ValueError(f'no skills found under {repository / skills_dir}')
    path = repository / BASELINE_RELATIVE
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({'schema': BASELINE_SCHEMA, 'skills': dict(sorted(sizes.items()))},
                               indent=2) + '\n', encoding='utf-8')
    return sizes


# --- duplication --------------------------------------------------------------------------

def normalize_block(text: str) -> str:
    return squash(re.sub(r'[*_`]', '', text)).lower()


def prose_blocks(text: str) -> set[str]:
    """Normalized paragraphs and list items long enough to be a stated rule."""
    blocks, current = [], []

    def flush():
        if current:
            blocks.append(' '.join(current))
            current.clear()

    for line in split_code(text)[0]:
        stripped = line.strip()
        if not stripped or stripped.startswith(('#', '|', '>', '---')):
            flush()
            continue
        if LIST_ITEM.match(line):
            flush()
            stripped = LIST_ITEM.sub('', line, count=1).strip()
        current.append(stripped)
    flush()
    normalized = {normalize_block(block) for block in blocks}
    return {block for block in normalized if len(block) >= DUPLICATE_MIN_CHARS}


def duplication_errors(repository: Path, skills_dir: str = 'skills',
                       allowed: tuple[str, ...] = ()) -> list[str]:
    """`allowed` holds sentences another policy requires verbatim in several files."""
    permitted = {normalize_block(text) for text in allowed}
    errors = []
    for directory in skill_dirs(repository, skills_dir):
        skill_file = directory / 'SKILL.md'
        if not skill_file.is_file():
            continue
        owned = prose_blocks(read_regular(skill_file))
        for reference in markdown_files(directory):
            if reference == skill_file:
                continue
            for block in sorted((owned & prose_blocks(read_regular(reference))) - permitted):
                errors.append(f'{skill_file.relative_to(repository)} and '
                              f'{reference.relative_to(repository)} both state: '
                              f'"{block[:70]}..."; keep it in one place')
    return errors


# --- link integrity -----------------------------------------------------------------------

def slug(heading: str) -> str:
    """GitHub's heading anchor: lowercase, punctuation dropped, spaces to hyphens."""
    heading = re.sub(r'\[([^\]]*)\]\([^)]*\)', r'\1', heading)
    kept = ''.join(ch for ch in heading.lower() if ch.isalnum() or ch in ' -_')
    return kept.replace(' ', '-')


def anchors(text: str) -> set[str]:
    found, seen = set(EXPLICIT_ANCHOR.findall(text)), {}
    for line in split_code(text)[0]:
        match = HEADING.match(line)
        if not match:
            continue
        base = slug(match.group(1))
        count = seen.get(base, 0)
        seen[base] = count + 1
        found.add(base if count == 0 else f'{base}-{count}')
    return found


def link_errors(repository: Path, skills_dir: str = 'skills') -> list[str]:
    root = repository.resolve()
    errors, cache = [], {}

    def anchors_of(path: Path) -> set[str]:
        if path not in cache:
            cache[path] = anchors(read_regular(path))
        return cache[path]

    for directory in skill_dirs(repository, skills_dir):
        for source in markdown_files(directory):
            relative = source.relative_to(repository)
            prose = INLINE_CODE.sub('', '\n'.join(split_code(read_regular(source))[0]))
            for target in LINK.findall(prose):
                if SCHEME.match(target):
                    continue
                path_part, _, anchor = target.partition('#')
                resolved = (source.parent / path_part).resolve() if path_part else source.resolve()
                if resolved != root and root not in resolved.parents:
                    errors.append(f'{relative} links outside the repository: {target}')
                    continue
                if not resolved.exists():
                    errors.append(f'{relative} links to a missing file: {target}')
                    continue
                if anchor and resolved.suffix == '.md' and anchor not in anchors_of(resolved):
                    errors.append(f'{relative} links to a missing heading: {target}')
    return errors


# --- description shape --------------------------------------------------------------------

def description_error(skill_file: Path) -> str | None:
    lines = read_regular(skill_file).splitlines()
    if not lines or lines[0] != '---' or '---' not in lines[1:]:
        return 'missing closed frontmatter'
    values = [line[len('description:'):].strip()
              for line in lines[1:lines.index('---', 1)] if line.startswith('description:')]
    if len(values) != 1:
        return 'needs exactly one description'
    value = values[0]
    if not value or value[0] in '>|':
        return 'description must be a single line, not a block scalar'
    if len(value) < 2 or value[0] not in '"\'' or value[-1] != value[0]:
        return 'description must be quoted'
    inner = value[1:-1]
    if '<' in inner or '>' in inner:
        return 'description must not contain angle brackets'
    if not DESCRIPTION_MIN <= len(inner) <= DESCRIPTION_MAX:
        return (f'description is {len(inner)} characters; keep it between {DESCRIPTION_MIN} '
                f'and {DESCRIPTION_MAX}')
    if not TRIGGER.search(inner):
        return 'description must state its trigger with "Use when", "Use for" or "Use only"'
    if not inner.endswith('.'):
        return 'description must end with a period'
    return None


def description_errors(repository: Path, skills_dir: str = 'skills') -> list[str]:
    errors = []
    for directory in skill_dirs(repository, skills_dir):
        skill_file = directory / 'SKILL.md'
        if skill_file.is_file():
            error = description_error(skill_file)
            if error:
                errors.append(f'{skill_file.relative_to(repository)}: {error}')
    return errors


# --- token preservation -------------------------------------------------------------------

def protected_tokens(text: str) -> set[str]:
    """Commands, flags, paths, identifiers (code spans and code lines) and bounded numbers."""
    prose, code = split_code(text)
    joined = '\n'.join(prose)
    tokens = {squash(span) for span in INLINE_CODE.findall(joined)}
    tokens.update(squash(line) for line in code)
    tokens.update(squash(match.group()) for match in BOUNDED_NUMBER.finditer(
        INLINE_CODE.sub(' ', joined)))
    return {token for token in tokens if token}


def version_text(directory: Path) -> str:
    return '\n'.join(read_regular(path) for path in markdown_files(directory))


def lost_tokens_between(before: str, after: str) -> list[str]:
    haystack = squash(after)
    return sorted(token for token in protected_tokens(before) if token not in haystack)


def lost_tokens(before: Path, after: Path) -> list[str]:
    return lost_tokens_between(version_text(before), version_text(after))


def load_removals(path: Path | None) -> dict[str, str]:
    if path is None:
        return {}
    data = json.loads(read_regular(path))
    if (not isinstance(data, dict) or set(data) != {'schema', 'removed'}
            or data['schema'] != REMOVALS_SCHEMA or not isinstance(data['removed'], list)
            or not all(isinstance(e, dict) and set(e) == {'token', 'reason'}
                       and isinstance(e['token'], str) and e['token'].strip()
                       and isinstance(e['reason'], str) and e['reason'].strip()
                       for e in data['removed'])):
        raise ValueError(f'{path}: expected {REMOVALS_SCHEMA} with token and reason entries')
    return {squash(entry['token']): entry['reason'] for entry in data['removed']}


def _preservation(before: str, after: str, removals: Path | None) -> list[str]:
    declared = load_removals(removals)
    lost = lost_tokens_between(before, after)
    errors = [f'token lost in the rewrite: {token}' for token in lost if token not in declared]
    errors.extend(f'declared removal is unused (the token was not lost): {token}'
                  for token in sorted(set(declared) - set(lost)))
    return errors


def preservation_errors(before: Path, after: Path, removals: Path | None = None) -> list[str]:
    return _preservation(version_text(before), version_text(after), removals)


def preservation_errors_from_git(repository: Path, revision: str, skill: str,
                                 removals: Path | None = None) -> list[str]:
    """Compare a skill at a Git revision with the same skill in the working tree."""
    def git(*args):
        return subprocess.run(['git', '-C', str(repository), *args], check=True,
                              capture_output=True, text=True).stdout
    names = [name for name in git('ls-tree', '-r', '-z', '--name-only', revision, '--',
                                  skill).split('\0') if name.endswith('.md')]
    if not names:
        raise ValueError(f'{skill} has no Markdown files at {revision}')
    before = '\n'.join(git('show', f'{revision}:{name}') for name in sorted(names))
    return _preservation(before, version_text(repository / skill), removals)
