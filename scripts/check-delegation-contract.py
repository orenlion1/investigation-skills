#!/usr/bin/env python3
"""Fail closed when the shared delegation contract stops being the single definition.

Implements R1-R7 from the repository's delegation-contract policy. The contract owns the
delegation machinery; a caller owns its own units, questions and bounds. This check is a
literal-token lint: it catches a duplicated schema key, vocabulary value or harness token,
which is the drift that actually occurred. It cannot distinguish a paraphrase of the contract
from a legitimate cross-reference to it, and does not pretend to.
"""
import argparse
import collections
import json
from pathlib import Path
import re
import sys


DEFAULT_POLICY = Path(__file__).resolve().parents[1] / 'policy/delegation-contract.json'
MAX_BYTES = 2 * 1024 * 1024
REQUIRED_KEYS = ('version', 'contract', 'callers', 'owned_concepts', 'caller_owned_tokens',
                 'contract_forbidden_numeric', 'caller_bounds', 'delegation_signature',
                 'required_caller_sentinel', 'exemptions')
LINK = re.compile(r'\]\(([^)\s]+)\)')

Failure = collections.namedtuple('Failure', 'rule message')
Report = collections.namedtuple('Report', 'failures concepts_checked callers_checked')


class PolicyError(Exception):
    """The policy itself cannot be trusted, so nothing downstream may be claimed."""


def load_policy(path):
    try:
        policy = json.loads(Path(path).read_text())
    except (OSError, ValueError) as error:
        raise PolicyError('policy unreadable: %s' % error)
    if not isinstance(policy, dict):
        raise PolicyError('policy must be an object')
    if policy.get('version') != 1:
        raise PolicyError('unsupported policy version: %r' % (policy.get('version'),))
    missing = [key for key in REQUIRED_KEYS if key not in policy]
    if missing:
        raise PolicyError('policy missing required key(s): %s' % ', '.join(sorted(missing)))
    if not isinstance(policy['contract'], str) or not policy['contract']:
        raise PolicyError('contract must be a non-empty path')
    callers = policy['callers']
    if not isinstance(callers, list) or not all(
            isinstance(caller, str) and caller for caller in callers):
        raise PolicyError('callers must be a list of paths')
    if len(callers) < 2:
        raise PolicyError('a shared contract needs at least two registered callers, found %d'
                          % len(callers))
    if len(set(callers)) != len(callers):
        raise PolicyError('duplicate caller entries')
    concepts = policy['owned_concepts']
    if not isinstance(concepts, list) or not concepts:
        raise PolicyError('owned_concepts must be a non-empty list')
    identifiers = []
    for concept in concepts:
        if not isinstance(concept, dict) or 'id' not in concept or 'pattern' not in concept:
            raise PolicyError('each owned concept needs an id and a pattern')
        identifiers.append(concept['id'])
        compile_pattern(concept['pattern'], 'owned concept %r' % concept['id'])
    duplicates = sorted({i for i in identifiers if identifiers.count(i) > 1})
    if duplicates:
        raise PolicyError('duplicate owned-concept id(s): %s' % ', '.join(duplicates))
    if not isinstance(policy['caller_owned_tokens'], list) or not all(
            isinstance(token, str) and token for token in policy['caller_owned_tokens']):
        raise PolicyError('caller_owned_tokens must be a list of tokens')
    if not isinstance(policy['caller_bounds'], dict) or not all(
            isinstance(key, str) and isinstance(value, str)
            for key, value in policy['caller_bounds'].items()):
        raise PolicyError('caller_bounds must map a caller path to a pattern')
    for caller, pattern in policy['caller_bounds'].items():
        if caller not in callers:
            raise PolicyError('caller_bounds names an unregistered caller: %s' % caller)
        compile_pattern(pattern, 'caller bound for %s' % caller)
    compile_pattern(policy['contract_forbidden_numeric'], 'contract_forbidden_numeric')
    compile_pattern(policy['delegation_signature'], 'delegation_signature')
    if not isinstance(policy['required_caller_sentinel'], str) \
            or not policy['required_caller_sentinel'].strip():
        raise PolicyError('required_caller_sentinel must be a non-empty sentence')
    if not isinstance(policy['exemptions'], list):
        raise PolicyError('exemptions must be a list')
    for exemption in policy['exemptions']:
        if not isinstance(exemption, dict) or not exemption.get('path') \
                or not exemption.get('reason'):
            raise PolicyError('each exemption needs a path and a stated reason')
    return policy


