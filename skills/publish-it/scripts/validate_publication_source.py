#!/usr/bin/env python3
"""Validate references before attachment uploads; never authorize page publication."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
from urllib.parse import unquote, urlsplit


def validate(artifact, manifest, roots, checker):
    """Retain every occurrence; locally resolved evidence is attachment-only proof."""
    artifact = Path(artifact).resolve(strict=True)
    roots = [Path(root).resolve(strict=True) for root in roots]
    if not roots or not all(root.is_dir() for root in roots):
        raise ValueError('explicit existing asset roots are required')
    receipt = checker.build_receipt([artifact], manifest)
    files = {}
    for row in receipt['rows']:
        if row['status'] != 'local-only':
            continue
        expected, actual = row['expected'], row['actual']
        if not expected or actual != expected:
            continue
        target = urlsplit(actual)
        if target.scheme or target.netloc or target.query or target.fragment or not target.path:
            continue
        unresolved = artifact.parent / unquote(target.path)
        if unresolved.is_symlink():
            continue
        try:
            path = unresolved.resolve(strict=True)
            if not path.is_file() or not any(path.is_relative_to(root) for root in roots):
                continue
            before = path.read_bytes()
            digest = hashlib.sha256(before).hexdigest()
            if path.read_bytes() != before:
                raise ValueError('local evidence changed during validation')
        except OSError:
            continue
        files[row['reference']] = {'path': str(path), 'sha256': digest, 'bytes': len(before)}
        row['original_status'] = row['status']
        row['status'] = 'verified-local-file'
    receipt.update(schema='publication-attachment-preflight/v1',
                   permission='attachment-uploads-only', page_publication_allowed=False,
                   local_files=files,
                   unresolved=sum(row['status'] not in ('linked', 'verified-local-file')
                                  for row in receipt['rows']))
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--artifact', type=Path, required=True)
    parser.add_argument('--asset-root', type=Path, action='append', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    try:
        checker_path = Path(__file__).resolve().parents[2] / 'report-authoring/scripts/check_reference_links.py'
        spec = importlib.util.spec_from_file_location('publication_reference_checker', checker_path)
        checker = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(checker)
        receipt = validate(args.artifact, json.loads(args.manifest.read_text()), args.asset_root, checker)
        with args.output.open('x') as handle:
            json.dump(receipt, handle, indent=2)
            handle.write('\n')
        print(json.dumps({'permission': receipt['permission'], 'occurrences': receipt['occurrences'],
                          'verified_local_files': len(receipt['local_files']),
                          'unresolved': receipt['unresolved'], 'page_publication_allowed': False}))
        return int(bool(receipt['unresolved']))
    except (OSError, ValueError, ImportError, KeyError) as error:
        print('Attachment preflight unavailable (' + type(error).__name__ + ')', file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
