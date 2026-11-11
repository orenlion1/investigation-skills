import copy
import importlib.util
import json
import subprocess
import sys
from pathlib import Path
import tempfile
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "skills/token-usage/scripts/collect_token_usage.py"
SPEC = importlib.util.spec_from_file_location("token_usage", SCRIPT)
collector = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(collector)
TASK = "docs/tasks/TASK-investigate-example.md"


def counts(input_tokens=100, output_tokens=10):
    return {"input_tokens": input_tokens, "cached_input_tokens": input_tokens // 2,
            "cache_write_input_tokens": 0, "output_tokens": output_tokens,
            "reasoning_output_tokens": output_tokens // 2,
            "total_tokens": input_tokens + output_tokens}


def record(kind, payload, second=0):
    return {"type": kind, "payload": payload, "timestamp": f"2026-10-16T10:00:{second:02d}Z"}


def start(turn="turn", parent=None, root=None, second=0):
    return record("event_msg", {"type": "task_started", "turn_id": turn,
        "turn_attribution": {"parent_turn_id": parent, "root_turn_id": root or turn}}, second)


def response(thread="root", turn="turn", response_id="response-1", second=2, values=None):
    return record("token_usage_record", {"thread_id": thread, "session_id": "root",
        "turn_id": turn, "root_turn_id": "turn", "response_id": response_id,
        "usage": values or counts()}, second)


class TokenUsageTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()
        self.records = [record("session_meta", {"id": "root"}), start(),
            record("response_item", {"type": "message", "role": "user",
                   "content": [{"type": "input_text", "text": "run " + TASK}]}, 1),
            response(), record("event_msg", {"type": "task_complete", "turn_id": "turn"}, 10)]

    def source(self, records, thread="root"):
        path = self.root / (thread + ".jsonl")
        path.write_text("".join(json.dumps(row) + "\n" for row in records))
        return {"path": str(path), "thread_id": thread}

    def proof(self, number, records=None, thread="root"):
        return {"thread_id": thread, "source_line": number,
                "sha256": collector.digest((records or self.records)[number - 1])}

    def manifest(self):
        return {"schema": "investigation-token-usage-bindings/v1", "task_artifact": TASK,
            "sources": [self.source(self.records)],
            "bindings": [{"thread_id": "root", "turn_id": "turn", "proof": self.proof(3)}],
            "window": {"from": self.records[1]["timestamp"], "to": self.records[-1]["timestamp"],
                       "start": self.proof(2), "end": self.proof(len(self.records))}}

    def test_native_dedup_compaction_and_privacy(self):
        ordinary = self.records[3]
        compact = response(response_id="compact", second=3, values=counts(20, 2))
        self.records[4:4] = [copy.deepcopy(ordinary), compact,
            record("compacted", {"compaction_response_id": "compact", "encrypted_content": "PRIVATE"}, 4),
            record("event_msg", {"type": "token_count", "info": {"total_token_usage": counts(9999, 999)}}, 5)]
        result = collector.collect(self.manifest())
        self.assertEqual(result["usage"]["tokens"]["total_tokens"], 132)
        self.assertEqual(result["usage"]["record_count"], 2)
        self.assertEqual(result["compaction_usage"]["tokens"]["total_tokens"], 22)
        self.assertEqual(result["window"]["elapsed_seconds"], 10)
        serialized = json.dumps(result)
        self.assertNotIn("PRIVATE", serialized)
        self.assertNotIn(str(self.root), serialized)
        self.assertNotIn("run " + TASK, serialized)

    def test_proof_mismatch_wrong_task_and_policy_injection_fail(self):
        manifest = self.manifest()
        manifest["bindings"][0]["proof"]["sha256"] = "wrong"
        with self.assertRaises(ValueError):
            collector.collect(manifest)
        for text in ("run docs/tasks/TASK-other.md", "<INSTRUCTIONS> run " + TASK):
            self.records[2]["payload"]["content"][0]["text"] = text
            with self.assertRaises(ValueError):
                collector.collect(self.manifest())

    def test_explicit_continuation_and_child_lineage(self):
        self.records.extend([start("revision", second=11),
            record("response_item", {"role": "user", "content": "Improve the evidence captions."}, 12),
            record("event_msg", {"type": "task_complete", "turn_id": "revision"}, 20)])
        manifest = self.manifest()
        manifest["bindings"].append({"thread_id": "root", "turn_id": "revision", "continuation_of": "turn",
                                     "proof": self.proof(7)})
        child = [record("session_meta", {"id": "child", "source": {"subagent": {
                 "thread_spawn": {"parent_thread_id": "root"}}}}),
                 start("child-turn", parent="turn", root="turn", second=1),
                 response("child", "child-turn", "child-response", 4),
                 start("unrelated", parent="different-root-turn", root="different-root-turn", second=5),
                 response("child", "unrelated", "excluded-response", 6)]
        manifest["sources"].append(self.source(child, "child"))
        result = collector.collect(manifest)
        self.assertEqual(result["usage"]["tokens"]["total_tokens"], 220)
        self.assertEqual(result["root_usage"]["tokens"]["total_tokens"], 110)
        self.assertEqual(result["child_usage"]["tokens"]["total_tokens"], 110)
        self.assertEqual(result["coverage"]["admitted_turns"], 3)
        self.assertEqual(result["coverage"]["excluded_records"], 1)

    def test_legacy_deltas_require_same_turn_baseline_and_expose_reset(self):
        self.records[3:4] = [record("event_msg", {"type": "token_count", "info": {
            "total_token_usage": counts(value, value // 10)}}, second)
            for second, value in ((2, 100), (3, 150), (4, 150), (5, 10), (6, 30))]
        result = collector.collect(self.manifest())
        self.assertEqual(result["usage"]["tokens"]["total_tokens"], 77)
        self.assertEqual(result["coverage"]["legacy_delta_count"], 2)
        self.assertEqual(result["coverage"]["status"], "partial")
        self.assertEqual({gap["reason"] for gap in result["coverage"]["gaps"]},
                         {"legacy_same_turn_baseline_missing", "legacy_counter_reset"})

    def test_missing_fields_remain_unavailable_and_counter_gaps_are_partial(self):
        del self.records[3]["payload"]["usage"]["reasoning_output_tokens"]
        self.records[3]["payload"]["turn_token_usage"] = counts(200, 20)
        result = collector.collect(self.manifest())
        self.assertIsNone(result["usage"]["tokens"]["reasoning_output_tokens"])
        self.assertEqual(result["usage"]["available_record_counts"]["reasoning_output_tokens"], 0)
        self.assertEqual(result["usage"]["tokens"]["total_tokens"], 110)
        self.assertEqual(result["coverage"]["status"], "partial")

    def test_model_is_observed_from_own_turn_context(self):
        self.records.insert(3, record("turn_context", {"turn_id": "turn", "model": "observed-model"}, 1))
        result = collector.collect(self.manifest())
        self.assertEqual(result["model_usage"][0]["model"], "observed-model")
        self.assertEqual(result["coverage"]["records_with_observed_model"], 1)

    def test_empty_admitted_turn_stays_unavailable(self):
        self.records.pop(3)
        result = collector.collect(self.manifest())
        self.assertIsNone(result["usage"]["tokens"]["total_tokens"])
        self.assertEqual(result["coverage"]["status"], "partial")
        self.assertIn("admitted_turn_has_no_observed_usage",
                      {gap["reason"] for gap in result["coverage"]["gaps"]})

    def test_legacy_does_not_use_baseline_outside_window(self):
        self.records[3:4] = [record("event_msg", {"type": "token_count", "info": {
            "total_token_usage": counts(value, value // 10)}}, second)
            for second, value in ((2, 100), (3, 150), (4, 200))]
        manifest = self.manifest()
        manifest["window"]["start"] = self.proof(5)
        manifest["window"]["from"] = self.records[4]["timestamp"]
        result = collector.collect(manifest)
        self.assertEqual(result["usage"]["tokens"]["total_tokens"], 55)
        self.assertIn("legacy_delta_crosses_window_start",
                      {gap["reason"] for gap in result["coverage"]["gaps"]})

    def test_conflicting_response_duplicate_and_unproven_end_fail(self):
        self.records.insert(4, response(values=counts(200, 20)))
        with self.assertRaises(ValueError):
            collector.collect(self.manifest())
        self.records.pop(4)
        manifest = self.manifest()
        manifest["window"]["to"] = "2026-10-16T10:01:00Z"
        with self.assertRaises(ValueError):
            collector.collect(manifest)

    def shorthand_manifest(self):
        self.records[2]['payload']['content'][0]['text'] = 'run task'
        self.records.insert(4, record('event_msg', {'type': 'item_completed', 'turn_id': 'turn',
            'item': {'type': 'CommandExecution', 'status': 'completed', 'exit_code': 0,
                     'cwd': self.root.as_uri(),
                     'aggregated_output': 'Finalized: ' + str(self.root / TASK) + '\n'}}, 3))
        manifest = self.manifest()
        manifest['bindings'][0]['task_resolution'] = self.proof(5)
        return manifest

    def test_shorthand_uses_hashed_successful_task_resolution(self):
        result = collector.collect(self.shorthand_manifest())
        self.assertEqual(result['usage']['tokens']['total_tokens'], 110)
        self.assertEqual(result['coverage']['status'], 'observed')
        self.assertNotIn(str(self.root), json.dumps(result))
        self.assertNotIn('Finalized:', json.dumps(result))

    def test_shorthand_without_resolution_fails(self):
        manifest = self.shorthand_manifest()
        del manifest['bindings'][0]['task_resolution']
        with self.assertRaises(ValueError):
            collector.collect(manifest)

    def test_editor_aliases_and_inline_requirements_bind_verified_task(self):
        original = copy.deepcopy(self.records)
        for command in ('open task', 'open TASK', 'open TASK.md',
                        'edit task', 'edit TASK', 'edit TASK.md'):
            with self.subTest(command=command):
                self.records = copy.deepcopy(original)
                manifest = self.shorthand_manifest()
                self.records[2]['payload']['content'][0]['text'] = (
                    command + '\nInvestigate the supplied alerts read-only.')
                manifest = self.manifest()
                manifest['bindings'][0]['task_resolution'] = self.proof(5)
                result = collector.collect(manifest)
                self.assertEqual(result['usage']['tokens']['total_tokens'], 110)
                self.assertEqual(result['coverage']['status'], 'observed')

    def test_editor_alias_requires_resolution_and_rejects_conflicting_task(self):
        self.records[2]['payload']['content'][0]['text'] = 'open task'
        with self.assertRaises(ValueError):
            collector.collect(self.manifest())
        manifest = self.shorthand_manifest()
        self.records[2]['payload']['content'][0]['text'] = (
            'edit task\nRun docs/tasks/TASK-other.md instead.')
        manifest = self.manifest()
        manifest['bindings'][0]['task_resolution'] = self.proof(5)
        with self.assertRaisesRegex(ValueError, 'request_names_other_task'):
            collector.collect(manifest)

    def test_editor_resolution_accepts_historical_single_path_output(self):
        manifest = self.shorthand_manifest()
        self.records[2]['payload']['content'][0]['text'] = 'open task'
        self.records[4]['payload']['item']['aggregated_output'] = str(self.root / TASK) + '\n'
        manifest = self.manifest()
        manifest['bindings'][0]['task_resolution'] = self.proof(5)
        result = collector.collect(manifest)
        self.assertEqual(result['usage']['tokens']['total_tokens'], 110)
        self.assertNotIn(str(self.root), json.dumps(result))

    def test_historical_path_output_rejects_ambiguous_or_failed_resolution(self):
        original = copy.deepcopy(self.records)
        for output, exit_code in ((str(self.root / TASK) + '\nextra text', 0),
                                  (str(self.root / 'docs/tasks/TASK-other.md'), 0),
                                  (str(self.root / TASK), 1),
                                  ('Finalized: ' + str(self.root / 'docs/tasks/TASK-other.md')
                                   + '\n' + str(self.root / TASK), 0)):
            with self.subTest(output=output, exit_code=exit_code):
                self.records = copy.deepcopy(original)
                self.shorthand_manifest()
                self.records[2]['payload']['content'][0]['text'] = 'edit task'
                self.records[4]['payload']['item'].update(
                    aggregated_output=output, exit_code=exit_code)
                manifest = self.manifest()
                manifest['bindings'][0]['task_resolution'] = self.proof(5)
                with self.assertRaises(ValueError):
                    collector.collect(manifest)

    def test_shorthand_rejects_wrong_tampered_failed_ambiguous_or_late_resolution(self):
        original = copy.deepcopy(self.records)
        mutations = [
            lambda item: item.update(aggregated_output='Finalized: ' + str(self.root / 'docs/tasks/TASK-other.md')),
            lambda item: item.update(exit_code=1),
            lambda item: item.update(status='in_progress'),
            lambda item: item.update(aggregated_output=item['aggregated_output'] + 'Finalized: ' + str(self.root / TASK)),
        ]
        for mutate in mutations:
            with self.subTest(mutate=mutate):
                self.records = copy.deepcopy(original)
                self.shorthand_manifest()
                mutate(self.records[4]['payload']['item'])
                manifest = self.manifest()
                manifest['bindings'][0]['task_resolution'] = self.proof(5)
                with self.assertRaises(ValueError):
                    collector.collect(manifest)
        self.records = copy.deepcopy(original)
        manifest = self.shorthand_manifest()
        manifest['bindings'][0]['task_resolution']['sha256'] = 'tampered'
        with self.assertRaises(ValueError):
            collector.collect(manifest)
        manifest['bindings'][0]['task_resolution'] = self.proof(5)
        manifest['window'].update(to=self.records[3]['timestamp'], end=self.proof(4))
        with self.assertRaises(ValueError):
            collector.collect(manifest)

    def test_shorthand_rejects_user_or_other_turn_resolution(self):
        manifest = self.shorthand_manifest()
        manifest['bindings'][0]['task_resolution'] = self.proof(3)
        with self.assertRaises(ValueError):
            collector.collect(manifest)
        self.records.insert(4, start('other', second=3))
        manifest = self.manifest()
        manifest['bindings'][0]['task_resolution'] = self.proof(6)
        with self.assertRaises(ValueError):
            collector.collect(manifest)

    def test_native_pre_window_counter_is_reconciliation_only(self):
        self.records[3]['payload']['turn_token_usage'] = counts()
        later = response(response_id='response-2', second=4, values=counts(20, 2))
        later['payload']['turn_token_usage'] = counts(120, 12)
        self.records.insert(4, later)
        manifest = self.manifest()
        manifest['window'].update(start=self.proof(5), **{'from': later['timestamp']})
        result = collector.collect(manifest)
        self.assertEqual(result['usage']['tokens']['total_tokens'], 22)
        self.assertEqual(result['usage']['record_count'], 1)
        self.assertEqual(result['coverage']['status'], 'observed')
        self.assertEqual(result['coverage']['native_counter_baselines'][0]['source_line'], 4)
        self.records[4]['payload']['turn_token_usage'] = counts(140, 14)
        result = collector.collect(self.updated_window_manifest())
        self.assertEqual(result['usage']['tokens']['total_tokens'], 22)
        self.assertEqual(result['coverage']['status'], 'partial')

    def editor_chain_manifest(self):
        self.records[2]['payload']['content'][0]['text'] = 'open task'
        self.records.extend([
            start('profile', second=11),
            record('response_item', {'role': 'user', 'content': 'load additional profile example'}, 12),
            start('draft', second=13),
            record('response_item', {'role': 'user', 'content': 'open new draft, delete existing draft'}, 14),
            record('event_msg', {'type': 'item_completed', 'turn_id': 'draft', 'item': {
                'type': 'CommandExecution', 'status': 'completed', 'exit_code': 0,
                'cwd': str(self.root), 'aggregated_output': 'Finalized: ' + str(self.root / TASK)}}, 15),
            record('event_msg', {'type': 'task_complete', 'turn_id': 'draft'}, 20)])
        manifest = self.manifest()
        manifest['bindings'][0]['task_resolution'] = self.proof(10)
        manifest['bindings'].extend([
            {'thread_id': 'root', 'turn_id': 'profile', 'continuation_of': 'turn', 'proof': self.proof(7)},
            {'thread_id': 'root', 'turn_id': 'draft', 'continuation_of': 'profile', 'proof': self.proof(9)}])
        return manifest

    def test_editor_resolution_reaches_original_request_through_verified_chain(self):
        result = collector.collect(self.editor_chain_manifest())
        self.assertEqual(result['usage']['tokens']['total_tokens'], 110)
        self.assertEqual(result['coverage']['admitted_turns'], 3)

    def test_editor_chain_rejects_missing_link_conflict_and_other_thread(self):
        manifest = self.editor_chain_manifest()
        manifest['bindings'].pop(1)
        with self.assertRaisesRegex(ValueError, 'continuation_not_bound'):
            collector.collect(manifest)
        manifest = self.manifest()
        manifest['bindings'][0]['task_resolution'] = self.proof(10)
        with self.assertRaisesRegex(ValueError, 'task_resolution_wrong_turn'):
            collector.collect(manifest)
        manifest['bindings'][0]['task_resolution']['thread_id'] = 'other'
        with self.assertRaisesRegex(ValueError, 'task_resolution_wrong_thread'):
            collector.collect(manifest)

    def test_missing_expected_child_source_is_a_gap_not_zero(self):
        manifest = self.manifest()
        manifest['expected_threads'] = ['root', 'missing-child']
        result = collector.collect(manifest)
        self.assertEqual(result['coverage']['status'], 'partial')
        self.assertIn({'thread_id': 'missing-child', 'reason': 'expected_source_missing'},
                      result['coverage']['gaps'])
        self.assertIsNone(result['child_usage']['tokens']['total_tokens'])

    def test_native_spawn_result_detects_omitted_child_source(self):
        self.records[4:4] = [
            record('response_item', {'type': 'function_call', 'name': 'spawn_agent',
                                    'call_id': 'spawn-1', 'arguments': 'PRIVATE'}, 3),
            record('response_item', {'type': 'function_call_output', 'call_id': 'spawn-1',
                                    'output': json.dumps({'agent_id': 'omitted-child'})}, 4)]
        result = collector.collect(self.manifest())
        self.assertIn({'thread_id': 'omitted-child', 'reason': 'expected_source_missing'},
                      result['coverage']['gaps'])
        self.assertEqual(result['coverage']['status'], 'partial')
        self.assertNotIn('PRIVATE', json.dumps(result))

    def test_cli_reports_sanitized_exact_wrong_request_code(self):
        manifest = self.shorthand_manifest()
        self.records.insert(3, record('event_msg', {'type': 'item_completed', 'item': {
            'type': 'UserMessage', 'text': 'PRIVATE /private/credential'}}, 1))
        manifest = self.manifest()
        manifest['bindings'][0]['proof'] = self.proof(4)
        path = self.root / 'manifest.json'; path.write_text(json.dumps(manifest))
        result = subprocess.run([sys.executable, str(SCRIPT), '--manifest', str(path)],
                                text=True, capture_output=True)
        self.assertEqual(result.returncode, 1)
        self.assertEqual(json.loads(result.stderr)['code'], 'user_request_required')
        self.assertEqual(result.stdout, '')
        self.assertNotIn('PRIVATE', result.stderr)
        self.assertNotIn(str(self.root), result.stderr)

    def test_cutoff_mismatch_has_precise_code_without_moving_cutoff(self):
        manifest = self.manifest()
        manifest['window']['to'] = '2026-10-16T10:00:10.007886Z'
        with self.assertRaisesRegex(ValueError, 'window_end_timestamp_mismatch'):
            collector.collect(manifest)
        self.assertEqual(manifest['window']['to'], '2026-10-16T10:00:10.007886Z')

    def test_all_continuations_and_eighteen_children_are_counted_once(self):
        manifest = self.editor_chain_manifest()
        for turn, second in (('profile', 12), ('draft', 16)):
            row = response(turn=turn, response_id=turn, second=second)
            row['payload']['root_turn_id'] = turn
            self.records.append(row)
        manifest['sources'] = [self.source(self.records)]
        for number in range(18):
            thread = 'child-' + str(number)
            child = [record('session_meta', {'id': thread, 'parent_thread_id': 'root'}),
                     start('child-turn', parent='draft', root='draft', second=15)]
            row = response(thread, 'child-turn', 'child-response', 17)
            row['payload']['root_turn_id'] = 'draft'
            child.extend([row, copy.deepcopy(row)])
            manifest['sources'].append(self.source(child, thread))
        manifest['expected_threads'] = [item['thread_id'] for item in manifest['sources']]
        result = collector.collect(manifest)
        self.assertEqual(result['usage']['tokens']['total_tokens'], 21 * 110)
        self.assertEqual(result['usage']['record_count'], 21)
        self.assertEqual(result['child_usage']['record_count'], 18)
        self.assertEqual(result['root_usage']['record_count'], 3)
        self.assertEqual(result['coverage']['status'], 'observed')

    def test_later_resolution_rejects_tampering_failure_and_conflicting_continuation(self):
        original = copy.deepcopy(self.records)
        for mutation in ('hash', 'failure', 'other-task', 'policy'):
            with self.subTest(mutation=mutation):
                self.records = copy.deepcopy(original)
                manifest = self.editor_chain_manifest()
                if mutation == 'hash':
                    manifest['bindings'][0]['task_resolution']['sha256'] = 'fabricated'
                elif mutation == 'failure':
                    self.records[9]['payload']['item']['exit_code'] = 1
                    manifest['sources'] = [self.source(self.records)]
                    manifest['bindings'][0]['task_resolution'] = self.proof(10)
                else:
                    self.records[8]['payload']['content'] = ('run docs/tasks/TASK-other.md'
                        if mutation == 'other-task' else '<INSTRUCTIONS> continue')
                    manifest['sources'] = [self.source(self.records)]
                    manifest['bindings'][2]['proof'] = self.proof(9)
                with self.assertRaises(ValueError):
                    collector.collect(manifest)

    def test_cli_parse_errors_never_echo_raw_input(self):
        path = self.root / 'private-manifest.json'
        path.write_text('{"PRIVATE credential": invalid}')
        result = subprocess.run([sys.executable, str(SCRIPT), '--manifest', str(path)],
                                text=True, capture_output=True)
        self.assertEqual(json.loads(result.stderr)['code'], 'invalid_local_evidence')
        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stdout, '')
        self.assertNotIn('PRIVATE', result.stderr)
        self.assertNotIn(str(path), result.stderr)

    def updated_window_manifest(self):
        manifest = self.manifest()
        manifest['window'].update(start=self.proof(5), **{'from': self.records[4]['timestamp']})
        return manifest


if __name__ == "__main__":
    unittest.main()