def compile_pattern(pattern, label):
    if not isinstance(pattern, str) or not pattern:
        raise PolicyError('%s must be a non-empty pattern' % label)
    try:
        return re.compile(pattern)
    except re.error as error:
        raise PolicyError('%s does not compile: %s' % (label, error))


def read_text(path):
    """Return decoded text, or None for anything this check must not interpret."""
    try:
        if path.is_symlink() or not path.is_file() or path.stat().st_size > MAX_BYTES:
            return None
        return path.read_bytes().decode('utf-8')
    except (OSError, UnicodeDecodeError):
        return None


def text_files(directory, exclude=None):
    for path in sorted(p for p in directory.rglob('*') if p.is_file()):
        if exclude is not None and path.resolve() == exclude:
            continue
        text = read_text(path)
        if text is not None:
            yield path, text


def relative(root, path):
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def check_contract(root, policy, failures):
    contract = root / policy['contract']
    if contract.is_symlink():
        failures.append(Failure('R1', '%s — the contract must be a regular file, not a symlink'
                                % policy['contract']))
        return None
    if not contract.is_file():
        failures.append(Failure('R1', '%s — the contract file is missing' % policy['contract']))
        return None
    text = read_text(contract)
    if not text or not text.strip():
        failures.append(Failure('R1', '%s — the contract file is empty' % policy['contract']))
        return None
    return text


def check_contract_scope(root, policy, contract_text, failures):
    """R4, contract half: the contract may not take over what a caller owns."""
    owned = re.compile('|'.join(r'\b%s\b' % re.escape(token)
                                for token in policy['caller_owned_tokens']))
    numeric = re.compile(policy['contract_forbidden_numeric'], re.IGNORECASE)
    for number, line in enumerate(contract_text.splitlines(), 1):
        match = owned.search(line)
        if match:
            failures.append(Failure('R4', '%s:%d — the contract names caller-owned token %r'
                                    % (policy['contract'], number, match.group())))
        match = numeric.search(line)
        if match:
            failures.append(Failure('R4', '%s:%d — the contract states numeric budget %r, which '
                                          'each caller owns'
                                    % (policy['contract'], number, match.group().strip())))


def check_caller(root, policy, caller, contract_absolute, compiled, failures):
    """Check one caller. Returns the concept ids actually applied, or None when not checked."""
    directory = root / caller
    if not directory.is_dir():
        failures.append(Failure('R7', '%s — registered caller directory is missing, so its rules '
                                      'were not checked' % caller))
        return None
    files = list(text_files(directory, contract_absolute))
    if not files:
        failures.append(Failure('R7', '%s — registered caller has no readable text file, so its '
                                      'rules were not checked' % caller))
        return None

    linked = False
    for path, text in files:
        if path.suffix != '.md':
            continue
        for target in LINK.findall(text):
            if target.startswith(('http://', 'https://', '#')):
                continue
            candidate = (path.parent / target.split('#', 1)[0])
            try:
                if candidate.resolve() == contract_absolute and candidate.is_file():
                    linked = True
            except OSError:
                continue
    if not linked:
        failures.append(Failure('R2', '%s — no relative link to %s resolves on disk from this '
                                      'caller' % (caller, policy['contract'])))

    applied = set()
    for path, text in files:
        lines = text.splitlines()
        for concept, pattern in compiled:
            applied.add(concept)
            for number, line in enumerate(lines, 1):
                if pattern.search(line):
                    failures.append(Failure('R3', '%s:%d — concept %s is owned by %s'
                                            % (relative(root, path), number, concept,
                                               policy['contract'])))

    sentinel = policy['required_caller_sentinel']
    if not any(sentinel in text for _, text in files):
        failures.append(Failure('R5', '%s — missing the verbatim co-copy sentinel' % caller))

    bound = policy['caller_bounds'].get(caller)
    if bound:
        pattern = re.compile(bound)
        if not any(pattern.search(text) for _, text in files):
            failures.append(Failure('R4', '%s — stopped stating its own bound (expected a match '
                                          'for %r in its own files)' % (caller, bound)))
    return frozenset(applied)


