"""Exact prospective design and causal witnesses; no learned-model execution."""
from collections import Counter, defaultdict
from copy import deepcopy
from itertools import product
import unittest

from experiments.predictive_nucleus import acceptance_contract as contract
from experiments.predictive_nucleus import hidden_cycle_data as data, multisource_law_oracle as oracle


def config():
    return {'version': 'hidden-cycle-data-tests-v1',
            'data': {'entity_counts': [3, 4, 5, 6], 'split_seed': 20261039998}}


def reference(case, law):
    """Enumerate whole deterministic histories before conditioning prior readings."""
    histories, ids, result = {}, sorted(case['ids']), []
    for mode in (0, 1):
        states = [dict(case['observations'][0])]
        for action in case['actions']:
            before, post = states[-1], dict(states[-1])
            source, target = action['participants'][mode], action['participants'][1 - mode]
            post[target] = int(not (bool(before[source]) and bool(before[target]))) if law == 'nand' else int(
                not (bool(before[source]) or bool(before[target])))
            states.append(post)
        histories[mode] = states
    for t in range(len(case['actions'])):
        modes = [m for m, states in histories.items() if all(v is None or states[j][name] == v
            for j, obs in enumerate(case['observations'][:t + 1]) for name, v in obs.items())]
        counts = Counter(sum(histories[m][t + 1][name] << (len(ids) - i - 1)
                             for i, name in enumerate(ids)) for m in modes)
        result.append({'information_key': contract.information_key(case, t), 'possible_worlds': sorted(counts),
            'probabilities': [counts[w] / len(modes) for w in sorted(counts)], 'surviving_modes': modes})
    return result


class HiddenCycleDataTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.assets = data.build_assets(config())

    def test_frozen_factorial_inventory_reproducibility_and_bounds(self):
        settings = config(); original = deepcopy(settings)
        self.assertEqual(data.build_assets(settings), self.assets); self.assertEqual(settings, original)
        for law, bank in self.assets['banks'].items():
            audit = self.assets['audit']['by_law'][law]
            names = ('episode_views', 'physical_lineages', 'role_pairs', 'twin_pairs', 'critical_twin_pairs',
                     'changed_hidden_twin_pairs', 'planned_forecasts', 'identifiable_points', 'ambiguous_points')
            self.assertEqual(tuple(audit[k] for k in names), (512, 64, 256, 256, 48, 112, 1536, 1024, 512))
            self.assertEqual(audit['expected_best_all_action_accuracy'], 5 / 6)
            self.assertEqual(audit['unique_templates'], 4)
            self.assertEqual(audit['max_cumulative_missing_bits'], 1)
            self.assertEqual(audit['combinatorial_live_path_bound'], 2)
            self.assertEqual(audit['combinatorial_candidate_expansion_bound'], 128)
            counts = Counter((r['family'], r['entities'], tuple(r['core_bits']), r['hidden_source_slot'],
                              r['direction'], r['condition']) for r in bank['cases'])
            self.assertEqual(counts, Counter({(f, n, bits, m, d, c): 1 for f in data.FAMILIES
                for n in (3, 4, 5, 6) for bits in product((0, 1), repeat=3)
                for m, d in product((0, 1), repeat=2) for c in data.CONDITIONS}))

    def test_independent_oracle_every_forecast_and_known_untouched_bits(self):
        for law, bank in self.assets['banks'].items():
            for case, meta, info, gold in zip(bank['inputs']['episodes'], bank['cases'],
                    bank['information']['episodes'], bank['oracle']['episodes'], strict=True):
                self.assertEqual(info['forecasts'], reference(case, law))
                self.assertEqual([len(f['possible_worlds']) for f in info['forecasts']], [2, 1, 1])
                self.assertEqual(set(case), {'episode', 'ids', 'observations', 'actions', 'coverage'})
                for t, action in enumerate(case['actions']):
                    target = action['participants'][1 - meta['hidden_source_slot']]
                    for name in set(case['ids']) - {target}:
                        self.assertEqual(gold['truth'][t][name], gold['truth'][t + 1][name])

    def test_mask_is_structural_and_twins_are_exact_information_controls(self):
        for bank in self.assets['banks'].values():
            twins, pairs = defaultdict(dict), defaultdict(list)
            for case, meta, info in zip(bank['inputs']['episodes'], bank['cases'], bank['information']['episodes'], strict=True):
                twins[meta['twin_id']][meta['condition']] = (case, meta, info['forecasts'])
                pairs[meta['pair_id']].append(meta['direction'])
                shared = set(case['actions'][1]['participants']) & set(case['actions'][2]['participants'])
                self.assertEqual(shared, {meta['hidden_handle']})
                missing = [(t, name) for t, obs in enumerate(case['observations']) for name, v in obs.items() if v is None]
                self.assertEqual(missing, [(2, meta['hidden_handle'])] if meta['condition'] == 'hidden' else [])
            self.assertTrue(all(sorted(v) == [0, 1] for v in pairs.values()))
            for pair in twins.values():
                full, hidden = (pair[c] for c in data.CONDITIONS)
                restored = deepcopy(hidden[0]); restored['episode'] = full[0]['episode']
                restored['observations'][2][hidden[1]['hidden_handle']] = full[0]['observations'][2][hidden[1]['hidden_handle']]
                self.assertEqual(restored, full[0]); self.assertEqual(full[2][:2], hidden[2][:2])
                self.assertNotEqual(full[2][2]['information_key'], hidden[2][2]['information_key'])
                self.assertEqual({k: v for k, v in full[2][2].items() if k != 'information_key'},
                                 {k: v for k, v in hidden[2][2].items() if k != 'information_key'})

    def test_law_banks_share_exact_design_but_not_physical_targets(self):
        left, right = (self.assets['banks'][law] for law in data.LAWS)
        for a, b, x, y in zip(left['inputs']['episodes'], right['inputs']['episodes'], left['cases'], right['cases'], strict=True):
            self.assertEqual({k: a[k] for k in ('episode', 'ids', 'actions', 'coverage')},
                             {k: b[k] for k in ('episode', 'ids', 'actions', 'coverage')})
            self.assertEqual(a['observations'][0], b['observations'][0])
            self.assertEqual(x['hidden_handle'], y['hidden_handle']); self.assertEqual(x['twin_id'], y['twin_id'])

    def test_critical_subset_requires_downstream_target_change_and_has_witnesses(self):
        for law, bank in self.assets['banks'].items():
            changed_only = 0
            for case, meta, gold in zip(bank['inputs']['episodes'], bank['cases'], bank['oracle']['episodes'], strict=True):
                truth = gold['truth']; stale = dict(truth[2]); stale[meta['hidden_handle']] = truth[1][meta['hidden_handle']]
                source, target = (case['actions'][2]['participants'][i] for i in (meta['hidden_source_slot'], 1 - meta['hidden_source_slot']))
                stale[target] = int(not (stale[source] and stale[target])) if law == 'nand' else int(not (stale[source] or stale[target]))
                self.assertEqual(meta['critical'], stale[target] != truth[3][target])
                self.assertEqual(meta['stale_final_world'], data._world(stale))
                self.assertEqual(meta['stale_target_bit'], stale[target]); self.assertEqual(meta['true_target_bit'], truth[3][target])
                if meta['critical']: self.assertTrue(meta['hidden_changed'])
                if not meta['critical'] and stale != truth[3]: changed_only += 1
                bits = [1, 0, 1] if law == 'nand' else [0, 1, 0]
                if meta['family'] == 'cycle_forward' and meta['entities'] == 3 and meta['core_bits'] == bits and meta['direction'] == meta['hidden_source_slot'] == 0:
                    a, b = case['actions'][0]['participants']; c = case['actions'][1]['participants'][1]
                    expected = [[1, 0, 1], [1, 1, 1], [1, 1, 0], [1, 1, 0]] if law == 'nand' else [
                        [0, 1, 0], [0, 0, 0], [0, 0, 1], [0, 0, 1]]
                    self.assertEqual([[state[i] for i in (a, b, c)] for state in truth], expected)
                    self.assertTrue(meta['critical'])
            self.assertGreater(changed_only, 0)

    def test_future_feedback_does_not_enter_own_prediction(self):
        for law, bank in self.assets['banks'].items():
            case = deepcopy(bank['inputs']['episodes'][0]); original = oracle.forecast_episode(case, law)
            for t in range(3):
                blinded = deepcopy(case)
                for obs in blinded['observations'][t + 1:]:
                    for name in obs: obs[name] = None
                self.assertEqual(oracle.forecast_episode(blinded, law)[t], original[t])

    def test_actual_training_has_no_full_cycle_and_old_topologies_are_reported(self):
        overlap = self.assets['audit']['historical_overlap']
        law_bank = overlap['multisource-law-v1/assets.json.xz']['partitions']
        for law in data.LAWS:
            self.assertEqual(law_bank[law + '/train']['blueprint_overlap'], 0)
            self.assertEqual(law_bank[law + '/train']['template_overlap'], 0)
        self.assertGreater(overlap['joint-correlation-v1/assets.json.xz']['partitions']['evaluation']['template_overlap'], 0)

    def test_invalid_entity_and_seed_configs_fail(self):
        for counts in ([], [3, 3], [6, 3], [2], [7], [True]):
            settings = config(); settings['data']['entity_counts'] = counts
            with self.assertRaises(ValueError): data.build_assets(settings)
        settings = config(); settings['data']['split_seed'] = 20261030062
        with self.assertRaises(ValueError): data.build_assets(settings)


if __name__ == '__main__': unittest.main()
