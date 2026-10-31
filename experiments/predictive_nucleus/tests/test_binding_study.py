"""Prospective-data/runner invariants; synthetic fits are not scientific scores."""
from copy import deepcopy
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import torch

from experiments.predictive_nucleus import binding_data as data, binding_study as run
from experiments.predictive_nucleus import binding_scoring as score, bilingual_run as prior
from experiments.predictive_nucleus.binding_model import encoder
from experiments.predictive_nucleus.bilingual_model import freeze_world, tokenize_batch
from experiments.predictive_nucleus.bilingual_contract import validate_inputs
from experiments.predictive_nucleus.continuation_run import _read, _write
from experiments.predictive_nucleus.domain_kernel import DomainKernel
from experiments.predictive_nucleus.joint_objective import fingerprint
from experiments.predictive_nucleus.tests.test_binding import observations


class BindingBankTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.assets = data.build_assets()

    def test_reproducible_recipe_and_exact_prescribed_inventory(self):
        self.assertEqual(self.assets, data.build_assets())
        audit = self.assets['audit']
        self.assertEqual((audit['train_episodes'], audit['train_forecasts']), (896, 1024))
        self.assertEqual((audit['challenge_episodes_per_law'], audit['challenge_forecasts_per_law']), (384, 1728))
        self.assertEqual(len(audit['held_cells']), 8)

    def test_preparation_matches_the_public_data_commitment(self):
        with tempfile.TemporaryDirectory() as folder:
            destination = Path(folder) / 'prepared'; run.prepare(destination)
            run.verify(destination)
            (destination / 'audit.json').write_text('{}')
            with self.assertRaises(ValueError): run.verify(destination)

    def test_actual_exposure_has_no_held_cell(self):
        seen = set()
        for episode in self.assets['train']['episodes']:
            for event in episode['utterances']:
                words = event['text'].split(); word = next(w for w in words if w not in episode['entities'])
                layout = {1: 'svo', 2: 'osv', 0: 'vos'}[words.index(word)]
                seen.add((word, layout))
        self.assertFalse(seen & set(map(tuple, self.assets['audit']['held_cells'])))
        for bank in (self.assets['nand'], self.assets['nor']):
            for case in bank['oracle']['episodes']:
                for cell in case['cells']: self.assertEqual(cell['held'], (cell['word'], cell['layout']) not in seen)

    def test_inputs_reject_gold_and_original_training_is_retained_verbatim(self):
        self.assertEqual(self.assets['train'], validate_inputs(self.assets['train']))
        original = _read(run.io.ROOT / 'data/bilingual-v1/train-inputs.json.xz')['episodes']
        self.assertEqual(self.assets['train']['episodes'][:len(original)], original)
        value = deepcopy(self.assets['train']); value['episodes'][0]['action_orders'] = [0]
        with self.assertRaises(ValueError): validate_inputs(value)

    def test_independent_truth_table_audits_every_new_reading_and_action(self):
        for law in ('nand', 'nor'):
            records, gold, pairs = score.oracle(self.assets[law]['inputs'], self.assets[law]['oracle'], law)
            self.assertEqual(len(records), 384); self.assertEqual(len(gold), 384)
            self.assertEqual({k: len(v) for k, v in pairs.items()}, {'lexical': 192, 'role': 192})

    def test_truth_table_audit_rejects_corrupt_foils(self):
        bad = deepcopy(self.assets['nand']['oracle']); bad['episodes'][0]['opposite_truth'][0][0] ^= 1
        with self.assertRaises(ValueError): score.oracle(self.assets['nand']['inputs'], bad, 'nand')

    def test_third_layout_and_mixed_sequence_are_not_renamed_old_layouts(self):
        for case in self.assets['nand']['oracle']['episodes']:
            self.assertEqual({cell['layout'] for cell in case['cells']}, {'svo', 'osv', 'vos'})
            self.assertIn(case['family'], ('return4', 'cross5'))
        roster = ['A', 'B', 'C']; features, _ = tokenize_batch(
            ['A tav B', 'B A tav', 'tav B A'], [roster] * 3)
        self.assertEqual(features[:, :, 0].tolist(), [[1., 0., 1.], [1., 1., 0.], [0., 1., 1.]])

    def test_all_planned_lexical_pairs_are_retained_without_target_filtering(self):
        records, gold, pairs = score.oracle(self.assets['nand']['inputs'], self.assets['nand']['oracle'], 'nand')
        distinct = [gold[a]['truth'][-1] != gold[b]['truth'][-1] for a, b in pairs['lexical'].values()]
        self.assertEqual(sum(distinct), 192)  # Audited design property, not a model score.
        self.assertEqual(len(distinct), 192)

    def test_scorer_accepts_synthetic_ideal_vectors_and_detects_one_broken_cell(self):
        import math
        from experiments.predictive_nucleus.acceptance_scoring import _index
        records, gold, pairs = score.oracle(self.assets['nand']['inputs'], self.assets['nand']['oracle'], 'nand')
        rows = {}
        for identity, record in records.items():
            count = 2 ** len(record['entities'])
            for t in range(len(record['utterances'])):
                logs = [math.log(.001 / (count - 1))] * count
                logs[_index(gold[identity]['truth'][t])] = math.log(.999)
                order = [math.log(.001)] * 2; order[gold[identity]['action_orders'][t]] = math.log(.999)
                rows[identity, t, 'canonical'] = {'id': identity, 'step': t, 'view': 'canonical',
                    'logp': logs, 'order_logp': order}
            rows[identity, t, 'masked'] = {'id': identity, 'step': t, 'view': 'masked',
                'logp': [-math.log(count)] * count, 'order_logp': [-math.log(2)] * 2}
        for a, b in pairs['lexical'].values():
            t = len(records[a]['utterances']) - 1
            for x, y in ((a, b), (b, a)):
                rows[x, t, 'swapped'] = dict(rows[y, t, 'canonical'], id=x, view='swapped')
        report, _ = score.summary(rows, records, gold, pairs, run.protocol()['analysis'])
        self.assertTrue(all(report['checks'].values()))
        first = next(iter(records)); selected = gold[first]['family'], gold[first]['cells'][0]
        for identity in records:
            for t, cell in enumerate(gold[identity]['cells']):
                if (gold[identity]['family'], cell) == selected:
                    row = rows[identity, t, 'canonical']
                    row['order_logp'] = row['order_logp'][::-1]
        report, _ = score.summary(rows, records, gold, pairs, run.protocol()['analysis'])
        self.assertFalse(report['checks']['cell_order_accuracy'])

    def test_no_duplicate_new_word_features(self):
        words = [word for pair in data.PAIRS for word in pair]
        features, _ = tokenize_batch(['A ' + word + ' B' for word in words], [['A', 'B', 'C']] * len(words))
        self.assertEqual(len({tuple(row) for row in features[:, 1, 1:].tolist()}), len(words))


