#!/usr/bin/env python3
"""Validate repository release metadata, or prepare an explicit forward version bump."""
import argparse
import json
from pathlib import Path
import re
import subprocess


ROOT = Path(__file__).resolve().parents[1]
SEMVER = re.compile(r"(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)")


def version_tuple(value):
    if not isinstance(value, str) or not SEMVER.fullmatch(value):
        raise ValueError(f"Expected stable unprefixed SemVer, got {value!r}")
    return tuple(map(int, value.split('.')))


def validate(root, tag=None):
    raw = (root / 'VERSION').read_text()
    current = raw.strip()
    version_tuple(current)
    if raw != current + '\n':
        raise ValueError('VERSION must contain one version and a trailing newline')
    package = json.loads((root / 'package.json').read_text())
    if package.get('version') != current:
        raise ValueError('package.json version differs from VERSION')
    if package.get('license') != 'MIT' or package.get('private') is not True:
        raise ValueError('Package must declare MIT and remain private')
    license_text = (root / 'LICENSE').read_text()
    if not license_text.startswith('MIT License\n\nCopyright (c) 2026 Oren Lion\n'):
        raise ValueError('Missing MIT license attribution')
    if tag is not None and tag != current:
        raise ValueError(f'Tag {tag!r} differs from VERSION {current}')
    return current, package


def check_tracked_outputs(root):
    paths = subprocess.check_output(
        ['git', 'ls-files', '-z'], cwd=root).decode().split('\0')
    forbidden = [p for p in paths if p.startswith(
        ('docs/tasks/', 'docs/reports/', 'logs/', 'outputs/', 'inputs/', '.codegraph/'))
        or '__pycache__' in p.split('/') or p.endswith(('.pyc', '.pyo'))]
    if forbidden:
        raise ValueError('Local outputs must stay untracked: ' + ', '.join(forbidden))


def bump(root, target, check=False):
    current, package = validate(root)
    if version_tuple(target) <= version_tuple(current):
        raise ValueError('New version must be greater than VERSION')
    # Validate every input before changing either release-owned file.
    package['version'] = target
    if not check:
        (root / 'VERSION').write_text(target + '\n')
        (root / 'package.json').write_text(json.dumps(package, indent=2) + '\n')
    return f'{current} -> {target}'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--tag')
    parser.add_argument('--version')
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    if args.tag and args.version:
        parser.error('--tag and --version cannot be combined')
    if args.check and not args.version:
        parser.error('--check requires --version')
    try:
        check_tracked_outputs(ROOT)
        if args.version:
            print(bump(ROOT, args.version, args.check))
        else:
            print('Validated release ' + validate(ROOT, args.tag)[0])
    except (ValueError, OSError, subprocess.CalledProcessError) as error:
        parser.exit(1, str(error) + '\n')


if __name__ == '__main__':
    main()
