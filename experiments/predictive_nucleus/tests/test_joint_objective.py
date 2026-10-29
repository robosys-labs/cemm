"""Synthetic invariants and public fixture feasibility, not scientific acceptance."""
from copy import deepcopy
from itertools import permutations
import math
import unittest
from unittest.mock import patch

import torch

from experiments.predictive_nucleus import joint_objective as j
from experiments.predictive_nucleus import informative_curriculum as c


class History:
    actions = (None,) * 3
    def __init__(self):
        self.states = ((0, 1, 0), (1, 1, 0), (0, 1, 0), (0, 1, 0))
        self.events = ({"kind": "contact", "participants": ["a", "b"]},
                       {"kind": "set", "participants": ["a"], "value": 0},
                       {"kind": "observe", "participants": []})
    def observation(self, t):
        return {"t": t, "measurements": [{"id": n, "bit": b} for n, b in zip("abc", self.states[t])]}
    def learner_turn(self, t):
        return {"observation": self.observation(t), "action": deepcopy(self.events[t])}
    def reveal_after_prediction(self, t):
        return self.observation(t + 1)
    def gold_after(self, t):
        raise AssertionError("evaluator truth must not be read")


class JointObjectiveTests(unittest.TestCase):
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

    def test_world_indices_are_lexicographic_complete_worlds(self):
        self.assertEqual(j.world_index(torch.tensor(j.WORLDS)).tolist(), list(range(8)))

    def test_batch_reads_only_sensor_action_records_and_is_detached(self):
        source = History()
        batch = j.batch_histories([source])
        source.states = ((1, 1, 1),) * 4
        self.assertEqual(batch.observations[0, 0].tolist(), [0, 1, 0])
        self.assertEqual(batch.actions[:, 0].tolist(), [[0, 0, 1, -1], [1, 0, -1, 0], [2, -1, -1, -1]])
        self.assertEqual(batch.digest(), self.batch.digest())

    def test_rejects_missing_duplicate_boolean_and_unknown_readings(self):
        mutations = (lambda r: r["measurements"].pop(),
                     lambda r: r["measurements"].append(r["measurements"][0]),
                     lambda r: r["measurements"][0].update(bit=True),
                     lambda r: r["measurements"][0].update(id="new"),
                     lambda r: r.update(t=4), lambda r: r.update(hidden_source_slot=0))
        for mutation in mutations:
            h = History()
            original = h.reveal_after_prediction
            def corrupt(t, mutation=mutation):
                row = original(t)
                mutation(row)
                return row
            h.reveal_after_prediction = corrupt
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                j.batch_histories([h])

    def test_rejects_action_shortcuts_and_discontinuous_pre_observations(self):
        invalid = [{"kind": "contact", "participants": ["a", "a"]},
                   {"kind": "set", "participants": ["a"], "value": True},
                   {"kind": "set", "participants": ["a"], "value": .5},
                   {"kind": "contact", "participants": "ab"},
                   {"kind": "observe", "participants": ["a"]},
                   {"kind": "contact", "participants": ["a", "b"], "mode": 1}]
        for action in invalid:
            h = History()
            h.events = (action,) + h.events[1:]
            with self.subTest(action=action), self.assertRaises(ValueError):
                j.batch_histories([h])
        h = History()
        original = h.learner_turn
        def corrupt(t):
            turn = original(t)
            if t == 1:
                turn["observation"]["measurements"][0]["bit"] ^= 1
            return turn
        h.learner_turn = corrupt
        with self.assertRaisesRegex(ValueError, "discontinuous"):
            j.batch_histories([h])

    def test_rejects_invalid_shapes_dtypes_bits_and_action_tensors(self):
        for x, a in ((self.batch.observations.float(), self.batch.actions),
                     (self.batch.observations, self.batch.actions.float()),
                     (self.batch.observations[:-1], self.batch.actions),
                     (self.batch.observations + .5, self.batch.actions),
                     (self.batch.observations, self.batch.actions + 10)):
            with self.subTest(x=x.shape, a=a.dtype), self.assertRaises(ValueError):
                j.SensorBatch(x, a).validate()
        with self.assertRaises(ValueError):
            j.batch_histories([])
        h = History()
        h.actions = h.actions[:-1]
        with self.assertRaises(ValueError):
            j.batch_histories([History(), h])

    def test_all_six_models_produce_normalized_joint_distributions_and_finite_gradients(self):
        for name, factory in c.model_factories().items():
            with self.subTest(model=name):
                model = factory()
                logp = j.joint_log_probabilities(model, self.batch)
                self.assertTrue(torch.allclose(logp.exp().sum(-1), torch.ones(3, 1, dtype=j.DTYPE), atol=1e-12))
                loss = j.full_world_nll(logp, self.batch.observations[1:])
                loss.backward()
                self.assertTrue(all(p.grad is not None and torch.isfinite(p.grad).all() for p in model.parameters()))
                self.assertTrue(any((p.grad != 0).any() for p in model.parameters()))

    def test_uniform_full_world_objective_is_not_mean_bit_loss(self):
        logp = torch.full((3, 1, 8), -math.log(8), dtype=j.DTYPE)
        self.assertAlmostEqual(float(j.full_world_nll(logp, self.batch.observations[1:])), math.log(8))
        changed = logp.clone()
        p = math.exp(-math.log(8) - 3)
        changed[1, 0, :] = math.log((1 - p) / 7)
        changed[1, 0, j.world_index(self.batch.observations[2, 0])] = math.log(p)
        self.assertAlmostEqual(float(j.full_world_nll(changed, self.batch.observations[1:])), math.log(8) + 1)
        with self.assertRaises(ValueError):
            j.full_world_nll(logp, self.batch.observations[1:] - .5)

    def test_loss_refuses_unnormalized_nan_and_positive_infinite_log_probabilities(self):
        for value in (0.0, float("nan"), float("inf"), -float("inf")):
            invalid = torch.full((3, 1, 8), value, dtype=j.DTYPE)
            with self.subTest(value=value), self.assertRaises(ValueError):
                j.full_world_nll(invalid, self.batch.observations[1:])

    def test_sequential_filter_equals_explicit_episode_mixture_in_value_and_gradient(self):
        model = j.JointKernel()
        actual = j.full_world_nll(j.joint_log_probabilities(model, self.batch), self.batch.observations[1:])
        modes = torch.zeros(1, 2, dtype=j.DTYPE)
        for t, action in enumerate(self.batch.actions):
            prior = model.initial(1)
            _, weighted = model.predict(self.batch.observations[t], action, prior)
            index = j.world_index(self.batch.observations[t + 1])
            modes = modes + (weighted - prior[:, :, None]).gather(2, index[:, None, None].expand(-1, 2, 1)).squeeze(-1)
        expected = -(modes.logsumexp(-1) - math.log(2)).mean() / 3
        self.assertTrue(torch.allclose(actual, expected, atol=1e-12, rtol=0))
        actual_grad = torch.autograd.grad(actual, tuple(model.parameters()), retain_graph=True)
        expected_grad = torch.autograd.grad(expected, tuple(model.parameters()))
        for left, right in zip(actual_grad, expected_grad, strict=True):
            self.assertTrue(torch.allclose(left, right, atol=1e-11, rtol=0))

    def test_memory_reset_has_eventwise_mixture_not_episode_mixture(self):
        model = j.JointKernel(memory=False)
        values = []
        for t, action in enumerate(self.batch.actions):
            logp, pending = model.predict(self.batch.observations[t], action, model.initial(1))
            values.append(logp)
            self.assertTrue(torch.equal(model.receive(pending, self.batch.observations[t + 1]), model.initial(1)))
        self.assertTrue(torch.allclose(torch.stack(values), j.joint_log_probabilities(model, self.batch)))

    def test_future_reading_cannot_change_its_own_forecast(self):
        for name, factory in c.model_factories().items():
            if "supplied" in name:
                continue
            with self.subTest(model=name):
                model = factory()
                original = j.joint_log_probabilities(model, self.batch)
                x = self.batch.observations.clone()
                x[2:, :, 0] = 1 - x[2:, :, 0]
                changed = j.joint_log_probabilities(model, j.SensorBatch(x, self.batch.actions))
                self.assertTrue(torch.equal(original[:2], changed[:2]))

    def test_preview_does_not_mutate_input_state_or_parameters(self):
        for name, factory in c.model_factories().items():
            with self.subTest(model=name):
                model = factory()
                state = model.initial(1)
                before, batch_before, weights = state.clone(), self.batch.digest(), j.fingerprint(model.state_dict())
                one, _ = model.predict(self.batch.observations[0], self.batch.actions[0], state)
                two, _ = model.predict(self.batch.observations[0], self.batch.actions[0], state)
                self.assertTrue(torch.equal(one, two))
                self.assertTrue(torch.equal(before, state))
                self.assertEqual(batch_before, self.batch.digest())
                self.assertEqual(weights, j.fingerprint(model.state_dict()))

    def test_supplied_persistence_is_identical_for_both_families(self):
        kernel, flat = j.JointKernel(persistence=True), j.JointFlatGRU(persistence=True)
        for t in range(3):
            left, _ = kernel.predict(self.batch.observations[t], self.batch.actions[t], kernel.initial(1))
            right, _ = flat.predict(self.batch.observations[t], self.batch.actions[t], flat.initial(1))
            self.assertTrue(torch.equal(torch.isfinite(left), torch.isfinite(right)))
        self.assertEqual(torch.isfinite(left).sum(), 1)  # observe has one possible world

    def test_false_persistence_is_rejected_not_repaired_or_clipped(self):
        states = self.batch.observations.clone()
        states[1:, :, 2] = 1  # untouched third entity changes
        wrong = j.SensorBatch(states, self.batch.actions)
        for model in (j.JointKernel(persistence=True), j.JointFlatGRU(persistence=True)):
            with self.subTest(model=type(model).__name__), self.assertRaises(ValueError):
                j.full_world_nll(j.joint_log_probabilities(model, wrong), wrong.observations[1:])
        for model in (j.JointKernel(), j.JointFlatGRU()):
            self.assertTrue(torch.isfinite(j.full_world_nll(j.joint_log_probabilities(model, wrong), wrong.observations[1:])))

    def test_all_kernel_ablations_are_id_equivariant_not_only_tied_roles(self):
        for options in ({}, {"role_tying": False}, {"memory": False}, {"persistence": True}):
            model = j.JointKernel(**options)
            original = j.joint_log_probabilities(model, self.batch)
            for order in permutations(range(3)):
                inverse = {old: new for new, old in enumerate(order)}
                actions = self.batch.actions.clone()
                for slot in (1, 2):
                    for old, new in inverse.items():
                        actions[:, :, slot][self.batch.actions[:, :, slot] == old] = new
                new_batch = j.SensorBatch(self.batch.observations[:, :, list(order)], actions)
                renamed = j.joint_log_probabilities(model, new_batch)
                mapped = [j.WORLDS.index(tuple(w[i] for i in order)) for w in j.WORLDS]
                self.assertTrue(torch.allclose(original, renamed[:, :, mapped], atol=1e-11, rtol=0))

    def test_optimizer_uses_same_input_and_records_actual_costs(self):
        original = self.batch.digest()
        for name, factory in c.model_factories().items():
            with self.subTest(model=name):
                result = j.fit(factory(), self.batch, updates=1, cpu_seconds=10)
                self.assertEqual(result["training_input_sha256"], original)
                self.assertEqual((result["completed_updates"], result["events_per_update"]), (1, 3))
                self.assertEqual(result["stop_reason"], "update_limit")
                self.assertNotEqual(result["initial_weights_sha256"], result["final_weights_sha256"])
                self.assertGreater(result["fit_cpu_seconds"], 0)
        self.assertEqual(self.batch.digest(), original)

    def test_cpu_ceiling_prevents_another_update_and_reports_overshoot(self):
        with patch.object(j, "process_time", side_effect=[0, 0, 0, .5, .5, .5]):
            result = j.fit(j.JointFlatGRU(), self.batch, updates=2, cpu_seconds=.1)
        self.assertEqual(result["completed_updates"], 1)
        self.assertEqual(result["stop_reason"], "cpu_limit")
        self.assertEqual(result["cpu_overshoot_seconds"], .4)

    def test_exhausted_budget_is_not_a_successful_fit(self):
        with patch.object(j, "process_time", side_effect=[0, 1, 1]):
            with self.assertRaisesRegex(ValueError, "before any"):
                j.fit(j.JointFlatGRU(), self.batch, updates=1, cpu_seconds=.1)

    def test_invalid_budgets_and_model_configs_fail(self):
        for updates, budget, lr in ((True, 1, .02), (0, 1, .02), (1, float("nan"), .02),
                                     (1, True, .02), (1, 1, 0), (1, 1, True)):
            with self.subTest(values=(updates, budget, lr)), self.assertRaises(ValueError):
                j.fit(j.JointFlatGRU(), self.batch, updates=updates, cpu_seconds=budget, learning_rate=lr)
        for construct in (lambda: j.JointKernel(persistence=1), lambda: j.JointKernel(hidden=0),
                          lambda: j.JointFlatGRU(hidden=True), lambda: j.JointFlatGRU(persistence=1)):
            with self.assertRaises(ValueError):
                construct()


