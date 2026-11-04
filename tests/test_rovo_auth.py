"""Exercise MCP destination binding through the real CLI without network or credentials."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from urllib.parse import quote


SCRIPT = Path(__file__).resolve().parents[1] / 'skills/rovo-dev-mcp/scripts/rovo-bitbucket-mcp.mjs'
OFFICIAL = 'https://mcp.atlassian.com/v2/mcp'
FIXTURE = 'synthetic-auth-fixture'
PRELOAD = r'''
import fs from 'node:fs';
import cp from 'node:child_process';
import { syncBuiltinESMExports } from 'node:module';
const fixture = 'synthetic-auth-fixture';
Object.defineProperty(process, 'platform', {value: 'darwin'});
const exists = fs.existsSync;
const read = fs.readFileSync;
fs.existsSync = (p) => String(p) === '/audit/config.json' || String(p) === '/audit/env' || exists(p);
fs.readFileSync = (p, ...args) => {
  if (String(p) !== '/audit/config.json') return read(p, ...args);
  console.log('CREDENTIAL_READ');
  return JSON.stringify({mcpServers: {test: {
    url: process.env.AUDIT_URL, headers: {Authorization: 'Bearer ' + fixture}
  }}});
};
cp.execFileSync = (command) => {
  console.log('CREDENTIAL_READ');
  if (command === '/bin/zsh') return JSON.stringify({MCP_OAUTH_TOKEN: fixture});
  if (command === '/usr/bin/security') return JSON.stringify({access_token: fixture});
  throw new Error('Unexpected subprocess in test');
};
const lstat = fs.lstatSync;
const open = fs.openSync;
let swapped = false;
function installRace(p) {
  if (!process.env.AUDIT_RACE_PATH || String(p) !== process.env.AUDIT_RACE_PATH || swapped) return;
  fs.unlinkSync(p);
  fs.symlinkSync(process.env.AUDIT_RACE_TARGET, p);
  swapped = true;
  console.log('RACE_INSTALLED');
}
fs.lstatSync = (p, ...args) => {
  const stat = lstat(p, ...args);
  installRace(p);
  return stat;
};
fs.openSync = (p, ...args) => {
  installRace(p);
  return open(p, ...args);
};
syncBuiltinESMExports();
globalThis.fetch = async (url, options) => {
  console.log('NETWORK_REACHED');
  const body = JSON.parse(options.body);
  return {
    ok: true, headers: new Headers(),
    text: async () => body.id === undefined ? '' : JSON.stringify({
      jsonrpc: '2.0', id: body.id, result: {}
    })
  };
};
'''


class RovoAuthTests(unittest.TestCase):
    def run_cli(self, url, source='bearer', extra=(), extra_env=None):
        env = {'PATH': os.environ['PATH'], 'HOME': '/audit/nonexistent', 'AUDIT_URL': url}
        env.update(extra_env or {})
        if source == 'bearer':
            env['MCP_OAUTH_TOKEN'] = FIXTURE
        elif source == 'header':
            env['ATLASSIAN_MCP_AUTH_HEADER'] = 'Bearer ' + FIXTURE
        elif source == 'basic':
            env.update(ATLASSIAN_MCP_USER='fixture-user', ATLASSIAN_MCP_TOKEN=FIXTURE)
        elif source == 'encoded-basic':
            env['ATLASSIAN_MCP_AUTH'] = FIXTURE
        config = '/audit/config.json' if source == 'config' else '/audit/nonexistent.json'
        return subprocess.run(
            ['node', '--import', 'data:text/javascript,' + quote(PRELOAD, safe=''),
             str(SCRIPT), 'resources', '--url', url, '--mcp-config', config, *extra],
            env=env, capture_output=True, text=True, timeout=10)

    def test_untrusted_destinations_are_rejected_before_credentials_or_network(self):
        for url in ('http://audit.invalid/mcp', 'https://audit.invalid/mcp',
                    'https://mcp.atlassian.com.audit.invalid/v2/mcp',
                    'https://mcp.atlassian.com/v2/mcp?tools=all&other=1',
                    'https://mcp.atlassian.com/v2/mcp#fragment',
                    'https://' + 'user:password' + '@' + 'mcp.atlassian.com/v2/mcp', 'not-a-url'):
            for source in ('bearer', 'header', 'basic', 'encoded-basic', 'config', 'keychain'):
                with self.subTest(url=url, source=source):
                    result = self.run_cli(url, source)
                    self.assertNotEqual(result.returncode, 0)
                    self.assertIn('official Atlassian v2', result.stderr)
                    self.assertNotIn('NETWORK_REACHED', result.stdout)
                    self.assertNotIn('CREDENTIAL_READ', result.stdout)
                    self.assertNotIn(FIXTURE, result.stdout + result.stderr)

    def test_invalid_destination_is_rejected_before_loading_env_file(self):
        result = self.run_cli('https://audit.invalid/mcp', 'keychain', ('--env', '/audit/env'))
        self.assertIn('official Atlassian v2', result.stderr)
        self.assertNotIn('CREDENTIAL_READ', result.stdout)
        self.assertNotIn('NETWORK_REACHED', result.stdout)

    def test_official_destinations_preserve_existing_authentication_sources(self):
        for url in (OFFICIAL, OFFICIAL + '?tools=all'):
            for source in ('bearer', 'header', 'basic', 'encoded-basic', 'config', 'keychain'):
                with self.subTest(url=url, source=source):
                    result = self.run_cli(url, source)
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertIn('NETWORK_REACHED', result.stdout)
                    self.assertNotIn(FIXTURE, result.stdout + result.stderr)

    def test_oauth_cache_cannot_follow_a_symlink_swapped_during_validation(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            cache = root / 'cache'
            entry = cache / 'mcp-remote-fixture' / 'server_tokens.json'
            entry.parent.mkdir(parents=True)
            # These are synthetic inputs; no real credential is read or stored by this test.
            data = {'access_token': FIXTURE, 'scope': 'read:bitbucket:agent-interface',
                    'expires_at': 4102444800}
            entry.write_text(json.dumps(data))
            target = root / 'outside-cache.json'
            target.write_text(json.dumps(data))
            allowed = self.run_cli(OFFICIAL, 'keychain', ('--oauth-cache', str(cache)))
            self.assertEqual(allowed.returncode, 0, allowed.stderr)
            attacked = self.run_cli(
                OFFICIAL, 'keychain', ('--oauth-cache', str(cache)),
                {'AUDIT_RACE_PATH': str(entry), 'AUDIT_RACE_TARGET': str(target)})
            self.assertIn('RACE_INSTALLED', attacked.stdout)
            self.assertNotEqual(attacked.returncode, 0)
            self.assertNotIn('NETWORK_REACHED', attacked.stdout)
            self.assertNotIn('CREDENTIAL_READ', attacked.stdout)
            self.assertNotIn(FIXTURE, attacked.stdout + attacked.stderr)


if __name__ == '__main__':
    unittest.main()
