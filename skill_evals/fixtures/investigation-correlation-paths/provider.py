#!/usr/bin/env python3
"""Deterministic, local-only provider stand-in; retains auditable read receipts."""
import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
catalog = json.loads((ROOT / 'catalog.json').read_text())
p = argparse.ArgumentParser()
p.add_argument('operation', choices=('catalog', 'read'))
p.add_argument('key', nargs='?', choices=tuple(catalog))
p.add_argument('--context')
p.add_argument('--profile')
p.add_argument('--region')
a = p.parse_args()
if a.operation == 'catalog':
    print(json.dumps(catalog))
else:
    if not a.key:
        p.error('read requires a key')
    if a.key.startswith('aws') and (a.profile != 'fixture-eu' or a.region != 'eu-central-1'):
        p.error('fixture AWS profile and explicit Region are required')
    if 'profile' in a.key and a.context != 'fixture-eu':
        p.error('fixture Grafana context is required')
    result = json.loads((ROOT / 'data' / (a.key + '.json')).read_text())
    receipt = {'provider': 'local synthetic integration stand-in', 'arguments': vars(a), 'result': result}
    (ROOT / 'receipts').mkdir(exist_ok=True)
    (ROOT / 'receipts' / (a.key + '.json')).write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps(receipt))
