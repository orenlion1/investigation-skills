#!/usr/bin/env python3
"""Read explicitly selected Codex transcripts; emit task-bound metadata only.

Adapted from Agent Tasks local-usage semantics at commit
f274648836361bfa05a62f86d88a0191a708632f: skills/agent-task/scripts/collect_local_usage.py
and references/analysis-processing.md. No sibling checkout or service is required.
"""

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import sys
from urllib.parse import unquote, urlsplit


FIELDS = ("input_tokens", "cached_input_tokens", "cache_write_input_tokens",
          "output_tokens", "reasoning_output_tokens", "total_tokens")
MAX_SOURCE = 64 * 1024 * 1024
MAX_SOURCES = 100
IDENTIFIER = re.compile(r"[A-Za-z0-9_.-]{1,128}\Z")


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def identity(value):
    require(isinstance(value, str) and IDENTIFIER.fullmatch(value), "invalid_identity")
    return value


def timestamp(value):
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    require(parsed.utcoffset() is not None, "timezone_required")
    return parsed.astimezone(timezone.utc)


def digest(record):
    return hashlib.sha256(json.dumps(record, sort_keys=True, separators=(",", ":"),
                                     ensure_ascii=True).encode()).hexdigest()


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, "duplicate_json_key")
        result[key] = value
    return result


def usage(values):
    require(isinstance(values, dict), "invalid_usage")
    result = {key: values.get(key) for key in FIELDS}
    require(all(value is None or type(value) is int and value >= 0
                for value in result.values()), "invalid_usage_count")
    for part, whole in (("cached_input_tokens", "input_tokens"),
                        ("reasoning_output_tokens", "output_tokens")):
        require(result[part] is None or result[whole] is None or
                result[part] <= result[whole], "invalid_usage_partition")
    if all(result[key] is not None for key in ("input_tokens", "output_tokens", "total_tokens")):
        require(result["total_tokens"] == result["input_tokens"] + result["output_tokens"],
                "invalid_usage_total")
    return result


def parent_id(metadata):
    parent = metadata.get("parent_thread_id")
    source = metadata.get("source", {})
    if isinstance(source, dict):
        child = source.get("subagent", {})
        spawn = child.get("thread_spawn", {}) if isinstance(child, dict) else {}
        nested = spawn.get("parent_thread_id") if isinstance(spawn, dict) else None
        require(not (parent and nested and parent != nested), "conflicting_parent")
        parent = parent or nested
    return identity(parent) if parent else None


def read_source(selected):
    path = Path(selected["path"])
    require(path.is_absolute() and path.is_file() and not path.is_symlink()
            and not any(parent.is_symlink() for parent in path.parents), "unsafe_source")
    require(path.stat().st_size <= MAX_SOURCE, "source_size_limit")
    with path.open("rb") as stream:
        raw = stream.read(MAX_SOURCE + 1)
    require(len(raw) <= MAX_SOURCE, "source_size_limit")
    records, gaps = {}, []
    lines = raw.splitlines(keepends=True)
    for number, line in enumerate(lines, 1):
        try:
            record = json.loads(line, object_pairs_hook=unique_object)
        except (json.JSONDecodeError, UnicodeError):
            if number == len(lines) and not line.endswith(b"\n"):
                gaps.append({"reason": "truncated_final_record", "source_line": number,
                             "after": records.get(number - 1, {}).get("timestamp")})
                break
            raise ValueError("malformed_source") from None
        require(isinstance(record, dict), "malformed_source")
        records[number] = record
    first = records.get(1, {})
    require(first.get("type") == "session_meta", "missing_session_identity")
    meta = first["payload"]
    thread = identity(selected["thread_id"])
    require(meta.get("id") == thread, "source_identity_mismatch")
    source = {"thread_id": thread, "parent": parent_id(meta), "records": records,
              "sha256": hashlib.sha256(raw).hexdigest(), "gaps": gaps,
              "turns": {}, "active": {}, "native": [], "snapshots": [], "compactions": set()}
    active, models = None, {}
    for number, record in records.items():
        payload = record.get("payload", {})
        payload = payload if isinstance(payload, dict) else {}
        kind = record.get("type")
        if kind == "event_msg" and payload.get("type") == "task_started":
            active = identity(payload.get("turn_id"))
            attribution = payload.get("turn_attribution", {}) or {}
            boundary = {"root_turn_id": payload.get("root_turn_id", attribution.get("root_turn_id", active)),
                        "parent_turn_id": attribution.get("parent_turn_id", payload.get("parent_turn_id"))}
            require(active not in source["turns"] or source["turns"][active] == boundary,
                    "conflicting_turn_identity")
            source["turns"][active] = boundary
        elif kind == "turn_context":
            active = identity(payload.get("turn_id"))
            model = payload.get("model")
            if isinstance(model, str) and re.fullmatch(r"[A-Za-z0-9._:/-]{1,160}", model):
                models[active] = model
        source["active"][number] = active
        if kind == "token_usage_record" and payload.get("thread_id") == thread:
            source["native"].append({"thread_id": thread,
                "session_id": identity(payload.get("session_id")),
                "turn_id": identity(payload.get("turn_id")),
                "root_turn_id": identity(payload.get("root_turn_id")),
                "response_id": identity(payload.get("response_id")),
                "observed_at": record["timestamp"], "usage": usage(payload.get("usage")),
                "turn_cumulative_usage": usage(payload["turn_token_usage"]) if payload.get("turn_token_usage") is not None else None,
                "source_line": number, "record_sha256": digest(record),
                "source_kind": "native_response", "model": models.get(payload.get("turn_id"))})
        elif kind == "event_msg" and payload.get("type") == "token_count":
            info = payload.get("info")
            if isinstance(info, dict) and isinstance(info.get("total_token_usage"), dict):
                source["snapshots"].append({"turn_id": active, "observed_at": record["timestamp"],
                    "usage": usage(info["total_token_usage"]), "source_line": number,
                    "record_sha256": digest(record), "model": models.get(active)})
        elif kind == "compacted" and payload.get("compaction_response_id"):
            source["compactions"].add(payload["compaction_response_id"])
    return source


