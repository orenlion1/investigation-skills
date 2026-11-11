#!/usr/bin/env python3
"""Record a current report-generation cutoff; never accepts a supplied timestamp."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import sys

from collect_token_usage import identity, require


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--task-artifact', required=True)
    parser.add_argument('--thread-id', required=True)
    parser.add_argument('--turn-id', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args(argv)
    try:
        require(re.fullmatch(r'docs/tasks/TASK-[a-z0-9-]+\.md', args.task_artifact),
                'invalid_task_artifact')
        thread, turn = identity(args.thread_id), identity(args.turn_id)
        path = Path(args.output)
        require(path.is_absolute() and path.parent.is_dir()
                and not any(parent.is_symlink() for parent in path.parents), 'unsafe_checkpoint')
        # Exclusive creation preserves every existing checkpoint, including a symlink.
        fd = os.open(str(path), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, 'wb') as stream:
            data = {'schema': 'investigation-accounting-cutoff/v1',
                    'task_artifact': args.task_artifact, 'thread_id': thread, 'turn_id': turn,
                    'purpose': 'report-generation-cutoff',
                    'observed_at': datetime.now(timezone.utc).isoformat()}
            raw = (json.dumps(data, sort_keys=True) + '\n').encode('utf-8')
            stream.write(raw)
        require(path.read_bytes() == raw, 'checkpoint_readback_mismatch')
    except (OSError, ValueError, TypeError):
        print(json.dumps({'schema': 'investigation-token-usage-error/v1', 'status': 'failed',
                          'code': 'checkpoint_recording_failed'}), file=sys.stderr)
        return 1
    print(json.dumps({'kind': 'checkpoint', 'path': str(path),
                      'sha256': hashlib.sha256(raw).hexdigest(), 'observed_at': data['observed_at']}))
    return 0


if __name__ == '__main__':
    sys.exit(main())
