"""Synthetic exhaustive physics/conditioning checks; no studies or model fitting."""
from collections import Counter
from copy import deepcopy
from hashlib import sha256
from itertools import product
import json
from pathlib import Path
import random
import unittest

from experiments.predictive_nucleus import acceptance_contract as contract
from experiments.predictive_nucleus import prospective_oracle as oracle
from experiments.predictive_nucleus.world import Action, World, step


def case(ids, bits, actions):
    return {'episode': 'synthetic', 'ids': list(ids),
            'observations': [dict(zip(ids, bits))] + [dict.fromkeys(ids) for _ in actions],
            'actions': deepcopy(actions), 'coverage': [list(ids) for _ in actions]}


def trajectories(data):
    """Independent complete physical histories; never use the affine oracle."""
    ids = tuple(data['ids'])
    result = {}
    for mode in (0, 1):
        world = World(ids, tuple(data['observations'][0][name] for name in ids), mode)
        history = [dict(zip(ids, world.bits))]
        for action in data['actions']:
            world = step(world, Action(action['kind'], tuple(action['participants']), action.get('value')))
            history.append(dict(zip(ids, world.bits)))
        result[mode] = history
    return result


def reference(data):
    """Enumerate whole histories, then condition separately on each past prefix."""
    history, ids, expected = trajectories(data), sorted(data['ids']), []
    for t in range(len(data['actions'])):
        modes = [mode for mode in (0, 1) if all(
            value is None or history[mode][j][name] == value
            for j, reading in enumerate(data['observations'][:t + 1]) for name, value in reading.items())]
        mass = Counter(int(''.join(str(history[mode][t + 1][name]) for name in ids), 2) for mode in modes)
        support = sorted(mass)
        expected.append({'information_key': contract.information_key(data, t),
                         'possible_worlds': support,
                         'probabilities': [mass[world] / len(modes) for world in support],
                         'surviving_modes': modes})
    return expected


