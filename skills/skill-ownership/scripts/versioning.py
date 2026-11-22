#!/usr/bin/env python3
"""Version metadata: frontmatter shape, VERSION agreement, and the downstream pin.

A carried copy says which release it is in one place only: a single quoted
`metadata.version` in its SKILL.md frontmatter. Where it came from lives in the
downstream pin file, never in frontmatter. Every reader here fails closed.
"""
from __future__ import annotations

import json
import re
from pathlib import Path, PurePosixPath
from urllib.parse import urlsplit

SEMVER = r'(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)'
VERSION_LINE = re.compile(rf'  version: "({SEMVER})"')
CARRIED_SKILL = 'skills/skill-ownership'
PIN_RELATIVE = 'policy/skill-ownership-pin.json'
PIN_SCHEMA = 'skill-ownership-pin/v1'
PIN_KEYS = {'schema', 'upstream_repository', 'commit', 'version', 'local_adaptations'}


def read_regular(path: Path) -> str:
    if path.is_symlink() or not path.is_file() or path.stat().st_size > 1024 * 1024:
        raise ValueError(f'{path}: expected a readable regular file under 1 MiB')
    return path.read_text(encoding='utf-8')


def _metadata_lines(path: Path) -> tuple[list[str], int, list[int]]:
    """Return all lines, the index of `metadata:`, and the indexes of its block lines."""
    lines = read_regular(path).splitlines(keepends=True)
    bare = [line.rstrip('\n') for line in lines]
    if not bare or bare[0] != '---' or '---' not in bare[1:]:
        raise ValueError(f'{path}: missing closed frontmatter')
    closing = bare.index('---', 1)
    heads = [i for i in range(1, closing) if re.match(r'metadata\s*:', bare[i])]
    if not heads:
        raise ValueError(f'{path}: metadata is missing')
    if len(heads) != 1 or bare[heads[0]] != 'metadata:':
        raise ValueError(f'{path}: metadata must be a unique block mapping')
    block = []
    for i in range(heads[0] + 1, closing):
        if bare[i].strip() and not bare[i].startswith((' ', '\t')):
            break
        if bare[i].strip():
            block.append(i)
    return lines, heads[0], block


def declared_version(path: Path) -> str:
    """The version a skill declares, or ValueError naming the shape rule it breaks."""
    lines, _, block = _metadata_lines(path)
    versions = [i for i in block if re.match(r'\s*version\s*:', lines[i])]
    others = [i for i in block if i not in versions]
    if others:
        raise ValueError(f'{path}: metadata holds a key other than version')
    if len(versions) != 1:
        raise ValueError(f'{path}: metadata needs exactly one version')
    match = VERSION_LINE.fullmatch(lines[versions[0]].rstrip('\n'))
    if not match:
        raise ValueError(f'{path}: metadata.version must be a quoted SemVer string, '
                         f'for example version: "0.1.0"')
    return match.group(1)


def frontmatter_errors(path: Path) -> list[str]:
    try:
        declared_version(path)
    except (OSError, ValueError, UnicodeError) as error:
        return [str(error)]
    return []


def set_version(path: Path, version: str) -> None:
    """Rewrite the version value and nothing else; refuse anything not already well formed."""
    if not re.fullmatch(SEMVER, version):
        raise ValueError(f'expected stable unprefixed SemVer, got {version!r}')
    declared_version(path)
    lines, _, block = _metadata_lines(path)
    index = block[0]
    lines[index] = f'  version: "{version}"' + ('\n' if lines[index].endswith('\n') else '')
    path.write_text(''.join(lines), encoding='utf-8')


def skill_files(repository: Path, skills_dir: str = 'skills') -> list[Path]:
    catalog = repository / skills_dir
    if catalog.is_symlink() or not catalog.is_dir():
        return []
    return sorted(p / 'SKILL.md' for p in catalog.iterdir()
                  if p.is_dir() and not p.name.startswith('.'))


