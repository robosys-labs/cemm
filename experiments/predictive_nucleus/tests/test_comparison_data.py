"""Expanded source/fixture audit; synthetic model/control invariants only."""
from collections import Counter
from copy import deepcopy
from itertools import permutations, product
import math
from pathlib import Path
import unittest
from unittest.mock import patch

import torch
from experiments.predictive_nucleus import comparison_data as d
from experiments.predictive_nucleus import informative_curriculum as old
from experiments.predictive_nucleus import joint_objective as j
from experiments.predictive_nucleus import empirical_joint as e
from experiments.predictive_nucleus.tests.test_joint_objective import History


class ComparisonDataTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = {(info, comp): j.batch_histories(d.histories(informative=info, composition=comp))
                    for info in (False, True) for comp in (False, True)}

    def test_all_entity_resets_remove_present_state_mode_shortcut(self):
        for info, comp in self.data:
            for case in range(d.N_CASES):
                one = d.make_history(case, informative=info, composition=comp)
                twin = d.make_history(case ^ 16, informative=info, composition=comp)
                self.assertEqual(one._action_records, twin._action_records)
                self.assertEqual(one._observations[d.QUERY_STEP], twin._observations[d.QUERY_STEP])
                self.assertEqual(one._observations[:3], twin._observations[:3])
                self.assertEqual(one._observations[3] == twin._observations[3], not info)

    def test_v1_shortcut_reproduced_and_v2_removed_without_deleting_history(self):
        legacy = j.batch_histories(old.histories(informative=True, composition=True))
        self.assertEqual(d.bounds(legacy, current_only=True)[5]['map_ceiling'], 1.0)
        for info, comp in self.data:
            batch = self.data[info, comp]
            self.assertEqual(d.bounds(batch, current_only=True)[6]['map_ceiling'], .625)
            self.assertEqual(d.bounds(batch)[6]['map_ceiling'], 1.0 if info else .625)

    def test_every_step_bound_and_probability_floor_are_accounted_for(self):
        for info, comp in self.data:
            rows = d.bounds(self.data[info, comp])
            ceilings = [1.] * 8
            ceilings[2 if info else 6] = .5 if info else .625
            self.assertEqual([r['map_ceiling'] for r in rows], ceilings)
            ambiguous = rows[2 if info else 6]
            fraction = 1.0 if info else .75
            self.assertAlmostEqual(ambiguous['min_mean_nll'], fraction * math.log(2))
            self.assertAlmostEqual(ambiguous['min_mean_brier'], fraction * .5)
            self.assertEqual(ambiguous['ambiguous_queries'], int(1536 * fraction))
            self.assertAlmostEqual(sum(ceilings) / 8, .9375 if info else .953125)

    def test_declared_simulator_outputs_match_separate_scalar_oracle(self):
        # Evaluator-only exhaustive check; never imported by any learner.
        for info, comp in self.data:
            for case in range(d.N_CASES):
                h = d.make_history(case, informative=info, composition=comp)
                state = dict(h._observations[0])
                mode = (case >> 4) & 1
                for t, (kind, names, value) in enumerate(h._action_records):
                    if kind == 'set':
                        state[names[0]] = value
                    elif kind == 'contact':
                        source, target = names[mode], names[1 - mode]
                        state[target] = int(state[source] != state[target])
                    self.assertEqual(state, dict(h._observations[t + 1]))

    def test_factorial_and_cost_counts_are_not_independent_world_claims(self):
        for info, comp in self.data:
            batch = self.data[info, comp]
            self.assertEqual(tuple(batch.actions.shape), (8, 1536, 4))
            self.assertEqual(tuple(batch.observations.shape), (9, 1536, 3))
            for case in range(256):
                h = d.make_history(case, informative=info, composition=comp)
                other = d.make_history(case, informative=not info, composition=comp)
                self.assertEqual(h._action_records[2:], other._action_records[2:])
                self.assertEqual(h._observations[0], other._observations[0])
            contexts = Counter()
            for h in d.histories(informative=info, composition=comp):
                contexts[tuple(sorted(h._observations[6]))] += 1
            self.assertEqual(set(contexts.values()), {192})
            self.assertEqual(len(contexts), 8)

    def test_second_pair_full_prefix_disjoint_but_local_controls_have_coverage(self):
        for info in (False, True):
            train, test = self.data[info, False], self.data[info, True]
            overlap = d.coverage(train, test, mode='prefix')
            self.assertEqual([r['covered'] for r in overlap['steps']], [1536] * 3 + [0] * 5)
            for mode in ('local', 'contact'):
                report = d.coverage(train, test, mode=mode)
                self.assertEqual([r['covered'] for r in report['steps']], [1536] * 8)

    def test_coverage_does_not_fit_a_control_or_predict_a_model(self):
        with patch.object(e.SensorMemory, 'fit', side_effect=AssertionError('no fitting')):
            self.assertEqual(d.coverage(self.data[True, False], self.data[True, True], mode='contact')
                             ['steps'][6]['covered'], 1536)

    def test_all_renamed_actions_and_observations_roundtrip(self):
        h = d.make_history(233, informative=True, composition=True)
        ids = tuple(sorted(name for name, _ in h._observations[0]))
        for names in permutations(ids):
            changed = old.rename(h, names)
            inverse = dict(zip(names, ids))
            self.assertEqual(old.rename(changed, tuple(inverse[n] for n in ids)), h)

    def test_invalid_selections_fail_closed(self):
        for case in (-1, 256, True, 1.0):
            with self.assertRaises(ValueError):
                d.make_history(case, informative=True)
        for options in ({'informative': 1}, {'informative': True, 'composition': 0}):
            with self.assertRaises(ValueError):
                d.make_history(0, **options)
        with self.assertRaises(ValueError):
            d.bounds(self.data[True, False], current_only=1)


class EmpiricalAndMathTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.threads = torch.get_num_threads()
        torch.set_num_threads(1)
    @classmethod
    def tearDownClass(cls):
        torch.set_num_threads(cls.threads)
    def setUp(self):
        self.rng = torch.random.get_rng_state()
        torch.manual_seed(7)
        self.batch = j.batch_histories([History()])
    def tearDown(self):
        torch.random.set_rng_state(self.rng)

    def test_full_world_memory_retains_frequency_and_zero_probabilities(self):
        other = History()
        other.states = ((0, 1, 0), (0, 0, 1), (0, 1, 0), (0, 1, 0))
        batch = j.batch_histories([History(), History(), other])
        for mode in ('prefix', 'local', 'contact'):
            memory = e.SensorMemory(mode).fit(batch)
            _, _, pre, action, past = next(e.queries(batch))
            before = memory.digest()
            result = memory.predict(pre, action, past)
            self.assertAlmostEqual(result[6], 2 / 3)
            self.assertAlmostEqual(result[1], 1 / 3)
            self.assertEqual(sum(p > 0 for p in result), 2)
            self.assertEqual(memory.digest(), before)
            self.assertIsNone(memory.predict((1, 0, 1), action, past))

    def test_contact_control_uses_evidence_without_copying_physics_or_persistence(self):
        memory = e.SensorMemory('contact').fit(self.batch)
        _, _, pre, action, past = next(e.queries(self.batch))
        self.assertEqual(memory.predict(pre, action, past)[6], 1.)
        # Earlier measured contact evidence changes the key; no mode bit exists.
        self.assertIsNone(memory.predict(pre, action, ((pre, action, (0, 0, 0)),)))
        # A synthetic target changes an untouched bit, which the table learns.
        changed = History()
        changed.states = ((0, 1, 0), (1, 1, 1), (0, 1, 1), (0, 1, 1))
        memory.fit(j.batch_histories([changed]))
        self.assertEqual(memory.predict(pre, action, past)[7], 1.)

    def test_contact_key_discards_identity_topology_but_exact_key_does_not(self):
        pre, act = (0, 1, 1), (0, 0, 1, -1)
        past = (((1, 1, 0), (0, 0, 1, -1), (1, 0, 0)),)
        changed = (((0, 1, 1), (0, 1, 2, -1), (0, 1, 0)),)
        self.assertEqual(e.context(pre, act, past, 'contact')[0], e.context(pre, act, changed, 'contact')[0])
        self.assertNotEqual(e.context(pre, act, past, 'prefix')[0], e.context(pre, act, changed, 'prefix')[0])
        self.assertEqual(e.context(pre, act, past, 'local')[0], e.context(pre, act, (), 'local')[0])

    def test_contexts_never_depend_on_own_or_future_feedback(self):
        original = list(e.queries(self.batch))
        x = self.batch.observations.clone()
        x[2:] = 1 - x[2:]
        changed = list(e.queries(j.SensorBatch(x, self.batch.actions)))
        for mode in ('prefix', 'local', 'contact'):
            for i in (0, 1):
                self.assertEqual(e.context(*original[i][2:], mode), e.context(*changed[i][2:], mode))

    def test_memory_outcomes_map_back_from_ordered_operands(self):
        memory = e.SensorMemory('contact').fit(self.batch)
        # Relabel a->c, b->a, c->b; ordered pair prebits still (0,1).
        result = memory.predict((1, 0, 0), (0, 2, 0, -1), ())
        self.assertEqual(result[5], 1.)  # original 110 maps to 101
        self.assertEqual(math.fsum(result), 1.)

    def test_bad_batch_and_unknown_control_mode_are_rejected(self):
        with self.assertRaises(ValueError):
            e.SensorMemory('oracle')
        with self.assertRaises(ValueError):
            e.context((0, 0, 0), (2, -1, -1, -1), (), 'oracle')
        with self.assertRaises(ValueError):
            e.SensorMemory('contact').fit(j.SensorBatch(self.batch.observations + .5, self.batch.actions))

    def test_model_and_control_source_have_no_simulator_dependency(self):
        # Transitive dependency boundary: controls no longer import data generator.
        for module in (j, e):
            source = Path(module.__file__).read_text()
            for forbidden in ('from .world', 'from .comparison_data', 'from .schedule_fixture',
                              'hidden_source_slot', 'gold_after'):
                self.assertNotIn(forbidden, source)

    def test_all_kernel_conditionals_match_scalar_probability_calculation(self):
        actions = [(0, a, b, -1) for a in range(3) for b in range(3) if a != b]
        actions += [(1, a, -1, value) for a in range(3) for value in (0, 1)] + [(2, -1, -1, -1)]
        with torch.no_grad():
            for persistence, tied in product((False, True), repeat=2):
                model = j.JointKernel(persistence=persistence, role_tying=tied)
                for bits, action in product(j.WORLDS, actions):
                    kind, first, second, value = action
                    pre = torch.tensor([bits], dtype=j.DTYPE)
                    prior = torch.tensor([[.27, .73]], dtype=j.DTYPE).log()
                    actual, _ = model.predict(pre, torch.tensor([action]), prior)
                    expected = []
                    for world in j.WORLDS:
                        mass = 0.
                        for mode, weight in enumerate((.27, .73)):
                            if kind == 0:
                                inputs = torch.tensor([bits[first], bits[second]], dtype=j.DTYPE)
                                if mode == 1 and tied:
                                    pair = model.pair(inputs.flip(-1)).softmax(-1)
                                    probability = float(pair[2 * world[second] + world[first]])
                                else:
                                    net = model.pair if mode == 0 else model.pair_other
                                    probability = float(net(inputs).softmax(-1)[2 * world[first] + world[second]])
                                active = (first, second)
                            elif kind == 1:
                                inputs = torch.tensor([bits[first], value], dtype=j.DTYPE)
                                probability = float(model.intervention(inputs).softmax(-1)[world[first]])
                                active = (first,)
                            else:
                                probability, active = 1., ()
                            for slot in range(3):
                                if slot in active:
                                    continue
                                if persistence:
                                    probability *= int(bits[slot] == world[slot])
                                else:
                                    inputs = torch.tensor([bits[slot]] + [int(k == kind) for k in range(3)], dtype=j.DTYPE)
                                    probability *= float(model.background(inputs).softmax(-1)[world[slot]])
                            mass += weight * probability
                        expected.append(mass)
                    self.assertTrue(torch.allclose(actual.exp()[0], torch.tensor(expected, dtype=j.DTYPE), atol=1e-12, rtol=0))

    def test_full_sequence_gradient_matches_central_difference(self):
        for model in (j.JointKernel(), j.JointKernel(persistence=True), j.JointFlatGRU()):
            loss = j.full_world_nll(j.joint_log_probabilities(model, self.batch), self.batch.observations[1:])
            loss.backward()
            for parameter in model.parameters():
                original, derivative = float(parameter.detach().flatten()[0]), float(parameter.grad.flatten()[0])
                values = []
                with torch.no_grad():
                    for delta in (-1e-6, 1e-6):
                        parameter.flatten()[0] = original + delta
                        values.append(float(j.full_world_nll(j.joint_log_probabilities(model, self.batch), self.batch.observations[1:])))
                    parameter.flatten()[0] = original
                self.assertAlmostEqual(derivative, (values[1] - values[0]) / 2e-6, delta=1e-7)


if __name__ == '__main__':
    unittest.main()
