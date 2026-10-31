"""Synthetic wiring and data-inventory tests; no research weights are evaluated."""
from contextlib import redirect_stdout
from copy import deepcopy
from io import StringIO
from pathlib import Path
import json
import math
import tempfile
import unittest
from unittest.mock import patch

import torch

from experiments.predictive_nucleus import saturation_data as data, saturation_run as run
from experiments.predictive_nucleus import saturation_scoring as scoring, binding_scoring as old
from experiments.predictive_nucleus.bilingual_model import freeze_world, tokenize_batch
from experiments.predictive_nucleus.bilingual_contract import validate_inputs
from experiments.predictive_nucleus.continuation_run import _read, _write
from experiments.predictive_nucleus.domain_kernel import DomainKernel
from experiments.predictive_nucleus.joint_objective import fingerprint
from experiments.predictive_nucleus.tests.test_binding import observations


def toy_world():
    with torch.random.fork_rng(devices=[]):
        torch.manual_seed(819)
        return freeze_world(DomainKernel(hidden=2, persistence=False, role_tying=False, memory=True))


def toy_inputs():
    value = observations()
    for record in value['episodes']:
        for event in record['utterances']:
            event['text'] = event['text'].replace('oddword', 'kef').replace('otherword', 'wom')
    return value


class SaturationDataTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.assets = data.build_assets()

    def test_reproducible_prescribed_data_inventory(self):
        self.assertEqual(self.assets, data.build_assets())
        a = self.assets['audit']
        self.assertEqual((a['old_training_forecasts'], a['train_forecasts']), (1024, 1152))
        self.assertEqual((a['challenge_episodes_per_law'], a['challenge_forecasts_per_law']), (384, 1728))
        self.assertEqual(len(a['held_cells_new']), 8)

    def test_original_training_is_byte_semantically_retained_and_no_gold_passes(self):
        original = _read(run.io.ROOT / 'data/binding-v1/train-inputs.json.xz')['episodes']
        self.assertEqual(original, self.assets['train']['episodes'][:len(original)])
        bad = deepcopy(self.assets['train']); bad['episodes'][0]['action_orders'] = [0]
        with self.assertRaises(ValueError): validate_inputs(bad)

    def test_held_cells_never_appear_in_training(self):
        cells = set()
        for record in self.assets['train']['episodes']:
            for event in record['utterances']:
                words = event['text'].split(); word = next(w for w in words if w not in record['entities'])
                cells.add((word, {0: 'vos', 1: 'svo', 2: 'osv'}[words.index(word)]))
        self.assertFalse(cells & set(map(tuple, self.assets['audit']['held_cells_new'])))
        for gold in self.assets['nand']['oracle']['episodes']:
            for cell in gold['cells']: self.assertEqual(cell['held'], (cell['word'], cell['layout']) not in cells)

    def test_new_words_are_not_old_challenge_lexemes_and_features_do_not_collide(self):
        known = set(data.old.SWAPS)
        self.assertFalse(set(data.WORDS.values()) & known)
        words = sorted(known | set(data.WORDS.values()))
        features, _ = tokenize_batch(['A ' + w + ' B' for w in words], [['A', 'B', 'C']] * len(words))
        self.assertEqual(len({tuple(v) for v in features[:, 1, 1:].tolist()}), len(words))
        for gold in self.assets['nand']['oracle']['episodes']:
            self.assertEqual(set(i for a in gold['actions'] for i in a[1:3]), set(range(4 if gold['family'] == 'diamond4' else 5)))

    def test_independent_truth_table_audits_every_mode_role_and_pair(self):
        for law in ('nand', 'nor'):
            records, gold, pairs = old.oracle(self.assets[law]['inputs'], self.assets[law]['oracle'], law)
            self.assertEqual(len(records), 384)
            self.assertEqual({k: len(v) for k, v in pairs.items()}, {'lexical': 192, 'role': 192})
            self.assertEqual(sum(gold[a]['truth'][-1] != gold[b]['truth'][-1] for a, b in pairs['lexical'].values()), 192)

    def test_prepared_bytes_match_public_commitment_and_reject_tampering(self):
        with tempfile.TemporaryDirectory() as folder:
            out = Path(folder) / 'prepared'; run.prepare(out); run.verify(out)
            (out / 'audit.json').write_text('{}')
            with self.assertRaises(ValueError): run.verify(out)


