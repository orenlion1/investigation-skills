"""Run each live-eval model call as an isolated, unprivileged user (CI only).

The workflow creates the user, closes the runner's home directory to it, and lets it reach
only the allowlist proxy (scripts/live_eval_proxy.py) through iptables. For every call this
module gives that user a fresh home directory and a clean environment, runs the real claude
there, then stops anything the call left running, copies its session files back for spend
metering, and returns the workspace to the runner. `selftest` proves the isolation holds
before any model call is made.
"""
import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

# Variables the isolated call may receive from the job; nothing else passes through.
PASSTHROUGH = ('ANTHROPIC_FEDERATION_RULE_ID', 'ANTHROPIC_ORGANIZATION_ID', 'ANTHROPIC_SERVICE_ACCOUNT_ID',
               'ANTHROPIC_WORKSPACE_ID', 'ANTHROPIC_MODEL', 'LANG')
QUIET = {'CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC': '1', 'DISABLE_TELEMETRY': '1',
         'DISABLE_ERROR_REPORTING': '1', 'DISABLE_AUTOUPDATER': '1'}


def isolation_flags(argv):
    """Extra CLI flags: executors lose web tools and MCP servers; the grader gets no tools."""
    if '--output-format' in argv:
        return ['--strict-mcp-config', '--disallowedTools', 'WebFetch', 'WebSearch']
    return ['--strict-mcp-config', '--tools', '']


def isolated_environment(env, home, proxy, real, token_file=None):
    child = {k: env[k] for k in PASSTHROUGH if env.get(k)}
    node = shutil.which('node', path=env.get('PATH'))
    path = [str(Path(real).parent)] + ([str(Path(node).parent)] if node else []) + ['/usr/local/bin', '/usr/bin', '/bin']
    child.update(QUIET, HOME=str(home), PATH=':'.join(dict.fromkeys(path)), HTTPS_PROXY=proxy, HTTP_PROXY=proxy,
                 https_proxy=proxy, http_proxy=proxy, NO_PROXY='', no_proxy='')
    if token_file is not None:
        child['ANTHROPIC_IDENTITY_TOKEN_FILE'] = str(token_file)
    return child


def isolated_command(user, child_env, real, argv, workdir):
    # The eval user owns the working directory and the runner cannot enter it, so the change of
    # directory happens on the eval user's side (GNU env --chdir), not in the runner's process.
    return ['sudo', '-n', '-u', user, '--', 'env', '-i', f'--chdir={workdir}',
            *(f'{k}={v}' for k, v in sorted(child_env.items())), real, *argv]


def sudo(*args):
    subprocess.run(['sudo', '-n', *args], check=True)


def stage_skill_catalog(catalog, work, argv):
    """Give an executor tracked skill packages, never the checkout, cases or local files."""
    catalog = Path(catalog)
    if catalog.is_symlink() or not catalog.is_dir():
        raise ValueError('live-eval skill catalog must be a real directory')
    root = Path(subprocess.check_output(
        ['git', '-C', str(catalog), 'rev-parse', '--show-toplevel'], text=True).strip()).resolve()
    catalog = catalog.resolve()
    relative = catalog.relative_to(root)
    if relative.as_posix() != 'skills':
        raise ValueError('live-eval catalog must be the repository skills directory')
    tracked = subprocess.check_output(
        ['git', '-C', str(root), 'ls-files', '-z', '--', str(relative)], text=True)
    sources = [root / name for name in tracked.split('\0') if name]
    if not sources:
        raise ValueError('live-eval catalog has no tracked package files')
    # Validate the entire input before creating anything; a replaced directory can also leak files.
    for source in sources:
        source.relative_to(catalog)
        if not source.is_file() or any(p.is_symlink() for p in (source, *source.parents)
                                       if p == catalog or catalog in p.parents):
            raise ValueError('live-eval skill packages cannot contain symlinks or missing files')
    args = list(argv)
    prompt = args.index('--append-system-prompt') + 1
    destination = Path(work) / '.eval-skills'
    destination.mkdir()
    for source in sources:
        target = destination / source.relative_to(catalog)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
    args[prompt] += (f'\n\nComplete skill packages are available at {destination}/<skill-name>/. '
                     'Resolve each relative reference from its owning SKILL.md directory; '
                     'read linked references and bundled scripts/assets as needed. '
                     'The source checkout and eval answers are not available.')
    return args