class InformativeCurriculumTests(unittest.TestCase):
    def test_probe_has_equal_declared_cost_and_always_changes_only_supplied_actions(self):
        for case in range(c.N_CASES):
            a = c.make_history(case, informative=True)
            b = c.make_history(case, informative=False)
            self.assertEqual((len(a.actions), len(b.actions)), (7, 7))
            self.assertEqual(a._observations[0], b._observations[0])
            self.assertEqual(a._action_records[2:], b._action_records[2:])
            self.assertEqual([len(s) for s in a._observations], [3] * 8)
            for informative, history in ((True, a), (False, b)):
                twin = c.make_history(case ^ 8, informative=informative)
                self.assertEqual(history._action_records, twin._action_records)
                self.assertEqual(history._observations[:3], twin._observations[:3])
                self.assertEqual(history._observations[3] == twin._observations[3], not informative)

    def test_public_query_identifiability_separates_evidence_deficit(self):
        for composition in (False, True):
            for informative in (False, True):
                group = c.histories(informative=informative, composition=composition)
                report = c.feasibility(group)
                self.assertEqual(len(group), 768)
                self.assertEqual(report["finite_fixture_max_correct"], 768 if informative else 480)
                self.assertEqual(report["ambiguous_prefixes"], 0 if informative else 288)

    def test_full_histories_have_no_hidden_labels_in_learner_tensors(self):
        for informative in (False, True):
            batch = j.batch_histories(c.histories(informative=informative))
            self.assertEqual(tuple(batch.observations.shape), (8, 768, 3))
            self.assertEqual(tuple(batch.actions.shape), (7, 768, 4))
            self.assertEqual(batch.actions.shape[0] * batch.actions.shape[1], 5376)

    def test_composition_uses_a_different_query_pair_not_a_new_training_view(self):
        for case in range(c.N_CASES):
            a = c.make_history(case, informative=True)
            b = c.make_history(case, informative=True, composition=True)
            self.assertEqual(a._observations[:4], b._observations[:4])
            self.assertEqual(a._action_records[:3], b._action_records[:3])
            self.assertEqual(set(a._action_records[c.QUERY_STEP][1]), {"unit-a", "unit-b"})
            self.assertEqual(set(b._action_records[c.QUERY_STEP][1]), {"unit-b", "unit-c"})

    def test_renaming_roundtrips_all_observations_and_ordered_actions(self):
        history = c.make_history(35, informative=True)
        ids = tuple(sorted(n for n, _ in history._observations[0]))
        for names in permutations(ids):
            changed = c.rename(history, names)
            inverse = dict(zip(names, ids, strict=True))
            restored = c.rename(changed, tuple(inverse[n] for n in ids))
            self.assertEqual(history, restored)
        with self.assertRaises(ValueError):
            c.rename(history, ("unit-a",) * 3)

    def test_all_query_before_after_participant_combinations_remain_present(self):
        # No-change and reversed same-kind roles are retained, not filtered away.
        for informative in (False, True):
            contexts = set()
            for case in range(c.N_CASES):
                h = c.make_history(case, informative=informative)
                turn = h.learner_turn(c.QUERY_STEP)
                pre = {m["id"]: m["bit"] for m in turn["observation"]["measurements"]}
                a, b = turn["action"]["participants"]
                contexts.add((a, b, pre[a], pre[b]))
            self.assertEqual(len(contexts), 8)

    def test_invalid_fixture_selection_fails_closed(self):
        for case in (-1, 128, True, 1.0):
            with self.assertRaises(ValueError):
                c.make_history(case, informative=True)
        with self.assertRaises(ValueError):
            c.make_history(0, informative=1)
        with self.assertRaises(ValueError):
            c.feasibility([])
        with self.assertRaises(ValueError):
            c.feasibility([c.make_history(0, informative=True)], query=7)


if __name__ == "__main__":
    unittest.main()