class SaturationTrainingTests(unittest.TestCase):
    def test_paired_initialization_exact_exposure_and_no_world_or_input_mutation(self):
        observed, world = toy_inputs(), toy_world(); before = deepcopy(observed)
        state = fingerprint(world.state_dict()); rng = torch.random.get_rng_state().clone()
        cfg = dict(run.protocol()['fit'], updates=1)
        expected = {arm: float(run.loss(run.encoder(arm, 7), world, run.prior.pack(observed, world))[0].detach()) for arm in run.ARMS}
        models, report = run.fit_pair(observed, world, 7, cfg)
        for arm in run.ARMS:
            self.assertEqual(report['reports'][arm]['observed_events_per_update'], 3)
            self.assertEqual(report['reports'][arm]['parameters'], 89)
            self.assertAlmostEqual(report['reports'][arm]['curve'][0][1], expected[arm], places=12)
            self.assertTrue(math.isfinite(report['reports'][arm]['final_observed_train_nll']))
            self.assertFalse(models[arm].training)
        self.assertEqual(report['reports']['factor']['initial_sha256'], report['reports']['unsaturated']['initial_sha256'])
        self.assertEqual(observed, before); self.assertEqual(state, fingerprint(world.state_dict()))
        self.assertTrue(all(p.grad is None for p in world.parameters()))
        self.assertTrue(torch.equal(rng, torch.random.get_rng_state()))

    def test_rejects_bad_budgets_labels_and_unfrozen_world(self):
        cfg = dict(run.protocol()['fit'], updates=1)
        for key, value in [('updates', True), ('updates', 0), ('learning_rate', 0), ('gradient_clip', float('nan'))]:
            with self.assertRaises(ValueError): run.fit_pair(toy_inputs(), toy_world(), 7, dict(cfg, **{key: value}))
        for seed in (True, -1):
            with self.assertRaises(ValueError): run.fit_pair(toy_inputs(), toy_world(), seed, cfg)
        bad = toy_inputs(); bad['episodes'][0]['utterances'][0]['order'] = 0
        with self.assertRaises(ValueError): run.fit_pair(bad, toy_world(), 7, cfg)
        world = toy_world().train()
        with self.assertRaises(ValueError): run.fit_pair(toy_inputs(), world, 7, cfg)
        self.assertTrue(world.training)

    def test_interruption_and_cpu_failure_do_not_return_completed_comparison(self):
        world = toy_world(); before = fingerprint(world.state_dict()); cfg = dict(run.protocol()['fit'], updates=1)
        with patch.object(torch.optim.Adam, 'step', side_effect=KeyboardInterrupt), self.assertRaises(KeyboardInterrupt):
            run.fit_pair(toy_inputs(), world, 7, cfg)
        with self.assertRaisesRegex(ValueError, 'CPU limit'):
            run.fit_pair(toy_inputs(), world, 7, dict(cfg, cpu_seconds_per_arm=1e-12))
        self.assertEqual(before, fingerprint(world.state_dict()))

    def test_controls_share_canonical_prefix_and_do_not_change_weights(self):
        world, net = toy_world(), run.encoder('unsaturated', 7); before = fingerprint(net.state_dict())
        for group in run.prior.pack(toy_inputs(), world):
            with torch.no_grad(): rows = list(run.probes(net, world, group))
            expected = list(run.prior.forecasts('grounded', net, world, group))
            self.assertEqual(len(rows), len(expected) + 2)
            for (_, _, raw, order), (a, b) in zip(rows, expected):
                self.assertTrue(torch.equal(raw, a)); self.assertTrue(torch.equal(order, b))
        self.assertEqual(before, fingerprint(net.state_dict()))

    def test_unknown_arm_fails(self):
        with self.assertRaises(ValueError): run.encoder('gru', 7)


