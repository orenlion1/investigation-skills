"""Fixture coverage for the delegation-contract checker's rules R1-R7."""
import importlib.util
import json
import os
from pathlib import Path
import shutil
import tempfile
import unittest


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
CHECKER = REPOSITORY_ROOT / 'scripts/check-delegation-contract.py'

SENTINEL = ('Delegating skills in this catalog share one delegation contract: copying any of '
            'them means copying the `per-store-fan-out` package too.')
CONTRACT_RELATIVE = 'skills/owner-skill/references/delegation-contract.md'


def load_checker():
    specification = importlib.util.spec_from_file_location('delegation_checker', CHECKER)
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module


class DelegationFixture(unittest.TestCase):
    """Builds a minimal conforming tree, then breaks exactly one rule per test."""

    def setUp(self):
        self.checker = load_checker()
        self.root = Path(tempfile.mkdtemp(prefix='delegation-fixture-'))
        self.addCleanup(shutil.rmtree, self.root, ignore_errors=True)
        self.contract = self.root / CONTRACT_RELATIVE
        self.contract.parent.mkdir(parents=True)
        self.contract.write_text(
            '# Shared Delegation Contract\n\n' + SENTINEL + '\n\n'
            '`launch_mode` is one of `parallel`, `sequential`, `unavailable`, `disabled`.\n'
            'Owned keys: "branches", degradation_reason, iteration_rounds, launched_at.\n'
            'Harness: spawn_agent, wait_agent, followup_task, send_message, SendMessage.\n'
            'Delegated output is leads until the orchestrating session verifies it.\n')
        for name in ('owner-skill', 'caller-one'):
            self.write_caller(name)
        self.policy_path = self.root / 'policy/delegation-contract.json'
        self.policy_path.parent.mkdir(parents=True)
        self.write_policy()

    def write_caller(self, name, link=True, sentinel=True, bound=True, owned_token=None):
        directory = self.root / 'skills' / name
        (directory / 'references').mkdir(parents=True, exist_ok=True)
        relative = ('references/delegation-contract.md' if name == 'owner-skill'
                    else '../owner-skill/references/delegation-contract.md')
        body = ['---', 'name: ' + name, 'description: one read-only sub-agent per unit.', '---',
                '', '# ' + name, '']
        if link:
            body.append('See the [delegation contract](%s).' % relative)
        if sentinel:
            body.append(SENTINEL)
        if bound:
            body.append('Stop after three follow-up rounds without convergence.')
        if owned_token:
            body.append(owned_token)
        (directory / 'SKILL.md').write_text('\n'.join(body) + '\n')

    def write_policy(self, **overrides):
        policy = {
            'version': 1,
            'contract': CONTRACT_RELATIVE,
            'callers': ['skills/owner-skill', 'skills/caller-one'],
            'owned_concepts': [
                {'id': 'launch-mode-vocabulary',
                 'pattern': r'\blaunch_mode\b|\bsequential agents\b'},
                {'id': 'manifest-schema',
                 'pattern': r'["`]branches["`]|\b(?:degradation_reason|iteration_rounds'
                            r'|launched_at)\b'},
                {'id': 'harness-mechanics',
                 'pattern': r'\b(?:spawn_agent|wait_agent|followup_task|send_message'
                            r'|SendMessage)\b'},
            ],
            'caller_owned_tokens': ['Grafana', 'AWS', 'Atlassian', 'Slack', 'gcx-cli',
                                    'aws-mcp', 'rovo-dev-mcp', 'slack-mcp'],
            'contract_forbidden_numeric':
                r'\b(?:\d+|one|two|three|four|five)\s+(?:follow-up|round|rounds|read|reads)\b',
            'caller_bounds': {'skills/owner-skill': 'three follow-up rounds'},
            'caller_no_bound': [{'path': 'skills/caller-one',
                                 'reason': 'Fixed branches; no follow-up budget.'}],
            'delegation_signature': r'\bspawn_agent\b|\bsub-agents?\b|\bone agent per\b',
            'required_caller_sentinel': SENTINEL,
            'exemptions': [],
        }
        policy.update(overrides)
        self.policy_path.write_text(json.dumps(policy, indent=2))

    def run_checker(self):
        return self.checker.run(self.root, self.policy_path)

    def assertPasses(self):
        failures = self.run_checker()
        self.assertEqual([], [f.message for f in failures])

    def assertFailsRule(self, rule):
        failures = self.run_checker()
        self.assertIn(rule, {f.rule for f in failures},
                      'expected %s, observed %s' % (rule, [(f.rule, f.message)
                                                           for f in failures]))
        return failures


