#!/usr/bin/env python3
"""Read-only ten-minute soft checkpoint calculation; never cancels an investigation."""
import argparse
from datetime import datetime, timezone
import json


def timestamp(value):
    result = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if result.utcoffset() is None:
        raise ValueError('timestamps require an explicit UTC offset')
    return result


def union_seconds(intervals):
    merged = []
    for start, end in sorted(intervals):
        if merged and start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(end, merged[-1][1]))
        else:
            merged.append((start, end))
    return sum((end - start).total_seconds() for start, end in merged)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--started', required=True, help='observed investigation request timestamp')
    parser.add_argument('--observed', help='current observation or verified handoff timestamp')
    parser.add_argument('--checkpoint', help='timestamp of an already delivered soft checkpoint')
    parser.add_argument('--wait', action='append', nargs=3, default=[],
                        metavar=('KIND', 'START', 'END'),
                        help='observed user, editor or authentication wait interval')
    parser.add_argument('--wait-coverage', choices=('partial', 'complete'), default='partial')
    args = parser.parse_args()
    try:
        start = timestamp(args.started)
        end = timestamp(args.observed) if args.observed else datetime.now(timezone.utc)
        if end < start:
            raise ValueError('observation precedes start')
        checkpoint = timestamp(args.checkpoint) if args.checkpoint else None
        if checkpoint and not start <= checkpoint <= end:
            raise ValueError('checkpoint lies outside observed interval')
        if checkpoint and (checkpoint - start).total_seconds() < 600:
            raise ValueError('soft checkpoint precedes ten-minute limit')
        waits = {kind: [] for kind in ('user', 'editor', 'authentication')}
        for kind, first, last in args.wait:
            if kind not in waits:
                raise ValueError('wait kind must be user, editor or authentication')
            first, last = timestamp(first), timestamp(last)
            if not start <= first <= last <= end:
                raise ValueError('wait lies outside observed interval or has reversed endpoints')
            waits[kind].append((first, last))
        elapsed = (end - start).total_seconds()
        waiting = union_seconds([span for spans in waits.values() for span in spans])
        print(json.dumps({'schema': 'investigation-budget/v1',
                          'started': start.isoformat(), 'observed': end.isoformat(),
                          'soft_limit_seconds': 600, 'elapsed_seconds': elapsed,
                          'checkpoint_due': elapsed >= 600 and checkpoint is None,
                          'observed_wait_seconds': waiting,
                          'wait_seconds_by_kind': {k: union_seconds(v) for k, v in waits.items()},
                          'wait_coverage': args.wait_coverage,
                          'non_wait_wall_seconds': elapsed - waiting
                          if args.wait_coverage == 'complete' else None,
                          'processing_seconds': None}, indent=2))
    except (ValueError, OverflowError) as error:
        parser.error(str(error))


if __name__ == '__main__':
    main()