def proved_record(sources, proof):
    source = sources[proof["thread_id"]]
    number = proof["source_line"]
    require(type(number) is int and number > 0, "invalid_proof_line")
    record = source["records"][number]
    require(digest(record) == proof["sha256"], "record_proof_mismatch")
    return source, record, source["active"][number]


def prove_task_resolution(sources, binding, artifact, end):
    """Bind shorthand to observed successful finalization, never assistant prose."""
    thread, turn = binding['thread_id'], binding['turn_id']
    proof = binding.get('task_resolution')
    require(isinstance(proof, dict), 'task_resolution_required')
    require(proof['thread_id'] == thread, 'task_resolution_wrong_thread')
    _, record, active = proved_record(sources, proof)
    payload = record.get('payload', {})
    item = payload.get('item', {})
    require(active == turn and payload.get('turn_id') == turn, 'task_resolution_wrong_turn')
    require(record.get('type') == 'event_msg' and payload.get('type') == 'item_completed'
            and item.get('type') == 'CommandExecution' and item.get('status') == 'completed'
            and type(item.get('exit_code')) is int and item['exit_code'] == 0,
            'successful_task_resolution_required')
    request = sources[thread]['records'][binding['proof']['source_line']]
    require(proof['source_line'] > binding['proof']['source_line']
            and timestamp(request['timestamp']) <= timestamp(record['timestamp']) <= end,
            'task_resolution_outside_request')
    cwd = item.get('cwd', '')
    if cwd.startswith('file:'):
        parsed = urlsplit(cwd)
        require(parsed.scheme == 'file' and parsed.netloc in ('', 'localhost')
                and not parsed.query and not parsed.fragment, 'invalid_resolution_cwd')
        cwd = unquote(parsed.path)
    require(Path(cwd).is_absolute() and '..' not in Path(cwd).parts, 'invalid_resolution_cwd')
    output = item.get('aggregated_output', '')
    require(isinstance(output, str), 'invalid_task_resolution_output')
    paths = re.findall(r'^Finalized: (.+)$', output, re.M)
    expected = str(Path(cwd) / artifact)
    # Older editor callers emitted only the verified absolute TASK path.
    # Accept that sole-line command result without inventing a past marker.
    historical = not paths and output.splitlines() == [expected]
    require(paths == [expected] or historical, 'task_resolution_ambiguous_or_wrong_task')