class BindingStudyTests(unittest.TestCase):
    def synthetic(self):
        value = observations()
        for episode in value['episodes']:
            for event in episode['utterances']:
                event['text'] = event['text'].replace('oddword', 'tav').replace('otherword', 'zun')
        return value

    def test_final_controls_preserve_prefix_mentions_and_model_state(self):
        world = freeze_world(DomainKernel(hidden=2, persistence=False, role_tying=False, memory=True))
        net = encoder('factor', 7).eval(); before = fingerprint(net.state_dict())
        for group in prior.pack(self.synthetic(), world):
            with torch.no_grad(): rows = list(run.probes(net, world, group))
            last = len(group['events']) - 1
            self.assertEqual([(view, t) for view, t, _, _ in rows],
                             [('canonical', t) for t in range(last + 1)] + [('masked', last), ('swapped', last)])
            canonical = list(prior.forecasts('grounded', net, world, group))
            for (_, _, raw, order), (reference, binding) in zip(rows, canonical):
                self.assertTrue(torch.equal(raw, reference)); self.assertTrue(torch.equal(order, binding))
        self.assertEqual(fingerprint(net.state_dict()), before)

    def test_trace_validation_rejects_missing_duplicate_or_unnormalized_points(self):
        observed = self.synthetic(); points = []
        for episode in observed['episodes']:
            for t in range(len(episode['utterances'])):
                points.append({'id': episode['id'], 'step': t, 'view': 'canonical',
                    'logp': [-2.0794415416798357] * 8, 'order_logp': [-0.6931471805599453] * 2})
        self.assertEqual(len(score.index_trace({'points': points}, observed, False)), 3)
        for bad in (points[:-1], points + [points[0]], [dict(points[0], logp=[0.] * 8)] + points[1:]):
            with self.assertRaises(ValueError): score.index_trace({'points': bad}, observed, False)

    def test_exact_and_probability_regressions_remain_separate(self):
        current = {('a', 0): {'correct': True, 'nll': .2}, ('b', 0): {'correct': False, 'nll': .8}}
        old = {('a', 0): {'correct': False, 'nll': .9}, ('b', 0): {'correct': True, 'nll': .1}}
        result = score.deltas(current, old)
        self.assertEqual(result['repairs'], [['a', 0]]); self.assertEqual(result['regressions'], [['b', 0]])
        self.assertEqual(len(result['nll_worse']), 1); self.assertEqual(len(result['nll_better']), 1)
        with self.assertRaises(ValueError): score.deltas(current, {})

    def test_infinite_probability_losses_are_not_silently_dropped(self):
        current = {('a', 0): {'correct': False, 'nll': float('inf')}, ('b', 0): {'correct': True, 'nll': .1}}
        old = {('a', 0): {'correct': False, 'nll': float('inf')}, ('b', 0): {'correct': False, 'nll': float('inf')}}
        result = score.deltas(current, old)
        self.assertIsNone(result['mean_nll_change'])
        self.assertEqual(result['nll_undefined_difference'], [['a', 0]])
        self.assertEqual(result['nll_better'], [['b', 0, -float('inf')]])

    def test_synthetic_fit_persistence_and_tamper_rejection(self):
        observed = self.synthetic(); config = deepcopy(run.protocol())
        config.update(model_seeds=[7], train_forecasts=3); config['fit']['updates'] = 1
        world = freeze_world(DomainKernel(hidden=2, persistence=False, role_tying=False, memory=True))
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); prepared = root / 'data'; prepared.mkdir(); fitted = root / 'fit'
            _write(prepared / 'freeze.json', {}); _write(prepared / 'train-inputs.json.xz', observed)
            with patch.object(run, 'verify', return_value=(config, {'checkpoints': {}})), \
                 patch.object(run.io, '_runtime', return_value={'synthetic': True}), \
                 patch.object(run.prior, 'world_for', return_value=world), redirect_stdout(StringIO()):
                run.fit(prepared, fitted, 'a' * 40)
            models = run.load_models(fitted, config, prepared)
            self.assertEqual(set(models), {'gru/7', 'factor/7', 'additive/7'})
            saved = _read(fitted / 'checkpoints.json.xz'); saved['reports']['7']['reports']['factor']['updates'] += 1
            (fitted / 'checkpoints.json.xz').unlink(); _write(fitted / 'checkpoints.json.xz', saved)
            with self.assertRaises(ValueError): run.load_models(fitted, config, prepared)

    def test_synthetic_collector_persists_all_views_without_opening_gold(self):
        observed = self.synthetic(); config = deepcopy(run.protocol()); config['model_seeds'] = [7]
        models = {arm + '/7': encoder(arm, 7).eval() for arm in ('gru', 'factor', 'additive')}
        world = freeze_world(DomainKernel(hidden=2, persistence=False, role_tying=False, memory=True))
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); prepared = root / 'data'; prepared.mkdir(); fitted = root / 'fit'; fitted.mkdir()
            _write(prepared / 'freeze.json', {}); _write(fitted / 'checkpoints.json.xz', {})
            for law in ('nand', 'nor'): _write(prepared / (law + '-inputs.json.xz'), observed)
            reads = []
            def read(path):
                reads.append(str(path)); return _read(path)
            with patch.object(run, 'verify', return_value=(config, {'checkpoints': {}})), \
                 patch.object(run.io, '_runtime', return_value={'synthetic': True}), \
                 patch.object(run.io, '_read', side_effect=read), patch.object(run, 'BANKS', {}), \
                 patch.object(run, 'load_models', return_value=models), \
                 patch.object(run.prior, 'world_for', return_value=world), redirect_stdout(StringIO()):
                run.collect(prepared, fitted, root / 'traces', 'b' * 40)
            manifest = _read(root / 'traces/manifest.json')
            self.assertEqual(len(manifest['artifacts']), 6); self.assertFalse(manifest['oracle_opened'])
            self.assertFalse(any('oracle' in path for path in reads))
            for name in manifest['artifacts']:
                trace = _read(root / 'traces' / name)
                self.assertEqual(len(score.index_trace(trace, observed, True)), 7)
                self.assertGreaterEqual(trace['resources']['batch_amortized_forecast_p95_seconds'], 0)

    def test_publication_attestation_requires_commit_shape(self):
        self.assertEqual(run.publication('a' * 40), 'a' * 40)
        for value in (None, '', 'a' * 39, 'g' * 40, 1):
            with self.assertRaises(ValueError): run.publication(value)


if __name__ == '__main__': unittest.main()
