import os
import contextlib
import hashlib
import io
import json
import socket
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import live_eval_proxy  # noqa: E402
import live_eval_sandbox as sandbox  # noqa: E402

SHIM = ROOT / 'scripts' / 'live-evals-runner' / 'claude'


class ExecutorTraceTests(unittest.TestCase):
    def test_large_image_payload_is_referenced_without_losing_text_or_mutating_raw(self):
        data = 'a' * 11000000
        raw = {'content': [{'type': 'image', 'source': {'type': 'base64',
                'media_type': 'image/png', 'data': data}}, {'type': 'text', 'text': 'actual check'}],
               'tool_use_result': {'type': 'image', 'file': {'base64': data, 'type': 'image/png',
                                   'dimensions': {'originalWidth': 900}}},
               'is_error': False}
        compact = sandbox.compact_image_payloads(raw)
        self.assertLess(len(json.dumps(compact)), 2000)
        self.assertIn(hashlib.sha256(data.encode()).hexdigest(), json.dumps(compact))
        self.assertEqual(compact['content'][1], raw['content'][1])
        self.assertFalse(compact['is_error'])
        self.assertEqual(raw['content'][0]['source']['data'], data)
        self.assertEqual(compact['tool_use_result']['file']['dimensions'], {'originalWidth': 900})
        self.assertEqual(raw['tool_use_result']['file']['base64'], data)

    def test_executor_retains_raw_stream_and_exit_status(self):
        row = {'type': 'image', 'source': {'type': 'base64', 'media_type': 'image/png', 'data': 'AAAA'}}
        script = f'import sys; print({json.dumps(json.dumps(row))}); print("plain diagnostic"); sys.exit(7)'
        with tempfile.TemporaryDirectory() as directory, contextlib.redirect_stdout(io.StringIO()) as output:
            raw = Path(directory) / 'raw.jsonl'
            code = sandbox.run_executor([sys.executable, '-c', script], raw_path=raw)
            self.assertEqual(code, 7)
            self.assertEqual(json.loads(raw.read_text().splitlines()[0]), row)
            self.assertIn('plain diagnostic', output.getvalue())
            self.assertNotIn('AAAA', output.getvalue())


class IsolationFlagTests(unittest.TestCase):
    def test_prepared_tools_are_available_without_inheriting_ambient_path(self):
        with tempfile.TemporaryDirectory() as directory:
            tools = Path(directory) / 'bin'
            tools.mkdir()
            python = tools / 'python3'
            python.write_text('#!/bin/sh\nprintf prepared-runtime')
            python.chmod(0o755)
            child = sandbox.isolated_environment(
                {'PATH': '/untrusted/ambient', 'LIVE_EVAL_TOOLS_BIN': str(tools)},
                directory, 'http://localhost:3128', '/opt/claude/bin/claude')
            result = subprocess.run(['python3'], env=child, capture_output=True, text=True, check=True)
            self.assertEqual(result.stdout, 'prepared-runtime')
            self.assertNotIn('/untrusted/ambient', child['PATH'])
            self.assertNotIn('LIVE_EVAL_TOOLS_BIN', child)

    def test_prepared_tools_refuse_relative_or_missing_directory(self):
        for directory in ('relative/bin', '/missing-eval-runtime/bin'):
            with self.subTest(directory=directory), self.assertRaises(ValueError):
                sandbox.isolated_environment({'LIVE_EVAL_TOOLS_BIN': directory},
                                             '/tmp/home', 'http://localhost:3128', '/opt/bin/claude')

    def test_executor_loses_web_tools_and_mcp_servers(self):
        flags = sandbox.isolation_flags(['-p', '--output-format', 'stream-json'])
        self.assertEqual(flags, ['--strict-mcp-config', '--disallowedTools', 'WebFetch', 'WebSearch'])

    def test_grader_gets_no_tools(self):
        self.assertEqual(sandbox.isolation_flags(['-p']), ['--strict-mcp-config', '--tools', ''])

    def test_isolated_environment_passes_only_allowlisted_variables(self):
        env = {'PATH': os.environ['PATH'], 'ANTHROPIC_MODEL': 'm', 'ANTHROPIC_FEDERATION_RULE_ID': 'r',
               'ACTIONS_ID_TOKEN_REQUEST_TOKEN': 'secret', 'GITHUB_TOKEN': 'secret', 'HOME': '/home/runner'}
        child = sandbox.isolated_environment(env, '/tmp/h', 'http://localhost:3128', '/opt/c/bin/claude', '/tmp/h/t')
        self.assertNotIn('ACTIONS_ID_TOKEN_REQUEST_TOKEN', child)
        self.assertNotIn('GITHUB_TOKEN', child)
        self.assertEqual(child['HOME'], '/tmp/h')
        self.assertEqual(child['HTTPS_PROXY'], 'http://localhost:3128')
        self.assertEqual(child['ANTHROPIC_IDENTITY_TOKEN_FILE'], '/tmp/h/t')
        self.assertEqual(child['ANTHROPIC_MODEL'], 'm')
        self.assertTrue(child['PATH'].startswith('/opt/c/bin:'))
        command = sandbox.isolated_command('live-eval', child, '/opt/c/bin/claude', ['-p'], '/tmp/work')
        self.assertEqual(command[:8], ['sudo', '-n', '-u', 'live-eval', '--', 'env', '-i', '--chdir=/tmp/work'])
        self.assertEqual(command[-2:], ['/opt/c/bin/claude', '-p'])

    def test_shim_refuses_in_ci_without_an_isolation_user(self):
        tmp = Path(tempfile.mkdtemp())
        env = {**os.environ, 'GITHUB_ACTIONS': 'true', 'LIVE_EVAL_REAL_CLAUDE': '/bin/echo',
               'LIVE_EVAL_LEDGER': str(tmp / 'ledger.jsonl'), 'LIVE_EVAL_PROJECTS': str(tmp / 'projects')}
        env.pop('LIVE_EVAL_ISOLATION_USER', None)
        result = subprocess.run([sys.executable, str(SHIM), '-p'], input='x', capture_output=True, text=True, env=env)
        self.assertEqual(result.returncode, 75)
        self.assertIn('LIVE_EVAL_ISOLATION_USER', result.stderr)


class SkillPackageTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.repo = self.root / 'checkout'
        self.repo.mkdir()
        subprocess.run(['git', 'init', '-q', str(self.repo)], check=True)
        self.catalog = self.repo / 'skills'
        for relative, text in {
            'report-authoring/SKILL.md': 'Read references/evidence.md',
            'report-authoring/references/evidence.md': 'Use the actual stack',
            'diagramming-style/SKILL.md': 'Read references/style.md',
            'diagramming-style/references/style.md': 'Render both themes',
            'diagramming-style/scripts/render.py': '# renderer',
        }.items():
            path = self.catalog / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text)
        subprocess.run(['git', '-C', str(self.repo), 'add', 'skills'], check=True)
        (self.repo / '.env').write_text('PRIVATE')
        (self.catalog / 'report-authoring' / 'untracked-secret').write_text('PRIVATE')
        self.work = self.root / 'work'
        self.work.mkdir()

    def test_executor_receives_complete_tracked_packages_and_reference_location(self):
        argv = ['-p', '--output-format', 'stream-json', '--append-system-prompt', 'skill instructions']
        actual = sandbox.stage_skill_catalog(self.catalog, self.work, argv)
        package = self.work / '.eval-skills'
        self.assertEqual((package / 'report-authoring/references/evidence.md').read_text(),
                         'Use the actual stack')
        self.assertTrue((package / 'diagramming-style/scripts/render.py').is_file())
        self.assertFalse((package / 'report-authoring/untracked-secret').exists())
        self.assertFalse((package / '.env').exists())
        self.assertFalse((package / '.git').exists())
        prompt = actual[actual.index('--append-system-prompt') + 1]
        self.assertIn('skill instructions', prompt)
        self.assertIn(str(package), prompt)
        self.assertNotIn(str(self.repo), prompt)
        self.assertEqual(argv[-1], 'skill instructions')

    def test_isolated_executor_can_find_references_but_receives_no_checkout_location(self):
        original_run = subprocess.run
        launched = []
        home = self.root / 'home'
        home.mkdir()

        def run(command, **kwargs):
            if command[0] == 'git':
                return original_run(command, **kwargs)
            if '--append-system-prompt' in command:
                launched.append(command)
                prompt = command[command.index('--append-system-prompt') + 1]
                self.assertIn(str(self.work / '.eval-skills'), prompt)
                self.assertNotIn(str(self.repo), prompt)
                self.assertTrue((self.work / '.eval-skills/report-authoring/references/evidence.md').is_file())
                self.assertFalse(any(v.startswith('LIVE_EVAL_SKILLS_DIR=') for v in command))
            return subprocess.CompletedProcess(command, 0)

        with patch.object(sandbox.os, 'getcwd', return_value=str(self.work)), \
                patch.object(sandbox.tempfile, 'mkdtemp', return_value=str(home)), \
                patch.object(sandbox, 'run_executor', side_effect=lambda command, **kw: run(command).returncode), \
                patch.object(sandbox.subprocess, 'run', side_effect=run):
            code = sandbox.run_isolated('eval', 'http://localhost:3128', '/bin/claude',
                                        ['-p', '--output-format', 'stream-json',
                                         '--append-system-prompt', 'skill instructions'],
                                        {'LIVE_EVAL_SKILLS_DIR': str(self.catalog)}, self.root / 'sessions')
        self.assertEqual(code, 0)
        self.assertEqual(len(launched), 1)

    def test_grader_does_not_receive_skill_packages(self):
        def temporary(prefix):
            directory = self.root / prefix
            directory.mkdir()
            return str(directory)

        with patch.object(sandbox.tempfile, 'mkdtemp', side_effect=temporary), \
                patch.object(sandbox, 'stage_skill_catalog', side_effect=AssertionError('grader packages')), \
                patch.object(sandbox.subprocess, 'run', return_value=subprocess.CompletedProcess([], 0)):
            self.assertEqual(sandbox.run_isolated(
                'eval', 'http://localhost:3128', '/bin/claude', ['-p'],
                {'LIVE_EVAL_SKILLS_DIR': str(self.catalog)}, self.root / 'sessions'), 0)

    def test_package_rejects_symlinks_and_existing_destination(self):
        target = self.catalog / 'report-authoring/references/evidence.md'
        target.unlink()
        target.symlink_to(self.repo / '.env')
        with self.assertRaises(ValueError):
            sandbox.stage_skill_catalog(self.catalog, self.work, ['--append-system-prompt', 'x'])
        self.assertFalse((self.work / '.eval-skills').exists())
        target.unlink()
        target.write_text('safe')
        (self.work / '.eval-skills').mkdir()
        with self.assertRaises(FileExistsError):
            sandbox.stage_skill_catalog(self.catalog, self.work, ['--append-system-prompt', 'x'])

    def test_package_rejects_directory_symlinks_before_copying(self):
        reference = self.catalog / 'report-authoring/references'
        (reference / 'evidence.md').unlink()
        reference.rmdir()
        reference.symlink_to(self.repo, target_is_directory=True)
        with self.assertRaises(ValueError):
            sandbox.stage_skill_catalog(self.catalog, self.work, ['--append-system-prompt', 'x'])
        self.assertFalse((self.work / '.eval-skills').exists())


