"""Coordinate/evidence invariants on arbitrary measured traces; no physics fit."""
from copy import deepcopy
from types import SimpleNamespace
import unittest

import numpy as np
import torch

from experiments.predictive_nucleus import comparison_scoring as frozen_scores
from experiments.predictive_nucleus.domain_contract import (
    DomainMemory, DomainSupport, binary_worlds, domain_context, normalize,
    persistence_support, validate_action, validate_anchor, validate_reading, world_index,
)
from experiments.predictive_nucleus.empirical_joint import SensorMemory, queries
from experiments.predictive_nucleus.joint_objective import SensorBatch


def measured_batch(entities=3, self_contact=False):
    # Hand-written readings deliberately do not encode any simulator mechanism.
    rows = [[(time + slot) % 2 for slot in range(entities)] for time in range(4)]
    events = [[0, entities - 1, entities - 1 if self_contact else 0, -1],
              [1, 1, -1, 0], [0, 0, 1, -1]]
    return SimpleNamespace(observations=torch.tensor(rows, dtype=torch.float64)[:, None, :],
                           actions=torch.tensor(events, dtype=torch.long)[:, None, :])


def envelope(time, **readings):
    return {'t': time, 'measurements': [{'id': name, 'bit': value} for name, value in readings.items()]}


class DomainCoordinateTests(unittest.TestCase):
    def test_world_coordinates_are_bijective_for_every_supported_count(self):
        for entities in range(3, 7):
            worlds = binary_worlds(entities)
            tensor = torch.tensor(worlds, dtype=torch.float64)
            self.assertEqual(len(worlds), 2 ** entities)
            self.assertEqual(worlds, tuple(sorted(set(worlds))))
            self.assertEqual(worlds[0], (0,) * entities)
            self.assertEqual(worlds[-1], (1,) * entities)
            self.assertTrue(torch.equal(world_index(tensor), torch.arange(2 ** entities)))
            self.assertEqual(world_index(tensor[None]).shape, (1, 2 ** entities))
        for invalid in (True, 3., 2, 7):
            with self.assertRaises(ValueError): binary_worlds(invalid)
        with self.assertRaises(ValueError): world_index(torch.tensor([0., .5, 1.]))

    def test_validators_keep_missingness_and_alias_policy_explicit(self):
        for entities in range(3, 7):
            anchor = torch.zeros(2, entities, dtype=torch.float64)
            self.assertEqual(validate_anchor(anchor, 64), entities)
            action = torch.tensor([[0, entities - 1, entities - 1, -1], [2, -1, -1, -1]])
            before = action.clone()
            validate_action(action, 2, entities)
            self.assertTrue(torch.equal(action, before))
            with self.assertRaises(ValueError): validate_action(action, 2, entities, allow_self=False)
            mask = torch.ones_like(anchor, dtype=torch.bool); mask[0, 0] = False
            reading = anchor.clone(); reading[0, 0] = -1
            validate_reading(reading, mask, 2, entities)
            with self.assertRaises(ValueError): validate_reading(anchor, mask, 2, entities)
            with self.assertRaises(ValueError): validate_anchor(reading, 64)
        with self.assertRaises(ValueError): validate_anchor(torch.zeros(1, 3), 64)
        with self.assertRaises(ValueError): validate_anchor(torch.zeros(1, 3, dtype=torch.float64), True)
        with self.assertRaises(ValueError): validate_action(torch.tensor([[0, 0, 3, -1]]), 1, 3)

    def test_dynamic_normalization_matches_frozen_three_entity_arithmetic(self):
        raw = torch.tensor([[0., -1000., *([-torch.inf] * 6)], [float('nan')] * 8], dtype=torch.float64)
        answer = np.array([True, False])
        left, lc = normalize(raw, answer); right, rc = frozen_scores.normalize(raw, answer)
        np.testing.assert_array_equal(left, right); np.testing.assert_array_equal(lc, rc)
        self.assertEqual(left[0, 1], -1000.)
        for entities in range(4, 7):
            raw = torch.zeros(2, 2 ** entities, dtype=torch.float64).log_softmax(-1)
            norm, correction = normalize(raw, np.ones(2, dtype=bool))
            np.testing.assert_allclose(np.exp(norm).sum(-1), [1., 1.], atol=1e-12)
            self.assertTrue(np.isfinite(correction).all())
        for raw in (torch.zeros(1, 12, dtype=torch.float64), torch.zeros(1, 8, dtype=torch.float64),
                    torch.full((1, 64), -torch.inf, dtype=torch.float64)):
            with self.assertRaises(ValueError): normalize(raw, np.array([True]))

    def test_persistence_masks_one_physical_alias_target_and_all_untouched_entities(self):
        for entities in range(3, 7):
            pre = torch.zeros(3, entities, dtype=torch.float64)
            action = torch.tensor([[0, entities - 1, entities - 1, -1],
                                   [0, 0, entities - 1, -1], [2, -1, -1, -1]])
            worlds = torch.tensor(binary_worlds(entities))
            support = persistence_support(pre, action, worlds)
            self.assertEqual(support.sum(-1).tolist(), [2, 4, 1])
            self.assertTrue(bool((worlds[support[0], :-1] == 0).all()))
            self.assertEqual(worlds[support[0], -1].tolist(), [0, 1])