class TestConformingTree(DelegationFixture):
    def test_clean_fixture_passes(self):
        self.assertPasses()

    def test_counts_cover_every_declared_concept_and_caller(self):
        report = self.checker.audit(self.root, self.policy_path)
        self.assertEqual(report.concepts_checked, 3)
        self.assertEqual(report.callers_checked, 2)
        self.assertEqual([], report.failures)


class TestR1ContractIntegrity(DelegationFixture):
    def test_missing_contract_fails(self):
        self.contract.unlink()
        self.assertFailsRule('R1')

    def test_empty_contract_fails(self):
        self.contract.write_text('')
        self.assertFailsRule('R1')

    def test_symlinked_contract_fails(self):
        real = self.root / 'elsewhere.md'
        real.write_text('# Shared Delegation Contract\n' + SENTINEL + '\n')
        self.contract.unlink()
        os.symlink(real, self.contract)
        failures = self.assertFailsRule('R1')
        self.assertIn('symlink', next(f.message for f in failures if f.rule == 'R1'),
                      'R1 must fail for being a symlink, not incidentally for reading empty')


class TestR2MandatoryInboundLink(DelegationFixture):
    def test_caller_without_any_link_fails(self):
        self.write_caller('caller-one', link=False)
        self.assertFailsRule('R2')

    def test_caller_whose_link_does_not_resolve_fails(self):
        directory = self.root / 'skills/caller-one'
        text = (directory / 'SKILL.md').read_text()
        (directory / 'SKILL.md').write_text(
            text.replace('../owner-skill/references/delegation-contract.md',
                         '../owner-skill/references/does-not-exist.md'))
        self.assertFailsRule('R2')


class TestR3SingleDefinition(DelegationFixture):
    def test_reintroduced_launch_mode_names_path_line_and_concept(self):
        self.write_caller('caller-one', owned_token='The manifest records `launch_mode`.')
        failures = self.assertFailsRule('R3')
        message = next(f.message for f in failures if f.rule == 'R3')
        self.assertIn('skills/caller-one/SKILL.md:', message)
        self.assertIn('launch-mode-vocabulary', message)
        self.assertIn(CONTRACT_RELATIVE, message)

    def test_reintroduced_manifest_key_fails(self):
        self.write_caller('caller-one', owned_token='Rows carry launched_at and iteration_rounds.')
        self.assertFailsRule('R3')

    def test_reintroduced_harness_token_fails(self):
        self.write_caller('caller-one', owned_token='Use native spawn_agent once per unit.')
        self.assertFailsRule('R3')

    def test_legitimate_prose_about_branches_does_not_fail(self):
        self.write_caller('caller-one',
                          owned_token='All in-scope branches launch before any result is awaited; '
                                      'failed branches never cancel the others.')
        self.assertPasses()

    def test_contract_itself_is_not_scanned_as_a_caller_file(self):
        self.assertIn('launch_mode', self.contract.read_text())
        self.assertPasses()