def run_isolated(user, proxy, real, argv, env, projects, token=None, stdin=None):
    """Run one call as `user` and return its exit code."""
    executor = '--output-format' in argv
    home = Path(tempfile.mkdtemp(prefix='live-eval-home-'))
    work = Path(os.getcwd()) if executor else Path(tempfile.mkdtemp(prefix='live-eval-grader-'))
    token_file = None
    if token is not None:
        token_file = home / 'identity-token'
        fd = os.open(token_file, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, 'w', encoding='utf-8') as handle:
            handle.write(token)
    (home / '.claude' / 'projects').mkdir(parents=True)
    owner = f'{os.getuid()}:{os.getgid()}'
    try:
        if executor:
            if not env.get('LIVE_EVAL_SKILLS_DIR'):
                raise ValueError('LIVE_EVAL_SKILLS_DIR is required for isolated executors')
            argv = stage_skill_catalog(env['LIVE_EVAL_SKILLS_DIR'], work, argv)
        sudo('chown', '-R', user, str(home), str(work))
        command = isolated_command(user, isolated_environment(env, home, proxy, real, token_file), real, argv, work)
        return subprocess.run(command, stdin=stdin, check=False).returncode
    finally:
        subprocess.run(['sudo', '-n', 'pkill', '-KILL', '-u', user], check=False)
        projects.mkdir(parents=True, exist_ok=True)
        subprocess.run(['sudo', '-n', 'cp', '-a', f'{home}/.claude/projects/.', str(projects)], check=False)
        subprocess.run(['sudo', '-n', 'chown', '-R', owner, str(projects), str(work)], check=False)
        subprocess.run(['sudo', '-n', 'rm', '-rf', str(home)], check=False)
        if not executor:
            subprocess.run(['sudo', '-n', 'rm', '-rf', str(work)], check=False)


def selftest(user, proxy, private_path, real):
    """Return the list of isolation failures (empty when isolation holds)."""
    def as_user(*command):
        return subprocess.run(['sudo', '-n', '-u', user, '--', 'env', '-i', 'PATH=/usr/local/bin:/usr/bin:/bin',
                               'HOME=/tmp', *command], capture_output=True, text=True, timeout=60)
    failures = []
    if as_user('cat', private_path).returncode == 0:
        failures.append(f'the eval user can read {private_path}')
    if as_user('curl', '-sS', '-m', '10', '-o', '/dev/null', 'https://example.com').returncode == 0:
        failures.append('the eval user reached example.com directly')
    if as_user('curl', '-sS', '-m', '10', '-o', '/dev/null', '-x', proxy, 'https://example.com').returncode == 0:
        failures.append('the proxy tunnelled example.com')
    if as_user('curl', '-sS', '-m', '20', '-o', '/dev/null', '-x', proxy, 'https://api.anthropic.com/').returncode != 0:
        failures.append('the eval user cannot reach api.anthropic.com through the proxy')
    if as_user(real, '--version').returncode != 0:
        failures.append(f'the eval user cannot run {real}')
    return failures


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest='command', required=True)
    s = sub.add_parser('selftest', help='prove the isolation holds before any model call')
    s.add_argument('--user', required=True)
    s.add_argument('--proxy', required=True)
    s.add_argument('--private-path', required=True, help='a file in the runner checkout the eval user must not read')
    s.add_argument('--claude', required=True)
    args = parser.parse_args(argv)
    failures = selftest(args.user, args.proxy, args.private_path, args.claude)
    for failure in failures:
        print(f'::error::Live eval isolation failed: {failure}')
    if not failures:
        print('Live eval isolation holds: no checkout access, no direct network, proxy allows only the Anthropic API.')
    return 1 if failures else 0


if __name__ == '__main__':
    sys.exit(main())