def check_registry(root, policy, failures):
    """R6: a skill that delegates must be registered as the owner, a caller, or an exemption."""
    registered = set(policy['callers'])
    registered.update(exemption['path'] for exemption in policy['exemptions'])
    owner_parts = Path(policy['contract']).parts[:2]
    if len(owner_parts) == 2:
        registered.add('/'.join(owner_parts))
    signature = re.compile(policy['delegation_signature'])
    skills = root / 'skills'
    if not skills.is_dir():
        return

    # Registry soundness: a signature that cannot detect a caller already registered would not
    # have detected that caller in the first place, so it is too narrow to enforce R6 at all.
    for caller in policy['callers']:
        directory = root / caller
        if not directory.is_dir():
            continue
        if not any(signature.search(text) for _, text in text_files(directory)):
            failures.append(Failure('R6', '%s — the delegation signature %r does not match this '
                                          'registered caller, so it could not have detected it'
                                    % (caller, policy['delegation_signature'])))
    for directory in sorted(p for p in skills.iterdir() if p.is_dir()):
        name = 'skills/' + directory.name
        if name in registered:
            continue
        for path, text in text_files(directory):
            match = signature.search(text)
            if match:
                failures.append(Failure('R6', '%s — matches the delegation signature at %s (%r) '
                                              'but is registered neither as a caller nor as an '
                                              'exemption'
                                        % (name, relative(root, path), match.group())))
                break


def audit(root, policy_path=DEFAULT_POLICY):
    """Run every rule and report how much was actually checked."""
    root = Path(root).resolve()
    failures = []
    try:
        policy = load_policy(policy_path)
    except PolicyError as error:
        return Report([Failure('R7', str(error))], 0, 0)

    contract_text = check_contract(root, policy, failures)
    contract_absolute = (root / policy['contract']).resolve()
    if contract_text is not None:
        check_contract_scope(root, policy, contract_text, failures)

    compiled = [(concept['id'], re.compile(concept['pattern']))
                for concept in policy['owned_concepts']]
    callers_checked = 0
    applied_everywhere = None
    for caller in policy['callers']:
        applied = check_caller(root, policy, caller, contract_absolute, compiled, failures)
        if applied is None:
            continue
        callers_checked += 1
        applied_everywhere = (applied if applied_everywhere is None
                              else applied_everywhere & applied)
    check_registry(root, policy, failures)

    # Observed, not declared: a concept counts only when it was applied to every checked
    # caller, so a concept that silently stops being scanned fails R7 instead of passing.
    concepts_checked = len(applied_everywhere or frozenset())
    if concepts_checked != len(policy['owned_concepts']):
        failures.append(Failure('R7', 'checked %d of %d owned concepts'
                                % (concepts_checked, len(policy['owned_concepts']))))
    if callers_checked != len(policy['callers']):
        failures.append(Failure('R7', 'checked %d of %d registered callers'
                                % (callers_checked, len(policy['callers']))))
    return Report(failures, concepts_checked, callers_checked)


def run(root, policy_path=DEFAULT_POLICY):
    return audit(root, policy_path).failures


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repository', default=str(DEFAULT_POLICY.parents[1]),
                        help='repository root to check')
    parser.add_argument('--policy', default=str(DEFAULT_POLICY), help='policy file to apply')
    arguments = parser.parse_args(argv)
    report = audit(arguments.repository, arguments.policy)
    for failure in report.failures:
        sys.stderr.write('error: %s %s\n' % (failure.rule, failure.message))
    if report.failures:
        sys.stderr.write('error: delegation contract check failed with %d error(s)\n'
                         % len(report.failures))
        return 1
    print('delegation contract: %d concept(s) checked across %d caller(s) — PASSED'
          % (report.concepts_checked, report.callers_checked))
    return 0


if __name__ == '__main__':
    sys.exit(main())
