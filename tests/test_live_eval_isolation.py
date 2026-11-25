import os
import socket
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import live_eval_proxy  # noqa: E402
import live_eval_sandbox as sandbox  # noqa: E402

SHIM = ROOT / 'scripts' / 'live-evals-runner' / 'claude'


class IsolationFlagTests(unittest.TestCase):
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
        command = sandbox.isolated_command('live-eval', child, '/opt/c/bin/claude', ['-p'])
        self.assertEqual(command[:7], ['sudo', '-n', '-u', 'live-eval', '--', 'env', '-i'])
        self.assertEqual(command[-2:], ['/opt/c/bin/claude', '-p'])

    def test_shim_refuses_in_ci_without_an_isolation_user(self):
        tmp = Path(tempfile.mkdtemp())
        env = {**os.environ, 'GITHUB_ACTIONS': 'true', 'LIVE_EVAL_REAL_CLAUDE': '/bin/echo',
               'LIVE_EVAL_LEDGER': str(tmp / 'ledger.jsonl'), 'LIVE_EVAL_PROJECTS': str(tmp / 'projects')}
        env.pop('LIVE_EVAL_ISOLATION_USER', None)
        result = subprocess.run([sys.executable, str(SHIM), '-p'], input='x', capture_output=True, text=True, env=env)
        self.assertEqual(result.returncode, 75)
        self.assertIn('LIVE_EVAL_ISOLATION_USER', result.stderr)


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
