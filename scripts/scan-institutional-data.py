#!/usr/bin/env python3
"""Fail closed on disallowed publication data; never print matched values or paths."""
import argparse
import hashlib
import ipaddress
import json
import os
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys
import unicodedata
from urllib.parse import unquote, unquote_plus, urlsplit


DEFAULT_POLICY = Path(__file__).resolve().parents[1] / 'security/disclosure-policy.json'
MAX_BYTES = 2 * 1024 * 1024
PRIVATE_ROOTS = {'docs', 'logs', 'outputs', 'inputs', '.codegraph', '.venv', '.aws', '.ssh'}
EMAIL = re.compile(r'(?<![\w.+%-])[\w.+%-]+@([\w.-]+\.[A-Za-z]{2,})\b', re.ASCII)
URL = re.compile(r'https?://[^\s<>"\x27`]+', re.I)
ACCOUNT = re.compile(r'(?<![\w])\d{12}(?![\w])')
TICKET = re.compile(r'\b[A-Z][A-Z0-9]{1,9}-[1-9]\d+\b')
PUBLIC_STANDARDS = {'SHA-256', 'SHA-512', 'UTF-16', 'UTF-32', 'ISO-8601'}


def normalize(text):
    return ''.join(c for c in unicodedata.normalize('NFKC', text).casefold()
                   if c.isascii() and c.isalnum())


def reserved(host):
    return host in {'example.com', 'example.net', 'example.org', 'localhost',
                    'example.atlassian.net', 'example.grafana.net', 'example.slack.com'} or any(
        host.endswith('.' + suffix) or host == suffix
        for suffix in ('example', 'invalid', 'test', 'example.com', 'example.net', 'example.org'))


def load_policy(path):
    policy = json.loads(path.read_text())
    if policy.get('version') != 1 or not policy.get('blocked_fingerprints'):
        raise ValueError('invalid policy')
    for entry in policy['blocked_fingerprints']:
        if (type(entry['length']) is not int or not 3 <= entry['length'] <= 128
                or not re.fullmatch('[a-f0-9]{64}', entry['sha256'])):
            raise ValueError('invalid fingerprint')
    for key in ('public_url_hosts', 'public_email_domains'):
        if not isinstance(policy[key], list) or not all(
                isinstance(host, str) and re.fullmatch('[a-z0-9.-]+', host) for host in policy[key]):
            raise ValueError('invalid public domain list')
    if not isinstance(policy['public_email_addresses'], list) or not all(
            isinstance(address, str) and EMAIL.fullmatch(address)
            for address in policy['public_email_addresses']):
        raise ValueError('invalid public email list')
    if not isinstance(policy['approved_binary_sha256'], dict):
        raise ValueError('invalid binary approvals')
    for path, digests in policy['approved_binary_sha256'].items():
        if isinstance(digests, str):
            digests = [digests]
        if (not isinstance(path, str) or not isinstance(digests, list) or not digests
                or not all(isinstance(digest, str) and re.fullmatch('[a-f0-9]{64}', digest)
                           for digest in digests)):
            raise ValueError('invalid binary approvals')
        policy['approved_binary_sha256'][path] = digests
    return policy


def identifier_rules(text, policy):
    rules = set()
    canonical = normalize(text)
    for entry in policy['blocked_fingerprints']:
        width = entry['length']
        if any(hashlib.sha256(canonical[i:i + width].encode()).hexdigest() == entry['sha256']
               for i in range(len(canonical) - width + 1)):
            rules.add('institution-fingerprint')
    if any(not reserved(m.group(1).lower()) and m.group(1).lower()
           not in policy['public_email_domains'] and m.group().lower()
           not in policy['public_email_addresses'] for m in EMAIL.finditer(text)):
        rules.add('email')
    if ACCOUNT.search(text):
        rules.add('account-identifier')
    if any(match.group() not in PUBLIC_STANDARDS for match in TICKET.finditer(text)):
        rules.add('ticket-identifier')
    return rules


def content_rules(text, policy):
    rules = identifier_rules(text, policy)
    for match in URL.finditer(text):
        try:
            # Documentation sometimes quotes an escaped URL regex rather than a literal URL.
            parsed = urlsplit(re.sub(r'\\+(?=\.)', '', match.group()))
            for component in (unquote(parsed.path), unquote_plus(parsed.query),
                              unquote(parsed.fragment)):
                rules.update(identifier_rules(component, policy))
            host = parsed.hostname
            if parsed.username is not None or parsed.password is not None:
                rules.add('url-userinfo')
            if host and not reserved(host) and host not in policy['public_url_hosts']:
                rules.add('unreviewed-host')
            if host:
                try:
                    if not ipaddress.ip_address(host).is_global:
                        rules.add('private-address')
                except ValueError:
                    pass
        except ValueError:
            rules.add('invalid-url')
    return rules


