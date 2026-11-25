"""Meter and cap the model spend of the Live Behavioral Evals workflow.

Claude Code records each session's cumulative cost (`totalCostUSD`, at list price) in its
session file under ~/.claude/projects. The runner shim in scripts/live-evals-runner/claude
wraps every model call the eval harness makes, reads that cost after the call, appends it
to a ledger, and refuses further calls once the job's share of the monthly budget is spent.
The `month` command sums the spend artifacts of this month's earlier runs; the `summary`
command turns a ledger into the spend artifact and a job summary.

This is a guard against accidental overspend, not against someone who can delete
artifacts or edit the workflow; pair it with a spend limit on the API key's workspace.
"""
import argparse
import datetime
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path

SPEND_ARTIFACT_PREFIX = 'live-evals-spend-'
# GitHub's variables for minting OIDC tokens. The shim uses them; the model under test never
# receives them, so it cannot mint tokens of its own.
OIDC_REQUEST_VARIABLES = ('ACTIONS_ID_TOKEN_REQUEST_URL', 'ACTIONS_ID_TOKEN_REQUEST_TOKEN')
REFUSED_EXIT = 75


def snapshot(projects):
    """Map each session file to its modification time."""
    if not projects.is_dir():
        return {}
    return {p: p.stat().st_mtime_ns for p in projects.glob('*/*.jsonl')}


def session_cost(path):
    """Return (cost, models) for one session file; cost is None when none was recorded."""
    cost, models = None, set()
    with open(path, encoding='utf-8') as handle:
        for line in handle:
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue
            value = record.get('totalCostUSD')
            if isinstance(value, (int, float)):
                cost = value if cost is None else max(cost, value)
            message = record.get('message')
            if record.get('type') == 'assistant' and isinstance(message, dict) and message.get('model'):
                models.add(message['model'])
    return cost, sorted(models)


def read_ledger(ledger):
    entries = []
    if ledger.is_file():
        for line in ledger.read_text(encoding='utf-8').splitlines():
            if line.strip():
                entries.append(json.loads(line))
    return entries


def totals(entries):
    known = [e['cost_usd'] for e in entries if isinstance(e.get('cost_usd'), (int, float))]
    return {'calls': len(entries), 'total_usd': round(sum(known), 6), 'max_call_usd': max(known, default=0.0),
            'unknown_cost_calls': len(entries) - len(known)}


def refusal(entries, budget):
    """Return a reason to refuse the next call, or None."""
    t = totals(entries)
    if t['unknown_cost_calls']:
        return 'a previous call recorded no cost, so spend cannot be tracked'
    if budget is not None and t['total_usd'] + t['max_call_usd'] > budget:
        return (f"this job has spent ${t['total_usd']:.2f} of its ${budget:.2f} share of the monthly "
                f"live-eval budget, and the next call could cost about ${t['max_call_usd']:.2f}")
    return None


def mint_identity_token(audience, env):
    """Request a fresh GitHub Actions OIDC token for the audience."""
    url = env['ACTIONS_ID_TOKEN_REQUEST_URL']
    separator = '&' if '?' in url else '?'
    request = urllib.request.Request(url + separator + urllib.parse.urlencode({'audience': audience}))
    request.add_header('Authorization', 'Bearer ' + env['ACTIONS_ID_TOKEN_REQUEST_TOKEN'])
    with urllib.request.urlopen(request, timeout=30) as response:
        value = json.loads(response.read()).get('value')
    if not value:
        raise RuntimeError('GitHub returned no OIDC token')
    return value


def child_environment(env, token_file=None):
    """The environment for the real claude: no token-minting variables, plus the token file."""
    child = {k: v for k, v in env.items() if k not in OIDC_REQUEST_VARIABLES}
    if token_file is not None:
        child['ANTHROPIC_IDENTITY_TOKEN_FILE'] = str(token_file)
    return child


def run_metered(argv, real, ledger, projects, budget, stdin=None, env=None):
    """Run the real claude, record what the call cost, and return its exit code.

    When LIVE_EVAL_OIDC_AUDIENCE is set inside GitHub Actions, each call gets a freshly minted
    OIDC token in a private file that is deleted afterwards: tokens last minutes and are
    exchanged once, so one token per call.
    """
    env = dict(os.environ if env is None else env)
    reason = refusal(read_ledger(ledger), budget)
    if reason:
        print(f'live-eval budget reached: {reason}; no model call was made.', file=sys.stderr)
        return REFUSED_EXIT
    audience = env.get('LIVE_EVAL_OIDC_AUDIENCE')
    token_dir = None
    token_file = None
    if audience:
        if not all(env.get(name) for name in OIDC_REQUEST_VARIABLES):
            print('live-eval OIDC: the job has no id-token: write permission; no model call was made.',
                  file=sys.stderr)
            return REFUSED_EXIT
        token_dir = tempfile.mkdtemp(prefix='live-eval-oidc-')
        token_file = Path(token_dir) / 'identity-token'
        fd = os.open(token_file, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, 'w', encoding='utf-8') as handle:
            handle.write(mint_identity_token(audience, env))
    before = snapshot(projects)
    started = datetime.datetime.now(datetime.timezone.utc).isoformat()
    try:
        code = subprocess.run([real, *argv], stdin=stdin, check=False,
                              env=child_environment(env, token_file)).returncode
    finally:
        if token_dir:
            shutil.rmtree(token_dir, ignore_errors=True)
    after = snapshot(projects)
    touched = [p for p, mtime in after.items() if before.get(p) != mtime]
    cost, models = None, set()
    for path in touched:
        value, used = session_cost(path)
        models.update(used)
        if value is not None:
            cost = (cost or 0.0) + value
    role = 'executor' if '--output-format' in argv else 'grader'
    entry = {'started': started, 'role': role, 'exit_code': code, 'cost_usd': cost, 'models': sorted(models),
             'sessions': [p.name for p in touched]}
    ledger.parent.mkdir(parents=True, exist_ok=True)
    with open(ledger, 'a', encoding='utf-8') as handle:
        handle.write(json.dumps(entry) + '\n')
    return code