class TestR4CallerOwnedScope(DelegationFixture):
    def test_missing_bound_declaration_names_caller_and_fails_accounting(self):
        self.write_policy(caller_no_bound=[])
        failures = self.assertFailsRule('R4')
        self.assertTrue(any('skills/caller-one' in f.message for f in failures if f.rule == 'R4'))
        report = self.checker.audit(self.root, self.policy_path)
        self.assertEqual(report.callers_checked, 1)
        self.assertIn('R7', {f.rule for f in report.failures})

    def test_explicit_no_bound_reason_passes(self):
        self.write_caller('caller-one', bound=False)
        self.assertPasses()

    def test_missing_declaration_for_owner_also_fails(self):
        self.write_policy(caller_bounds={})
        self.assertFailsRule('R4')

    def test_invalid_no_bound_declarations_fail_closed(self):
        for declarations in (None, {}, [{'path': 'skills/caller-one', 'reason': ' '}],
                             [{'path': 'skills/stranger', 'reason': 'No budget.'}],
                             [{'path': 'skills/owner-skill', 'reason': 'Conflicts.'}],
                             [{'path': 'skills/caller-one', 'reason': 'No budget.'}] * 2):
            with self.subTest(declarations=declarations):
                self.write_policy(caller_no_bound=declarations)
                self.assertFailsRule('R7')

    def test_contract_naming_a_store_fails(self):
        self.contract.write_text(self.contract.read_text() + '\nResolve the Grafana branch.\n')
        self.assertFailsRule('R4')

    def test_contract_naming_an_integration_skill_fails(self):
        self.contract.write_text(self.contract.read_text() + '\nAuthenticate through gcx-cli.\n')
        self.assertFailsRule('R4')

    def test_contract_naming_a_numeric_budget_fails(self):
        self.contract.write_text(self.contract.read_text()
                                 + '\nStop after three follow-up rounds.\n')
        self.assertFailsRule('R4')

    def test_caller_that_stops_stating_its_own_bound_fails(self):
        self.write_caller('owner-skill', bound=False)
        self.assertFailsRule('R4')


class TestR5CoCopyDeclaration(DelegationFixture):
    def test_caller_without_the_verbatim_sentinel_fails(self):
        self.write_caller('caller-one', sentinel=False)
        self.assertFailsRule('R5')

    def test_paraphrased_sentinel_fails(self):
        directory = self.root / 'skills/caller-one'
        text = (directory / 'SKILL.md').read_text()
        (directory / 'SKILL.md').write_text(
            text.replace(SENTINEL, 'Copy the per-store-fan-out package along with this one.'))
        self.assertFailsRule('R5')


class TestR6RegistryCompleteness(DelegationFixture):
    def test_unregistered_skill_matching_the_signature_fails(self):
        stranger = self.root / 'skills/stranger-skill'
        stranger.mkdir(parents=True)
        (stranger / 'SKILL.md').write_text(
            '# Stranger\n\nLaunch one agent per unit with native spawn_agent.\n')
        failures = self.assertFailsRule('R6')
        self.assertIn('skills/stranger-skill',
                      next(f.message for f in failures if f.rule == 'R6'))

    def test_exempt_skill_matching_the_signature_passes(self):
        stranger = self.root / 'skills/stranger-skill'
        stranger.mkdir(parents=True)
        (stranger / 'SKILL.md').write_text(
            '# Stranger\n\nPropose two parallel sub-agents and route the work elsewhere.\n')
        # Guard against a vacuous assertion: without the exemption this must actually fail.
        self.assertFailsRule('R6')
        self.write_policy(exemptions=[{'path': 'skills/stranger-skill',
                                       'reason': 'Proposes without launching or briefing.'}])
        self.assertPasses()

    def test_plural_sub_agents_matches_the_signature(self):
        stranger = self.root / 'skills/stranger-skill'
        stranger.mkdir(parents=True)
        (stranger / 'SKILL.md').write_text(
            '# Stranger\n\nThis workflow launches two read-only sub-agents in parallel.\n')
        self.assertFailsRule('R6')

    def test_contract_owner_need_not_be_a_registered_caller(self):
        self.write_policy(callers=['skills/caller-one', 'skills/caller-two'],
                          caller_bounds={'skills/caller-one': 'three follow-up rounds'})
        self.write_caller('caller-two')
        # owner-skill holds the contract but is not a caller: R6 must not flag it, and its own
        # caller rules must not be applied to it.
        failures = self.run_checker()
        self.assertEqual([], [(f.rule, f.message) for f in failures
                              if 'owner-skill' in f.message])

    def test_signature_too_narrow_to_detect_a_registered_caller_fails(self):
        # The real defect this caught: the signature matched only the singular "sub-agent",
        # so it could not detect parallel-alert-investigation, a registered caller.
        self.write_policy(delegation_signature=r'\bspawn_agent\b')
        failures = self.assertFailsRule('R6')
        self.assertTrue(any('could not have detected it' in f.message for f in failures))

    def test_skill_not_matching_the_signature_needs_no_registration(self):
        stranger = self.root / 'skills/quiet-skill'
        stranger.mkdir(parents=True)
        (stranger / 'SKILL.md').write_text('# Quiet\n\nRead a dashboard and report.\n')
        self.assertPasses()