class DomainMemoryTests(unittest.TestCase):
    def test_alias_context_deduplicates_physical_coordinates(self):
        for entities in range(3, 7):
            pre = (1,) * entities
            own, order = domain_context(pre, (0, entities - 1, entities - 1, -1), (), 'contact')
            other, _ = domain_context(pre, (0, entities - 1, 0, -1), (), 'contact')
            self.assertEqual(order, (entities - 1, *range(entities - 1)))
            self.assertEqual(len(set(order)), entities)
            self.assertEqual(own[3], (0, 0))
            self.assertEqual(other[3], (0, 1))
            self.assertNotEqual(own, other)
            for mode in ('prefix', 'local', 'contact'):
                key, order = domain_context(pre, (2, -1, -1, -1), (), mode)
                self.assertEqual(key[0], entities)
                self.assertEqual(order, tuple(range(entities)))

    def test_contact_history_distinguishes_aliases_and_missing_readings(self):
        pre, action = (1, 1, 0), (0, 1, 2, -1)
        distinct = ((pre, (0, 0, 1, -1), pre),)
        aliased = ((pre, (0, 0, 0, -1), pre),)
        missing = (((-1, 1, 0), (0, 0, 0, -1), pre),)
        keys = [domain_context(pre, action, history, 'contact')[0] for history in (distinct, aliased, missing)]
        self.assertEqual(len(set(keys)), 3)
        self.assertEqual(keys[1][-1], (((0, 0), (1,), (1,)),))
        self.assertEqual(keys[2][-1], (((0, 0), (-1,), (1,)),))

    def test_fit_uses_measured_worlds_and_one_count_per_physical_outcome(self):
        for entities in range(3, 7):
            for mode in ('prefix', 'local', 'contact'):
                batch = measured_batch(entities, self_contact=True)
                x, a = batch.observations.clone(), batch.actions.clone()
                memory = DomainMemory(mode).fit(batch)
                pre, act = tuple(map(int, x[0, 0])), tuple(map(int, a[0, 0]))
                prediction = memory.predict(pre, act, ())
                self.assertEqual(len(prediction), 2 ** entities)
                self.assertEqual(prediction[int(world_index(x[1, 0]))], 1.)
                self.assertEqual(sum(sum(v.values()) for v in memory.table.values()), 3)
                self.assertIsNone(memory.predict(pre, (0, entities - 1, 0, -1), ()))
                self.assertTrue(torch.equal(x, batch.observations))
                self.assertTrue(torch.equal(a, batch.actions))

    def test_bad_fit_is_transactional_and_never_imputes_missing_targets(self):
        memory = DomainMemory('contact').fit(measured_batch())
        before = memory.digest()
        batch = measured_batch(); batch.observations[-1, 0, 1] = -1
        with self.assertRaises(ValueError): memory.fit(batch)
        self.assertEqual(memory.digest(), before)

    def test_legacy_migration_preserves_counts_predictions_and_original_digest(self):
        given = measured_batch()
        batch = SensorBatch(given.observations, given.actions).validate()
        for mode in ('prefix', 'local', 'contact'):
            legacy = SensorMemory(mode).fit(batch)
            before = legacy.digest()
            upgraded = DomainMemory.from_legacy(legacy)
            self.assertEqual(upgraded.origin_digest, before)
            for _, _, pre, action, past in queries(batch):
                self.assertEqual(upgraded.predict(pre, action, past), legacy.predict(pre, action, past))
            self.assertIsNone(upgraded.predict((0, 1, 0, 1), (0, 3, 0, -1), ()))
            self.assertIsNone(upgraded.predict((0, 1, 0), (0, 2, 2, -1), ()))
            self.assertEqual(sum(sum(v.values()) for v in upgraded.table.values()), 3)
            first = next(iter(upgraded.table)); outcome = next(iter(upgraded.table[first]))
            upgraded.table[first][outcome] += 1
            self.assertEqual(legacy.digest(), before)
            self.assertEqual(DomainMemory.from_legacy(legacy).origin_digest, before)

    def test_legacy_contact_migration_does_not_invent_self_contact_history(self):
        batch = measured_batch(); legacy = SensorMemory('contact').fit(SensorBatch(batch.observations, batch.actions))
        upgraded = DomainMemory.from_legacy(legacy)
        records = list(queries(SensorBatch(batch.observations, batch.actions)))
        _, _, pre, action, past = records[-1]
        aliased = ((past[0][0], (0, 2, 2, -1), past[0][2]), *past[1:])
        self.assertIsNotNone(upgraded.predict(pre, action, past))
        self.assertIsNone(upgraded.predict(pre, action, aliased))

    def test_adaptation_metadata_is_detached_and_new_observed_fit_resets_origin(self):
        batch = measured_batch(); legacy = SensorMemory('local').fit(SensorBatch(batch.observations, batch.actions))
        upgraded = DomainMemory.from_legacy(legacy)
        self.assertEqual(upgraded.domain_adaptation['origin_table_sha256'], legacy.digest())
        self.assertFalse(upgraded.domain_adaptation['larger_or_alias_counts_synthesized'])
        metadata = upgraded.domain_adaptation; metadata['supported_entities'].clear()
        metadata['origin_table_sha256'] = 'modified'
        self.assertEqual(upgraded.domain_adaptation['supported_entities'], [3, 4, 5, 6])
        self.assertEqual(upgraded.domain_adaptation['origin_table_sha256'], legacy.digest())
        with self.assertRaises(AttributeError): upgraded.domain_adaptation = {}
        upgraded.fit(measured_batch(4, self_contact=True))
        self.assertIsNone(upgraded.domain_adaptation['origin_table_sha256'])


