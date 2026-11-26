#!/usr/bin/env python3
"""Copy a private eval catalog, optionally selecting case IDs for one skill."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys


def select(cases_dir, output_dir, skill='all', case_ids=''):
    if cases_dir.is_symlink() or not cases_dir.is_dir() or output_dir.exists() or output_dir.is_symlink():
        raise ValueError('invalid directory')
    catalog = {}
    for path in sorted(cases_dir.glob('*.json')):
        if path.is_symlink() or not path.is_file() or path.stat().st_size > 1_048_576:
            raise ValueError('invalid case file')
        raw = path.read_bytes()
        data = json.loads(raw)
        ids = [entry['id'] for entry in data['evals']]
        if (not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*', path.stem) or not ids
                or any(type(value) is not int or value < 1 for value in ids)
                or len(ids) != len(set(ids))):
            raise ValueError('invalid catalog')
        catalog[path.stem] = (raw, data, ids)
    if not catalog or (skill != 'all' and skill not in catalog):
        raise ValueError('unknown skill')
    selected = list(catalog) if skill == 'all' else [skill]
    requested = None
    if case_ids.strip():
        parts = [part.strip() for part in case_ids.split(',')]
        if skill == 'all' or any(not re.fullmatch(r'[1-9][0-9]*', part) for part in parts):
            raise ValueError('invalid selection')
        requested = [int(part) for part in parts]
        if len(requested) != len(set(requested)) or not set(requested) <= set(catalog[skill][2]):
            raise ValueError('invalid selection')
    payloads = {name: entry[0] for name, entry in catalog.items()}
    selected_ids = {name: catalog[name][2] for name in selected}
    if requested is not None:
        data = dict(catalog[skill][1])
        data['evals'] = [entry for entry in data['evals'] if entry['id'] in requested]
        selected_ids[skill] = [entry['id'] for entry in data['evals']]
        payloads[skill] = (json.dumps(data, indent=2) + '\n').encode()
    output_dir.mkdir(mode=0o700)
    for name, raw in payloads.items():
        path = output_dir / (name + '.json')
        path.write_bytes(raw)
        path.chmod(0o600)
    return {'skills': selected, 'evals': {name: len(selected_ids[name]) for name in selected},
            'selected_ids': selected_ids,
            'source_sha256': {name: hashlib.sha256(catalog[name][0]).hexdigest() for name in selected},
            'selected_sha256': {name: hashlib.sha256(payloads[name]).hexdigest() for name in selected}}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cases-dir', type=Path, required=True)
    parser.add_argument('--output-dir', type=Path, required=True)
    parser.add_argument('--skill', default='all')
    parser.add_argument('--case-ids', default='')
    args = parser.parse_args(argv)
    try:
        result = select(args.cases_dir, args.output_dir, args.skill, args.case_ids)
    except (ValueError, OSError, TypeError, KeyError):
        print('Invalid live eval selection; require known skill, unique positive case IDs and fresh private output.',
              file=sys.stderr)
        return 2
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == '__main__':
    sys.exit(main())