class SaturationPipelineTests(unittest.TestCase):
    def fixture(self, root):
        prepared = root / 'data'; prepared.mkdir(); _write(prepared / 'freeze.json', {})
        _write(prepared / 'train-inputs.json.xz', toy_inputs())
        for law in ('nand', 'nor'):
            records, cases = [], []
            for direction in (0, 1):
                for polarity in (0, 1):
                    record, gold = data.episode(['synthetic-only'], 3, (0, 1, 0), 0, direction,
                        law, ((0, 1),), [(4, polarity)], [1])
                    gold.update(family='toy', polarity=polarity,
                                lexical_pair_id='lex-' + str(direction), role_pair_id='role-' + str(polarity))
                    records.append(record); cases.append(gold)
            inputs = {'version': 'bilingual-input-v1', 'episodes': records}
            _write(prepared / f'{law}-inputs.json.xz', inputs)
            _write(prepared / f'{law}-oracle.json.xz', {'version': 'binding-oracle-v1',
                'input_sha256': run.c.digest(inputs), 'episodes': cases})
        config = deepcopy(run.protocol()); config.update(model_seeds=[7], train_forecasts=3)
        config['fit']['updates'] = 1
        return prepared, config

    def test_complete_synthetic_pipeline_serializes_decision_and_rejects_reuse(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); prepared, config = self.fixture(root); world = toy_world()
            with patch.object(run, 'verify', return_value=(config, {'checkpoints': {}})), \
                 patch.object(run.io, '_runtime', return_value={'synthetic': True}), \
                 patch.object(run, 'BANKS', {}), patch.object(run.prior, 'world_for', return_value=world), \
                 redirect_stdout(StringIO()) as stdout:
                run.fit(prepared, root / 'fit', 'a' * 40)
                self.assertEqual(set(run.load_models(root / 'fit', config, prepared)), {'factor/7', 'unsaturated/7'})
                run.collect(prepared, root / 'fit', root / 'traces', 'b' * 40)
                scoring.score(prepared, root / 'fit', root / 'traces', root / 'score')
                with self.assertRaises(FileExistsError): run.fit(prepared, root / 'fit', 'a' * 40)
            decision = _read(root / 'score/decision.json')
            self.assertEqual(json.loads(stdout.getvalue().splitlines()[-1]), decision)
            self.assertFalse(decision['scientific_admission']); self.assertTrue(decision['execution_complete'])
            self.assertEqual(len(_read(root / 'traces/manifest.json')['artifacts']), 4)

    def test_missing_trace_is_rejected_before_targets_are_opened(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); prepared, config = self.fixture(root)
            with patch.object(run, 'verify', return_value=(config, {'checkpoints': {}})), \
                 patch.object(run.io, '_runtime', return_value={'synthetic': True}), patch.object(run, 'BANKS', {}), \
                 patch.object(run.prior, 'world_for', return_value=toy_world()), redirect_stdout(StringIO()):
                run.fit(prepared, root / 'fit', 'a' * 40); run.collect(prepared, root / 'fit', root / 'traces', 'b' * 40)
                path = root / 'traces/manifest.json'; manifest = _read(path); manifest['artifacts'].pop(next(iter(manifest['artifacts'])))
                path.unlink(); _write(path, manifest)
                reads = []
                def read(path): reads.append(str(path)); return _read(path)
                with patch.object(run.io, '_read', side_effect=read), self.assertRaises(ValueError):
                    scoring.score(prepared, root / 'fit', root / 'traces', root / 'score')
                self.assertFalse(any('oracle' in p for p in reads)); self.assertFalse((root / 'score').exists())

    def test_checkpoint_exposure_and_tensor_tampering_are_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); prepared, config = self.fixture(root)
            with patch.object(run, 'verify', return_value=(config, {'checkpoints': {}})), \
                 patch.object(run.io, '_runtime', return_value={'synthetic': True}), \
                 patch.object(run.prior, 'world_for', return_value=toy_world()), redirect_stdout(StringIO()):
                run.fit(prepared, root / 'fit', 'a' * 40)
            path = root / 'fit/checkpoints.json.xz'; original = _read(path)
            for mutate in ('updates', 'tensor', 'missing', 'initial'):
                saved = deepcopy(original)
                if mutate == 'updates': saved['reports']['7']['reports']['unsaturated']['updates'] = 2
                elif mutate == 'tensor': saved['checkpoints']['unsaturated/7']['state']['order.bias'][0] += .1
                elif mutate == 'missing': saved['checkpoints'].pop('factor/7')
                else: saved['reports']['7']['reports']['unsaturated']['initial_sha256'] = '0' * 64
                path.unlink(); _write(path, saved)
                with self.assertRaises(ValueError): run.load_models(root / 'fit', config, prepared)

    def test_scientific_decision_retains_regressions_and_probability_failures(self):
        config = deepcopy(run.protocol()); config['model_seeds'] = [7]
        saved = {'reports': {'7': {'reports': {'unsaturated': {'final_observed_train_nll': .01}}}}}
        reports = {law + '/7/unsaturated': {'checks': {'cell_nll': True}} for law in ('nand', 'nor')}
        clean = {'regressions': [], 'mean_nll_change': -.1}
        comparisons = {law + '/7': {'native': {'unsaturated': clean}, 'retention': {'unsaturated': {'old': clean}},
            'retention_pair': {'old': clean}, 'fresh_pair': clean} for law in ('nand', 'nor')}
        self.assertEqual(scoring.decide(reports, comparisons, saved, config)['decision'], 'KEEP_UNSATURATED_BINDING')
        changed = deepcopy(comparisons); changed['nand/7']['retention']['unsaturated']['old']['regressions'] = [['x', 0]]
        self.assertEqual(scoring.decide(reports, changed, saved, config)['decision'], 'REVISE_SATURATION_HYPOTHESIS')
        saved['reports']['7']['reports']['unsaturated']['final_observed_train_nll'] = .06
        self.assertFalse(scoring.decide(reports, comparisons, saved, config)['checks']['nor/7']['observed_training_fit'])


if __name__ == '__main__': unittest.main()
