#!/usr/bin/env python3
"""Check imported skill contract versions against offline, immutable upstream pins.

The catalog marks imported skills with metadata.version. Pins identify upstream contracts,
not content equality: local adaptations remain permitted. This checker deliberately accepts
only the catalog's block metadata form, failing closed on ambiguous YAML rather than guessing.
"""
import argparse
import json
from pathlib import Path
import re
import sys
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
VERSION = re.compile(r'[0-9]+\.[0-9]+\.[0-9]+')


def read_regular(path):
    if path.is_symlink() or not path.is_file() or path.stat().st_size > 1024 * 1024:
        raise ValueError(f'{path}: expected a readable regular file under 1 MiB')
    return path.read_text(encoding='utf-8')


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f'duplicate pin key: {key}')
        result[key] = value
    return result


def load_pins(path):
    pins = json.loads(read_regular(path), object_pairs_hook=unique_object)
    if (not isinstance(pins, dict) or set(pins) != {'schema', 'skills'}
            or pins['schema'] != 'vendored-imports/v1'
            or not isinstance(pins['skills'], dict) or not pins['skills']):
        raise ValueError('pin requires vendored-imports/v1 and a nonempty skills object')
    for skill, pin in pins['skills'].items():
        if not re.fullmatch(r'skills/[a-z0-9]+(?:-[a-z0-9]+)*', skill):
            raise ValueError(f'invalid pin skill path: {skill}')
        if not isinstance(pin, dict) or set(pin) != {'upstream_repository', 'commit', 'version'}:
            raise ValueError(f'{skill}: pin needs upstream_repository, commit and version')
        repository = pin['upstream_repository']
        if not isinstance(repository, str):
            raise ValueError(f'{skill}: invalid pin upstream_repository')
        parsed = urlsplit(repository)
        if (parsed.scheme != 'https' or not parsed.hostname or parsed.username is not None
                or parsed.password is not None or parsed.query or parsed.fragment
                or not parsed.path.strip('/') or re.search(r'\s', repository)):
            raise ValueError(f'{skill}: invalid pin upstream_repository')
        for field, pattern in [('commit', r'[0-9a-f]{40}'),
                               ('version', VERSION.pattern)]:
            if not isinstance(pin[field], str) or not re.fullmatch(pattern, pin[field]):
                raise ValueError(f'{skill}: invalid pin {field}: {pin[field]!r}')
    return pins['skills']


def declared_version(path):
    lines = read_regular(path).splitlines()
    if not lines or lines[0] != '---' or '---' not in lines[1:]:
        raise ValueError(f'{path}: missing closed frontmatter')
    frontmatter = lines[1:lines.index('---', 1)]
    metadata = [i for i, line in enumerate(frontmatter) if re.match(r'^metadata\s*:', line)]
    if not metadata:
        return None
    if len(metadata) != 1 or frontmatter[metadata[0]] != 'metadata:':
        raise ValueError(f'{path}: metadata must be a unique block mapping')
    values = []
    for line in frontmatter[metadata[0] + 1:]:
        if line.strip() and not line.startswith((' ', '\t', '#')):
            break
        if not line.strip() or line.lstrip().startswith('#'):
            continue
        match = re.fullmatch(r'  version: (?:"([^"\n]+)"|\x27([^\x27\n]+)\x27|([^\s\x27"]+))', line)
        if not match:
            raise ValueError(f'{path}: unsupported metadata field or version form')
        values.append(next(value for value in match.groups() if value is not None))
    if len(values) != 1 or not VERSION.fullmatch(values[0]):
        raise ValueError(f'{path}: metadata needs exactly one valid version')
    return values[0]


def check(root):
    pins = load_pins(root / 'policy/vendored-imports.json')
    skills = root / 'skills'
    if skills.is_symlink() or not skills.is_dir():
        raise ValueError('skills must be a regular directory')
    discovered = {}
    for directory in sorted(skills.iterdir()):
        if directory.is_symlink() or not directory.is_dir():
            raise ValueError(f'{directory}: expected a regular skill directory')
        version = declared_version(directory / 'SKILL.md')
        if version is not None:
            discovered['skills/' + directory.name] = version
    errors = []
    for skill, version in discovered.items():
        if skill not in pins:
            errors.append(f'{skill}: metadata.version {version!r} has no upstream pin')
        elif version != pins[skill]['version']:
            errors.append(f'{skill}: metadata.version {version!r} disagrees with pinned version '
                          f'{pins[skill]["version"]!r}')
    for skill in pins.keys() - discovered.keys():
        errors.append(f'{skill}: pinned skill is missing metadata.version')
    if errors:
        raise ValueError('; '.join(sorted(errors)))
    return len(discovered)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repository', type=Path, default=ROOT)
    args = parser.parse_args()
    try:
        count = check(args.repository)
    except (OSError, ValueError, UnicodeError) as error:
        print(f'error: vendored import pin check: {error}', file=sys.stderr)
        return 1
    print(f'vendored imports: {count} imported skill(s) checked — PASSED')
    return 0


if __name__ == '__main__':
    sys.exit(main())