class DomainSupportTests(unittest.TestCase):
    def test_direct_support_has_no_inherited_posterior_interface(self):
        support = DomainSupport(envelope(0, a=1, b=1, c=0))
        self.assertFalse(hasattr(support, 'assess_posterior'))
        alias = {'kind': 'contact', 'participants': ['a', 'a']}
        distinct = {'kind': 'contact', 'participants': ['a', 'b']}
        support.commit_action(alias, intended_sensor_ids=('a',), next_time=1)
        support.receive(envelope(1, a=1), 'one')
        self.assertEqual(support.assess(alias)['observed_events'], 1)
        self.assertEqual(support.assess(distinct)['observed_events'], 0)
        support.receive(envelope(1, a=1), 'one')
        self.assertEqual(support.assess(alias)['observed_events'], 1)
        support.commit_action(alias, intended_sensor_ids=('a',), next_time=2)
        with self.assertRaises(RuntimeError): support.receive(envelope(1, a=1), 'one')
        support.receive(envelope(2), 'two')
        self.assertEqual(support.assess(alias)['status'], 'UNOBSERVED_INPUT')
        self.assertEqual(sum(support._contexts.values()), 1)

    def test_alias_missing_input_cannot_be_reconstructed_from_later_feedback(self):
        support = DomainSupport(envelope(0, a=1, b=1, c=0))
        alias = {'kind': 'contact', 'participants': ['a', 'a']}
        support.commit_action(alias, intended_sensor_ids=('a',), next_time=1)
        support.receive(envelope(1), 'one')
        support.commit_action(alias, intended_sensor_ids=('a',), next_time=2)
        support.receive(envelope(2, a=1), 'two')
        self.assertEqual(support.assess(alias)['observed_events'], 0)
        before = deepcopy(support.__dict__)
        support.commit_action(alias, intended_sensor_ids=('a',), next_time=3)
        with self.assertRaises(ValueError): support.receive(envelope(3, b=0), 'three')
        self.assertEqual(support.time, before['time'])
        self.assertEqual(support._contexts, before['_contexts'])


if __name__ == '__main__':
    unittest.main()