class TestR7PolicyIntegrityAndCounts(DelegationFixture):
    def test_concept_silently_not_applied_to_a_caller_fails(self):
        real = self.checker.check_caller

        def drop_one(root, policy, caller, contract_absolute, compiled, failures):
            applied = real(root, policy, caller, contract_absolute, compiled, failures)
            if applied is None or caller != 'skills/caller-one':
                return applied
            return frozenset(sorted(applied)[1:])

        self.checker.check_caller = drop_one
        self.addCleanup(setattr, self.checker, 'check_caller', real)
        report = self.checker.audit(self.root, self.policy_path)
        self.assertLess(report.concepts_checked, 3)
        self.assertIn('R7', {f.rule for f in report.failures})

    def test_no_caller_checked_reports_zero_concepts(self):
        shutil.rmtree(self.root / 'skills/owner-skill')
        shutil.rmtree(self.root / 'skills/caller-one')
        report = self.checker.audit(self.root, self.policy_path)
        self.assertEqual(report.concepts_checked, 0)
        self.assertEqual(report.callers_checked, 0)
        self.assertIn('R7', {f.rule for f in report.failures})

    def test_unknown_version_fails(self):
        self.write_policy(version=2)
        self.assertFailsRule('R7')

    def test_duplicate_concept_ids_fail(self):
        duplicate = [{'id': 'same', 'pattern': 'alpha'}, {'id': 'same', 'pattern': 'beta'}]
        self.write_policy(owned_concepts=duplicate)
        self.assertFailsRule('R7')

    def test_fewer_than_two_callers_fails(self):
        self.write_policy(callers=['skills/owner-skill'])
        self.assertFailsRule('R7')

    def test_uncompilable_pattern_fails(self):
        self.write_policy(owned_concepts=[{'id': 'broken', 'pattern': '([unclosed'}])
        self.assertFailsRule('R7')

    def test_missing_required_key_fails(self):
        policy = json.loads(self.policy_path.read_text())
        del policy['delegation_signature']
        self.policy_path.write_text(json.dumps(policy))
        self.assertFailsRule('R7')

    def test_unreadable_policy_fails_closed(self):
        self.policy_path.write_text('{not json')
        self.assertFailsRule('R7')

    def test_caller_directory_absent_fails_rather_than_being_skipped(self):
        shutil.rmtree(self.root / 'skills/caller-one')
        failures = self.run_checker()
        self.assertTrue(failures, 'an absent caller must fail, never be silently skipped')


class TestDeliveredRepository(unittest.TestCase):
    """The rules must hold on the tree this repository actually ships."""

    def test_shipped_signature_detects_every_registered_caller(self):
        checker = load_checker()
        policy = checker.load_policy(REPOSITORY_ROOT / 'policy/delegation-contract.json')
        signature = __import__('re').compile(policy['delegation_signature'])
        for caller in policy['callers']:
            directory = REPOSITORY_ROOT / caller
            matched = [str(path) for path, text in checker.text_files(directory)
                       if signature.search(text)]
            self.assertTrue(matched, '%s is registered but the shipped signature %r cannot '
                                     'detect it' % (caller, policy['delegation_signature']))

    def test_live_tree_passes(self):
        checker = load_checker()
        policy = REPOSITORY_ROOT / 'policy/delegation-contract.json'
        report = checker.audit(REPOSITORY_ROOT, policy)
        self.assertEqual([], [(f.rule, f.message) for f in report.failures])
        self.assertEqual(report.concepts_checked, 3)
        self.assertEqual(report.callers_checked, 3)


if __name__ == '__main__':
    unittest.main()
