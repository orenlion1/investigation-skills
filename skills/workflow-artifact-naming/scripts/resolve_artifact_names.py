#!/usr/bin/env python3
"""Read-only workflow identity and repository location resolution (Python 3.8+)."""
import argparse
import json
import os
from pathlib import Path
import re
import stat
import sys

SCHEMA = 'workflow-artifact-naming/v1'
CONFIG_NAME = 'workflow-artifact-naming.json'
DEFAULT_LOCATIONS = {'TASK': 'docs/tasks', 'SPEC': 'docs/specs', 'PLAN': 'docs/plans',
                     'REPORT': 'docs/reports', 'LOG': 'logs'}
SLUG = re.compile(r'[a-z0-9]+(?:-[a-z0-9]+)*\Z')
TYPE = re.compile(r'[A-Z][A-Z0-9]*(?:-[A-Z0-9]+)*\Z')
EXTENSION = re.compile(r'[A-Za-z0-9]+(?:\.[A-Za-z0-9]+)*\Z')
TICKET = re.compile(r'[A-Za-z0-9]+(?:-[A-Za-z0-9]+)*\Z')


class NamingError(ValueError):
    """Invalid identity, configuration or destination; never repaired implicitly."""


def normalize_slug(title):
    """Lowercase, then retain ASCII slug characters; never transliterate."""
    # Legacy tr uses simple lowercase for U+0130; Python expands it to i + dot.
    title = title.replace('\u0130', 'i').lower()
    slug = re.sub(r'[^a-z0-9]+', '-', title).strip('-')
    if not slug:
        raise NamingError('title normalizes to an empty value')
    return slug


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise NamingError('duplicate configuration key: ' + key)
        result[key] = value
    return result


def directory_value(value):
    if isinstance(value, str):
        try:
            value.encode('utf-8')
        except UnicodeError as error:
            raise NamingError('directory must have valid Unicode encoding') from error
    if (not isinstance(value, str) or not value or value != value.strip()
            or any(ord(char) < 32 for char in value)
            or any(char in value for char in '\\$~*?[]') or '://' in value):
        raise NamingError('location must be a non-empty literal directory without shell expressions')
    if Path(value).is_absolute() and Path(value) == Path('/'):
        raise NamingError('filesystem root is not an artifact output directory')
    return value


def selected_directory(root, value):
    selected = Path(os.path.abspath(root / directory_value(value)))
    if selected == Path(selected.anchor):
        raise NamingError('filesystem root is not an artifact output directory')
    return selected


def repository_root(value):
    root = Path(value).resolve()
    if not root.is_dir():
        raise NamingError('repository root must be an existing directory')
    return root


def load_configuration(root):
    path = root / CONFIG_NAME
    if not os.path.lexists(path):
        return {}
    try:
        if path.is_symlink() or not stat.S_ISREG(path.stat().st_mode):
            raise NamingError('configuration must be a regular repository-owned file')
        if path.stat().st_size > 65536:
            raise NamingError('configuration exceeds 64 KiB')
        config = json.loads(path.read_text(encoding='utf-8'), object_pairs_hook=unique_object)
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise NamingError('cannot read valid ' + CONFIG_NAME) from error
    if (not isinstance(config, dict) or set(config) != {'schema', 'locations'}
            or config['schema'] != SCHEMA or not isinstance(config['locations'], dict)):
        raise NamingError('configuration requires schema ' + SCHEMA + ' and locations object')
    locations = config['locations']
    if set(locations) - set(DEFAULT_LOCATIONS):
        raise NamingError('unknown configured artifact type')
    for value in locations.values():
        selected_directory(root, value)
    return locations


def contained(path, boundary):
    try:
        path.relative_to(boundary)
        return True
    except ValueError:
        return False


def inspect_path(path, boundary):
    """Check existing components without creating output or deciding ownership."""
    try:
        if not contained(path.resolve(), boundary):
            raise NamingError('symlink escapes approved output root: ' + str(path))
        # Compare only siblings of each selected component; no recursive scan.
        for component in reversed((path, *path.parents)):
            parent = component.parent
            if component != path and os.path.lexists(component) and not component.is_dir():
                raise NamingError('destination ancestor is not a directory: ' + str(component))
            if component == parent or not parent.is_dir():
                continue
            matches = [item.name for item in parent.iterdir()
                       if item.name.casefold() == component.name.casefold()]
            if any(name != component.name for name in matches):
                raise NamingError('case-folded destination collision: ' + str(component))
    except (OSError, RuntimeError) as error:
        raise NamingError('cannot safely inspect destination: ' + str(path)) from error


def resolve_location(root, artifact_type, destination=None, configuration=None):
    root = repository_root(root)
    config = load_configuration(root) if configuration is None else configuration
    if destination is not None:
        directory, source = directory_value(destination), 'explicit'
    elif artifact_type in config:
        directory, source = config[artifact_type], 'configuration'
    elif artifact_type in DEFAULT_LOCATIONS:
        directory, source = DEFAULT_LOCATIONS[artifact_type], 'default'
    else:
        raise NamingError('supporting artifact type requires an explicit destination')
    selected = selected_directory(root, directory)
    boundary = root if source == 'default' else selected
    inspect_path(selected, boundary)
    if selected.exists() and not selected.is_dir():
        raise NamingError('output location is not a directory: ' + str(selected))
    return selected, boundary, source


