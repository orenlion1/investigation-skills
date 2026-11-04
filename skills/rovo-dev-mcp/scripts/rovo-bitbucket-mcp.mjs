#!/usr/bin/env node
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { execFileSync } from 'node:child_process';

const HOME = process.env.HOME || os.homedir();
const DEFAULT_URL = 'https://mcp.atlassian.com/v2/mcp';
const DEFAULT_MCP_CONFIG_PATH = path.join(HOME, '.rovodev/mcp.json');
const ROVO_DEV_OAUTH_KEYCHAIN_SERVICE = 'rovodev-oauth';
const BITBUCKET_READ_SCOPE = 'read:bitbucket:agent-interface';
const READ_SCOPES = new Set([
  BITBUCKET_READ_SCOPE,
  'read:jira:agent-interface',
  'search:jira:agent-interface',
  'read:confluence:agent-interface',
  'search:confluence:agent-interface',
]);
const REQUEST_TIMEOUT_MS = 30_000;

function usage(exitCode = 0) {
  const text = [
    'Usage:',
    '  rovo-bitbucket-mcp.mjs list-tools [--env PATH] [--mcp-config PATH] [--url URL]',
    '  rovo-bitbucket-mcp.mjs resources [--env PATH] [--mcp-config PATH] [--url URL]',
    '  rovo-bitbucket-mcp.mjs discover QUERY [--env PATH] [--mcp-config PATH] [--url URL]',
    '  rovo-bitbucket-mcp.mjs execute-read --cloud CLOUD_ID --name OPERATION --inputs JSON [--env PATH] [--mcp-config PATH] [--url URL]',
    '  rovo-bitbucket-mcp.mjs call-tool TOOL_NAME JSON_ARGS [--env PATH] [--mcp-config PATH] [--url URL]',
    '  Add --oauth-cache PATH to use one valid scoped mcp-remote credential exclusively.',
    '  Optional --oauth-scope SCOPE selects a Jira/Confluence read/search grant; default: ' + BITBUCKET_READ_SCOPE,
  ].join('\n');
  console.log(text);
  process.exit(exitCode);
}

function parseArgs(argv) {
  const out = { _: [] };
  for (let i = 0; i < argv.length; i += 1) {
    const arg = argv[i];
    if (arg === '--help' || arg === '-h') usage(0);
    if (arg.startsWith('--')) {
      const key = arg.slice(2);
      const next = argv[i + 1];
      if (!next || next.startsWith('--')) out[key] = true;
      else {
        out[key] = next;
        i += 1;
      }
    } else {
      out._.push(arg);
    }
  }
  return out;
}

