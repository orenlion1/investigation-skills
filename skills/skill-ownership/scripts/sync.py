#!/usr/bin/env python3
"""Keep a carried copy of this skill in step with an upstream release.

`report` is read-only: it says which release the repository carries, which is the latest,
what changed between them, and whether the carried copy drifted from its pinned release.
`apply` replaces the carried copy and updates the pin together, preserving the files the
pin declares as local adaptations. It writes only inside the carried directory and the pin
file, and never commits: the result is one working-tree change for the repository's own
review path.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

import versioning

CARRIED = versioning.CARRIED_SKILL
RELEASE_TAG = re.compile(rf'refs/tags/({versioning.SEMVER})(\^\{{\}})?')
EXIT_BEHIND = 3
EXIT_DRIFT = 4


def _git(*args: str, cwd: Path | None = None) -> str:
    environment = dict(os.environ, GIT_TERMINAL_PROMPT='0')
    result = subprocess.run(['git', *args], cwd=cwd, capture_output=True, text=True,
                            env=environment)
    if result.returncode:
        raise ValueError(f'git {args[0]} failed: {result.stderr.strip() or result.stdout.strip()}')
    return result.stdout


def version_key(version: str) -> tuple[int, ...]:
    return tuple(int(part) for part in version.split('.'))


def releases(source: str) -> dict[str, str]:
    """Release tags of the upstream, each mapped to the commit it names."""
    found: dict[str, str] = {}
    for line in _git('ls-remote', '--tags', source).splitlines():
        sha, _, ref = line.partition('\t')
        match = RELEASE_TAG.fullmatch(ref)
        if match and (match.group(2) or match.group(1) not in found):
            found[match.group(1)] = sha  # a peeled entry wins: it is the commit itself
    if not found:
        raise ValueError(f'no release tags found at {source}')
    return found


class Upstream:
    """A throwaway local mirror of the release tags, outside the target repository."""

    def __init__(self, source: str):
        self.source = source
        self.releases = releases(source)
        self.directory = Path(tempfile.mkdtemp(prefix='skill-ownership-sync-'))
        _git('init', '--quiet', '--bare', str(self.directory))

    def close(self) -> None:
        shutil.rmtree(self.directory, ignore_errors=True)

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()

    def fetch(self, version: str) -> None:
        if version not in self.releases:
            raise ValueError(f'no release {version} at {self.source}')
        _git('fetch', '--quiet', '--depth', '1', self.source,
             f'+refs/tags/{version}:refs/tags/{version}', cwd=self.directory)

    def files(self, version: str) -> dict[str, tuple[bytes, bool]]:
        """Carried files of a release: relative path to (content, executable)."""
        self.fetch(version)
        listing = _git('ls-tree', '-r', '-z', version, '--', CARRIED, cwd=self.directory)
        result = {}
        for entry in filter(None, listing.split('\0')):
            meta, _, path = entry.partition('\t')
            mode, kind, sha = meta.split()
            if kind != 'blob' or mode == '120000':
                raise ValueError(f'release {version} carries a non-regular file: {path}')
            content = subprocess.run(['git', 'cat-file', 'blob', sha], cwd=self.directory,
                                     capture_output=True, check=True).stdout
            result[path[len(CARRIED) + 1:]] = (content, mode == '100755')
        if 'SKILL.md' not in result:
            raise ValueError(f'release {version} has no {CARRIED}/SKILL.md')
        return result


def carried_files(repository: Path) -> dict[str, bytes]:
    directory = repository / CARRIED
    if directory.is_symlink():
        raise ValueError(f'{CARRIED} must not be a symlink')
    if not directory.is_dir():
        return {}
    files = {}
    for path in sorted(directory.rglob('*')):
        relative = path.relative_to(directory).as_posix()
        if '__pycache__' in path.parts or path.is_dir():
            continue
        if path.is_symlink():
            raise ValueError(f'{CARRIED}/{relative} must not be a symlink')
        files[relative] = path.read_bytes()
    return files


def drift(repository: Path, pinned: dict[str, tuple[bytes, bool]], adaptations: set[str]) -> list[str]:
    """Carried files that differ from the pinned release and are not declared adaptations."""
    local = carried_files(repository)
    names = set(local) | set(pinned)
    return sorted(name for name in names if name not in adaptations
                  and local.get(name) != (pinned[name][0] if name in pinned else None))


def _load(repository: Path) -> dict | None:
    path = repository / versioning.PIN_RELATIVE
    if not path.exists() and not path.is_symlink():
        return None
    return versioning.load_pin(path)


def report(repository: Path, source: str | None = None) -> dict:
    """Read-only: what the repository carries, what is latest, what changed, what drifted."""
    repository = Path(repository)
    pin = _load(repository)
    if pin is None:
        raise ValueError(f'pin is missing: {versioning.PIN_RELATIVE}; adopt with sync --apply '
                         f'--upstream <repository>')
    with Upstream(source or pin['upstream_repository']) as upstream:
        current = pin['version']
        if upstream.releases.get(current) != pin['commit']:
            raise ValueError(f'pin commit {pin["commit"]} does not match upstream release '
                             f'{current} ({upstream.releases.get(current, "no such release")})')
        latest = max(upstream.releases, key=version_key)
        pinned = upstream.files(current)
        adaptations = {entry['path'] for entry in pin['local_adaptations']}
        changed = []
        if latest != current:
            newer = upstream.files(latest)
            for name in sorted(set(pinned) | set(newer)):
                if name not in pinned:
                    changed.append(f'A {name}')
                elif name not in newer:
                    changed.append(f'D {name}')
                elif pinned[name] != newer[name]:
                    changed.append(f'M {name}')
            changed.sort()
        return {'schema': 'skill-ownership-sync/v1', 'upstream': upstream.source,
                'current': current, 'commit': pin['commit'], 'latest': latest,
                'status': 'current' if latest == current else 'behind',
                'changed': changed, 'drift': drift(repository, pinned, adaptations),
                'local_adaptations': sorted(adaptations)}


def exit_code(result: dict) -> int:
    if result['drift']:
        return EXIT_DRIFT
    return EXIT_BEHIND if result['status'] == 'behind' else 0


def render(result: dict) -> str:
    lines = [f'carried release: {result["current"]} ({result["commit"]})',
             f'latest release:  {result["latest"]}',
             f'status:          {result["status"]}']
    if result['changed']:
        lines.append(f'changed between {result["current"]} and {result["latest"]}:')
        lines.extend(f'  {change}' for change in result['changed'])
    if result['local_adaptations']:
        lines.append('declared local adaptations (preserved by sync):')
        lines.extend(f'  {name}' for name in result['local_adaptations'])
    if result['drift']:
        lines.append('undeclared drift from the pinned release (declare it in the pin or '
                     'restore the file):')
        lines.extend(f'  {name}' for name in result['drift'])
    elif result['status'] == 'current':
        lines.append('clean: the carried copy matches its pinned release')
    return '\n'.join(lines) + '\n'


def apply(repository: Path, source: str | None = None, to: str | None = None,
          repository_url: str | None = None) -> dict:
    """Replace the carried copy with a release and update the pin in the same change."""
    repository = Path(repository)
    pin = _load(repository)
    if pin is None and not source:
        raise ValueError('first adoption needs --upstream <repository>')
    with Upstream(source or pin['upstream_repository']) as upstream:
        target = to or max(upstream.releases, key=version_key)
        if target not in upstream.releases:
            raise ValueError(f'no release {target} at {upstream.source}')
        adaptations: set[str] = set()
        if pin is not None:
            if version_key(target) < version_key(pin['version']):
                raise ValueError(f'refusing a downgrade from {pin["version"]} to {target}')
            if upstream.releases.get(pin['version']) != pin['commit']:
                raise ValueError(f'pin commit {pin["commit"]} does not match upstream release '
                                 f'{pin["version"]}')
            adaptations = {entry['path'] for entry in pin['local_adaptations']}
            undeclared = drift(repository, upstream.files(pin['version']), adaptations)
            if undeclared:
                raise ValueError('refusing to overwrite undeclared local changes: '
                                 + ', '.join(undeclared))
            if target == pin['version']:
                return {'from': pin['version'], 'to': target, 'changed': [],
                        'preserved': sorted(adaptations)}
        elif carried_files(repository):
            raise ValueError(f'{CARRIED} exists without a pin; remove it or add a pin first')
        release = upstream.files(target)
        directory = repository / CARRIED
        before = carried_files(repository)
        for name in before:
            if name not in adaptations and name not in release:
                (directory / name).unlink()
        changed = sorted(name for name in set(before) | set(release)
                         if name not in adaptations
                         and before.get(name) != (release[name][0] if name in release else None))
        for name, (content, executable) in release.items():
            if name in adaptations and name in before:
                continue
            path = directory / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content)
            path.chmod(0o755 if executable else 0o644)
        for parent in sorted((p for p in directory.rglob('*') if p.is_dir()), reverse=True):
            if not any(parent.iterdir()):
                parent.rmdir()
        if 'SKILL.md' in adaptations:
            versioning.set_version(directory / 'SKILL.md', target)
        new_pin = {'schema': versioning.PIN_SCHEMA,
                   'upstream_repository': (pin['upstream_repository'] if pin
                                           else repository_url or source),
                   'commit': upstream.releases[target], 'version': target,
                   'local_adaptations': pin['local_adaptations'] if pin else []}
        pin_path = repository / versioning.PIN_RELATIVE
        pin_path.parent.mkdir(parents=True, exist_ok=True)
        pin_path.write_text(json.dumps(new_pin, indent=2) + '\n', encoding='utf-8')
        return {'from': pin['version'] if pin else None, 'to': target, 'changed': changed,
                'preserved': sorted(adaptations & set(before))}
