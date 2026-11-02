"""Synthetic v3 audit checks restored after workspace loss; no real evidence."""
from copy import deepcopy
import json
import lzma
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from experiments.predictive_nucleus import audit_effect_role_saved_v2 as prior
from experiments.predictive_nucleus import audit_effect_role_saved_v3 as audit
from experiments.predictive_nucleus import effect_role_scoring_v3 as scoring
from experiments.predictive_nucleus.tests.test_effect_role_scoring import fixture, retention_fixture, LIMITS, one_hot


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = (json.dumps(audit.h.safe(value), sort_keys=True, indent=2, allow_nan=False) + '\n').encode()
    path.write_bytes(lzma.compress(raw) if str(path).endswith('.xz') else raw)
    return {'sha256': audit.h.sha(path), 'bytes': path.stat().st_size}


class EffectRoleSavedAuditV3Tests(unittest.TestCase):
    def test_frozen_arithmetic_reused_and_study_origins_are_distinct(self):
        for name in ('index_rows', 'inventory', 'measured', 'retained', 'lexical_receipt', 'verify_analysis', 'opened_comparison'):
            self.assertIs(getattr(audit, name), getattr(prior, name))
        bundle, traces = fixture()
        for version in audit.REFERENCES:
            saved = scoring.analyze_opened(bundle, traces, traces['grounded'], LIMITS, version)
            self.assertEqual(saved['evidence_roles'], audit.evidence_roles(version)); self.assertEqual(saved['reference_study'], version)
        code = ('import sys; from experiments.predictive_nucleus import audit_effect_role_saved_v3; '
            'assert "torch" not in sys.modules; assert not any(k.endswith(("effect_role_scoring", '
            '"effect_role_scoring_v2", "effect_role_scoring_v3", "effect_role_model", '
            '"effect_role_lexical", "effect_role_data_v3")) for k in sys.modules)')
        subprocess.run([sys.executable, '-B', '-c', code], check=True)

    def test_exact_protected88_and_learned4_with_no_extra_saved_parameters(self):
        parent = {'body': [0.] * 84, 'order.weight': [[[.1]], [[.2]]], 'order.bias': [0., 0.]}
        state = {'parent.' + k: deepcopy(v) for k, v in parent.items()}; state['new_coordinates'] = [[.3, -.2], [2., 1.]]
        registry = {'legacy_tokens': ['old'], 'tokens': {'old': {'id': 'a' * 64}, 'new1': {'id': 'b' * 64}, 'new2': {'id': 'c' * 64}}}
        checked = audit.protected_state(state, parent, registry)
        self.assertEqual((checked['protected_parameters'], checked['learned_parameters']), (88, 4))
        self.assertEqual(checked['protected_final_sha256'], audit.h.fingerprint(parent)[0])
        self.assertEqual(checked['new_ids'], ['b' * 64, 'c' * 64])
        for defect in ('changed_parent', 'extra_weight', 'missing_weight', 'wrong_shape', 'nonfinite', 'extra_identity'):
            bad, lexicon = deepcopy(state), deepcopy(registry)
            if defect == 'changed_parent': bad['parent.body'][0] = .01
            elif defect == 'extra_weight': bad['hidden'] = [0.]
            elif defect == 'missing_weight': del bad['parent.order.bias']
            elif defect == 'wrong_shape': bad['new_coordinates'] = [0.] * 4
            elif defect == 'nonfinite': bad['new_coordinates'][0][0] = float('nan')
            else: lexicon['tokens']['new3'] = {'id': 'd' * 64}
            with self.subTest(defect=defect), self.assertRaises(ValueError): audit.protected_state(bad, parent, lexicon)

    def test_frozen_reference_identity_rejects_wrong_sources_and_updates(self):
        config = {'checkpoint_publication': 'a' * 40, 'implementation_publication': 'b' * 40}
        checkpoint = {'sha256': 'c' * 64, 'state_sha256': 'd' * 64}
        row = {'source_study': 'effect-role-v2', 'source_checkpoint_publication': config['checkpoint_publication'],
            'source_implementation_publication': config['implementation_publication'], 'source_training_sha256': 'e' * 64,
            'source_checkpoint_sha256': checkpoint['sha256'], 'state_sha256': checkpoint['state_sha256'],
            'parameters_frozen': True, 'model_updates': 0}
        audit.reference_provenance(row, config, 'e' * 64, checkpoint)
        for field in row:
            bad = deepcopy(row); bad[field] = False if field == 'model_updates' else 'wrong'
            with self.subTest(field=field), self.assertRaises(ValueError):
                audit.reference_provenance(bad, config, 'e' * 64, checkpoint)

    def test_exact_raw_inventory_rejects_missing_extra_and_interrupted_artifacts(self):
        artifacts = {'trace-test.json.xz', 'lexical-identities.json'}
        receipts = {'shard-test.json', 'shard-attempt-test.json'}
        with tempfile.TemporaryDirectory() as folder:
            directory = Path(folder)
            for name in artifacts | receipts | {'attempt.json', 'manifest.json'}:
                (directory / name).write_text('synthetic')
            audit.raw_inventory(directory, artifacts, receipts)
            for name in ('failure-test.json', 'trace-unmanifested.json.xz', 'unlisted.json'):
                path = directory / name; path.write_text('synthetic')
                with self.subTest(extra=name), self.assertRaisesRegex(ValueError, 'exact raw directory inventory'):
                    audit.raw_inventory(directory, artifacts, receipts)
                path.unlink()
            path = directory / 'shard-test.json'; path.unlink()
            with self.assertRaisesRegex(ValueError, 'exact raw directory inventory'):
                audit.raw_inventory(directory, artifacts, receipts)
            path.mkdir()
            with self.assertRaisesRegex(ValueError, 'exact raw directory inventory'):
                audit.raw_inventory(directory, artifacts, receipts)
            path.rmdir(); path.symlink_to(directory / 'attempt.json')
            with self.assertRaisesRegex(ValueError, 'exact raw directory inventory'):
                audit.raw_inventory(directory, artifacts, receipts)

    def test_complete_three_stage_driver_and_final_opened_row_before_targets(self):
        """Published synthetic stages cover160 traces,10 shards, missing v2 evidence and changed hardware."""
        from experiments.predictive_nucleus.effect_role_model import create_registry
        bundle, predictions = fixture(); rehearsal, current, archived = retention_fixture()
        teach = deepcopy(rehearsal); teach['episodes'] = [deepcopy(teach['episodes'][0]) for _ in range(2)]
        for i, word in enumerate(('lights', 'zef')):
            teach['episodes'][i]['id'] = 'teaching-' + str(i)
            teach['episodes'][i]['utterances'][0]['text'] = 'a ' + word + ' b'
        registry = create_registry([rehearsal, teach]); unknown = ['unseen_alpha', 'unseen_beta']
        archived_predictions = {'v1': deepcopy(predictions), 'v2': deepcopy(predictions)}
        adverse = next(r for r in archived_predictions['v2']['grounded'] if r['view'] == 'canonical')
        adverse['logp'], adverse['action_logp'] = one_hot(8, 0), one_hot(4, 1)
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
                'training_forecasts': {'teach': 2, 'rehearsal': 1}, 'fresh_episodes_per_law': 24,
                'fresh_forecasts_per_law': 48, 'identifiable_forecasts_per_law': 48, 'ambiguous_forecasts_per_law': 0,
                'held_new_word_forecasts_per_law': 4, 'goal_groups_per_law': 6, 'goal_decisions_per_law': 24,
                'fresh_saved_forecasts': 1920, 'retention_saved_forecasts': 60, 'opened_v1_saved_forecasts': 1920,
                'opened_v2_saved_forecasts': 1920, 'reference_v2_saved_forecasts': 960, 'total_saved_forecasts': 6780, 'analysis': LIMITS, 'unknown_tokens': unknown,
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
            for version in (1, 2, 3):
                data = root / f'data/effect-role-v{version}'; fitted = root / f'data/effect-role-fit-v{version}'
                traces = root / f'results/effect-role-v{version}/traces'; scored = traces.parent / 'scored'
                config = {**config, 'version': f'effect-role-v{version}'}
                if version > 1: config['parent_result_publication'] = stage[version - 1]['publication']
                if version == 3: config['reference_v2'] = {k: stage[2][k] for k in ('checkpoint_publication', 'implementation_publication')}
                protocol = root / f'effect_role_protocol_v{version}.json'; write(protocol, config)
                lock = root / f'snapshots/effect_role_protocol_v{version}.sha256'; lock.parent.mkdir(exist_ok=True)
                lock.write_text(audit.h.sha(protocol) + '\n')
                artifacts = {name: write(data / name, value) for name, value in training_artifacts.items()}
                for law in audit.LAWS:
                    artifacts[law + '-inputs.json.xz'] = write(data / f'{law}-inputs.json.xz', bundle['inputs'])
                    artifacts[law + '-evaluator.json.xz'] = write(data / f'{law}-evaluator.json.xz',
                        {k: v for k, v in bundle.items() if k != 'inputs'})
                numerical = {**config['execution']['runtime'], 'cpu': 'Intel-original' if version < 3 else 'AMD-current'}
                freeze = {'version': config['version'], 'sources': {protocol.name: audit.h.sha(protocol)},
                    'historical': {}, 'artifacts': artifacts, 'world_checkpoints': worlds,
                    'runtime': numerical, 'runtime_sha256': audit.h.canonical(numerical),
                    'protocol_sha256': audit.h.sha(protocol)}
                if version > 1: freeze['parent_result_publication'] = config['parent_result_publication']
                if version == 3:
                    freeze['historical']['results/effect-role-interruption-v2.json'] = audit.h.sha(root / 'results/effect-role-interruption-v2.json')
                write(data / 'freeze.json', freeze)
                write(root / f'effect_role_freeze_v{version}.json', {p.name: audit.h.sha(p) for p in data.iterdir()})
                source_commit = commit('synthetic source and data ' + str(version))
                identity = {'source_publication': source_commit, 'runtime': freeze['runtime'], 'freeze_sha256': audit.h.sha(data / 'freeze.json')}
                write(fitted / 'attempt.json', identity); weights, reports = {}, {}
                for arm in audit.ARMS:
                    for seed in audit.SEEDS:
                        if arm == 'text_only':
                            state = {'body': [(.001 if version == 3 else 0.)] * 1048}; initial_hash = audit.h.fingerprint(state)[0]
                        elif version < 3:
                            state = deepcopy(parent_state); state['order.weight'] += [[[0.]], [[0.]]]; state['order.bias'] += [0., 0.]
                            initial_hash = audit.h.fingerprint(state)[0]
                        else:
                            state = {'parent.' + name: deepcopy(value) for name, value in parent_state.items()}
                            state['new_coordinates'] = [[0., 0.], [0., 0.]]; initial_hash = audit.h.fingerprint(state)[0]
                            state['new_coordinates'] = [[.3, -.2], [1., .8]]
                        digest, count = audit.h.fingerprint(state); key = f'{arm}/{seed}'; name = f'{arm}-{seed}.json'
                        weights[key] = {'file': name, **write(fitted / name, {'arm': arm, 'seed': seed, 'state': state, 'state_sha256': digest})}
                        reports[key] = {'initial_sha256': initial_hash, 'final_sha256': digest, 'world_sha256': world_digest,
                            'world_unchanged': True, 'parameters': count, 'settings': config['fit'], 'updates': 1,
                            'observed_forecasts_per_update': config['training_forecasts'], 'fresh_optimizer': True,
                            'optimizer': {'name': 'Adam', 'betas': [.9, .999], 'eps': 1e-8, 'weight_decay': 0., 'amsgrad': False},
                            'resources': {'synthetic_stage': version}, 'curve': [[0, 1.]]}
                        if version == 3 and arm != 'text_only':
                            legacy = sorted(registry['tokens'][word]['id'] for word in registry['legacy_tokens'])
                            parent_hash = audit.h.fingerprint(parent_state)[0]
                            reports[key].update(protected_parameters=88, learned_parameters=4,
                                protected_initial_sha256=parent_hash, protected_final_sha256=parent_hash, protected_unchanged=True,
                                registry_sha256=audit.h.canonical(registry), legacy_ids=legacy,
                                new_ids=sorted({item['id'] for item in registry['tokens'].values()} - set(legacy)))
                        write(fitted / f'fit-{arm}-{seed}.json', reports[key])
                trained = {**identity, 'version': config['version'], 'complete': True, 'checkpoints': weights, 'reports': reports,
                    'training_input_sha256': {'teach': audit.h.canonical(teach), 'rehearsal': audit.h.canonical(rehearsal)}}
                write(fitted / 'training.json', trained); weight_commit = commit('synthetic weights ' + str(version))
                if version == 2:
                    write(root / 'results/effect-role-interruption-v2.json', {'decision': 'STOP_INCOMPLETE_EVIDENCE',
                        'execution_complete': False, 'g3_complete': False, 'scientific_decision': None,
                        'source_publication': source_commit, 'weights_publication': weight_commit,
                        'freeze_sha256': audit.h.sha(data / 'freeze.json')})
                    stage[2] = {'checkpoint_publication': weight_commit, 'implementation_publication': source_commit,
                        'fit': fitted, 'weights': weights, 'reports': reports, 'training_sha256': audit.h.sha(fitted / 'training.json')}
                    stage[2]['publication'] = commit('synthetic v2 incomplete evidence')
                    continue
                raw_identity = {'weights_publication': weight_commit, 'runtime': freeze['runtime'],
                    'freeze_sha256': identity['freeze_sha256'], 'training_sha256': audit.h.sha(fitted / 'training.json')}
                write(traces / 'attempt.json', raw_identity)
                raw_files = {'lexical-identities.json': write(traces / 'lexical-identities.json', lexical)}
                for law in audit.LAWS:
                    for seed in audit.SEEDS:
                        for arm in audit.ARMS:
                            banks = ('fresh', *(audit.OPENED.values() if version == 3 else ()),
                                     *((b + '_retention' for b in audit.BANKS) if arm == 'grounded' else ()))
                            for bank in banks:
                                name = f'trace-{law}-{seed}-{arm}-{bank}.json.xz'; challenge = bank in ('fresh', *audit.OPENED.values())
                                raw_files[name] = write(traces / name, {**raw_identity, 'law': law, 'seed': seed, 'arm': arm,
                                    'bank': bank, 'input_sha256': audit.h.canonical(bundle['inputs'] if challenge else rehearsal),
                                    'state_sha256': reports[f'{arm}/{seed}']['final_sha256'], 'points': predictions[arm] if challenge else current})
                        if version == 3:
                            key = f'grounded/{seed}'; name = f'trace-{law}-{seed}-reference_v2-opened_effect_role_v2.json.xz'
                            raw_files[name] = write(traces / name, {**raw_identity, 'law': law, 'seed': seed,
                                'arm': 'reference_v2', 'bank': audit.OPENED['v2'], 'input_sha256': audit.h.canonical(bundle['inputs']),
                                'state_sha256': stage[2]['reports'][key]['final_sha256'],
                                'source_study': 'effect-role-v2', 'source_checkpoint_publication': stage[2]['checkpoint_publication'],
                                'source_implementation_publication': stage[2]['implementation_publication'],
                                'source_training_sha256': stage[2]['training_sha256'],
                                'source_checkpoint_sha256': stage[2]['weights'][key]['sha256'],
                                'parameters_frozen': True, 'model_updates': 0, 'points': archived_predictions['v2']['grounded']})
                shards = {}
                if version == 3:
                    execution = weight_commit
                    for law in audit.LAWS:
                        for seed in audit.SEEDS:
                            key = f'{law}/{seed}'; name = f'shard-{law}-{seed}.json'; attempt_name = f'shard-attempt-{law}-{seed}.json'
                            identity_shard = {**raw_identity, 'law': law, 'seed': seed, 'execution_publication': execution}
                            attempt_item = {'file': attempt_name, **write(traces / attempt_name, identity_shard)}
                            shard = {**identity_shard, 'complete': True, 'oracle_opened': False,
                                'artifacts': {name: item for name, item in raw_files.items() if name.startswith(f'trace-{law}-{seed}-')},
                                'resources': {'cpu_seconds': 0., 'wall_seconds': 0., 'peak_rss_kib': 0}}
                            shards[key] = {'file': name, **write(traces / name, shard), 'attempt': attempt_item}
                            execution = commit('synthetic durable shard ' + key)
                raw_manifest = {**raw_identity, 'complete': True, 'oracle_opened': False, 'artifacts': raw_files}
                if version == 3: raw_manifest['shards'] = shards
                write(traces / 'manifest.json', raw_manifest)
                raw_commit = commit('synthetic sealed raw ' + str(version))
                if version < 3:
                    write(scored / 'decision.json', {'decision': 'REVISE_EFFECT_ROLE_GROUNDING', 'synthetic': True})
                    stage[version] = {'publication': commit('synthetic parent decision')}
            command = [sys.executable, audit.__file__, '--repo', str(repo), '--publication', raw_commit]
            # A separate process prevents test-only scorer/model imports entering the auditor.
            guard = """import sys
sys.path.insert(0, sys.argv[1])
import audit_effect_role_saved_v3 as a
read = a.h.read
def observed_only(path):
    if 'evaluator' in str(path) or '/scored/' in str(path):
        raise AssertionError('targets parsed before all raw evidence')
    return read(path)
a.h.read = observed_only
if sys.argv[4] == 'pass':
    result = a.audit_saved(a.Path(sys.argv[2]), a.h.Audit(), True, sys.argv[3])
    assert result['audit_passed'] and result['trace_files'] == 160
    assert result['archived_forecasts_validated'] == {'v1': 960}
else:
    try:
        a.audit_saved(a.Path(sys.argv[2]), a.h.Audit(), True, sys.argv[3])
    except ValueError as error:
        assert str(error) == 'missing raw forecasts', str(error)
    else:
        raise AssertionError('missing final opened-v2 row accepted')
"""
            subprocess.run([sys.executable, '-c', guard, str(Path(audit.__file__).parent), str(repo), raw_commit, 'pass'], check=True)
            fresh = scoring.analyze(bundle, predictions, LIMITS)
            opened = {version: scoring.analyze_opened(bundle, predictions, archived_predictions[version]['grounded'], LIMITS, version)
                      for version in audit.REFERENCES}
            self.assertEqual(opened['v1']['comparisons']['canonical']['world_repairs'], [])
            self.assertEqual(len(opened['v2']['comparisons']['canonical']['world_repairs']), 1)
            retained = scoring.retention(rehearsal, current, archived, LIMITS); score_files, checks = {}, {}
            for law in audit.LAWS:
                for seed in audit.SEEDS:
                    key = f'{law}/{seed}'; checks[key] = {**fresh['checks'], **{'opened_' + version + '/' + k: v for version in audit.REFERENCES for k, v in opened[version]['checks'].items()},
                        **{bank + '_retention/' + k: v for bank in audit.BANKS for k, v in retained['checks'].items()}}
                    score_files[key] = write(scored / f'report-{law}-{seed}.json.xz', {'fresh': fresh, 'opened': opened,
                        'retention': {bank + '_retention': retained for bank in audit.BANKS}})
            write(scored / 'manifest.json', {'runtime': freeze['runtime'], 'traces_publication': raw_commit,
                'trace_manifest_sha256': audit.h.sha(traces / 'manifest.json'), 'reports': score_files})
            write(scored / 'decision.json', {'checks': checks, 'lexical_identity_checks': lexical['checks'],
                'decision': 'DEVELOPMENT_G3_COMPLETE', 'g3_complete': True,
                'execution_complete': True, 'scientific_admission': False, 'next_stage': 'G4'})
            completed = subprocess.run([*command, '--output', str(repo / 'audit.json')], check=True, capture_output=True, text=True)
            self.assertIn('"audit_passed": true', completed.stdout)
            result = audit.h.read(repo / 'audit.json'); self.assertEqual(result['trace_files'], 160)
            self.assertEqual(result['forecast_counts'], {'fresh': 1920, 'retention': 60, 'opened_v1': 1920, 'opened_v2': 1920, 'reference_v2': 960})
            self.assertEqual(result['shard_receipts_validated'], 10)
            self.assertFalse((root / 'results/effect-role-v2/traces').exists())
            self.assertFalse((root / 'results/effect-role-v2/scored').exists())
            self.assertEqual(len(result['protected_language_states']), 10)
            # Published malformed final rows must fail inventory, not just a checksum.
            name = 'trace-nor-53-reference_v2-opened_effect_role_v2.json.xz'
            value = audit.h.read(traces / name); value['points'].pop()
            raw_files[name] = write(traces / name, value)
            item = shards['nor/53']; shard = audit.h.read(traces / item['file']); shard['artifacts'][name] = raw_files[name]
            shards['nor/53'] = {'file': item['file'], **write(traces / item['file'], shard), 'attempt': item['attempt']}
            write(traces / 'manifest.json', {**raw_identity, 'complete': True, 'oracle_opened': False, 'artifacts': raw_files, 'shards': shards})
            broken_commit = commit('synthetic malformed final raw row')
            subprocess.run([sys.executable, '-c', guard, str(Path(audit.__file__).parent), str(repo), broken_commit, 'fail'], check=True)


if __name__ == '__main__': unittest.main()
