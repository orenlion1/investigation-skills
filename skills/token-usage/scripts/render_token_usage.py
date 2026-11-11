#!/usr/bin/env python3
"""Render compact report metadata/details from saved collector accounting JSON."""
import argparse
from datetime import date
import html
import json
from pathlib import Path
import re
import sys

from collect_token_usage import EvidenceError, identity, require, summary, timestamp, unique_object, usage


def validate(accounting):
    require(accounting.get('schema') == 'investigation-token-usage/v1', 'validated_accounting_required')
    require(re.fullmatch(r'docs/tasks/TASK-[a-z0-9-]+\.md', accounting['task_artifact']),
            'invalid_task_artifact')
    window = accounting['window']
    start, end = timestamp(window['from']), timestamp(window['to'])
    require(start <= end and window['elapsed_seconds'] == (end - start).total_seconds(),
            'accounting_duration_mismatch')
    rows, sessions = accounting['responses'], accounting['sessions']
    require(isinstance(rows, list) and isinstance(sessions, list) and 0 < len(sessions) <= 100,
            'invalid_accounting_rows')
    threads = [identity(session['thread_id']) for session in sessions]
    require(len(threads) == len(set(threads)), 'duplicate_accounting_session')
    seen = set()
    for row in rows:
        key = identity(row['thread_id']), identity(row['response_id'])
        require(key not in seen, 'duplicate_accounting_response')
        seen.add(key)
        require(key[0] in threads and start <= timestamp(row['observed_at']) <= end,
                'accounting_response_outside_scope')
        require(row['usage'] == usage(row['usage']), 'invalid_accounting_usage')
        require(row['model'] is None or isinstance(row['model'], str)
                and re.fullmatch(r'[A-Za-z0-9._:/-]{1,160}', row['model']), 'invalid_accounting_model')
    require(accounting['usage'] == summary(rows), 'accounting_total_mismatch')
    for session in sessions:
        expected = summary([row for row in rows if row['thread_id'] == session['thread_id']])
        require(all(session[key] == value for key, value in expected.items()), 'accounting_session_mismatch')
    require(accounting['coverage']['status'] in ('partial', 'observed'), 'invalid_accounting_coverage')
    return rows, threads


def label(value):
    require(isinstance(value, str) and value.strip() and '\n' not in value and '\r' not in value,
            'invalid_report_label')
    return html.escape(value).replace('\\', '\\\\').replace('|', '&#124;')


def number(value):
    return 'unavailable' if value is None else str(value)


def render(accounting, subject=None, scope=None, completed=None):
    rows, threads = validate(accounting)
    tokens, window = accounting['usage']['tokens'], accounting['window']
    total = number(tokens['total_tokens'])
    duration = str(window['elapsed_seconds']) + ' seconds'
    lines = ['## Token usage details', '', 'Total recorded tokens: ' + total,
             'Input tokens: ' + number(tokens['input_tokens']),
             'Output tokens: ' + number(tokens['output_tokens'])]
    for field, title in (('cached_input_tokens', 'Cached input (input subset)'),
                         ('reasoning_output_tokens', 'Reasoning output (output subset)')):
        if tokens[field] is not None:
            lines.append(title + ': ' + number(tokens[field]))
    lines.extend(['', 'Report processing duration: ' + duration,
                  'Observed start: ' + window['from'], 'Report-generation cutoff: ' + window['to'],
                  'Timezone: explicit UTC offsets in the endpoints', '',
                  '| Session | Model | Recorded tokens | Responses |',
                  '| --- | --- | --- | --- |'])
    for thread in threads:
        selected = [row for row in rows if row['thread_id'] == thread]
        models = sorted({row['model'] for row in selected}, key=lambda item: item or '') or [None]
        for model in models:
            aggregate = summary([row for row in selected if row['model'] == model])
            lines.append('| ' + ' | '.join([label(thread), label(model) if model else 'unavailable',
                         number(aggregate['tokens']['total_tokens']), str(aggregate['record_count'])]) + ' |')
    subheading = None
    if any(item is not None for item in (subject, scope, completed)):
        require(all(item is not None for item in (subject, scope, completed)), 'report_metadata_incomplete')
        day = date.fromisoformat(completed)
        subheading = (label(subject) + ' | ' + label(scope) + ' | Investigation completed '
                      + day.strftime('%B') + ' ' + str(day.day) + ', ' + str(day.year)
                      + ' | Report processing duration: ' + duration + ' | Total recorded tokens: ' + total)
    return {'subheading': subheading, 'details': '\n'.join(lines) + '\n'}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--accounting', required=True)
    parser.add_argument('--format', choices=('markdown', 'json'), default='markdown')
    parser.add_argument('--subject')
    parser.add_argument('--scope')
    parser.add_argument('--completed', help='Verified investigation completion date (YYYY-MM-DD)')
    args = parser.parse_args(argv)
    try:
        path = Path(args.accounting)
        require(path.stat().st_size <= 64 * 1024 * 1024, 'accounting_size_limit')
        sections = render(json.loads(path.read_text(), object_pairs_hook=unique_object),
                          args.subject, args.scope, args.completed)
    except EvidenceError as error:
        print(json.dumps({'schema': 'investigation-token-usage-error/v1', 'status': 'failed',
                          'code': error.code}), file=sys.stderr)
        return 1
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        print(json.dumps({'schema': 'investigation-token-usage-error/v1', 'status': 'failed',
                          'code': 'invalid_accounting_data'}), file=sys.stderr)
        return 1
    if args.format == 'json':
        print(json.dumps(sections))
    else:
        print((sections['subheading'] + '\n\n' if sections['subheading'] else '') + sections['details'], end='')
    return 0


if __name__ == '__main__':
    sys.exit(main())