class Scanner:
    def __init__(self, repository, policy):
        self.repository = repository
        self.policy = policy
        self.seen_content = set()
        self.seen_entries = set()
        self.failures = set()

    def git(self, *args, input=None):
        # `-C` alone is not authoritative: an ambient GIT_DIR/GIT_WORK_TREE wins over it, and
        # Git exports GIT_DIR pointing at the main checkout when a hook runs from a linked
        # worktree, which made `rev-list --all HEAD` fail there. Scan the repository that was
        # actually requested.
        environment = {key: value for key, value in os.environ.items()
                       if key not in ('GIT_DIR', 'GIT_WORK_TREE', 'GIT_INDEX_FILE',
                                      'GIT_OBJECT_DIRECTORY', 'GIT_COMMON_DIR')}
        return subprocess.check_output(['git', '-C', str(self.repository), *args],
                                       input=input, stderr=subprocess.DEVNULL,
                                       env=environment)

    def report(self, rule, identity):
        # Paths and refs can themselves contain sensitive values or workflow commands.
        self.failures.add((rule, hashlib.sha256(identity.encode()).hexdigest()[:16]))

    def content(self, oid, path=None):
        if oid in self.seen_content:
            return
        size = int(self.git('cat-file', '-s', oid))
        if size > MAX_BYTES:
            self.report('oversize-object', oid)
            return
        data = self.git('cat-file', '-p', oid)
        try:
            if b'\x00' in data:
                raise UnicodeError()
            text = data.decode('utf-8')
        except UnicodeError:
            approvals = self.policy['approved_binary_sha256']
            if path is None or hashlib.sha256(data).hexdigest() not in approvals.get(path, []):
                self.report('unreviewed-binary', oid)
            # Binary approvals are bound to both path and bytes; never cache an approval.
            return
        self.seen_content.add(oid)
        for rule in content_rules(text, self.policy):
            self.report(rule, oid)

    def entry(self, mode, oid, raw_path):
        identity = (mode, oid, raw_path)
        if identity in self.seen_entries:
            return
        self.seen_entries.add(identity)
        path = raw_path.decode('utf-8', errors='strict')
        parts = PurePosixPath(path).parts
        lowered = [p.casefold() for p in parts]
        if (not parts or lowered[0] in PRIVATE_ROOTS or '__pycache__' in lowered
                or any(p == '.env' or p.startswith('.env.') and p != '.env.example'
                       or p.endswith(('.pem', '.key', '.p12', '.pfx', '.pyc', '.pyo', '.bundle'))
                       for p in lowered)):
            self.report('private-path', path)
        for rule in content_rules(path, self.policy):
            self.report(rule, path)
        if mode not in {'100644', '100755'}:
            self.report('symlink-or-submodule', path)
            return
        self.content(oid, path)

    def scan(self, staged):
        if self.git('rev-parse', '--is-shallow-repository').strip() != b'false':
            raise ValueError('complete history required')
        for entry in self.git('ls-files', '--stage', '-z').split(b'\0'):
            if entry:
                header, path = entry.split(b'\t', 1)
                mode, oid, stage = header.decode().split()
                if stage != '0':
                    raise ValueError('unmerged index')
                self.entry(mode, oid, path)
        if not staged:
            commits = self.git('rev-list', '--all', 'HEAD').decode().splitlines()
            for commit in commits:
                self.content(commit)
                for entry in self.git('ls-tree', '-rz', commit).split(b'\0'):
                    if entry:
                        header, path = entry.split(b'\t', 1)
                        mode, _, oid = header.decode().split()
                        self.entry(mode, oid, path)
            # Include intermediate annotated tags even when they have no ref of their own.
            objects = self.git('rev-list', '--objects', '--all', '--no-object-names', 'HEAD')
            types = self.git('cat-file', '--batch-check=%(objectname) %(objecttype)', input=objects)
            for line in types.decode().splitlines():
                oid, kind = line.split()
                if kind == 'tag':
                    self.content(oid)
            for ref in self.git('for-each-ref', '--format=%(objectname) %(objecttype) %(refname)').decode().splitlines():
                oid, kind, name = ref.split(' ', 2)
                for rule in content_rules(name, self.policy):
                    self.report(rule, oid)
                if kind == 'tag':
                    target = self.git('rev-parse', oid + '^{}').decode().strip()
                    if self.git('cat-file', '-t', target).strip() != b'commit':
                        self.report('noncommit-ref', oid)
                elif kind != 'commit':
                    self.report('noncommit-ref', oid)
        for rule, identity in sorted(self.failures):
            print(f'Disclosure blocked: rule={rule} location={identity}; values and paths omitted')
        if not self.failures:
            print('Institutional data scan passed (values and paths are never logged).')
        return int(bool(self.failures))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repository', type=Path, default=Path('.'))
    parser.add_argument('--policy', type=Path, default=DEFAULT_POLICY)
    parser.add_argument('--staged', action='store_true', help='Index only; permits an unborn initial commit')
    args = parser.parse_args()
    try:
        return Scanner(args.repository, load_policy(args.policy)).scan(args.staged)
    except (OSError, ValueError, KeyError, TypeError, subprocess.CalledProcessError):
        print('Disclosure scan could not complete: verify Git, complete history, index, and policy; details omitted.',
              file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
