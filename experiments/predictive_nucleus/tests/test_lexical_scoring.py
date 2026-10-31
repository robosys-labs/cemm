"""Saved synthetic probabilities test decisions and hostile artifacts; no models."""
from copy import deepcopy
import json
import math
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from experiments.predictive_nucleus import bilingual_data, lexical_data, lexical_scoring as score

LIMITS = {'min_accuracy': .95, 'max_mean_nll': .05, 'min_true_probability': .9,
    'max_wrong_order_probability': .1, 'min_lexical_probability_gap': .8,
    'max_twin_tv': .02, 'max_control_tv': 1e-10, 'min_prior_probe_accuracy_gain': .25}


def logs(target, p=.99, size=16):
    return [math.log(p if i == target else (1 - p) / (size - 1)) for i in range(size)]


def rows(bank, arm, p=.99):
    result = []
    for gold in bank['oracle']['episodes']:
        steps = [gold['contrast_step']] if arm in score.VIEWS else range(len(gold['truth']))
        for t in steps:
            wrong = (arm == 'prior' and t == gold['contrast_step'] and gold['effect_polarity'] == 1) or arm == 'swapped'
            wrong |= arm == 'cross_order' and gold['contrast_synonym'] == 1
            bits = gold['opposite_truth'][t] if wrong else gold['truth'][t]
            result.append({'id': gold['id'], 'step': t,
                'logp': [-math.log(16)] * 16 if arm == 'masked' else logs(score.previous._index(bits), p),
                'order_logp': logs(gold['action_orders'][t] ^ int(wrong), p, 2)})
    return result


class LexicalScoringTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.old, cls.fresh = {}, {}
        cfg = {'version': 'lexical-scoring-fixture', 'data': {'split_seeds': {'train': 20261031983, 'challenge': 20261031989},
            'train_entity_counts': [4], 'challenge_entity_counts': [4]}}
        for law in ('nand', 'nor'):
            bank = bilingual_data._bank(cfg, 'challenge', law)
            lineage = next(g['lineage'] for g in bank['oracle']['episodes'] if g['family'] == 'disjoint')
            selected = [(r, g) for r, g in zip(bank['inputs']['episodes'], bank['oracle']['episodes'], strict=True)
                        if g['lineage'] == lineage and g['mode'] == 0]
            inputs = {'version': 'bilingual-input-v1', 'episodes': [r for r, _ in selected]}
            cls.old[law] = {'inputs': inputs, 'oracle': {'version': 'bilingual-oracle-v1',
                'input_sha256': score.base.digest(inputs), 'episodes': [g for _, g in selected]}}
            cls.fresh[law] = lexical_data._contrast_bank(cls.old[law], 'challenge', law)

    def setUp(self):
        temporary = tempfile.TemporaryDirectory(); self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name); self.data, self.output, self.fitted = (self.root / p for p in ('data', 'output', 'fitted'))
        for path in (self.data, self.output, self.fitted, self.root / 'data/bilingual-v1', self.root / 'results/bilingual-v1'):
            path.mkdir(parents=True, exist_ok=True)
        patcher = patch.object(score.io, 'ROOT', self.root); patcher.start(); self.addCleanup(patcher.stop)
        self.config = {'version': 'lexical-test', 'model_seeds': [7], 'analysis': LIMITS,
            'fit': {'updates': 1, 'training_forecasts_per_update': 32},
            'parent_language_training_sha256': 'd' * 64, 'old_data_freeze_sha256': 'e' * 64}
        artifacts = {'train-inputs.json.xz': score.io._write(self.data / 'train-inputs.json.xz', self.old['nand']['inputs'])}
        for law in ('nand', 'nor'):
            for kind in ('inputs', 'oracle'):
                name = f'{law}-{kind}.json.xz'; artifacts[name] = score.io._write(self.data / name, self.fresh[law][kind])
                score.io._write(self.root / 'data/bilingual-v1' / name, self.old[law][kind])
        self.freeze = {'sources': {}, 'historical_artifacts': {}, 'artifacts': artifacts, 'checkpoints': {},
            'language_checkpoints': {'7': {'sha256': 'a' * 64, 'state_sha256': 'b' * 64}}}
        score.io._write(self.data / 'freeze.json', self.freeze); self.freeze_hash = score.io._hash(self.data / 'freeze.json')
        item = {'file': 'grounded-7.json', 'state_sha256': 'c' * 64,
                **score.io._write(self.fitted / 'grounded-7.json', {'synthetic_saved_checkpoint': True})}
        self.checkpoint = item['sha256']
        training = {'version': 'lexical-test', 'complete': True, 'world_checkpoints_unchanged': True,
            'freeze_sha256': self.freeze_hash, 'training_input_sha256': score.base.digest(self.old['nand']['inputs']),
            'checkpoints': {'grounded/7': item}, 'reports': {'grounded/7': {'parameters': 474, 'updates': 1,
                'training_forecasts_per_update': 32, 'parent_sha256': 'a' * 64, 'initial_sha256': 'b' * 64, 'final_sha256': 'c' * 64}}}
        score.io._write(self.fitted / 'training.json', training); self.training_hash = score.io._hash(self.fitted / 'training.json')
        for law in ('nand', 'nor'):
            for arm in score.ARMS:
                bank = self.old[law] if arm == 'retention' else self.fresh[law]
                trace = self.trace(bank, law, arm, rows(bank, arm))
                score.io._write(self.path(law, arm), trace)
            archived = self.trace(self.old[law], law, 'grounded', rows(self.old[law], 'grounded', .995))
            archived.update(checkpoint_sha256='a' * 64, training_sha256='d' * 64, freeze_sha256='e' * 64)
            score.io._write(self.root / f'results/bilingual-v1/trace-{law}-7-grounded.json.xz', archived)

    def trace(self, bank, law, arm, points):
        return {'law': law, 'seed': 7, 'arm': arm, 'points': points, 'resources': {},
            'input_sha256': score.base.digest(bank['inputs']), 'freeze_sha256': self.freeze_hash,
            'training_sha256': self.training_hash, 'checkpoint_sha256': 'a' * 64 if arm == 'prior' else self.checkpoint}

    def path(self, law='nand', arm='grounded'): return self.output / f'trace-{law}-7-{arm}.json.xz'

    def change(self, mutate, law='nand', arm='grounded'):
        path = self.path(law, arm); trace = score.io._read(path); mutate(trace)
        path.unlink(); score.io._write(path, trace)

    @staticmethod
    def native(inputs, gold, inventory, law, seed):
        return {(g['id'], t): {'id': g['id'], 'step': t, 'order_logp': None,
            'logp': logs(score.previous._index(bits), .995)} for g in gold.values() for t, bits in enumerate(g['truth'])}

    def evaluate(self):
        with patch.object(score.previous, '_native', side_effect=self.native):
            return score.evaluate(self.data, self.output, self.config, self.freeze, self.fitted)

    def test_primary_keep_is_separate_from_failed_structural_transfer_and_nll_retention(self):
        report = self.evaluate(); decision = report['decision']
        self.assertEqual(decision['decision'], 'KEEP_LEXICAL_GROUNDING')
        self.assertEqual(decision['structural_transfer'], 'STRUCTURAL_TRANSFER_NOT_ESTABLISHED')
        self.assertTrue(all(decision['structural_checks']['nand/7']['seen'].values()))
        self.assertFalse(decision['structural_checks']['nand/7']['held_out']['cells'])
        self.assertEqual(report['structural_transfer']['nand/7']['seen']['all']['correct'], 8)
        self.assertEqual(report['structural_transfer']['nand/7']['held_out']['all']['correct'], 0)
        comparison = report['comparisons']['nand/7']['parent_retention']
        self.assertEqual(comparison['regressions'], []); self.assertEqual(comparison['nll_worse_count'], 32)
        self.assertEqual(len(comparison['nll_worse']), 32)
        self.assertAlmostEqual(comparison['mean_nll_delta'], math.log(.995 / .99))
        json.dumps(report, allow_nan=False)

    def test_trace_inventory_geometry_and_checkpoint_bindings_fail_closed(self):
        original = self.trace(self.fresh['nand'], 'nand', 'masked', rows(self.fresh['nand'], 'masked'))
        mutations = [lambda t: t['points'].pop(), lambda t: t['points'].append(deepcopy(t['points'][0])),
            lambda t: t['points'][0].update(step=0), lambda t: t['points'][0].update(step=True),
            lambda t: t['points'][0].update(logp=[0.] * 16), lambda t: t['points'][0].update(logp=[math.nan] * 16),
            lambda t: t['points'][0].update(order_logp=None), lambda t: t.update(checkpoint_sha256='f' * 64)]
        for mutate in mutations:
            trace = deepcopy(original); mutate(trace)
            with self.assertRaises(ValueError): score.trace_rows(trace, self.fresh['nand']['inputs'], law='nand', seed=7,
                arm='masked', checkpoint=self.checkpoint, training=self.training_hash, freeze=self.freeze_hash)

    def test_missing_view_and_invalid_complete_inventory_precede_oracle_opening(self):
        read, opened = score.io._read, []
        def logged(path):
            opened.append(Path(path).name); return read(path)
        self.change(lambda t: t['points'].pop(), 'nor', 'cross_order')
        with patch.object(score.io, '_read', side_effect=logged), self.assertRaisesRegex(ValueError, 'missing planned'):
            self.evaluate()
        self.assertFalse(any('oracle' in name for name in opened))
        self.path('nand', 'masked').unlink(); opened.clear()
        with patch.object(score.io, '_read', side_effect=logged), self.assertRaises(FileNotFoundError): self.evaluate()
        self.assertFalse(any('oracle' in name for name in opened))

    def test_saved_checkpoint_bytes_and_exposure_bindings_are_enforced(self):
        path = self.fitted / 'grounded-7.json'; original = path.read_bytes()
        path.write_bytes(b'{"substituted":true}\n')
        with self.assertRaisesRegex(ValueError, 'fitted checkpoint/exposure'): self.evaluate()
        path.write_bytes(original)
        path = self.fitted / 'training.json'; training = score.io._read(path)
        training['reports']['grounded/7']['training_forecasts_per_update'] += 1
        path.unlink(); score.io._write(path, training)
        with self.assertRaisesRegex(ValueError, 'fitted checkpoint/exposure'): self.evaluate()

    def test_changed_prefix_wrong_counterpart_and_identical_final_word_reject(self):
        records, gold, _ = score.previous._inventory(self.fresh['nand']['inputs'], self.fresh['nand']['oracle'], 'nand')
        identity = next(iter(gold)); other = gold[identity]['counterpart_id']
        for change in ('history', 'counterpart', 'word', 'action'):
            r, g = deepcopy(records), deepcopy(gold)
            if change == 'history': r[identity]['utterances'][0]['reading'][0] ^= 1
            elif change == 'counterpart': g[identity]['counterpart_id'] = identity
            elif change == 'word': r[identity]['utterances'][-1]['text'] = r[other]['utterances'][-1]['text']
            else: g[identity]['actions'][-1] = g[other]['actions'][-1].copy()
            with self.subTest(change=change), self.assertRaises(ValueError): score.lexical_pairs(r, g)

    def test_opposite_polarity_failure_cannot_hide_in_high_pooled_accuracy(self):
        gold = {g['id']: g for g in self.fresh['nand']['oracle']['episodes']}
        target = next(g for g in gold.values() if g['effect_polarity'] == 1)
        def fail(trace):
            for row in trace['points']:
                if (row['id'], row['step']) == (target['id'], target['contrast_step']):
                    row['logp'] = logs(score.previous._index(target['opposite_truth'][-1]))
        self.change(fail); report = self.evaluate()
        self.assertGreater(report['by_trace']['nand/7/grounded']['all']['accuracy'], .95)
        self.assertFalse(report['decision']['checks']['nand/7']['lexical_cells'])
        self.assertEqual(report['decision']['decision'], 'REVISE_LEXICAL_GROUNDING')

    def test_swap_must_predict_counterpart_and_mask_must_remove_information(self):
        baseline = self.evaluate()['controls']['nand/7']
        self.assertEqual(baseline['masked_max_tv'], 0.); self.assertEqual(baseline['masked_both_correct'], 0)
        self.assertEqual(baseline['swapped_max_counterpart_tv'], 0.)
        self.change(lambda t: [r.update(logp=logs(15)) for r in t['points']], arm='swapped')
        result = self.evaluate()
        self.assertFalse(result['decision']['checks']['nand/7']['swapped_counterfactual'])
        correct = rows(self.fresh['nand'], 'grounded'); final = {(r['id'], r['step']): r for r in correct}
        self.change(lambda t: [r.update(logp=final[r['id'], r['step']]['logp']) for r in t['points']], arm='masked')
        result = self.evaluate()
        self.assertEqual(result['controls']['nand/7']['masked_both_correct'], 8)
        self.assertFalse(result['decision']['checks']['nand/7']['mask_information_removed'])


if __name__ == '__main__': unittest.main()