def agreement_errors(repository: Path, tag: str | None = None) -> tuple[list[str], int]:
    """Upstream rule: VERSION, every skill's metadata.version, and the tag are one value."""
    try:
        raw = read_regular(repository / 'VERSION')
    except (OSError, ValueError) as error:
        return [str(error)], 0
    version = raw.strip()
    if not re.fullmatch(SEMVER, version) or raw != version + '\n':
        return ['VERSION must contain one stable SemVer value and a trailing newline'], 0
    errors = []
    skills = skill_files(repository)
    if not skills:
        return [f'no skills found under {repository / "skills"}'], 0
    for skill in skills:
        name = f'skills/{skill.parent.name}'
        try:
            declared = declared_version(skill)
        except (OSError, ValueError, UnicodeError) as error:
            errors.append(str(error))
            continue
        if declared != version:
            errors.append(f'{name}: metadata.version {declared!r} differs from VERSION '
                          f'{version!r}')
    if tag is not None and tag != version:
        errors.append(f'tag {tag!r} differs from VERSION {version!r}')
    return errors, len(skills)


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f'duplicate pin key: {key}')
        result[key] = value
    return result


def load_pin(path: Path) -> dict:
    """Parse and validate the pin; ValueError names the offending field."""
    pin = json.loads(read_regular(path), object_pairs_hook=_unique_object)
    if not isinstance(pin, dict) or set(pin) != PIN_KEYS:
        raise ValueError('pin must hold exactly: ' + ', '.join(sorted(PIN_KEYS)))
    if pin['schema'] != PIN_SCHEMA:
        raise ValueError(f'unsupported pin schema: {pin["schema"]!r}')
    repository = pin['upstream_repository']
    parsed = urlsplit(repository) if isinstance(repository, str) else None
    if (parsed is None or parsed.scheme != 'https' or not parsed.hostname
            or parsed.username is not None or parsed.password is not None or parsed.query
            or parsed.fragment or not parsed.path.strip('/') or re.search(r'\s', repository)):
        raise ValueError('invalid pin upstream_repository: expected a plain https URL')
    if not isinstance(pin['commit'], str) or not re.fullmatch(r'[0-9a-f]{40}', pin['commit']):
        raise ValueError('invalid pin commit: expected a full 40-character lowercase SHA')
    if not isinstance(pin['version'], str) or not re.fullmatch(SEMVER, pin['version']):
        raise ValueError(f'invalid pin version: {pin["version"]!r}')
    adaptations = pin['local_adaptations']
    if not isinstance(adaptations, list):
        raise ValueError('pin local_adaptations must be a list')
    for entry in adaptations:
        if (not isinstance(entry, dict) or set(entry) != {'path', 'reason'}
                or not isinstance(entry['path'], str) or not isinstance(entry['reason'], str)
                or not entry['reason'].strip() or not safe_relative(entry['path'])):
            raise ValueError('pin local_adaptations entries need a relative path inside the '
                             'carried skill and a nonempty reason')
    return pin


def safe_relative(path: str) -> bool:
    """True for a normalized relative POSIX path that cannot leave its base directory."""
    pure = PurePosixPath(path)
    return (bool(path) and not pure.is_absolute() and '\\' not in path
            and all(part not in ('', '.', '..') for part in pure.parts)
            and str(pure) == path)


def pin_errors(repository: Path) -> list[str]:
    """Downstream rule: the pin exists, is well formed, and matches the carried copy."""
    path = repository / PIN_RELATIVE
    if not path.exists() and not path.is_symlink():
        return [f'pin is missing: {PIN_RELATIVE}']
    try:
        pin = load_pin(path)
        carried = declared_version(repository / CARRIED_SKILL / 'SKILL.md')
    except (OSError, ValueError, UnicodeError) as error:
        return [str(error)]
    if pin['version'] != carried:
        return [f'pin version {pin["version"]!r} does not match the carried copy\'s '
                f'metadata.version {carried!r}']
    return []
