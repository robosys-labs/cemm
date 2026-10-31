"""Independent physical histories, timing witnesses and future-evidence checks."""
from collections import Counter, defaultdict
from copy import deepcopy
import unittest

from experiments.predictive_nucleus import timing_contract as contract
from experiments.predictive_nucleus import timing_data as data, timing_oracle as oracle


def config():
    return {'version': 'timing-data-tests-v1', 'data': {'entity_counts': [3, 4, 5, 6], 'split_seed': 20261039999}}


def reference(case, law):
    """Whole mode-specific trajectories, then condition each prior observed prefix."""
    ids = sorted(case['ids']); histories = []
    def contact(state, pair, mode):
        value = list(state)
        source, target = (ids.index(pair[i]) for i in (mode, 1 - mode))
        value[target] = int(not (state[source] and state[target])) if law == 'nand' else int(not (state[source] or state[target]))
        return value
    for mode in (0, 1):
        states = [[case['observations'][0][i] for i in ids]]
        for action in case['actions']:
            state = states[-1]
            if action['kind'] == 'contact':
                post = contact(state, action['participants'], mode)
            elif action['timing'] == 'ordered':
                post = state
                for pair in action['contacts']: post = contact(post, pair, mode)
            else:
                outcomes = [contact(state, pair, mode) for pair in action['contacts']]
                post = [start ^ ((a ^ start) | (b ^ start)) for start, a, b in zip(state, *outcomes, strict=True)]
            states.append(post)
        histories.append(states)
    result = []
    for step in range(len(case['actions'])):
        modes = [mode for mode, states in enumerate(histories) if all(
            states[t] == [obs[i] for i in ids] for t, obs in enumerate(case['observations'][:step + 1]))]
        worlds = Counter(sum(bit << (len(ids) - i - 1) for i, bit in enumerate(histories[mode][step + 1])) for mode in modes)
        result.append({'history_key': contract.history_key(case, step), 'information_key': contract.information_key(case, step),
            'possible_worlds': sorted(worlds), 'probabilities': [worlds[w] / len(modes) for w in sorted(worlds)], 'surviving_modes': modes})
    return histories, result


class TimingDataTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.assets = data.build_assets(config())

    def test_factorial_inventory_and_reproducibility(self):
        settings = config(); original = deepcopy(settings)
        self.assertEqual(data.build_assets(settings), self.assets); self.assertEqual(settings, original)
        for law, bank in self.assets['banks'].items():
            audit = self.assets['audit']['by_law'][law]
            names = ('episode_views', 'physical_lineages', 'role_pairs', 'timing_pairs', 'permutation_pairs',
                     'nontrivial_permutation_pairs', 'critical_timing_pairs', 'planned_forecasts', 'physical_contacts',
                     'group_events', 'singleton_events', 'identifiable_points', 'ambiguous_points')
            self.assertEqual(tuple(audit[name] for name in names),
                (1728, 144, 864, 576, 576, 448, 120, 4608, 6336, 1728, 2880, 2880, 1728))
            self.assertEqual(audit['expected_best_all_action_accuracy'], .8125)
            self.assertEqual(audit['critical_by_family'], {'chain': 16, 'repeated': 64, 'fan_in': 40})
            self.assertEqual(audit['family_views'], {'chain': 384, 'repeated': 384, 'fan_in': 384, 'disjoint': 576})
            self.assertEqual(audit['condition_views'], dict.fromkeys(data.CONDITIONS, 576))
            self.assertEqual(sum(sum(states.values()) for states in audit['group_entry_core_coverage'].values()), 576)
            self.assertEqual(len(bank['inputs']['episodes']), len(bank['cases']))
        training = self.assets['audit']['actual_training']['per_law']
        self.assertTrue(all(v['max_contacts'] == 2 and v['group_events'] == 0 for v in training.values()))

    def test_independent_oracle_complete_worlds_and_fixed_mode(self):
        for law, bank in self.assets['banks'].items():
            for case, meta, target, info in zip(bank['inputs']['episodes'], bank['cases'], bank['oracle']['episodes'],
                    bank['information']['episodes'], strict=True):
                histories, expected = reference(case, law)
                self.assertEqual(expected, info['forecasts'])
                self.assertEqual(target['possible_worlds'], [row['possible_worlds'] for row in expected])
                actual = [[state[i] for i in sorted(case['ids'])] for state in target['truth']]
                self.assertEqual(actual, histories[meta['hidden_source_slot']])
                self.assertEqual([len(row['possible_worlds']) for row in expected], [2] + [1] * (len(case['actions']) - 1))
                self.assertTrue(all(row['surviving_modes'] == [meta['hidden_source_slot']] for row in expected[1:]))
                self.assertEqual(len(case['actions']), meta['contact_count'] - 1)
                self.assertEqual(meta['query_steps'], list(range(1, len(case['actions']))))
                active = {name for action in case['actions'] for pair in
                    ([action['participants']] if action['kind'] == 'contact' else action['contacts']) for name in pair}
                for state in target['truth']:
                    for name in set(case['ids']) - active:
                        self.assertEqual(state[name], case['observations'][0][name])

    def test_timing_triples_match_history_and_critical_worlds(self):
        for bank in self.assets['banks'].values():
            cases = {c['episode']: c for c in bank['inputs']['episodes']}
            metadata = {c['episode']: c for c in bank['cases']}
            information = {c['episode']: c['forecasts'] for c in bank['information']['episodes']}
            roles = defaultdict(list)
            for meta in bank['cases']: roles[meta['pair_id']].append(meta)
            self.assertTrue(all(len(pair) == 2 and {m['direction'] for m in pair} == {0, 1} and
                len({(m['family'], m['lineage'], m['condition'], m['hidden_source_slot']) for m in pair}) == 1 for pair in roles.values()))
            for contrast in bank['timing_contrasts']:
                left, right = (cases[contrast[key]] for key in ('ordered_episode', 'snapshot_episode'))
                self.assertEqual(left['observations'][:2], right['observations'][:2])
                self.assertEqual(left['actions'][0], right['actions'][0])
                self.assertEqual(left['actions'][1]['contacts'], right['actions'][1]['contacts'])
                self.assertEqual(left['actions'][2:], right['actions'][2:])
                self.assertEqual(left['coverage'], right['coverage'])
                self.assertEqual(contract.history_key(left, 1), contract.history_key(right, 1))
                self.assertNotEqual(contract.information_key(left, 1), contract.information_key(right, 1))
                self.assertEqual(contrast['critical'], contrast['ordered_world'] != contrast['snapshot_world'])
                for case, name in ((left, 'ordered_world'), (right, 'snapshot_world')):
                    self.assertEqual(information[case['episode']][1]['possible_worlds'], [contrast[name]])
                    self.assertEqual(metadata[case['episode']]['critical'], contrast['critical'])
                if contrast['family'] == 'disjoint': self.assertFalse(contrast['critical'])

    def test_snapshot_permutations_are_actual_equal_outcome_episodes(self):
        for bank in self.assets['banks'].values():
            cases = {c['episode']: c for c in bank['inputs']['episodes']}
            gold = {c['episode']: c for c in bank['oracle']['episodes']}
            info = {c['episode']: c['forecasts'] for c in bank['information']['episodes']}
            for pair in bank['permutation_pairs']:
                a, b = (cases[pair[key]] for key in ('snapshot_episode', 'permuted_episode'))
                self.assertNotEqual(a['episode'], b['episode'])
                self.assertEqual(a['actions'][1]['timing'], b['actions'][1]['timing'])
                self.assertEqual(a['actions'][1]['contacts'], b['actions'][1]['contacts'][::-1])
                self.assertEqual(a['observations'], b['observations'])
                self.assertEqual(gold[a['episode']]['truth'], gold[b['episode']]['truth'])
                self.assertTrue(all(x['possible_worlds'] == y['possible_worlds'] and x['probabilities'] == y['probabilities']
                    for x, y in zip(info[a['episode']], info[b['episode']], strict=True)))
                if pair['family'] == 'repeated': self.assertFalse(pair['nontrivial_event_permutation'])

    def test_first_forecast_does_not_reveal_later_mode_evidence(self):
        for bank in self.assets['banks'].values():
            rows = {c['episode']: c['forecasts'][0] for c in bank['information']['episodes']}
            twins = defaultdict(list)
            for meta in bank['cases']:
                twins[meta['lineage'], meta['condition'], meta['direction']].append(meta)
            for pair in twins.values():
                self.assertEqual({m['hidden_source_slot'] for m in pair}, {0, 1})
                self.assertEqual(rows[pair[0]['episode']], rows[pair[1]['episode']])
                self.assertEqual(rows[pair[0]['episode']]['probabilities'], [.5, .5])

    def test_laws_match_inputs_except_observed_outcomes_and_labels_never_enter(self):
        a, b = (self.assets['banks'][law]['inputs']['episodes'] for law in data.LAWS)
        for left, right in zip(a, b, strict=True):
            self.assertEqual(set(left), {'episode', 'ids', 'observations', 'actions', 'coverage'})
            self.assertEqual({key: left[key] for key in ('episode', 'ids', 'actions', 'coverage')},
                             {key: right[key] for key in ('episode', 'ids', 'actions', 'coverage')})
            self.assertEqual(left['observations'][0], right['observations'][0])
            renamed = deepcopy(left); renamed['episode'] = 'fresh-episode-label'
            for t in range(len(left['actions'])):
                self.assertEqual(contract.information_key(left, t), contract.information_key(renamed, t))
                self.assertEqual(contract.history_key(left, t), contract.history_key(renamed, t))

    def test_malformed_timing_inputs_fail(self):
        original = self.assets['banks']['nand']['inputs']['episodes'][0]
        for corruption in ('timing', 'empty_group', 'large_group', 'unknown_id', 'alias', 'partial', 'boolean', 'coverage', 'extra_label'):
            case = deepcopy(original); ids = case['ids']
            if corruption == 'timing': case['actions'][1]['timing'] = 'guess'
            elif corruption == 'empty_group': case['actions'][1]['contacts'] = []
            elif corruption == 'large_group': case['actions'][1]['contacts'].append(list(ids[:2]))
            elif corruption == 'unknown_id': case['actions'][1]['contacts'][0][0] = 'absent'
            elif corruption == 'alias': case['actions'][1]['contacts'][0] = [ids[0], ids[0]]
            elif corruption == 'partial': case['observations'][1][ids[0]] = None
            elif corruption == 'boolean': case['observations'][1][ids[0]] = True
            elif corruption == 'coverage': case['coverage'][1] = ids[:-1]
            else: case['actions'][1]['physical_mode'] = 0
            with self.subTest(corruption=corruption), self.assertRaises(ValueError):
                contract.validate_inputs({'version': 'timing-input-v1', 'episodes': [case]})

    def test_invalid_generator_and_oracle_inputs_fail(self):
        for counts in ([], [3, 3], [6, 3], [2], [7], [True]):
            settings = config(); settings['data']['entity_counts'] = counts
            with self.assertRaises(ValueError): data.build_assets(settings)
        settings = config(); settings['data']['split_seed'] = 20261031066
        with self.assertRaises(ValueError): data.build_assets(settings)
        with self.assertRaises(ValueError): oracle.law_digest('xor')


if __name__ == '__main__': unittest.main()