class ProxyTests(unittest.TestCase):
    def setUp(self):
        self.echo = socket.socket()
        self.echo.bind(('localhost', 0))
        self.echo.listen()
        threading.Thread(target=self.serve_echo, daemon=True).start()
        allowed = f'localhost:{self.echo.getsockname()[1]}'
        self.proxy = live_eval_proxy.Proxy(('localhost', 0), [allowed], log=open(os.devnull, 'w'))
        threading.Thread(target=self.proxy.serve_forever, daemon=True).start()
        self.addCleanup(self.proxy.shutdown)
        self.allowed = allowed

    def serve_echo(self):
        while True:
            try:
                conn, _ = self.echo.accept()
            except OSError:
                return
            data = conn.recv(1024)
            conn.sendall(data)
            conn.close()

    def connect(self, target):
        sock = socket.create_connection(self.proxy.server_address[:2], timeout=5)
        sock.sendall(f'CONNECT {target} HTTP/1.1\r\nHost: {target}\r\n\r\n'.encode())
        status = sock.recv(1024).split(b'\r\n')[0]
        return sock, status

    def test_allowlisted_target_is_tunnelled(self):
        sock, status = self.connect(self.allowed)
        self.assertIn(b'200', status)
        sock.sendall(b'ping')
        self.assertEqual(sock.recv(1024), b'ping')

    def test_other_targets_and_plain_requests_are_refused(self):
        _, status = self.connect('example.com:443')
        self.assertIn(b'403', status)
        sock = socket.create_connection(self.proxy.server_address[:2], timeout=5)
        sock.sendall(b'GET http://example.com/ HTTP/1.1\r\nHost: example.com\r\n\r\n')
        self.assertIn(b'405', sock.recv(1024))


if __name__ == '__main__':
    unittest.main()
