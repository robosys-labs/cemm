"""Independent audit arithmetic on fabricated records; no real forecasts or fits."""
from copy import deepcopy
import json
import lzma
import math
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from experiments.predictive_nucleus import audit_effect_role_saved as audit
from experiments.predictive_nucleus import effect_role_scoring as scoring
from experiments.predictive_nucleus.tests.test_effect_role_scoring import fixture, retention_fixture, LIMITS, one_hot, logs


class EffectRoleSavedAuditTests(unittest.TestCase):
    def check_fresh(self, bundle, traces):
        original = deepcopy((bundle, traces)); saved = scoring.analyze(bundle, traces, LIMITS); checked = audit.h.Audit()
        records, gold, pairs = audit.inventory(bundle['inputs'], {k: v for k, v in bundle.items() if k != 'inputs'})
        indexed = {arm: audit.index_rows(rows, records, arm) for arm, rows in traces.items()}
        points = {arm: audit.measured(views['canonical'], records, gold) for arm, views in indexed.items()}
        points['masked'] = audit.measured(indexed['grounded']['masked'], records, gold)
        reports = {arm: audit.summary(rows, pairs) for arm, rows in points.items()}
        goals = {arm: audit.goals(rows, bundle['goal_groups']) for arm, rows in points.items()}
        for arm, rows in points.items():
            audit.compare_subset(checked, saved['reports'][arm], reports[arm], arm)
            checked.equal(saved['points'][arm], [{k: v for k, v in p.items() if k not in ('logp', 'probabilities')}
                                                for p in rows.values()], 'all point metrics/' + arm)
            checked.equal(saved['goals'][arm], goals[arm], 'all goal records/' + arm)
        checks, comparison = audit.decision_checks(reports, goals, LIMITS)
        self.assertEqual(checks, saved['checks']); checked.equal(comparison, saved['comparisons'], 'control gains')
        self.assertEqual(checked.discrepancy_count, 0, checked.discrepancies)
        self.assertGreater(checked.checks, 10000)
        self.assertEqual((bundle, traces), original)
        return saved

    def test_reconstructs_complete_pass_ambiguity_and_valid_failures(self):
        for variant in ('deterministic', 'ambiguous', 'uniform', 'mode_peek', 'underflow'):
            bundle, traces = fixture(variant in ('ambiguous', 'mode_peek'))
            if variant == 'uniform':
                for row in traces['grounded']:
                    if row['view'] == 'canonical': row['logp'], row['action_logp'] = [-math.log(8)] * 8, [-math.log(4)] * 4
            if variant == 'mode_peek':
                gold = {m['id']: m for m in bundle['oracle']['episodes']}
                for row in traces['grounded']:
                    if row['view'] == 'canonical': row['logp'] = one_hot(8, audit.h.index(gold[row['id']]['truth'][row['step']]))
            if variant == 'underflow':
                group = bundle['goal_groups'][0]; target = group['before'].copy(); target[:2] = [1, 1]
                for choice, eid in enumerate(group['episodes']):
                    row = next(r for r in traces['grounded'] if r['id'] == eid and r['step'] == 1 and r['view'] == 'canonical')
                    row['logp'] = one_hot(8, 0); row['logp'][audit.h.index(target)] = -800. if choice == 3 else -900.
            with self.subTest(variant=variant):
                saved = self.check_fresh(bundle, traces)
                self.assertEqual(saved['passed'], variant in ('deterministic', 'ambiguous'))

    def test_retention_reconstructs_every_record_and_preserves_new_set_mass(self):
        for variant in ('pass', 'action_change', 'world_regression', 'both_zero', 'boundary'):
            inputs, now, old = retention_fixture(2); records = {r['id']: r for r in inputs['episodes']}
            if variant == 'action_change': now[0]['action_logp'] = logs([.01, .01, .97, .01])
            if variant == 'world_regression': now[0]['logp'] = one_hot(8, 1)
            if variant == 'both_zero': now[0]['logp'] = old[0]['logp'] = one_hot(8, 1)
            if variant == 'boundary': now[0]['logp'] = [v + 5e-11 if type(v) is float else v for v in now[0]['logp']]
            result = audit.retained(audit.index_rows(now, records, fresh=False)['canonical'],
                audit.index_rows(old, records, fresh=False, archived=True)['canonical'], records, LIMITS)
            expected = scoring.retention(inputs, now, old, LIMITS); checked = audit.h.Audit()
            checked.equal(expected, result, variant)
            self.assertEqual(checked.discrepancy_count, 0, checked.discrepancies)
            self.assertGreater(result['mean_candidate_set_mass'], 0.)

    def test_input_only_validation_rejects_missing_wrong_and_unnormalized_rows(self):
        bundle, traces = fixture(); records = {r['id']: r for r in bundle['inputs']['episodes']}
        # Only identities, dimensions and sequence lengths are consulted here.
        stripped = {eid: {'entities': r['entities'], 'utterances': [None] * len(r['utterances'])} for eid, r in records.items()}
        with patch.object(audit.h, 'read', side_effect=AssertionError('unexpected file read')):
            self.assertEqual(sum(map(len, audit.index_rows(traces['grounded'], stripped).values())), 96)
        for defect in ('missing', 'duplicate', 'foreign', 'bool_step', 'view', 'dimension', 'mass', 'nan', 'positive_inf', 'none'):
            rows = deepcopy(traces['grounded'])
            if defect == 'missing': rows.pop()
            elif defect == 'duplicate': rows.append(deepcopy(rows[0]))
            elif defect == 'foreign': rows[0]['id'] = 'foreign'
            elif defect == 'bool_step': rows[0]['step'] = True
            elif defect == 'view': rows[0]['view'] = 'swapped'
            elif defect == 'dimension': rows[0]['action_logp'].pop()
            elif defect == 'mass': rows[0]['logp'] = [0.] * 8
            else: rows[0]['logp'][0] = {'nan': math.nan, 'positive_inf': math.inf, 'none': None}[defect]
            with self.subTest(defect=defect), self.assertRaises(ValueError): audit.index_rows(rows, records)
        self.assertEqual(audit.logs([5e-11, 'negative_infinity'], 2, 1e-10), [5e-11, -math.inf])
        with self.assertRaises(ValueError): audit.logs([5e-11, 'negative_infinity'], 2, 1e-12)

    def test_registry_unknown_receipt_arithmetic_and_valid_failed_control(self):
        from experiments.predictive_nucleus.effect_role_model import create_registry
        from experiments.predictive_nucleus.effect_role_run import lexical_controls
        inputs, _, _ = retention_fixture(); teach = deepcopy(inputs)
        teach['episodes'][0]['utterances'][0]['text'] = 'a lights b'
        observed = [inputs, teach]; registry = create_registry(observed); unknown = ['novel_a', 'novel_b']
        receipt = lexical_controls(registry, unknown)
        self.assertEqual(audit.lexical_receipt(registry, observed, unknown, receipt), receipt)
        failed = deepcopy(receipt); failed['unknown'] = []; failed['unresolved_exception'] = False
        rebuilt = audit.lexical_receipt(registry, observed, unknown, failed)
        self.assertFalse(rebuilt['checks']['unknown_identities_unresolved'])
        changed = deepcopy(registry); changed['tokens']['lights']['id'] = '0' * 64
        with self.assertRaisesRegex(ValueError, 'lexical identity'): audit.lexical_receipt(changed, observed, unknown)

    def test_goal_prefix_and_oracle_probability_corruption_rejected(self):
        for defect in ('future_key', 'goal_utility', 'branch_prefix', 'oracle_mass'):
            bundle, _ = fixture(); evaluator = {k: v for k, v in bundle.items() if k != 'inputs'}
            if defect == 'future_key': evaluator['oracle']['episodes'][0]['forecasts'][0]['information_key'] = 'a' * 64
            elif defect == 'goal_utility': evaluator['goal_groups'][0]['goals'][0]['oracle_utilities'][0] = .125
            elif defect == 'branch_prefix': bundle['inputs']['episodes'][0]['utterances'][0]['text'] = 'a other c'
            else: evaluator['oracle']['episodes'][0]['forecasts'][0]['probabilities'][0] = .5
            with self.subTest(defect=defect), self.assertRaises(ValueError): audit.inventory(bundle['inputs'], evaluator)

    def test_auditor_imports_only_stdlib_helpers(self):
        code = ('import sys; import experiments.predictive_nucleus.audit_effect_role_saved; '
            'assert "torch" not in sys.modules; '
            'assert not any(k.endswith(("effect_role_model", "effect_role_scoring", "effect_role_data")) for k in sys.modules)')
        subprocess.run([sys.executable, '-c', code], check=True)

    def test_synthetic_published_stage_driver_and_target_opening_boundary(self):
        """Exercise every file/binding path with tiny fabricated stages in local git."""
        from experiments.predictive_nucleus.effect_role_model import create_registry
        bundle, synthetic = fixture(); rehearsal, current, archived = retention_fixture()
        teach = deepcopy(rehearsal); teach['episodes'][0]['utterances'][0]['text'] = 'a lights b'
        registry = create_registry([rehearsal, teach]); unknown = ['unseen_alpha', 'unseen_beta']
        with tempfile.TemporaryDirectory() as folder:
            repo = Path(folder); root = repo / 'experiments/predictive_nucleus'; data = root / 'data/effect-role-v1'
            fitted = root / 'data/effect-role-fit-v1'; traces = root / 'results/effect-role-v1/traces'; scored = traces.parent / 'scored'
            def write(path, value):
                path.parent.mkdir(parents=True, exist_ok=True)
                raw = (json.dumps(audit.h.safe(value), sort_keys=True, indent=2, allow_nan=False) + '\n').encode()
                path.write_bytes(lzma.compress(raw) if str(path).endswith('.xz') else raw)
                return {'sha256': audit.h.sha(path), 'bytes': path.stat().st_size}
            def git(*args):
                return subprocess.check_output(['git', '-C', str(repo), *args], stderr=subprocess.DEVNULL, text=True).strip()
            def commit(message):
                git('add', 'experiments'); git('commit', '-m', message); return git('rev-parse', 'HEAD')
            git('init'); git('config', 'user.name', 'Synthetic Audit Test'); git('config', 'user.email', 'synthetic@example.invalid')
            config = {'version': 'effect-role-v1', 'model_seeds': list(audit.SEEDS), 'arms': list(audit.ARMS),
                'parameters': {'world': 562, 'grounded': 92, 'parser': 92, 'text_only': 1048},
                'training_forecasts': {'teach': 1, 'rehearsal': 1}, 'fresh_episodes_per_law': 24,
                'fresh_forecasts_per_law': 48, 'identifiable_forecasts_per_law': 48, 'ambiguous_forecasts_per_law': 0,
                'held_new_word_forecasts_per_law': 4, 'goal_groups_per_law': 6, 'goal_decisions_per_law': 24,
                'fresh_saved_forecasts': 1920, 'retention_saved_forecasts': 60, 'analysis': LIMITS, 'unknown_tokens': unknown,
                'fit': {'updates': 1}, 'execution': {'runtime': {'python': 'synthetic'}}}
            write(root / 'effect_role_protocol_v1.json', config)
            (root / 'snapshots').mkdir(); (root / 'snapshots/effect_role_protocol_v1.sha256').write_text(
                audit.h.sha(root / 'effect_role_protocol_v1.json') + '\n')
            artifacts = {name: write(data / name, value) for name, value in (
                ('teach-inputs.json.xz', teach), ('rehearsal-inputs.json.xz', rehearsal), ('lexical-registry.json', registry))}
            write(root / 'data/saturation-v1/train-inputs.json.xz', rehearsal)
            worlds = {}; native_state = {'vector': [0.] * 562}; world_digest = audit.h.fingerprint(native_state)[0]
            for law in audit.LAWS:
                for seed in audit.SEEDS:
                    name = f'{law}-{seed}.json'; path = root / 'data/set-acquisition-fit-v2' / name
                    worlds[f'{law}/{seed}'] = {'file': name, 'state_sha256': world_digest,
                        **write(path, {'state': native_state, 'state_sha256': world_digest})}
                artifacts[law + '-inputs.json.xz'] = write(data / f'{law}-inputs.json.xz', bundle['inputs'])
                artifacts[law + '-evaluator.json.xz'] = write(data / f'{law}-evaluator.json.xz',
                    {k: v for k, v in bundle.items() if k != 'inputs'})
                for bank in audit.BANKS:
                    write(root / f'data/{bank}-v1/{law}-inputs.json.xz', rehearsal)
                    for seed in audit.SEEDS:
                        write(root / f'results/set-acquisition-v2/traces/trace-{law}-{seed}-acquired-{bank}_retention.json.xz',
                              {'input_sha256': audit.h.canonical(rehearsal), 'points': archived})
            parent_state = {'body': [0.] * 84, 'order.weight': [[[.1]], [[.2]]], 'order.bias': [0., 0.]}
            write(root / 'data/coordinate-fit-v1/checkpoints.json.xz', {'checkpoints': {
                f'coordinates/{seed}': {'state': parent_state} for seed in audit.SEEDS}})
            freeze = {'version': config['version'], 'sources': {}, 'historical': {}, 'artifacts': artifacts,
                'world_checkpoints': worlds, 'runtime': config['execution']['runtime'],
                'runtime_sha256': audit.h.canonical(config['execution']['runtime']),
                'protocol_sha256': audit.h.sha(root / 'effect_role_protocol_v1.json')}
            write(data / 'freeze.json', freeze)
            write(root / 'effect_role_freeze_v1.json', {p.name: audit.h.sha(p) for p in data.iterdir()})
            source_commit = commit('synthetic source and data'); identity = {'source_publication': source_commit,
                'runtime': freeze['runtime'], 'freeze_sha256': audit.h.sha(data / 'freeze.json')}
            write(fitted / 'attempt.json', identity); weights, reports = {}, {}
            for arm in audit.ARMS:
                for seed in audit.SEEDS:
                    state = deepcopy(parent_state)
                    state['order.weight'] += [[[0.]], [[0.]]]; state['order.bias'] += [0., 0.]
                    if arm == 'text_only': state = {'body': [0.] * 1048}
                    digest, count = audit.h.fingerprint(state); key = f'{arm}/{seed}'; name = f'{arm}-{seed}.json'
                    weights[key] = {'file': name, **write(fitted / name, {'arm': arm, 'seed': seed, 'state': state, 'state_sha256': digest})}
                    reports[key] = {'initial_sha256': digest, 'final_sha256': digest, 'world_sha256': world_digest,
                        'world_unchanged': True, 'parameters': count, 'settings': config['fit'], 'updates': 1,
                        'observed_forecasts_per_update': config['training_forecasts'], 'fresh_optimizer': True,
                        'optimizer': {'name': 'Adam', 'betas': [.9, .999], 'eps': 1e-8, 'weight_decay': 0., 'amsgrad': False}}
                    write(fitted / f'fit-{arm}-{seed}.json', reports[key])
            write(fitted / 'training.json', {**identity, 'version': config['version'], 'complete': True,
                'checkpoints': weights, 'reports': reports, 'training_input_sha256': {
                    'teach': audit.h.canonical(teach), 'rehearsal': audit.h.canonical(rehearsal)}})
            weight_commit = commit('synthetic fitted weights'); raw_identity = {'weights_publication': weight_commit,
                'runtime': freeze['runtime'], 'freeze_sha256': identity['freeze_sha256'], 'training_sha256': audit.h.sha(fitted / 'training.json')}
            write(traces / 'attempt.json', raw_identity); raw_files = {}
            lexical = audit.lexical_receipt(registry, [rehearsal, teach], unknown)
            raw_files['lexical-identities.json'] = write(traces / 'lexical-identities.json', lexical)
            for law in audit.LAWS:
                for seed in audit.SEEDS:
                    for arm in audit.ARMS:
                        for bank in ('fresh', *(b + '_retention' for b in audit.BANKS)) if arm == 'grounded' else ('fresh',):
                            name = f'trace-{law}-{seed}-{arm}-{bank}.json.xz'; fresh = bank == 'fresh'
                            raw_files[name] = write(traces / name, {**raw_identity, 'law': law, 'seed': seed, 'arm': arm,
                                'bank': bank, 'input_sha256': audit.h.canonical(bundle['inputs'] if fresh else rehearsal),
                                'state_sha256': reports[f'{arm}/{seed}']['final_sha256'], 'points': synthetic[arm] if fresh else current})
            write(traces / 'manifest.json', {**raw_identity, 'complete': True, 'oracle_opened': False, 'artifacts': raw_files})
            raw_commit = commit('synthetic raw forecasts')
            command = [sys.executable, audit.__file__, '--repo', str(repo), '--publication', raw_commit]
            # Guard the actual audit reader: opaque hashing is permitted; parsing targets/reports is forbidden.
            guard = ('import importlib.util,sys; sys.path.insert(0,sys.argv[1]); import audit_effect_role_saved as a; '
                'read=a.h.read; a.h.read=lambda p: (_ for _ in ()).throw(AssertionError(str(p))) '
                'if "evaluator" in str(p) or "/scored/" in str(p) else read(p); '
                'r=a.audit_saved(a.Path(sys.argv[2]),a.h.Audit(),True,sys.argv[3]); assert r["audit_passed"]')
            subprocess.run([sys.executable, '-c', guard, str(Path(audit.__file__).parent), str(repo), raw_commit], check=True)
            fresh_report = scoring.analyze(bundle, synthetic, LIMITS)
            retained = scoring.retention(rehearsal, current, archived, LIMITS); score_files, checks = {}, {}
            for law in audit.LAWS:
                for seed in audit.SEEDS:
                    key = f'{law}/{seed}'; checks[key] = {**fresh_report['checks'], **{
                        bank + '_retention/' + name: value for bank in audit.BANKS for name, value in retained['checks'].items()}}
                    score_files[key] = write(scored / f'report-{law}-{seed}.json.xz', {'fresh': fresh_report,
                        'retention': {bank + '_retention': retained for bank in audit.BANKS}})
            write(scored / 'manifest.json', {'runtime': freeze['runtime'], 'traces_publication': raw_commit,
                'trace_manifest_sha256': audit.h.sha(traces / 'manifest.json'), 'reports': score_files})
            write(scored / 'decision.json', {'checks': checks, 'lexical_identity_checks': lexical['checks'],
                'decision': 'DEVELOPMENT_G3_COMPLETE', 'g3_complete': True, 'execution_complete': True,
                'scientific_admission': False, 'next_stage': 'G4'})
            completed = subprocess.run([*command, '--output', str(repo / 'audit.json')], check=True, capture_output=True, text=True)
            self.assertIn('"audit_passed": true', completed.stdout)
            result = audit.h.read(repo / 'audit.json'); self.assertEqual(result['trace_files'], 90)
            self.assertEqual(result['forecast_counts'], {'fresh': 1920, 'retention': 60})


if __name__ == '__main__': unittest.main()
