#!/usr/bin/env python3
"""Run the skill ownership checks for one repository.

One entry point for a repository that carries this skill: `ownership.py check` runs every
check in a fixed order and prints one line per check. A check whose optional policy is
absent reports `not configured`; a policy that is present but unreadable or malformed
fails closed. The root contract is the principle itself, so it is always required.
A downstream repository must also carry a pin that matches its copy of this skill; the
upstream repository runs with `--upstream`, where VERSION agreement takes the pin's place.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import audit as audit_module  # noqa: E402
import delegation_contract  # noqa: E402
import docs_contract  # noqa: E402
import guardrails  # noqa: E402
import root_contract  # noqa: E402
import skill_validation  # noqa: E402
import sync as sync_module  # noqa: E402
import vendored_imports  # noqa: E402
import versioning  # noqa: E402

ROOT_POLICY = 'policy/root-contract.json'
NOT_CONFIGURED = 'not configured'


def check_root_contract(repository: Path) -> tuple[list[str], str]:
    policy = root_contract.load_policy(repository / ROOT_POLICY)
    errors = root_contract.check(repository, policy)
    return errors, f'{len(policy["files"])} root file(s), clause, sections and routing verified'


def check_docs_contract(repository: Path) -> tuple[list[str], str]:
    docs = docs_contract.load_docs_policy(repository / ROOT_POLICY)
    if docs is None:
        return [], NOT_CONFIGURED
    root_file = json.loads((repository / ROOT_POLICY).read_text(encoding='utf-8'))['files'][0]
    return docs_contract.check(repository, docs, root_file), 'diagram sets and README verified'


def check_delegation_contract(repository: Path) -> tuple[list[str], str]:
    policy = repository / delegation_contract.POLICY_RELATIVE
    if not policy.exists():
        return [], NOT_CONFIGURED
    report = delegation_contract.audit(repository, policy)
    errors = [f'{failure.rule} {failure.message}' for failure in report.failures]
    return errors, (f'{report.concepts_checked} concept(s) across '
                    f'{report.callers_checked} caller(s) verified')


def check_vendored_imports(repository: Path) -> tuple[list[str], str]:
    if not (repository / 'policy/vendored-imports.json').exists():
        return [], NOT_CONFIGURED
    return [], f'{vendored_imports.check(repository)} imported skill(s) verified'


def check_skill_validation(repository: Path) -> tuple[list[str], str]:
    errors, count = skill_validation.check(repository, skills_dir_of(repository))
    return errors, f'{count} skill package(s) valid'


def skills_dir_of(repository: Path) -> str:
    policy = repository / ROOT_POLICY
    if policy.is_file():
        return json.loads(policy.read_text(encoding='utf-8')).get('skills_dir', 'skills')
    return 'skills'


def check_size_ratchet(repository: Path) -> tuple[list[str], str]:
    errors = guardrails.ratchet_errors(repository, skills_dir_of(repository))
    if errors is None:
        return [], NOT_CONFIGURED
    return errors, 'no SKILL.md grew past its recorded baseline'


def check_duplication(repository: Path) -> tuple[list[str], str]:
    allowed = ()
    delegation = repository / delegation_contract.POLICY_RELATIVE
    if delegation.is_file():
        # The delegation contract requires its sentinel verbatim in every caller.
        sentinel = json.loads(delegation.read_text(encoding='utf-8')).get(
            'required_caller_sentinel')
        allowed = (sentinel,) if isinstance(sentinel, str) else ()
    errors = guardrails.duplication_errors(repository, skills_dir_of(repository), allowed)
    return errors, 'no rule is stated in both a SKILL.md and its references'


def check_links(repository: Path) -> tuple[list[str], str]:
    return (guardrails.link_errors(repository, skills_dir_of(repository)),
            'relative links and heading anchors resolve')


def check_description_shape(repository: Path) -> tuple[list[str], str]:
    return (guardrails.description_errors(repository, skills_dir_of(repository)),
            'descriptions are one quoted line with a trigger')


def check_frontmatter(repository: Path) -> tuple[list[str], str]:
    path = repository / versioning.CARRIED_SKILL / 'SKILL.md'
    return versioning.frontmatter_errors(path), 'metadata.version is a single quoted SemVer'


def check_pin(repository: Path) -> tuple[list[str], str]:
    return versioning.pin_errors(repository), 'pin matches the carried copy'


def check_version_agreement(repository: Path) -> tuple[list[str], str]:
    errors, count = versioning.agreement_errors(repository)
    return errors, f'VERSION agrees with {count} skill(s)'


CHECKS = (
    ('root-contract', check_root_contract),
    ('docs-contract', check_docs_contract),
    ('delegation-contract', check_delegation_contract),
    ('vendored-imports', check_vendored_imports),
    ('skill-validation', check_skill_validation),
    ('frontmatter', check_frontmatter),
    ('size-ratchet', check_size_ratchet),
    ('duplication', check_duplication),
    ('links', check_links),
    ('description-shape', check_description_shape),
)
DOWNSTREAM_CHECKS = CHECKS + (('pin', check_pin),)
UPSTREAM_CHECKS = CHECKS + (('version-agreement', check_version_agreement),)


def run_checks(repository: Path, checks=DOWNSTREAM_CHECKS) -> int:
    """Run every check; never stop at the first failure, so one run shows the whole state."""
    failed = 0
    for name, function in checks:
        try:
            errors, summary = function(repository)
        except delegation_contract.PolicyError as error:
            errors, summary = [str(error)], ''
        except (OSError, ValueError, KeyError, TypeError) as error:
            errors, summary = [f'{type(error).__name__}: {error}'], ''
        for error in errors:
            print(f'error: {name}: {error}', file=sys.stderr)
        if errors:
            failed += 1
            print(f'{name}: FAILED ({len(errors)} error(s))')
        elif summary == NOT_CONFIGURED:
            print(f'{name}: not configured')
        else:
            print(f'{name}: {summary} — PASSED')
    return 1 if failed else 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    check = commands.add_parser('check', help='run every ownership check')
    check.add_argument('--repository', type=Path, default=Path.cwd())
    check.add_argument('--upstream', action='store_true',
                       help='this is the skill-ownership repository itself: require VERSION '
                            'agreement instead of a downstream pin')
    audit = commands.add_parser(
        'audit', help='read-only report: section classes, routing gaps, size and links')
    audit.add_argument('--repository', type=Path, default=Path.cwd())
    audit.add_argument('--format', choices=('markdown', 'json'), default='markdown')
    sync = commands.add_parser(
        'sync', help='report whether the carried copy is behind upstream; --apply updates it')
    sync.add_argument('--repository', type=Path, default=Path.cwd())
    sync.add_argument('--upstream', help='where to read releases from (URL or path); '
                                         'defaults to the pin\'s upstream_repository')
    sync.add_argument('--upstream-url', help='https URL to record in a new pin at first '
                                             'adoption, when --upstream is not one')
    sync.add_argument('--apply', action='store_true',
                      help='replace the carried copy and update the pin together')
    sync.add_argument('--to', help='release to apply (default: the latest)')
    sync.add_argument('--format', choices=('text', 'json'), default='text')
    ratchet = commands.add_parser('ratchet', help='show or record the SKILL.md size baseline')
    ratchet.add_argument('--repository', type=Path, default=Path.cwd())
    ratchet.add_argument('--record', action='store_true',
                         help='write current sizes as the new baseline (a reviewable change)')
    preserve = commands.add_parser(
        'preserve', help='fail when a rewrite of a skill lost a protected token')
    preserve.add_argument('--repository', type=Path, default=Path.cwd())
    preserve.add_argument('--before', type=Path, help='skill directory before the rewrite')
    preserve.add_argument('--after', type=Path, help='skill directory after the rewrite')
    preserve.add_argument('--base', help='Git revision holding the version before the rewrite')
    preserve.add_argument('--skill', help='skill path for --base, for example skills/alpha')
    preserve.add_argument('--removals', type=Path, help='declared removals (token-removals/v1)')
    args = parser.parse_args(argv)
    repository = args.repository.resolve()
    if args.command == 'check':
        return run_checks(repository, UPSTREAM_CHECKS if args.upstream else DOWNSTREAM_CHECKS)
    try:
        if args.command == 'audit':
            report = audit_module.audit(repository)
            print(json.dumps(report, indent=2) if args.format == 'json'
                  else audit_module.render_markdown(report), end='\n' if args.format == 'json' else '')
            return 0
        if args.command == 'sync':
            return run_sync(repository, args, parser)
        if args.command == 'ratchet':
            return run_ratchet(repository, args.record)
        return run_preserve(repository, args, parser)
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        print(f'error: {args.command}: {error}', file=sys.stderr)
        return 1


def run_sync(repository: Path, args, parser) -> int:
    if not args.apply:
        if args.to or args.upstream_url:
            parser.error('--to and --upstream-url apply only with --apply')
        result = sync_module.report(repository, args.upstream)
        print(json.dumps(result, indent=2) if args.format == 'json'
              else sync_module.render(result), end='\n' if args.format == 'json' else '')
        return sync_module.exit_code(result)
    result = sync_module.apply(repository, args.upstream, args.to, args.upstream_url)
    if args.format == 'json':
        print(json.dumps(result, indent=2))
        return 0
    if not result['changed']:
        print(f'sync: already at {result["to"]}; nothing changed')
        return 0
    print(f'sync: {result["from"] or "no copy"} -> {result["to"]}; '
          f'{len(result["changed"])} file(s) changed, pin updated')
    for name in result['changed']:
        print(f'  {name}')
    for name in result['preserved']:
        print(f'  preserved local adaptation: {name}')
    print('Review the working tree and deliver it through this repository\'s normal path.')
    return 0


def run_ratchet(repository: Path, record: bool) -> int:
    skills_dir = skills_dir_of(repository)
    if record:
        sizes = guardrails.record_baseline(repository, skills_dir)
        print(f'size-ratchet: recorded {len(sizes)} skill(s), {sum(sizes.values())} bytes total')
        return 0
    errors = guardrails.ratchet_errors(repository, skills_dir)
    if errors is None:
        print('size-ratchet: not configured; run ratchet --record to start')
        return 0
    for error in errors:
        print(f'error: size-ratchet: {error}', file=sys.stderr)
    for skill, size in guardrails.current_sizes(repository, skills_dir).items():
        print(f'{size:>8}  {skill}')
    return 1 if errors else 0


def run_preserve(repository: Path, args, parser) -> int:
    if args.base and args.skill and not (args.before or args.after):
        errors = guardrails.preservation_errors_from_git(repository, args.base, args.skill,
                                                         args.removals)
    elif args.before and args.after and not (args.base or args.skill):
        errors = guardrails.preservation_errors(args.before, args.after, args.removals)
    else:
        parser.error('preserve needs either --before and --after, or --base and --skill')
    for error in errors:
        print(f'error: preserve: {error}', file=sys.stderr)
    if errors:
        return 1
    print('preserve: no protected token was lost — PASSED')
    return 0


if __name__ == '__main__':
    sys.exit(main())