def month_start(now):
    return now.astimezone(datetime.timezone.utc).strftime('%Y-%m-01')


def sum_spend_zips(blobs):
    """Sum total_usd across spend artifacts (zip bytes), skipping unreadable members."""
    total, files = 0.0, 0
    for blob in blobs:
        with zipfile.ZipFile(io.BytesIO(blob)) as archive:
            for name in archive.namelist():
                if name.endswith('.json'):
                    data = json.loads(archive.read(name))
                    total += float(data.get('total_usd') or 0)
                    files += 1
    return round(total, 6), files


def github(path, token, raw=False):
    request = urllib.request.Request('https://api.github.com/' + path.lstrip('/'))
    request.add_header('Accept', 'application/vnd.github+json')
    request.add_header('X-GitHub-Api-Version', '2022-11-28')
    # Not forwarded on the redirect to the pre-signed artifact download URL.
    request.add_unredirected_header('Authorization', 'Bearer ' + token)
    with urllib.request.urlopen(request, timeout=60) as response:
        body = response.read()
    return body if raw else json.loads(body)


def month_spend(repository, workflow, current_run, token, now):
    created = urllib.parse.quote('>=' + month_start(now))
    blobs, page = [], 1
    while True:
        runs = github(f'repos/{repository}/actions/workflows/{workflow}/runs?created={created}&per_page=100&page={page}', token)
        for run in runs['workflow_runs']:
            if str(run['id']) == str(current_run):
                continue
            artifacts = github(f"repos/{repository}/actions/runs/{run['id']}/artifacts?per_page=100", token)
            for artifact in artifacts['artifacts']:
                if artifact['name'].startswith(SPEND_ARTIFACT_PREFIX):
                    if artifact.get('expired'):
                        raise SystemExit(f"spend artifact {artifact['name']} expired; month-to-date spend is unknown")
                    blobs.append(github(f"repos/{repository}/actions/artifacts/{artifact['id']}/zip", token, raw=True))
        if len(runs['workflow_runs']) < 100:
            break
        page += 1
    return sum_spend_zips(blobs)


def allot(remaining, evals):
    """Split the remaining budget across skills in proportion to their eval counts."""
    total = sum(max(int(n), 0) for n in evals.values())
    if total <= 0:
        return {skill: 0.0 for skill in evals}
    return {skill: round(max(remaining, 0) * max(int(n), 0) / total, 4) for skill, n in evals.items()}


def output(**values):
    target = os.environ.get('GITHUB_OUTPUT')
    lines = ''.join(f'{k}={v}\n' for k, v in values.items())
    if target:
        with open(target, 'a', encoding='utf-8') as handle:
            handle.write(lines)
    print(lines, end='')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest='command', required=True)
    m = sub.add_parser('month', help='check the monthly budget before a run')
    m.add_argument('--budget', type=float, required=True)
    m.add_argument('--evals', required=True,
                   help='JSON object mapping each skill in this run to its eval count')
    m.add_argument('--repository', required=True)
    m.add_argument('--workflow', required=True)
    m.add_argument('--run-id', required=True)
    s = sub.add_parser('summary', help='write the spend artifact and a job summary from a ledger')
    s.add_argument('--ledger', type=Path, required=True)
    s.add_argument('--output', type=Path, required=True)
    s.add_argument('--skill', required=True)
    s.add_argument('--model', required=True)
    s.add_argument('--run-id', required=True)
    args = parser.parse_args(argv)
    now = datetime.datetime.now(datetime.timezone.utc)
    if args.command == 'month':
        token = os.environ.get('GITHUB_TOKEN')
        if not token:
            raise SystemExit('GITHUB_TOKEN is required to read earlier spend')
        spent, files = month_spend(args.repository, args.workflow, args.run_id, token, now)
        remaining = round(args.budget - spent, 6)
        shares = allot(remaining, json.loads(args.evals))
        output(spent=f'{spent:.4f}', remaining=f'{remaining:.4f}', artifacts=files,
               shares=json.dumps(shares, separators=(',', ':')))
        if remaining <= 0:
            print(f'::error::Live evals are paused: ${spent:.2f} of the ${args.budget:.2f} budget for '
                  f'{now:%B %Y} is spent. They resume on the first of next month (UTC).')
            return 1
        return 0
    entries = read_ledger(args.ledger)
    t = totals(entries)
    record = {'run_id': args.run_id, 'skill': args.skill, 'model': args.model, 'month': f'{now:%Y-%m}', **t,
              'by_role': {role: round(sum(e['cost_usd'] or 0 for e in entries if e['role'] == role), 6)
                          for role in ('executor', 'grader')}}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(record, indent=1) + '\n', encoding='utf-8')
    summary = (f"### Live eval spend: {args.skill}\n\n| Calls | Executor | Grader | Total | Unknown-cost calls |\n"
               f"|---:|---:|---:|---:|---:|\n| {t['calls']} | ${record['by_role']['executor']:.4f} | "
               f"${record['by_role']['grader']:.4f} | ${t['total_usd']:.4f} | {t['unknown_cost_calls']} |\n\n"
               'Costs are Claude Code list-price figures from its session files.\n')
    target = os.environ.get('GITHUB_STEP_SUMMARY')
    if target:
        with open(target, 'a', encoding='utf-8') as handle:
            handle.write(summary)
    print(summary)
    return 0


if __name__ == '__main__':
    sys.exit(main())
