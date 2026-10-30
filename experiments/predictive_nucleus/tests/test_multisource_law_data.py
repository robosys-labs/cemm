"""New-law design, independent oracle and causal witnesses; no learned models."""
from collections import Counter
from copy import deepcopy
from itertools import product
import unittest

from experiments.predictive_nucleus import acceptance_contract as contract
from experiments.predictive_nucleus import multisource_law_data as data, multisource_law_oracle as oracle


def config():
    return {'version': 'multisource-law-data-tests-v1', 'data': {'entity_counts': [3, 4, 5, 6],
            'split_seeds': {'train': 20261039996, 'evaluation': 20261039997}}}


def reference(case, law):
    histories, ids, result = {}, sorted(case['ids']), []
    for mode in (0, 1):
        states = [dict(case['observations'][0])]
        for action in case['actions']:
            before = states[-1]; post = dict(before)
            source, target = action['participants'][mode], action['participants'][1 - mode]
            post[target] = int(not (bool(before[source]) and bool(before[target]))) if law == 'nand' else int(
                not (bool(before[source]) or bool(before[target])))
            states.append(post)
        histories[mode] = states
    for t in range(len(case['actions'])):
        modes = [m for m, states in histories.items() if all(v is None or states[j][name] == v
            for j, obs in enumerate(case['observations'][:t + 1]) for name, v in obs.items())]
        mass = Counter(sum(histories[m][t + 1][name] << (len(ids) - i - 1) for i, name in enumerate(ids)) for m in modes)
        result.append({'information_key': contract.information_key(case, t), 'possible_worlds': sorted(mass),
            'probabilities': [mass[w] / len(modes) for w in sorted(mass)], 'surviving_modes': modes})
    return result


class MultisourceLawDataTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.assets = data.build_assets(config())

    def test_exact_inventory_and_reproducibility(self):
        settings = config(); before = deepcopy(settings)
        self.assertEqual(data.build_assets(settings), self.assets); self.assertEqual(settings, before)
        for split, expected in [('train', (128, 32, 64, 256, 0, 1152, 128, 128)),
                                ('evaluation', (384, 96, 192, 1536, 768, 6912, 1152, 384))]:
            audit = self.assets['audit'][split]
            self.assertEqual(tuple(audit[k] for k in ('episode_views', 'physical_lineages', 'role_pairs',
                'planned_forecasts', 'primary_composition_points', 'visible_bits', 'identifiable_points', 'ambiguous_points')), expected)
        self.assertEqual(self.assets['audit']['current_split_overlap'], {'blueprint': 0, 'template': 0})
        self.assertEqual(self.assets['audit']['law_contrasts'], 64)

    def test_all_factorial_anchors_modes_reversals_and_law_matched_design(self):
        for split in ('train', 'evaluation'):
            a, b = [self.assets['banks'][law]['splits'][split] for law in data.LAWS]
            self.assertEqual(a['cases'], b['cases'])
            counts = Counter((r['family'], r['entities'], tuple(r['core_bits']), r['hidden_source_slot'], r['direction']) for r in a['cases'])
            self.assertEqual(counts, Counter({(f, n, bits, m, d): 1 for f in data.FAMILIES[split]
                for n in (3, 4, 5, 6) for bits in product((0, 1), repeat=3) for m, d in product((0, 1), repeat=2)}))
            for x, y in zip(a['inputs']['episodes'], b['inputs']['episodes'], strict=True):
                self.assertEqual({k: x[k] for k in ('episode', 'ids', 'actions', 'coverage')},
                                 {k: y[k] for k in ('episode', 'ids', 'actions', 'coverage')})
                self.assertEqual(x['observations'][0], y['observations'][0])
                self.assertTrue(all(v in (0, 1) for c in (x, y) for obs in c['observations'] for v in obs.values()))

    def test_independent_whole_history_oracle_source_preservation_and_flow(self):
        for law, bank in self.assets['banks'].items():
            for split, bundle in bank['splits'].items():
                for case, meta, info, gold in zip(bundle['inputs']['episodes'], bundle['cases'],
                        bundle['information']['episodes'], bundle['oracle']['episodes'], strict=True):
                    rows = info['forecasts']; self.assertEqual(rows, reference(case, law))
                    self.assertEqual(len(rows[0]['possible_worlds']), 2)
                    self.assertTrue(all(len(row['possible_worlds']) == 1 for row in rows[1:]))
                    self.assertEqual(set(case), {'episode', 'ids', 'observations', 'actions', 'coverage'})
                    targets = []
                    for t, action in enumerate(case['actions']):
                        target = action['participants'][1 - meta['hidden_source_slot']]; targets.append(target)
                        for name in set(case['ids']) - {target}: self.assertEqual(gold['truth'][t][name], gold['truth'][t + 1][name])
                    if split == 'evaluation':
                        self.assertEqual(meta['flow'], 'fan_in' if meta['hidden_source_slot'] == meta['direction'] else 'fan_out')
                        self.assertEqual(len(set(targets)), 1 if meta['flow'] == 'fan_in' else 2)
                        self.assertEqual(meta['query_steps'], list(range(2, len(case['actions']))))

    def test_critical_law_contrasts_are_same_prefix_unique_and_include_both_equal_inputs(self):
        lookups = {law: {c['episode']: (c, m, i['forecasts']) for c, m, i in zip(
            b['splits']['evaluation']['inputs']['episodes'], b['splits']['evaluation']['cases'],
            b['splits']['evaluation']['information']['episodes'], strict=True)} for law, b in self.assets['banks'].items()}
        bits = Counter()
        for row in self.assets['law_contrasts']:
            a, meta, x = lookups['nand'][row['episode']]; b, _, y = lookups['nor'][row['episode']]
            self.assertEqual(a['observations'][:2], b['observations'][:2]); self.assertEqual(a['actions'][:2], b['actions'][:2])
            self.assertEqual(row['information_key'], x[1]['information_key']); self.assertEqual(row['information_key'], y[1]['information_key'])
            self.assertEqual(x[1]['possible_worlds'], [row['nand_world']]); self.assertEqual(y[1]['possible_worlds'], [row['nor_world']])
            self.assertNotEqual(row['nand_world'], row['nor_world']); bits[meta['core_bits'][0]] += 1
        self.assertEqual(bits, {0: 32, 1: 32})

    def test_current_feedback_cannot_change_own_prediction_and_bad_histories_reject(self):
        for law in data.LAWS:
            case = deepcopy(self.assets['banks'][law]['splits']['train']['inputs']['episodes'][0])
            rows = oracle.forecast_episode(case, law)
            blinded = deepcopy(case)
            for obs in blinded['observations'][1:]:
                for name in obs: obs[name] = None
            self.assertEqual(oracle.forecast_episode(blinded, law)[0], rows[0])
            bad = deepcopy(case); bad['actions'][0]['participants'][1] = bad['actions'][0]['participants'][0]
            with self.assertRaises(ValueError): oracle.forecast_episode(bad, law)
            bad = deepcopy(case); spectator = next(name for name in bad['ids'] if name not in bad['actions'][0]['participants'])
            bad['observations'][1][spectator] ^= 1
            with self.assertRaises(ValueError): oracle.forecast_episode(bad, law)
        with self.assertRaises(ValueError): oracle.forecast_episode(case, 'xor')
        settings = config(); settings['data']['split_seeds']['evaluation'] = settings['data']['split_seeds']['train']
        with self.assertRaises(ValueError): data.build_assets(settings)


if __name__ == '__main__': unittest.main()