def resolve_artifact(root, artifact_type, title=None, slug=None, destination=None,
                     suffix=None, extension='md', ticket=None, draft=False, asset=False):
    root = repository_root(root)
    if (title is None) == (slug is None):
        raise NamingError('supply exactly one title or verified slug')
    slug = normalize_slug(title) if title is not None else slug
    if not SLUG.fullmatch(slug):
        raise NamingError('slug must already be normalized lowercase ASCII kebab-case')
    if not TYPE.fullmatch(artifact_type):
        raise NamingError('artifact type must be uppercase and filesystem-safe')
    if suffix is not None and not SLUG.fullmatch(suffix):
        raise NamingError('suffix must be a normalized descriptive slug')
    if not EXTENSION.fullmatch(extension):
        raise NamingError('extension must be an actual safe extension without a leading dot')
    if ticket is not None and (artifact_type != 'LOG' or not TICKET.fullmatch(ticket) or asset):
        raise NamingError('ticket is valid only for a Markdown child LOG')
    if artifact_type == 'LOG' and not asset and extension != 'md':
        raise NamingError('new parent and child LOG files require Markdown .md')
    if draft and (artifact_type != 'TASK' or extension != 'md' or asset or suffix):
        raise NamingError('draft is valid only for a temporary TASK.md')
    config = load_configuration(root)
    selected, boundary, source = resolve_location(root, 'LOG' if asset else artifact_type,
                                                  destination, config)
    stem = artifact_type + '-' + slug
    if ticket is not None:
        stem += '-' + ticket
    if suffix:
        stem += '-' + suffix
    filename = ('TASK' if draft else stem) + '.' + extension
    directory = selected / 'assets' / slug if asset else selected
    output = directory / filename
    inspect_path(output, boundary)
    if output.exists() and not output.is_file():
        raise NamingError('artifact destination is not a regular file')
    return {'slug': slug, 'type': artifact_type, 'filename': filename,
            'path': Path(os.path.relpath(output, root)).as_posix(),
            'absolute_path': str(output), 'output_root': str(boundary),
            'location_source': source}


def document_link(document, target):
    """Return a document-relative local link even for configured sibling roots."""
    from urllib.parse import quote
    return quote(Path(os.path.relpath(target, Path(document).parent)).as_posix(), safe='/.-')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--normalize-title', help='print legacy-compatible slug only; no repository required')
    identity = parser.add_mutually_exclusive_group()
    identity.add_argument('--title')
    identity.add_argument('--slug')
    parser.add_argument('--repository-root')
    parser.add_argument('--locations', action='store_true', help='resolve all effective directories without a work identity')
    parser.add_argument('--type', dest='artifact_type')
    parser.add_argument('--destination', help='explicit approved output directory, relative to repository or absolute')
    parser.add_argument('--suffix')
    parser.add_argument('--extension', default='md')
    parser.add_argument('--ticket')
    parser.add_argument('--draft', action='store_true')
    parser.add_argument('--asset', action='store_true')
    args = parser.parse_args()
    try:
        if args.locations:
            if not args.repository_root or any((args.normalize_title is not None, args.title is not None, args.slug is not None, args.artifact_type is not None, args.destination is not None, args.suffix is not None, args.ticket is not None, args.draft, args.asset, args.extension != 'md')):
                raise NamingError('--locations requires only --repository-root')
            root = repository_root(args.repository_root)
            configuration = load_configuration(root)
            locations = {}
            for kind in DEFAULT_LOCATIONS:
                selected, boundary, source = resolve_location(root, kind, configuration=configuration)
                locations[kind] = {'path': Path(os.path.relpath(selected, root)).as_posix(), 'absolute_path': str(selected), 'output_root': str(boundary), 'location_source': source}
            print(json.dumps(locations, sort_keys=True))
        elif args.normalize_title is not None:
            if any((args.title is not None, args.slug is not None, args.repository_root is not None,
                    args.artifact_type is not None, args.destination is not None,
                    args.suffix is not None, args.ticket is not None,
                    args.draft, args.asset, args.extension != 'md')):
                raise NamingError('--normalize-title cannot be combined with artifact inputs')
            print(normalize_slug(args.normalize_title))
        else:
            if not args.repository_root or not args.artifact_type:
                raise NamingError('--repository-root and --type are required')
            print(json.dumps(resolve_artifact(args.repository_root, args.artifact_type,
                title=args.title, slug=args.slug, destination=args.destination,
                suffix=args.suffix, extension=args.extension, ticket=args.ticket,
                draft=args.draft, asset=args.asset), sort_keys=True))
    except (NamingError, OSError, RuntimeError) as error:
        print('resolve_artifact_names.py: ' + str(error), file=sys.stderr)
        return 2
    return 0


if __name__ == '__main__':
    sys.exit(main())
