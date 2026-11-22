# Accounting Evidence Reference

Manifest proofs, collector diagnostics, checkpoint verification and counter reconciliation for
[Token Usage](../SKILL.md). Read it when building or repairing a manifest or diagnosing a
collection failure.

## Manifest

Canonical JSON for a proof hash is
`json.dumps(record, sort_keys=True, separators=(',', ':'), ensure_ascii=True)` encoded as UTF-8. Source filenames and user text stay private; the output contains metadata.

```json
{
  "schema": "investigation-token-usage-bindings/v1",
  "task_artifact": "docs/tasks/TASK-example.md",
  "sources": [{"path": "/absolute/selected-session.jsonl", "thread_id": "native-thread-id"}],
  "bindings": [{
    "thread_id": "native-thread-id", "turn_id": "native-turn-id",
    "proof": {"source_line": 10, "sha256": "canonical-record-sha256"}
  }],
  "window": {
    "from": "2026-10-16T10:00:00Z", "to": "2026-10-16T10:10:00Z",
    "start": {"thread_id": "native-thread-id", "source_line": 8, "sha256": "canonical-record-sha256"},
    "end": {"thread_id": "native-thread-id", "source_line": 100, "sha256": "canonical-record-sha256"}
  }
}
```

## Request binding and task resolution

For shorthand `run task`, `open task`, or `edit task` (case insensitive, optional `.md`), supply
`task_resolution` on the first binding: a proof object with `thread_id`, `source_line`, and
`sha256`. An editor command may be the first line of a user message followed by inline
requirements; a conflicting TASK filename in that message is rejected.

```json
"task_resolution": {
  "thread_id": "native-thread-id", "source_line": 20,
  "sha256": "canonical-completed-command-record-sha256"
}
```

Select the native `event_msg` / `item_completed` record for the successful finalization command
in the same thread and either the request turn or an explicitly verified descendant continuation
turn, after the request and no later than the report cutoff. Its item must be a completed
`CommandExecution` with exit code zero, an absolute `cwd` (or local `file:` URI), and exactly one
output line `Finalized: <absolute-task-path>` matching `<cwd>/<task_artifact>`.

- For historical recordings only, a successful command whose entire output is the sole absolute
  TASK path (with an optional final newline) is also accepted.
- Extra output, a different path, or a failed, tampered, ambiguous, other-thread, unbound-turn,
  or out-of-window record is rejected.

## Continuations

Explicit attribution of a `continuation_of` binding is the agent's responsibility.

- The helper verifies the hashed user record, turn, continuity link, and absence of a
  conflicting TASK filename. It never accepts injected AGENTS policy as a task request.
- List root bindings in continuation order; child turns are admitted from their native lineage
  without invented bindings.
- Resolution is checked only after every root binding is validated. A later resolution must
  follow `continuation_of` links back to the original shorthand request; an independent root,
  missing link, conflicting task, wrong-thread proof or assistant explanation never substitutes
  for that chain.

## Contributing threads

Beyond the explicit `expected_threads` list, the collector detects omitted children from
standard Codex native agent-spawn function calls and JSON results containing `agent_id` in
admitted turns.

- Unreadable selected files fail collection. Unresolved spawn results remain gaps.
- Other native spawn formats require explicit inventory verification; the helper does not scan
  session directories or prove that the supplied inventory is exhaustive.

## Collector limits and diagnostics

Source reads are bounded to 100 selected files, 64 MiB each. Malformed/conflicting evidence
fails closed with a sanitized JSON diagnostic on stderr (exit 1, no accounting JSON on stdout),
schema `investigation-token-usage-error/v1`, `status: failed`, and a fixed `code`:

| `code` | Meaning |
| --- | --- |
| `user_request_required` | Wrong request record |
| `task_resolution_wrong_turn` | Unbound resolution |
| `window_start_timestamp_mismatch`, `window_end_timestamp_mismatch` | Endpoint mismatch, as distinct from missing turn proof |
| `invalid_local_evidence` | Structural/read failure |

The table gives examples, not the full code list. Raw exceptions and private paths never enter
diagnostics.

## Checkpoint cutoff verification

The recorder's thread and turn IDs must come from the canonical root request/continuation being
processed. It exclusively writes owner-only evidence using the current UTC time and has no
timestamp argument. Collection checks the checkpoint's hash, schema, purpose, task, admitted root
turn and exact timestamp. Its sanitized output retains endpoint proofs without the private file
path.

## Counter reconciliation

- A request may start partway through a native turn that includes earlier editor/setup work.
  The collector uses the latest same-turn, same-lineage native counter before the window only to
  reconcile the first included response. It records that baseline's proof metadata, never adds
  its tokens, and preserves actual counter mismatches as coverage gaps. Legacy counter-only
  deltas still cannot cross the window start.
- When native usage is absent for an entire turn, the helper uses only nonnegative deltas
  between consecutive cumulative snapshots in that same turn. Missing baselines, resets, and
  deltas crossing the selected window's start remain gaps.

## Provenance

The attribution, deduplication, compaction, legacy-delta, and duration rules follow Agent Tasks
at commit `f274648836361bfa05a62f86d88a0191a708632f`:
[analysis-processing.md](https://github.com/orenlion1/agent-tasks/blob/f274648836361bfa05a62f86d88a0191a708632f/skills/agent-task/references/analysis-processing.md)
and [collect_local_usage.py](https://github.com/orenlion1/agent-tasks/blob/f274648836361bfa05a62f86d88a0191a708632f/skills/agent-task/scripts/collect_local_usage.py).
This focused implementation adds investigation request/continuation bindings and observed
conversation endpoints. It does not invoke the Agent Tasks lifecycle or alter frozen logs.
