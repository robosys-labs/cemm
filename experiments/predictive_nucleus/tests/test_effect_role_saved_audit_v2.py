"""Synthetic v2 audit proof: reused arithmetic, opened comparisons and custody."""
from copy import deepcopy
import json
import lzma
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from experiments.predictive_nucleus import audit_effect_role_saved as old_audit
from experiments.predictive_nucleus import audit_effect_role_saved_v2 as audit
from experiments.predictive_nucleus import effect_role_scoring_v2 as scoring
from experiments.predictive_nucleus.tests.test_effect_role_scoring import fixture, retention_fixture, LIMITS, logs, one_hot


class EffectRoleSavedAuditV2Tests(unittest.TestCase):
    def test_arithmetic_is_exact_frozen_reuse_and_imports_are_independent(self):
        for name in ('index_rows', 'inventory', 'measured', 'summary', 'goals', 'decision_checks', 'retained', 'lexical_receipt'):
            self.assertIs(getattr(audit, name), getattr(old_audit, name))
        code = ('import sys; from experiments.predictive_nucleus import audit_effect_role_saved_v2; '
            'assert "torch" not in sys.modules; assert not any(k.endswith(("effect_role_scoring", '
            '"effect_role_scoring_v2", "effect_role_model", "effect_role_neutral", '
            '"effect_role_data", "effect_role_data_v2")) for k in sys.modules)')
        subprocess.run([sys.executable, '-c', code], check=True)

    def test_every_opened_comparison_record_and_complete_failure_arithmetic(self):
        for variant in ('same', 'regression_and_repair', 'ambiguous_shift', 'masked_regression', 'wrong_action_change'):
            bundle, traces = fixture(variant == 'ambiguous_shift'); archive = deepcopy(traces['grounded'])
            row = next(r for r in traces['grounded'] if r['view'] == 'canonical')
            oldrow = next(r for r in archive if (r['id'], r['step'], r['view']) == (row['id'], row['step'], 'canonical'))
            if variant == 'regression_and_repair':
                row['logp'], row['action_logp'] = one_hot(8, 0), one_hot(4, 1)
                later = [r for r in archive if r['view'] == 'canonical'][1]
                later['logp'], later['action_logp'] = one_hot(8, 0), one_hot(4, 1)
            elif variant == 'ambiguous_shift':
                meta = next(m for m in bundle['oracle']['episodes'] if m['direction'] == 0 and m['layout'] == 'svo' and m['final_choice'] == 0)
                row = next(r for r in traces['grounded'] if (r['id'], r['step'], r['view']) == (meta['id'], 1, 'canonical'))
                worlds = meta['forecasts'][1]['possible_worlds']; probability = [0.] * 8
                probability[worlds[0]], probability[worlds[1]] = .49, .51; row['logp'] = logs(probability)
            elif variant == 'masked_regression':
                for prior in archive:
                    if prior['view'] == 'masked':
                        reference = next(r for r in archive if (r['id'], r['step'], r['view']) == (prior['id'], prior['step'], 'canonical'))
                        prior['logp'], prior['action_logp'] = reference['logp'][:], reference['action_logp'][:]
            elif variant == 'wrong_action_change':
                oldrow['action_logp'], row['action_logp'] = one_hot(4, 1), one_hot(4, 2)
            before = deepcopy((bundle, traces, archive)); saved = scoring.analyze_opened(bundle, traces, archive, LIMITS)
            records, gold, pairs = audit.inventory(bundle['inputs'], {k: v for k, v in bundle.items() if k != 'inputs'})
            indexed = {arm: audit.index_rows(rows, records, arm) for arm, rows in traces.items()}
            all_views = {arm: views['canonical'] for arm, views in indexed.items()}; all_views['masked'] = indexed['grounded']['masked']
            check = audit.h.Audit()
            checks, points, _, _ = audit.verify_analysis(check, saved['analysis'], all_views, records, gold, pairs,
                                                        bundle['goal_groups'], LIMITS, variant)
            previous = audit.index_rows(archive, records)
            comparisons = {view: audit.opened_comparison(points[arm], audit.measured(previous[view], records, gold))
                           for view, arm in (('canonical', 'grounded'), ('masked', 'masked'))}
            checks.update(opened_identifiable_world_retention=not comparisons['canonical']['identifiable_world_regressions'],
                          opened_taught_action_retention=not comparisons['canonical']['action_regressions'])
            check.equal(saved['comparisons'], comparisons, variant); check.equal(saved['evidence_roles'], audit.EVIDENCE_ROLES, 'origins')
            self.assertEqual(check.discrepancy_count, 0, check.discrepancies)
            self.assertEqual(checks, saved['checks']); self.assertEqual(all(checks.values()), saved['passed'])
            self.assertEqual((bundle, traces, archive), before)
            if variant == 'ambiguous_shift':
                self.assertTrue(checks['opened_identifiable_world_retention'])
                self.assertEqual(len(comparisons['canonical']['ambiguous_world_regressions']), 1)
            if variant == 'masked_regression':
                self.assertTrue(saved['passed']); self.assertTrue(comparisons['masked']['world_regressions'])
            if variant == 'regression_and_repair':
                self.assertFalse(saved['passed']); self.assertEqual(len(comparisons['canonical']['points']), 48)
                self.assertIsNone(comparisons['canonical']['mean_nll_change'])

    def test_complete_published_driver_and_pre_score_target_boundary(self):
        """Tiny fabricated v1/v2 stages exercise all100 trace paths and controls."""
        from experiments.predictive_nucleus.effect_role_model import create_registry
        bundle, predictions = fixture(); rehearsal, current, archived = retention_fixture()
        teach = deepcopy(rehearsal); teach['episodes'][0]['utterances'][0]['text'] = 'a lights b'
        registry = create_registry([rehearsal, teach]); unknown = ['unseen_alpha', 'unseen_beta']
        with tempfile.TemporaryDirectory() as folder:
            repo = Path(folder); root = repo / 'experiments/predictive_nucleus'
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
            config = {'model_seeds': list(audit.SEEDS), 'arms': list(audit.ARMS),
                'parameters': {'world': 562, 'grounded': 92, 'parser': 92, 'text_only': 1048},
                'training_forecasts': {'teach': 1, 'rehearsal': 1}, 'fresh_episodes_per_law': 24,
                'fresh_forecasts_per_law': 48, 'identifiable_forecasts_per_law': 48, 'ambiguous_forecasts_per_law': 0,
                'held_new_word_forecasts_per_law': 4, 'goal_groups_per_law': 6, 'goal_decisions_per_law': 24,
                'fresh_saved_forecasts': 1920, 'retention_saved_forecasts': 60, 'opened_saved_forecasts': 960,
                'total_saved_forecasts': 2940, 'analysis': LIMITS, 'unknown_tokens': unknown,
                'fit': {'updates': 1}, 'execution': {'runtime': {'python': 'synthetic'}}}
            training_artifacts = {'teach-inputs.json.xz': teach, 'rehearsal-inputs.json.xz': rehearsal,
                'lexical-registry.json': registry, 'parser-labels.json.xz': {'synthetic': 'unchanged'}}
            write(root / 'data/saturation-v1/train-inputs.json.xz', rehearsal)
            worlds = {}; native_state = {'vector': [0.] * 562}; world_digest = audit.h.fingerprint(native_state)[0]
            for law in audit.LAWS:
                for seed in audit.SEEDS:
                    name = f'{law}-{seed}.json'; path = root / 'data/set-acquisition-fit-v2' / name
                    worlds[f'{law}/{seed}'] = {'file': name, 'state_sha256': world_digest,
                        **write(path, {'state': native_state, 'state_sha256': world_digest})}
                for bank in audit.BANKS:
                    write(root / f'data/{bank}-v1/{law}-inputs.json.xz', rehearsal)
                    for seed in audit.SEEDS:
                        write(root / f'results/set-acquisition-v2/traces/trace-{law}-{seed}-acquired-{bank}_retention.json.xz',
                              {'input_sha256': audit.h.canonical(rehearsal), 'points': archived})
            parent_state = {'body': [0.] * 84, 'order.weight': [[[.1]], [[.2]]], 'order.bias': [0., 0.]}
            write(root / 'data/coordinate-fit-v1/checkpoints.json.xz', {'checkpoints': {
                f'coordinates/{seed}': {'state': parent_state} for seed in audit.SEEDS}})
            lexical = audit.lexical_receipt(registry, [rehearsal, teach], unknown)
            stage = {}
            for version in (1, 2):
                data = root / f'data/effect-role-v{version}'; fitted = root / f'data/effect-role-fit-v{version}'
                traces = root / f'results/effect-role-v{version}/traces'; scored = traces.parent / 'scored'
                config = {**config, 'version': f'effect-role-v{version}'}
                if version == 2: config['parent_result_publication'] = stage[1]['publication']
                protocol = root / f'effect_role_protocol_v{version}.json'; write(protocol, config)
                lock = root / f'snapshots/effect_role_protocol_v{version}.sha256'; lock.parent.mkdir(exist_ok=True)
                lock.write_text(audit.h.sha(protocol) + '\n')
                artifacts = {name: write(data / name, value) for name, value in training_artifacts.items()}
                for law in audit.LAWS:
                    artifacts[law + '-inputs.json.xz'] = write(data / f'{law}-inputs.json.xz', bundle['inputs'])
                    artifacts[law + '-evaluator.json.xz'] = write(data / f'{law}-evaluator.json.xz',
                        {k: v for k, v in bundle.items() if k != 'inputs'})
                freeze = {'version': config['version'], 'sources': {protocol.name: audit.h.sha(protocol)},
                    'historical': {}, 'artifacts': artifacts, 'world_checkpoints': worlds,
                    'runtime': config['execution']['runtime'], 'runtime_sha256': audit.h.canonical(config['execution']['runtime']),
                    'protocol_sha256': audit.h.sha(protocol)}
                if version == 2: freeze['parent_result_publication'] = config['parent_result_publication']
                write(data / 'freeze.json', freeze)
                write(root / f'effect_role_freeze_v{version}.json', {p.name: audit.h.sha(p) for p in data.iterdir()})
                source_commit = commit('synthetic source and data ' + str(version))
                identity = {'source_publication': source_commit, 'runtime': freeze['runtime'], 'freeze_sha256': audit.h.sha(data / 'freeze.json')}
                write(fitted / 'attempt.json', identity); weights, reports = {}, {}
                for arm in audit.ARMS:
                    for seed in audit.SEEDS:
                        state = deepcopy(parent_state); state['order.weight'] += [[[0.]], [[0.]]]; state['order.bias'] += [0., 0.]
                        if arm == 'text_only': state = {'body': [0.] * 1048}
                        digest, count = audit.h.fingerprint(state); key = f'{arm}/{seed}'; name = f'{arm}-{seed}.json'
                        weights[key] = {'file': name, **write(fitted / name, {'arm': arm, 'seed': seed, 'state': state, 'state_sha256': digest})}
                        reports[key] = {'initial_sha256': digest, 'final_sha256': digest, 'world_sha256': world_digest,
                            'world_unchanged': True, 'parameters': count, 'settings': config['fit'], 'updates': 1,
                            'observed_forecasts_per_update': config['training_forecasts'], 'fresh_optimizer': True,
                            'optimizer': {'name': 'Adam', 'betas': [.9, .999], 'eps': 1e-8, 'weight_decay': 0., 'amsgrad': False},
                            'resources': {'synthetic_stage': version}, 'curve': [[0, 1.]]}
                        write(fitted / f'fit-{arm}-{seed}.json', reports[key])
                trained = {**identity, 'version': config['version'], 'complete': True, 'checkpoints': weights, 'reports': reports,
                    'training_input_sha256': {'teach': audit.h.canonical(teach), 'rehearsal': audit.h.canonical(rehearsal)}}
                reproduction = {'version': 'effect-role-text-only-reproduction-v2', 'passed': True, 'resources_excluded': True,
                    'seeds': {str(seed): {'checkpoint_bytes_equal': True, 'report_except_resources_equal': True,
                        'checkpoint_sha256': weights[f'text_only/{seed}']['sha256'],
                        'state_sha256': reports[f'text_only/{seed}']['final_sha256']} for seed in audit.SEEDS}}
                if version == 2: trained['text_only_reproduction'] = reproduction
                write(fitted / 'training.json', trained); weight_commit = commit('synthetic weights ' + str(version))
                raw_identity = {'weights_publication': weight_commit, 'runtime': freeze['runtime'],
                    'freeze_sha256': identity['freeze_sha256'], 'training_sha256': audit.h.sha(fitted / 'training.json')}
                write(traces / 'attempt.json', raw_identity)
                raw_files = {'lexical-identities.json': write(traces / 'lexical-identities.json', lexical)}
                for law in audit.LAWS:
                    for seed in audit.SEEDS:
                        for arm in audit.ARMS:
                            banks = ('fresh', *(b + '_retention' for b in audit.BANKS), *((audit.OPENED,) if version == 2 else ())) if arm == 'grounded' else ('fresh',)
                            for bank in banks:
                                name = f'trace-{law}-{seed}-{arm}-{bank}.json.xz'; challenge = bank in ('fresh', audit.OPENED)
                                raw_files[name] = write(traces / name, {**raw_identity, 'law': law, 'seed': seed, 'arm': arm,
                                    'bank': bank, 'input_sha256': audit.h.canonical(bundle['inputs'] if challenge else rehearsal),
                                    'state_sha256': reports[f'{arm}/{seed}']['final_sha256'], 'points': predictions[arm] if challenge else current})
                write(traces / 'manifest.json', {**raw_identity, 'complete': True, 'oracle_opened': False, 'artifacts': raw_files})
                raw_commit = commit('synthetic raw ' + str(version))
                if version == 1:
                    write(scored / 'decision.json', {'decision': 'REVISE_EFFECT_ROLE_GROUNDING', 'synthetic': True})
                    stage[1] = {'publication': commit('synthetic parent decision')}
            command = [sys.executable, audit.__file__, '--repo', str(repo), '--publication', raw_commit]
            # A separate process prevents test-only scorer/model imports entering the auditor.
            guard = ('import sys; sys.path.insert(0,sys.argv[1]); import audit_effect_role_saved_v2 as a; '
                'read=a.h.read; a.h.read=lambda p: (_ for _ in ()).throw(AssertionError(str(p))) '
                'if "evaluator" in str(p) or "/scored/" in str(p) else read(p); '
                'r=a.audit_saved(a.Path(sys.argv[2]),a.h.Audit(),True,sys.argv[3]); '
                'assert r["audit_passed"] and r["trace_files"]==100 and r["archived_forecasts_validated"]==1920')
            subprocess.run([sys.executable, '-c', guard, str(Path(audit.__file__).parent), str(repo), raw_commit], check=True)
            fresh = scoring.analyze(bundle, predictions, LIMITS)
            opened = scoring.analyze_opened(bundle, predictions, predictions['grounded'], LIMITS)
            retained = scoring.retention(rehearsal, current, archived, LIMITS); score_files, checks = {}, {}
            for law in audit.LAWS:
                for seed in audit.SEEDS:
                    key = f'{law}/{seed}'; checks[key] = {**fresh['checks'], **{'opened/' + k: v for k, v in opened['checks'].items()},
                        **{bank + '_retention/' + k: v for bank in audit.BANKS for k, v in retained['checks'].items()}}
                    score_files[key] = write(scored / f'report-{law}-{seed}.json.xz', {'fresh': fresh, 'opened': opened,
                        'retention': {bank + '_retention': retained for bank in audit.BANKS}})
            write(scored / 'manifest.json', {'runtime': freeze['runtime'], 'traces_publication': raw_commit,
                'trace_manifest_sha256': audit.h.sha(traces / 'manifest.json'), 'reports': score_files})
            write(scored / 'decision.json', {'checks': checks, 'lexical_identity_checks': lexical['checks'],
                'text_only_reproduction': reproduction, 'decision': 'DEVELOPMENT_G3_COMPLETE', 'g3_complete': True,
                'execution_complete': True, 'scientific_admission': False, 'next_stage': 'G4'})
            completed = subprocess.run([*command, '--output', str(repo / 'audit.json')], check=True, capture_output=True, text=True)
            self.assertIn('"audit_passed": true', completed.stdout)
            result = audit.h.read(repo / 'audit.json'); self.assertEqual(result['trace_files'], 100)
            self.assertEqual(result['forecast_counts'], {'fresh': 1920, 'retention': 60, 'opened': 960})
            self.assertEqual(result['text_only_reproduction'], reproduction)
            # Alter a saved control curve while leaving its tensor bytes and claimed receipt unchanged.
            # This must fail before any evaluator access, even after rebinding the current raw manifest.
            trained['reports']['text_only/7']['curve'] = [[0, .5]]
            write(fitted / 'training.json', trained); write(fitted / 'fit-text_only-7.json', trained['reports']['text_only/7'])
            manifest = audit.h.read(traces / 'manifest.json'); manifest['training_sha256'] = audit.h.sha(fitted / 'training.json')
            write(traces / 'manifest.json', manifest); attempt = audit.h.read(traces / 'attempt.json')
            attempt['training_sha256'] = manifest['training_sha256']; write(traces / 'attempt.json', attempt)
            reject = '''import sys
sys.path.insert(0, sys.argv[1])
import audit_effect_role_saved_v2 as a
checked = a.h.Audit()
read = a.h.read
def observed_only(path):
    if 'evaluator' in str(path) or '/scored/' in str(path):
        raise AssertionError('targets parsed before raw/control validation')
    return read(path)
a.h.read = observed_only
try:
    a.audit_saved(a.Path(sys.argv[2]), checked, True, sys.argv[3])
except ValueError:
    assert 'exact text-only control reproduction' in checked.discrepancies, checked.discrepancies
else:
    raise AssertionError('changed control curve accepted')
'''
            subprocess.run([sys.executable, '-c', reject, str(Path(audit.__file__).parent), str(repo), raw_commit], check=True)


if __name__ == '__main__': unittest.main()