class ProspectiveOracleTests(unittest.TestCase):
    def test_exhaustive_all_states_actions_and_entity_counts_match_original_physics(self):
        for n in range(3, 7):
            ids = tuple(chr(97 + i) for i in reversed(range(n)))
            actions = ([{'kind': 'observe', 'participants': []}] +
                       [{'kind': 'set', 'participants': [name], 'value': bit} for name in ids for bit in (0, 1)] +
                       [{'kind': 'contact', 'participants': [a, b]} for a in ids for b in ids])
            for bits in product((0, 1), repeat=n):
                for action in actions:
                    with self.subTest(n=n, bits=bits, action=action):
                        data = case(ids, bits, [action])
                        self.assertEqual(oracle.forecast_episode(data), reference(data))

    def test_every_sensor_mask_filters_complete_correlated_histories_in_all_domains(self):
        for n in range(3, 7):
            ids = tuple(chr(97 + i) for i in reversed(range(n)))
            actions = [{'kind': 'contact', 'participants': [ids[a], ids[b]]}
                       for a, b in ((0, 1), (1, 2), (2, 0), (0, 1))]
            for mask in product((False, True), repeat=n):
                for actual in (0, 1):
                    with self.subTest(n=n, mask=mask, actual=actual):
                        data = case(ids, [int(i % 2 == 0) for i in range(n)], actions)
                        history = trajectories(data)[actual]
                        for t in range(1, len(history)):
                            data['observations'][t] = {name: history[t][name] if mask[(i + t) % n] else None
                                                       for i, name in enumerate(ids)}
                        self.assertEqual(oracle.forecast_episode(data), reference(data))

    def test_persistent_mode_retains_joint_and_temporal_correlations_after_world_coalescence(self):
        data = case(('a', 'b', 'c'), (1, 1, 0),
                    [{'kind': 'contact', 'participants': ['a', 'b']} for _ in range(3)])
        rows = oracle.forecast_episode(data)
        self.assertEqual([row['possible_worlds'] for row in rows], [[2, 4], [6], [2, 4]])
        self.assertEqual([row['probabilities'] for row in rows], [[.5, .5], [1.], [.5, .5]])
        self.assertEqual([row['surviving_modes'] for row in rows], [[0, 1]] * 3)
        # Independent bit marginals would invent 000/110 at the first contact;
        # resampling the mode at the next contact would lose the certain return.
        self.assertEqual(rows, reference(data))

    def test_affine_constants_aliases_and_observe_compose_after_interventions(self):
        for n in range(3, 7):
            ids = tuple(chr(97 + i) for i in range(n))
            actions = [{'kind': 'set', 'participants': ['a'], 'value': 1},
                       {'kind': 'contact', 'participants': ['a', 'b']},
                       {'kind': 'contact', 'participants': ['b', 'b']},
                       {'kind': 'observe', 'participants': []},
                       {'kind': 'set', 'participants': ['a'], 'value': 0},
                       {'kind': 'contact', 'participants': ['b', 'a']},
                       {'kind': 'contact', 'participants': ['a', 'a']}]
            for bits in product((0, 1), repeat=n):
                data = case(ids, bits, actions)
                self.assertEqual(oracle.forecast_episode(data), reference(data))

    def test_own_feedback_and_future_actions_cannot_select_the_current_forecast(self):
        data = case(('a', 'b', 'c'), (1, 1, 0),
                    [{'kind': 'contact', 'participants': ['a', 'b']},
                     {'kind': 'observe', 'participants': []}])
        before = oracle.forecast_episode(data)
        history = trajectories(data)
        futures = []
        for mode in (0, 1):
            delivered = deepcopy(data)
            delivered['observations'][1] = history[mode][1]
            rows = oracle.forecast_episode(delivered)
            self.assertEqual(rows[0], before[0])
            self.assertEqual(rows[1]['surviving_modes'], [mode])
            self.assertEqual(rows[1]['probabilities'], [1.])
            futures.append(rows[1]['possible_worlds'])
        self.assertNotEqual(*futures)
        later = deepcopy(data)
        later['episode'] = 'another-label'
        later['actions'][1] = {'kind': 'set', 'participants': ['c'], 'value': 1}
        later['coverage'][1] = ['c']
        self.assertEqual(oracle.forecast_episode(later)[0], before[0])
        selected = deepcopy(data)
        selected['coverage'][0] = ['a']
        row = oracle.forecast_episode(selected)[0]
        self.assertNotEqual(row['information_key'], before[0]['information_key'])
        self.assertEqual(row['possible_worlds'], before[0]['possible_worlds'])
        self.assertEqual(row['probabilities'], before[0]['probabilities'])

    def test_jointly_impossible_and_later_contradictory_feedback_reject_the_episode(self):
        data = case(('a', 'b', 'c'), (1, 1, 0),
                    [{'kind': 'contact', 'participants': ['a', 'b']},
                     {'kind': 'observe', 'participants': []}])
        impossible = deepcopy(data)
        impossible['observations'][1] = {'a': 0, 'b': 0, 'c': None}
        with self.assertRaisesRegex(ValueError, 'contradicts.*step 0'):
            oracle.forecast_episode(impossible)
        histories = trajectories(data)
        data['observations'][1] = histories[0][1]
        data['observations'][2] = histories[1][2]
        with self.assertRaisesRegex(ValueError, 'contradicts.*step 1'):
            oracle.forecast_episode(data)
        neutral = case(('a', 'b', 'c'), (0, 0, 0), [{'kind': 'observe', 'participants': []}])
        neutral['observations'][1]['c'] = 1
        with self.assertRaisesRegex(ValueError, 'contradicts.*step 0'):
            oracle.forecast_episode(neutral)

    def test_shared_input_validation_rejects_hidden_fields_and_partial_anchor(self):
        data = case(('a', 'b', 'c'), (0, 0, 0), [{'kind': 'observe', 'participants': []}])
        for field in ('actual_mode', 'truth', 'possible_worlds', 'family'):
            bad = deepcopy(data)
            bad[field] = 0
            with self.subTest(field=field), self.assertRaises(ValueError):
                oracle.forecast_episode(bad)
        partial = deepcopy(data)
        partial['observations'][0]['a'] = None
        with self.assertRaises(ValueError):
            oracle.forecast_episode(partial)
        with self.assertRaises(TypeError):
            oracle.forecast_episode(data, actual_mode=0)

    def test_source_law_json_and_input_rng_purity(self):
        self.assertEqual(oracle.law_digest(), contract.digest(oracle.LAW))
        self.assertEqual(oracle.source_digest(), sha256(Path(oracle.__file__).read_bytes()).hexdigest())
        self.assertEqual(oracle.LAW['hidden_source_slot']['probabilities'], [.5, .5])
        data = case(('z', 'a', 'm'), (1, 0, 1),
                    [{'kind': 'contact', 'participants': ['z', 'a']}])
        untouched, law, rng = deepcopy(data), deepcopy(oracle.LAW), random.getstate()
        rows = oracle.forecast_episode(data)
        self.assertEqual(data, untouched)
        self.assertEqual(oracle.LAW, law)
        self.assertEqual(random.getstate(), rng)
        self.assertEqual(json.loads(json.dumps(rows, allow_nan=False)), rows)
        self.assertEqual(rows, reference(data))
        rows[0]['surviving_modes'].clear()
        self.assertEqual(oracle.forecast_episode(data)[0]['surviving_modes'], [0, 1])


if __name__ == '__main__':
    unittest.main()