function shellQuote(value) {
  return "'" + String(value).replace(/'/g, "'\\''") + "'";
}

function loadEnvFile(filePath) {
  if (!filePath || !fs.existsSync(filePath)) return;
  const keys = [
    'ATLASSIAN_MCP_USER',
    'ATLASSIAN_MCP_TOKEN',
    'ATLASSIAN_MCP_AUTH',
    'ATLASSIAN_MCP_AUTH_HEADER',
    'MCP_OAUTH_TOKEN',
  ];
  const nodeCode = 'const keys=' + JSON.stringify(keys)
    + '; console.log(JSON.stringify(Object.fromEntries(keys.map(k=>[k,process.env[k]||""]))))';
  const command = 'set -a; source ' + shellQuote(filePath) + '; node -e ' + shellQuote(nodeCode);
  let env;
  try {
    const output = execFileSync('/bin/zsh', ['-lc', command], {
      encoding: 'utf8',
      stdio: ['ignore', 'pipe', 'pipe'],
    });
    env = JSON.parse(output);
  } catch {
    throw new Error('Cannot load the selected environment file; command output omitted');
  }
  for (const [key, value] of Object.entries(env)) {
    if (value && !process.env[key]) process.env[key] = value;
  }
}

function authValue() {
  if (process.env.ATLASSIAN_MCP_AUTH) return process.env.ATLASSIAN_MCP_AUTH;
  const user = process.env.ATLASSIAN_MCP_USER;
  const token = process.env.ATLASSIAN_MCP_TOKEN;
  if (user && token) return Buffer.from(user + ':' + token).toString('base64');
  return '';
}

function configuredAuthorizationHeader(filePath, url) {
  if (!filePath || !fs.existsSync(filePath)) return '';
  try {
    const config = JSON.parse(fs.readFileSync(filePath, 'utf8'));
    const servers = config?.mcpServers;
    if (!servers || typeof servers !== 'object') return '';
    for (const server of Object.values(servers)) {
      if (!server || typeof server !== 'object' || server.url !== url) continue;
      const headers = server.headers;
      if (!headers || typeof headers !== 'object') continue;
      const authorization = Object.entries(headers)
        .find(([key]) => key.toLowerCase() === 'authorization')?.[1];
      if (typeof authorization !== 'string' || !authorization.trim()) continue;
      const resolved = authorization.replace(
        /\$\{([A-Za-z_][A-Za-z0-9_]*)\}/g,
        (placeholder, key) => process.env[key] || placeholder,
      );
      if (!resolved.includes('$' + '{')) return resolved.trim();
    }
  } catch {
    // An unreadable app-owned config must not prevent other auth paths.
  }
  return '';
}

function timestampMs(value) {
  if (typeof value === 'number' || (typeof value === 'string' && /^\d+(\.\d+)?$/.test(value))) {
    const numeric = Number(value);
    return numeric < 1e12 ? numeric * 1000 : numeric;
  }
  return typeof value === 'string' ? Date.parse(value) : NaN;
}

function requireOfficialEndpoint(url) {
  if (![DEFAULT_URL, DEFAULT_URL + '?tools=all'].includes(url)) {
    throw new Error('MCP URL must be the official Atlassian v2 MCP endpoint (optional ?tools=all)');
  }
  return url;
}

function cachedOAuthToken(cachePath, url, requiredScope) {
  if (typeof cachePath !== 'string' || !cachePath.trim()) {
    throw new Error('--oauth-cache requires a cache directory path');
  }
  requireOfficialEndpoint(url);
  if (typeof fs.constants.O_NOFOLLOW !== 'number') {
    throw new Error('This runtime cannot safely open OAuth cache files without following symlinks');
  }
  const candidates = [];
  try {
    for (const directory of fs.readdirSync(cachePath, { withFileTypes: true })) {
      if (!directory.isDirectory() || !directory.name.startsWith('mcp-remote-')) continue;
      const directoryPath = path.join(cachePath, directory.name);
      for (const file of fs.readdirSync(directoryPath, { withFileTypes: true })) {
        if (!file.isFile() || !file.name.endsWith('_tokens.json')) continue;
        const filePath = path.join(directoryPath, file.name);
        let descriptor;
        try {
          // Validate and read the same open file, refusing a swapped-in symlink.
          descriptor = fs.openSync(filePath,
            fs.constants.O_RDONLY | fs.constants.O_NOFOLLOW | fs.constants.O_NONBLOCK);
          const stat = fs.fstatSync(descriptor);
          if (!stat.isFile()) continue;
          const credential = JSON.parse(fs.readFileSync(descriptor, 'utf8'));
          const scopes = typeof credential.scope === 'string' ? credential.scope.split(/\s+/) : [];
          if (!scopes.includes(requiredScope)) continue;
          if (typeof credential.access_token !== 'string' || !credential.access_token.trim()) continue;
          if (credential.token_type && credential.token_type.toLowerCase() !== 'bearer') continue;
          const expiry = timestampMs(credential.expires_at);
          if (!Number.isFinite(expiry) || expiry <= Date.now()) continue;
          candidates.push(credential.access_token);
        } catch {
          // Ignore malformed/vanished cache entries without exposing their contents.
        } finally {
          if (descriptor !== undefined) fs.closeSync(descriptor);
        }
      }
    }
  } catch {
    throw new Error('Cannot read the selected OAuth cache directory');
  }
  if (candidates.length > 1) {
    throw new Error('Ambiguous OAuth cache: more than one valid scoped credential; use a dedicated cache');
  }
  if (!candidates.length) {
    throw new Error('No unexpired OAuth credential with ' + requiredScope
      + ' in the selected cache; authenticate or refresh using mcp-remote-client');
  }
  return candidates[0];
}

function keychainOAuthToken() {
  if (process.platform !== 'darwin') return '';
  try {
    const raw = execFileSync(
      '/usr/bin/security',
      ['find-generic-password', '-s', ROVO_DEV_OAUTH_KEYCHAIN_SERVICE, '-w'],
      { encoding: 'utf8', stdio: ['ignore', 'pipe', 'ignore'] },
    ).trim();
    if (!raw) return '';
    try {
      const credential = JSON.parse(raw);
      const expiresAt = timestampMs(credential?.expires_at);
      if (Number.isFinite(expiresAt) && expiresAt <= Date.now()) return '';
      return typeof credential?.access_token === 'string' ? credential.access_token : '';
    } catch {
      return raw;
    }
  } catch {
    return '';
  }
}

function authorizationHeader({ mcpConfigPath = DEFAULT_MCP_CONFIG_PATH, url = DEFAULT_URL, oauthCache, oauthScope } = {}) {
  requireOfficialEndpoint(url);
  if (oauthScope !== undefined && oauthCache === undefined) {
    throw new Error('--oauth-scope requires --oauth-cache');
  }
  const requiredScope = oauthScope === undefined ? BITBUCKET_READ_SCOPE : oauthScope;
  if (!READ_SCOPES.has(requiredScope)) throw new Error('--oauth-scope must be a supported read/search agent-interface scope');
  if (oauthCache !== undefined) return 'Bearer ' + cachedOAuthToken(oauthCache, url, requiredScope);
  if (process.env.ATLASSIAN_MCP_AUTH_HEADER) return process.env.ATLASSIAN_MCP_AUTH_HEADER;
  if (process.env.MCP_OAUTH_TOKEN) return 'Bearer ' + process.env.MCP_OAUTH_TOKEN;
  const auth = authValue();
  if (auth) return 'Basic ' + auth;
  const configured = configuredAuthorizationHeader(mcpConfigPath, url);
  if (configured) return configured;
  const oauthToken = keychainOAuthToken();
  return oauthToken ? 'Bearer ' + oauthToken : '';
}

function parseJsonRpcText(text) {
  if (!text) return null;
  const dataLines = text.split(/\r?\n/).filter((line) => line.startsWith('data:'));
  const payload = dataLines.length ? dataLines.map((line) => line.slice(5).trim()).join('\n') : text;
  return JSON.parse(payload);
}

function classifyToolError(result) {
  const statuses = [];
  const messages = [];
  function inspect(value, depth = 0) {
    if (depth > 3) return;
    if (typeof value === 'string') {
      messages.push(value.slice(0, 32_768));
    } else if (Array.isArray(value)) {
      for (const item of value.slice(0, 10)) inspect(item, depth + 1);
    } else if (value && typeof value === 'object') {
      for (const key of ['status', 'statusCode', 'httpStatus', 'code']) {
        if (Number.isInteger(value[key])) statuses.push(value[key]);
      }
      for (const key of ['error', 'message', 'error_description', 'detail', 'details', 'errors']) {
        inspect(value[key], depth + 1);
      }
    }
  }
  inspect(result.structuredContent);
  for (const block of (Array.isArray(result.content) ? result.content : []).slice(0, 10)) {
    if (block.type !== 'text' || typeof block.text !== 'string') continue;
    const text = block.text.slice(0, 32_768);
    try { inspect(JSON.parse(text)); } catch { inspect(text); }
  }
  const message = messages.join('\n');
  const missingScope = /\binsufficient_scope\b|\b(?:missing|insufficient|lacks?|lacking)\b.{0,40}\bscopes?\b|\bscopes?\b.{0,40}\b(?:missing|insufficient|not granted)\b/i;
  const invalidQuery = /\b(?:CQL|JQL|query)\b.{0,60}\b(?:syntax|parse|parsing|invalid|malformed)\b|\b(?:invalid|malformed)\b.{0,30}\b(?:CQL|JQL|query)\b/i;
  if (missingScope.test(message)) return 'missing_scope';
  if (statuses.includes(401)) return 'authentication_failed';
  if (statuses.includes(403)) return 'access_denied';
  if (statuses.includes(429)) return 'rate_limited';
  if (statuses.some((status) => status >= 500 && status <= 599)) return 'upstream_failure';
  if (statuses.includes(400) || statuses.includes(-32602)) {
    return invalidQuery.test(message) ? 'invalid_query' : 'invalid_request';
  }
  if (/\b(?:unauthorized|invalid_token|authentication failed)\b/i.test(message)) return 'authentication_failed';
  if (/\b(?:forbidden|access denied|permission denied)\b/i.test(message)) return 'access_denied';
  if (invalidQuery.test(message)) return 'invalid_query';
  if (/\b(?:invalid_request|invalid params|invalid parameters|bad request)\b/i.test(message)) return 'invalid_request';
  if (/\b(?:rate limit|rate limited|too many requests)\b/i.test(message)) return 'rate_limited';
  return 'unknown';
}

class RovoMcpClient {
  constructor({ url, authorization }) {
    this.url = url;
    this.authorization = authorization;
    this.sessionId = null;
    this.nextId = 1;
  }

  async post(body) {
    const headers = {
      Authorization: this.authorization,
      'Content-Type': 'application/json',
      Accept: 'application/json, text/event-stream',
    };
    if (this.sessionId) headers['Mcp-Session-Id'] = this.sessionId;
    let res;
    let text;
    const signal = AbortSignal.timeout(REQUEST_TIMEOUT_MS);
    try {
      res = await fetch(this.url, {
        method: 'POST', headers, body: JSON.stringify(body), redirect: 'error', signal,
      });
      text = await res.text();
    } catch (error) {
      if (signal.aborted || error?.name === 'TimeoutError' || error?.name === 'AbortError') {
        throw new Error('MCP request timed out after 30 seconds; request details omitted');
      }
      throw new Error('MCP connection failed; request details omitted');
    }
    if (!res.ok) {
      throw new Error('MCP HTTP ' + res.status + '; response body omitted');
    }
    const responseSession = res.headers.get('mcp-session-id');
    if (responseSession && !this.sessionId) this.sessionId = responseSession;
    let response;
    try {
      response = parseJsonRpcText(text);
    } catch {
      throw new Error('Invalid MCP JSON response; response body omitted');
    }
    if (response?.error) {
      const code = Number.isInteger(response.error.code) ? ' (' + response.error.code + ')' : '';
      throw new Error('MCP protocol error' + code + '; response body omitted');
    }
    if (body.id !== undefined && (!response || response.jsonrpc !== '2.0'
        || response.id !== body.id || !Object.hasOwn(response, 'result'))) {
      throw new Error('Invalid MCP response envelope; response body omitted');
    }
    return response;
  }

  async initialize() {
    await this.post({
      jsonrpc: '2.0',
      id: this.nextId++,
      method: 'initialize',
      params: {
        protocolVersion: '2025-03-26',
        capabilities: {},
        clientInfo: { name: 'rovo-bitbucket-mcp', version: '2.0.0' },
      },
    });
    await this.post({ jsonrpc: '2.0', method: 'notifications/initialized', params: {} });
  }

  async listTools() {
    const tools = [];
    let cursor;
    do {
      const response = await this.post({
        jsonrpc: '2.0',
        id: this.nextId++,
        method: 'tools/list',
        params: cursor ? { cursor } : {},
      });
      tools.push(...(response?.result?.tools || []));
      cursor = response?.result?.nextCursor || null;
    } while (cursor);
    return tools;
  }

  async callTool(name, args) {
    const response = await this.post({
      jsonrpc: '2.0',
      id: this.nextId++,
      method: 'tools/call',
      params: { name, arguments: args },
    });
    const result = response?.result;
    if (result?.isError) {
      throw new Error('MCP tool ' + name + ' failed [' + classifyToolError(result) + ']; response body omitted');
    }
    const text = result?.content?.find((item) => item.type === 'text')?.text;
    if (!text) return result;
    try {
      return JSON.parse(text);
    } catch {
      return text;
    }
  }
}

function printJson(value) {
  console.log(JSON.stringify(value, null, 2));
}

function requireArg(args, index, label) {
  const value = args._[index];
  if (!value) throw new Error('Missing ' + label);
  return value;
}

function requireFlag(args, key) {
  if (!args[key]) throw new Error('Missing --' + key);
  return args[key];
}

function parseInputs(value) {
  let inputs;
  try {
    inputs = JSON.parse(value);
  } catch {
    throw new Error('--inputs must be valid JSON');
  }
  if (!inputs || typeof inputs !== 'object' || Array.isArray(inputs)) {
    throw new Error('--inputs must be a JSON object');
  }
  return inputs;
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  const command = args._[0];
  if (!command) usage(1);

  // Reject destinations before sourcing an environment file or reading credentials.
  const url = requireOfficialEndpoint(args.url || DEFAULT_URL);
  if (args['oauth-cache'] === undefined) loadEnvFile(args.env);
  const authorization = authorizationHeader({
    mcpConfigPath: args['mcp-config'] || DEFAULT_MCP_CONFIG_PATH,
    url,
    oauthCache: args['oauth-cache'],
    oauthScope: args['oauth-scope'],
  });
  if (!authorization) {
    throw new Error('Atlassian MCP auth is not set; provide MCP_OAUTH_TOKEN, ATLASSIAN_MCP_AUTH_HEADER, ATLASSIAN_MCP_AUTH, or ATLASSIAN_MCP_USER/ATLASSIAN_MCP_TOKEN via --env, configure an Authorization header in the Rovo Dev MCP config, or authenticate Rovo Dev');
  }

  const client = new RovoMcpClient({ url, authorization });
  await client.initialize();

  const requestedTool = command === 'call-tool'
    ? args._[1]
    : command === 'execute-read' ? 'executeRead' : '';
  if (!['list-tools', 'resources'].includes(command)
      && requestedTool !== 'getAccessibleAtlassianResources') {
    await client.callTool('getAccessibleAtlassianResources', {});
  }

  if (command === 'list-tools') {
    const tools = await client.listTools();
    printJson(tools.map((tool) => ({
      name: tool.name,
      description: tool.description,
      inputSchema: tool.inputSchema,
    })));
    return;
  }

  if (command === 'resources') {
    printJson(await client.callTool('getAccessibleAtlassianResources', {}));
    return;
  }

  if (command === 'discover') {
    printJson(await client.callTool('discover', {
      query: requireArg(args, 1, 'QUERY'),
    }));
    return;
  }

  if (command === 'execute-read') {
    printJson(await client.callTool('executeRead', {
      cloudId: requireFlag(args, 'cloud'),
      name: requireFlag(args, 'name'),
      inputs: parseInputs(requireFlag(args, 'inputs')),
    }));
    return;
  }

  if (command === 'call-tool') {
    const toolName = requireArg(args, 1, 'TOOL_NAME');
    const jsonArgs = requireArg(args, 2, 'JSON_ARGS');
    let parsedArgs;
    try {
      parsedArgs = JSON.parse(jsonArgs);
    } catch {
      throw new Error('JSON_ARGS must be valid JSON');
    }
    printJson(await client.callTool(toolName, parsedArgs));
    return;
  }

  throw new Error('Unknown command: ' + command);
}

main().catch((error) => {
  const message = String(error?.message || error)
    .replace(/Basic\s+[A-Za-z0-9+/=._:-]+/g, 'Basic [REDACTED]')
    .replace(/Bearer\s+[A-Za-z0-9+/=._:-]+/g, 'Bearer [REDACTED]')
    .replace(/Mcp-Session-Id:\s*[^\s]+/gi, 'Mcp-Session-Id: [REDACTED]');
  console.error(message);
  process.exit(1);
});