def bind_turns(sources, bindings, artifact, end):
    admitted, proof_lines = {}, {}
    for binding in bindings:
        thread, turn = identity(binding["thread_id"]), identity(binding["turn_id"])
        source, record, active = proved_record(sources, {**binding["proof"], "thread_id": thread})
        require(source["parent"] is None and active == turn, "root_turn_proof_mismatch")
        payload = record.get("payload", {})
        require(record.get("type") == "response_item" and payload.get("role") == "user",
                "user_request_required")
        content = payload.get("content", [])
        text = content if isinstance(content, str) else "\n".join(
            item.get("text", "") for item in content if item.get("type") in ("text", "input_text"))
        require(not re.search(r"#\s*AGENTS\.md|<INSTRUCTIONS>|<environment_context>|<system>|<developer>",
                              text, re.I), "injected_policy_not_task_proof")
        previous = binding.get("continuation_of")
        if previous is None:
            explicit = re.fullmatch(r"(?:run|edit task)\s+" + re.escape(artifact), text.strip())
            if not explicit:
                first_line = text.strip().splitlines()[0] if text.strip() else ''
                editor = re.fullmatch(r'(?:open|edit)\s+task(?:\.md)?', first_line, re.I)
                require(editor or re.fullmatch(r'run\s+task(?:\.md)?', text.strip(), re.I),
                        'explicit_task_command_required')
                named_tasks = re.findall(r'(?:docs/tasks/)?TASK-[A-Za-z0-9_-]+\.md', text)
                require(all(Path(item).name == Path(artifact).name for item in named_tasks),
                        'request_names_other_task')
                prove_task_resolution(sources, binding, artifact, end)
        else:
            require((thread, previous) in admitted and previous != turn, "continuation_not_bound")
            require(binding["proof"]["source_line"] > proof_lines[(thread, previous)],
                    "continuation_precedes_request")
            other_tasks = re.findall(r"(?:docs/tasks/)?TASK-[A-Za-z0-9_-]+\.md", text)
            require(all(Path(item).name == Path(artifact).name for item in other_tasks),
                    "continuation_names_other_task")
        require((thread, turn) not in admitted, "duplicate_binding")
        admitted[(thread, turn)] = (thread, turn)
        proof_lines[(thread, turn)] = binding["proof"]["source_line"]
    changed = True
    while changed:
        changed = False
        for thread, source in sources.items():
            for turn, boundary in source["turns"].items():
                parent = admitted.get((source["parent"], boundary["parent_turn_id"]))
                if source["parent"] and parent and boundary["root_turn_id"] == parent[1] and (thread, turn) not in admitted:
                    admitted[(thread, turn)] = parent
                    changed = True
    return admitted


def summary(rows):
    return {"record_count": len(rows), "tokens": {
        field: sum(row["usage"][field] for row in rows)
        if rows and all(row["usage"][field] is not None for row in rows) else None for field in FIELDS},
        "available_record_counts": {field: sum(row["usage"][field] is not None for row in rows)
                                    for field in FIELDS}}


def counter_gaps(rows, baselines=()):
    """Counters reconcile response rows; they never add usage to the population."""
    previous = {(row['thread_id'], row['turn_id']): row['turn_cumulative_usage']
                for row in baselines}
    gaps = []
    for row in rows:
        current = row.get("turn_cumulative_usage")
        if current is None:
            continue
        key = row["thread_id"], row["turn_id"]
        prior = previous.get(key, dict.fromkeys(FIELDS, 0))
        mismatch = any(current[field] is not None and prior[field] is not None
                       and row["usage"][field] is not None
                       and current[field] - prior[field] != row["usage"][field] for field in FIELDS)
        if mismatch:
            gaps.append({"thread_id": key[0], "turn_id": key[1], "source_line": row["source_line"],
                         "reason": "native_counter_does_not_reconcile_to_observed_responses"})
        previous[key] = current
    return gaps


def collect(manifest):
    require(manifest.get("schema") == "investigation-token-usage-bindings/v1", "invalid_manifest_schema")
    artifact = manifest["task_artifact"]
    require(isinstance(artifact, str) and re.fullmatch(r"docs/tasks/TASK-[a-z0-9-]+\.md", artifact),
            "invalid_task_artifact")
    selected = manifest["sources"]
    require(isinstance(selected, list) and 0 < len(selected) <= MAX_SOURCES, "source_count_limit")
    sources = {}
    for item in selected:
        source = read_source(item)
        require(source["thread_id"] not in sources, "duplicate_source_thread")
        sources[source["thread_id"]] = source
    window = manifest["window"]
    start, end = timestamp(window["from"]), timestamp(window["to"])
    require(start <= end, "invalid_window")
    admitted = bind_turns(sources, manifest["bindings"], artifact, end)
    for key, expected in (("start", start), ("end", end)):
        source, record, turn = proved_record(sources, window[key])
        require((source["thread_id"], turn) in admitted and timestamp(record["timestamp"]) == expected,
                "window_endpoint_not_proven")
    rows, gaps, excluded, seen = [], [], 0, {}
    for thread, source in sources.items():
        gaps.extend({"thread_id": thread, **gap} for gap in source["gaps"]
                    if gap.get("after") is None or timestamp(gap["after"]) <= end)
        native_turns = {row["turn_id"] for row in source["native"]}
        candidates = list(source["native"])
        previous = None
        for snapshot in source["snapshots"]:
            turn = snapshot["turn_id"]
            if turn not in native_turns and (thread, turn) in admitted:
                reason = None
                if previous is None or previous["turn_id"] != turn:
                    reason = "legacy_same_turn_baseline_missing"
                elif any(snapshot["usage"][field] is not None and previous["usage"][field] is not None
                         and snapshot["usage"][field] < previous["usage"][field] for field in FIELDS):
                    reason = "legacy_counter_reset"
                elif timestamp(previous["observed_at"]) < start:
                    reason = "legacy_delta_crosses_window_start"
                else:
                    delta = {field: snapshot["usage"][field] - previous["usage"][field]
                             if snapshot["usage"][field] is not None and previous["usage"][field] is not None
                             else None for field in FIELDS}
                    if any(value for value in delta.values()):
                        root_thread, root_turn = admitted[(thread, turn)]
                        candidates.append({**snapshot, "thread_id": thread, "session_id": root_thread,
                            "root_turn_id": root_turn, "response_id": "legacy-" + snapshot["record_sha256"],
                            "source_kind": "legacy_counter_delta", "usage": usage(delta)})
                if reason and start <= timestamp(snapshot["observed_at"]) <= end:
                    gaps.append({"thread_id": thread, "turn_id": turn, "reason": reason,
                                 "source_line": snapshot["source_line"]})
            previous = snapshot
        for row in candidates:
            root = admitted.get((thread, row["turn_id"]))
            if not root or not start <= timestamp(row["observed_at"]) <= end:
                excluded += 1
                continue
            require((row["session_id"], row["root_turn_id"]) == root, "native_lineage_mismatch")
            key = (thread, row["response_id"])
            comparable = {field: row.get(field) for field in ("session_id", "turn_id", "root_turn_id", "usage", "observed_at", "turn_cumulative_usage")}
            require(key not in seen or seen[key] == comparable, "conflicting_response_usage")
            if key in seen:
                continue
            seen[key] = comparable
            rows.append({**row, "population": "root" if thread == root[0] else "child",
                         "is_compaction": row["response_id"] in source["compactions"]})
    rows.sort(key=lambda row: (timestamp(row["observed_at"]), row["thread_id"], row["source_line"]))
    # A scoped request can start inside an existing native turn. Earlier counters
    # reconcile its first response but never contribute tokens to this window.
    baselines = {}
    for thread, source in sources.items():
        for row in source['native']:
            root = admitted.get((thread, row['turn_id']))
            if (root and timestamp(row['observed_at']) < start
                    and row.get('turn_cumulative_usage') is not None
                    and (row['session_id'], row['root_turn_id']) == root):
                key = thread, row['turn_id']
                if key not in baselines or timestamp(row['observed_at']) > timestamp(baselines[key]['observed_at']):
                    baselines[key] = row
    gaps.extend(counter_gaps(rows, baselines.values()))
    observed_turns = {(row["thread_id"], row["turn_id"]) for row in rows}
    gaps.extend({"thread_id": thread, "turn_id": turn, "reason": "admitted_turn_has_no_observed_usage"}
                for thread, turn in admitted if (thread, turn) not in observed_turns)
    return {"schema": "investigation-token-usage/v1", "task_artifact": artifact,
        "window": {"from": window["from"], "to": window["to"], "elapsed_seconds": (end - start).total_seconds(),
                   "semantics": "observed wall-clock interval; includes waits and gaps"},
        "usage": summary(rows), "root_usage": summary([row for row in rows if row["population"] == "root"]),
        "child_usage": summary([row for row in rows if row["population"] == "child"]),
        "compaction_usage": summary([row for row in rows if row["is_compaction"]]),
        "model_usage": [{"model": model, **summary([row for row in rows if row["model"] == model])}
                        for model in sorted({row["model"] for row in rows}, key=lambda item: item or "")],
        "sessions": [{"thread_id": thread, "source_sha256": source["sha256"],
                      **summary([row for row in rows if row["thread_id"] == thread])}
                     for thread, source in sources.items()],
        "coverage": {"scope": "explicitly selected sources and proved turns within the window",
                     "status": "partial" if gaps or not rows else "observed",
                     "admitted_turns": len(admitted), "excluded_records": excluded, "gaps": gaps,
                     "records_with_observed_model": sum(row["model"] is not None for row in rows),
                     "native_counter_baselines": [{key: row[key] for key in
                         ('thread_id', 'turn_id', 'source_line', 'record_sha256', 'observed_at')}
                         for row in baselines.values()],
                     "child_discovery": "only explicitly supplied child sources are inspected",
                     "legacy_delta_count": sum(row["source_kind"] == "legacy_counter_delta" for row in rows)},
        "responses": rows}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True)
    args = parser.parse_args(argv)
    try:
        path = Path(args.manifest)
        require(path.stat().st_size <= 2 * 1024 * 1024, "manifest_size_limit")
        result = collect(json.loads(path.read_text(), object_pairs_hook=unique_object))
    except (OSError, ValueError, TypeError, KeyError, AttributeError):
        print("Token usage unavailable: invalid, missing, or conflicting local evidence.", file=sys.stderr)
        return 1
    print(json.dumps(result, sort_keys=True, allow_nan=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
