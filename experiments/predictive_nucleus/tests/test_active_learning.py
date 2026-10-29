"""Independent masked-likelihood and common-path wiring checks, not a study."""
from copy import deepcopy
from hashlib import sha256
from itertools import product
import json
import math
from pathlib import Path
import tempfile
import unittest

import torch
from torch import nn

from experiments.predictive_nucleus import active_checkpoint as checkpoint
from experiments.predictive_nucleus import active_learning as learning
from experiments.predictive_nucleus import active_paths
from experiments.predictive_nucleus import joint_objective as old
from experiments.predictive_nucleus.active_participant import Session
from experiments.predictive_nucleus.domain_contract import DomainMemory
from experiments.predictive_nucleus.domain_flat import DomainFlatGRU
from experiments.predictive_nucleus.domain_kernel import DomainKernel
from experiments.predictive_nucleus.informative_curriculum import model_factories


DTYPE = torch.float64
OBSERVE = (2, -1, -1, -1)


def batch(entities=3, *, masked=True, aliases=True, tag=None):
    """A tiny delivered tape; every recorded outcome permits supplied persistence."""
    observations = torch.zeros(5, 1, entities, dtype=DTYPE)
    observations[:, 0, 1] = 1
    observations[1:4, 0, 0] = 1
    observations[3, 0, -1] = 1
    actions = torch.tensor([[(0, 0, entities - 1, -1)], [(1, 1, -1, 1)],
                            [(0, entities - 1 if aliases else 0, entities - 1, -1)],
                            [(0, 0, entities - 1, -1)]], dtype=torch.long)
    masks = torch.ones_like(observations, dtype=torch.bool)
    if masked:
        masks[1:3, 0, -1] = False
        masks[4, 0, 0] = False
    observations[~masks] = -1
    coverage = torch.ones(4, 1, entities, dtype=torch.bool)
    identity = tag or ('masked' if masked else 'complete')
    return learning.ObservedBatch(observations, actions, masks, coverage,
                                  (f'{identity}-{entities}',)).validate()


def models():
    return (
        ('kernel', lambda: DomainKernel(hidden=4)),
        ('kernel_persistence', lambda: DomainKernel(hidden=4, persistence=True)),
        ('kernel_untied', lambda: DomainKernel(hidden=4, role_tying=False)),
        ('kernel_reset', lambda: DomainKernel(hidden=4, memory=False)),
        ('flat', lambda: DomainFlatGRU(hidden=4)),
        ('flat_persistence', lambda: DomainFlatGRU(hidden=4, persistence=True)),
    )


def sequence_log_likelihood(model, tape):
    """Enumerate whole histories, sum log joints once, never use a path filter.

    No intermediate path weights are normalized and no observed marginal is
    computed stepwise. This is deliberately separate from production replay.
    """
    worlds = torch.tensor(tuple(product((0, 1), repeat=tape.observations.shape[-1])), dtype=DTYPE)
    result = []
    for episode in range(tape.observations.shape[1]):
        histories = [(torch.zeros((), dtype=DTYPE), tape.observations[0, episode:episode + 1],
                      model.initial(1))]
        for step in range(len(tape.actions)):
            visible = tape.masks[step + 1, episode]
            reading = tape.observations[step + 1, episode]
            compatible = [i for i, world in enumerate(worlds) if torch.equal(world[visible], reading[visible])]
            successors = []
            for mass, pre, state in histories:
                logp, pending = model.predict(pre, tape.actions[step, episode:episode + 1], state)
                for index in compatible:
                    if bool(torch.isneginf(logp[0, index])):
                        continue
                    post = worlds[index:index + 1]
                    successors.append((mass + logp[0, index], post, model.receive(pending, post)))
            histories = successors
        if not histories:
            raise AssertionError('test oracle was given an impossible tape')
        result.append(torch.stack([mass for mass, _, _ in histories]).logsumexp(0))
    return torch.stack(result)


class DelayedBit(nn.Module):
    """A hidden bit survives a shared current state and is revealed one turn later."""
    supported_entities, supports_self_contact = (3, 4, 5, 6), True

    def __init__(self, logit=-.7, *, impossible=False, outcome=1):
        super().__init__()
        self.logit = nn.Parameter(torch.tensor([logit], dtype=DTYPE))
        self.impossible, self.outcome, self.predict_calls = impossible, outcome, 0

    def initial(self, n):
        return torch.zeros(n, 2, dtype=DTYPE)

    def predict(self, pre, action, state):
        self.predict_calls += 1
        raw = torch.full((len(pre), 2 ** pre.shape[1]), -torch.inf, dtype=DTYPE)
        pair = torch.stack((self.logit[0] * 0, self.logit[0])).log_softmax(0)
        if self.impossible:
            pair = torch.stack((self.logit[0] * 0, self.logit.new_tensor(-torch.inf)))
        for i, (phase, remembered) in enumerate(state.tolist()):
            if phase == 0:
                raw[i, 0], raw[i, self.outcome] = pair[0], pair[1]
            else:
                raw[i, 0 if phase == 1 else int(remembered)] = self.logit[0] * 0
        return raw, state.clone()

    def receive(self, pending, post):
        return torch.stack((pending[:, 0] + 1,
                            torch.where(pending[:, 0] == 0, post[:, -1], pending[:, 1])), -1)


def delayed_batch(entities=6):
    x = torch.zeros(4, 1, entities, dtype=DTYPE)
    mask = torch.ones_like(x, dtype=torch.bool)
    mask[1] = False
    mask[3] = False
    mask[3, 0, -1] = True
    x[3, 0, -1] = 1
    x[~mask] = -1
    coverage = torch.ones(3, 1, entities, dtype=torch.bool)
    coverage[2] = mask[3]
    return learning.ObservedBatch(x, torch.tensor([[OBSERVE]] * 3, dtype=torch.long), mask,
                                  coverage, ('delayed',)).validate()


class ActiveLearningTests(unittest.TestCase):
    def setUp(self):
        state, threads = torch.random.get_rng_state(), torch.get_num_threads()
        self.addCleanup(torch.random.set_rng_state, state)
        self.addCleanup(torch.set_num_threads, threads)
        torch.set_num_threads(1)
        torch.manual_seed(29)

    def assert_gradients(self, actual, expected, model):
        parameters = tuple(model.parameters())
        left = torch.autograd.grad(actual, parameters)
        right = torch.autograd.grad(expected, parameters)
        for name, a, b in zip(dict(model.named_parameters()), left, right, strict=True):
            with self.subTest(parameter=name):
                self.assertTrue(bool(torch.isfinite(a).all()))
                torch.testing.assert_close(a, b, atol=2e-10, rtol=1e-9)

    def test_masked_sequence_likelihood_and_gradients_match_global_enumeration_for_all_arms_and_sizes(self):
        for entities in range(3, 7):
            tape = batch(entities)
            for name, factory in models():
                with self.subTest(entities=entities, model=name):
                    model = factory()
                    actual = learning.replay(tape, model=model, differentiable=True)
                    joint = sequence_log_likelihood(model, tape)
                    expected = -joint.sum() / actual['observed_events']
                    self.assertEqual(actual['observed_events'], 4)
                    self.assertTrue(bool(actual['answered'].all() and actual['scored'].all()))
                    torch.testing.assert_close(actual['observed_log_likelihood'].sum(0), joint,
                                               atol=1e-11, rtol=0)
                    torch.testing.assert_close(actual['loss'], expected, atol=1e-11, rtol=0)
                    self.assert_gradients(actual['loss'], expected, model)

    def test_full_three_entity_objective_and_gradients_match_frozen_six_arm_path(self):
        tape = batch(3, masked=False, aliases=False)
        old_batch = old.SensorBatch(tape.observations, tape.actions)
        for name, factory in model_factories().items():
            with self.subTest(model=name):
                model = factory()
                actual = learning.replay(tape, model=model, differentiable=True)
                reference = old.joint_log_probabilities(model, old_batch)
                expected = old.full_world_nll(reference, tape.observations[1:])
                torch.testing.assert_close(actual['log_probabilities'], reference, atol=1e-12, rtol=0)
                torch.testing.assert_close(actual['loss'], expected, atol=1e-12, rtol=0)
                self.assert_gradients(actual['loss'], expected, model)

    def test_visible_joint_is_a_correlated_marginal_not_independent_bit_loss(self):
        x = torch.zeros(2, 1, 6, dtype=DTYPE)
        mask = torch.ones_like(x, dtype=torch.bool)
        mask[1, :, :-2] = False
        x[~mask] = -1
        tape = learning.ObservedBatch(x, torch.tensor([[OBSERVE]]), mask, mask[1:].clone(), ('joint',))
        model = DelayedBit(0., outcome=3)
        result = learning.replay(tape, model=model, differentiable=True)
        self.assertAlmostEqual(float(result['loss'].detach()), math.log(2), places=12)
        self.assertAlmostEqual(float(torch.autograd.grad(result['loss'], model.logit)[0]), .5, places=12)

    def test_later_evidence_backpropagates_through_underflowed_hidden_history(self):
        tape, model = delayed_batch(), DelayedBit(-1000.)
        result = learning.replay(tape, model=model, differentiable=True)
        self.assertEqual(result['scored'].flatten().tolist(), [False, True, True])
        self.assertEqual(result['observed_events'], 2)
        self.assertEqual(result['observed_log_likelihood'][:, 0].tolist(), [0., 0., -1000.])
        self.assertEqual(float(result['loss'].detach()), 500.)
        self.assertEqual(float(torch.autograd.grad(result['loss'], model.logit)[0]), -.5)
        self.assertEqual(float(result['log_probabilities'][2, 0, 1].exp().detach()), 0.)
        with self.assertRaisesRegex(ValueError, 'outside model support'):
            learning.replay(tape, model=DelayedBit(impossible=True), differentiable=True)

    def test_converged_worlds_keep_distinct_recurrent_histories_and_training_graph(self):
        model, tape = DelayedBit(math.log(1 / 3)), delayed_batch()
        paths = active_paths.NeuralPaths(model, tape.observations[0], differentiable=True)
        for step in range(2):
            paths.predict(tape.actions[step])
            paths.receive(tape.observations[step + 1], tape.masks[step + 1])
        self.assertEqual(paths.bits.tolist(), [[0.] * 6, [0.] * 6])
        self.assertEqual(paths.state[:, 1].tolist(), [0., 1.])
        self.assertTrue(paths.weight.requires_grad)
        forecast, _ = paths.predict(tape.actions[2])
        torch.testing.assert_close(forecast[0, :2].exp(), torch.tensor([.75, .25], dtype=DTYPE),
                                   atol=1e-12, rtol=0)
        evidence = paths.receive(tape.observations[3], tape.masks[3])
        self.assertAlmostEqual(float(torch.autograd.grad(-evidence.sum(), model.logit)[0]), -.75, places=12)

    def test_all_missing_step_has_no_loss_but_does_not_reset_the_hidden_transition(self):
        tape = delayed_batch()
        prefix = learning.ObservedBatch(tape.observations[:2], tape.actions[:1], tape.masks[:2],
                                       tape.coverage[:1], tape.episode_ids)
        result = learning.replay(prefix, model=DelayedBit(), differentiable=True)
        self.assertEqual(result['observed_events'], 0)
        self.assertIsNone(result['loss'])
        self.assertEqual(result['observed_log_likelihood'].tolist(), [[0.]])
        self.assertFalse(bool(result['scored'].any()))
        with self.assertRaisesRegex(ValueError, 'observ'):
            learning.fit(DelayedBit(), [prefix], updates=1, cpu_seconds=10)

    def test_default_and_differentiable_replay_agree_without_mutating_data_or_weights(self):
        tape = batch(6)
        for name, factory in models():
            with self.subTest(model=name):
                model = factory()
                before, weights = tape.digest(), old.fingerprint(model.state_dict())
                inference = learning.replay(tape, model=model)
                training = learning.replay(tape, model=model, differentiable=True)
                for field in ('log_probabilities', 'observed_log_likelihood', 'loss'):
                    torch.testing.assert_close(inference[field], training[field], atol=1e-12, rtol=0)
                    self.assertFalse(inference[field].requires_grad)
                    self.assertTrue(training[field].requires_grad)
                self.assertTrue(all(p.grad is None for p in model.parameters()))
                self.assertEqual((tape.digest(), old.fingerprint(model.state_dict())), (before, weights))

    def test_future_observations_cannot_change_their_own_forecasts(self):
        original = batch(6)
        changed = deepcopy(original)
        values, visible = changed.observations[2:, :, 0], changed.masks[2:, :, 0]
        values[visible] = 1 - values[visible]
        changed.validate()
        for model in (DomainKernel(hidden=4), DomainFlatGRU(hidden=4)):
            with self.subTest(model=type(model).__name__):
                a = learning.replay(original, model=model, differentiable=True)['log_probabilities']
                b = learning.replay(changed, model=model, differentiable=True)['log_probabilities']
                self.assertTrue(torch.equal(a[:2], b[:2]))
                self.assertFalse(torch.equal(a[2], b[2]))

    def test_unequal_mask_batch_matches_separate_episode_likelihoods_and_gradients(self):
        left, right = batch(6, tag='left'), batch(6, tag='right')
        right.masks[2] = False
        right.observations[2] = -1
        combined = learning.ObservedBatch(*(torch.cat([getattr(left, name), getattr(right, name)], dim=1)
            for name in ('observations', 'actions', 'masks', 'coverage')), left.episode_ids + right.episode_ids)
        for model in (DomainKernel(hidden=4, persistence=True), DomainFlatGRU(hidden=4, persistence=True)):
            together = learning.replay(combined, model=model, differentiable=True)
            separate = [learning.replay(tape, model=model, differentiable=True) for tape in (left, right)]
            self.assertEqual(together['observed_events'], 7)
            for episode, result in enumerate(separate):
                torch.testing.assert_close(together['log_probabilities'][:, episode:episode + 1],
                                           result['log_probabilities'], atol=1e-12, rtol=0)
            expected = sum(r['loss'] * r['observed_events'] for r in separate) / 7
            torch.testing.assert_close(together['loss'], expected, atol=1e-12, rtol=0)
            self.assert_gradients(together['loss'], expected, model)

    def test_differentiable_filter_preserves_order_and_checks_limits_without_pruning(self):
        tape, model = delayed_batch(), DelayedBit(-1000.)
        paths = active_paths.NeuralPaths(model, tape.observations[0], differentiable=True,
                                         limit=2, expansion_limit=64)
        with self.assertRaisesRegex(ValueError, 'prediction required'):
            paths.receive(tape.observations[1], tape.masks[1])
        paths.predict(tape.actions[0])
        with self.assertRaisesRegex(ValueError, 'feedback required'):
            paths.predict(tape.actions[0])
        paths.receive(tape.observations[1], tape.masks[1])
        self.assertEqual(paths.weight.tolist(), [0., -1000.])
        before = (paths.bits.clone(), paths.weight.clone(), paths.state.clone())
        with self.assertRaisesRegex(ValueError, 'candidate expansion'):
            paths.predict(tape.actions[1])
        self.assertEqual(model.predict_calls, 1)
        for current, saved in zip((paths.bits, paths.weight, paths.state), before, strict=True):
            self.assertTrue(torch.equal(current, saved))
        limited = active_paths.NeuralPaths(DelayedBit(-1000.), tape.observations[0],
                                           differentiable=True, limit=1)
        limited.predict(tape.actions[0])
        with self.assertRaisesRegex(ValueError, 'live path bound'):
            limited.receive(tape.observations[1], tape.masks[1])
        self.assertEqual(limited.weight.tolist(), [0.])

    def test_every_arm_and_empirical_abstraction_fits_the_same_realized_histories(self):
        tapes = [batch(n, masked=masked) for n in range(3, 7) for masked in (False, True)]
        hashes, inputs = set(), [tape.digest() for tape in tapes]
        for name, factory in models():
            with self.subTest(model=name):
                model = factory()
                before = old.fingerprint(model.state_dict())
                report = learning.fit(model, tapes, updates=1, cpu_seconds=30)
                self.assertEqual((report['objective'], report['completed_updates']), ('observed_joint_nll', 1))
                self.assertNotEqual(old.fingerprint(model.state_dict()), before)
                hashes.add(report['training_input_sha256'])
                json.dumps(report, allow_nan=False)
        for mode, first in (('local', False), ('prefix', False), ('contact', False), ('contact', True)):
            memory, report = learning.fit_empirical(tapes, mode=mode, first_contact=first)
            self.assertEqual(report['objective'], 'observed_counts')
            self.assertEqual(sum(sum(counts.values()) for counts in memory.table.values()), 16)
            hashes.add(report['training_input_sha256'])
            json.dumps(report, allow_nan=False)
        self.assertEqual(len(hashes), 1)
        self.assertEqual([tape.digest() for tape in tapes], inputs)

    def test_incomplete_contact_history_is_never_repaired_with_later_full_observations(self):
        tape = batch(6, masked=False)
        tape.masks[1, 0, -1] = False
        tape.observations[1, 0, -1] = -1
        before, hashes = tape.digest(), set()
        for mode, first, expected in (('local', False, 2), ('prefix', False, 0),
                                       ('contact', False, 0), ('contact', True, 0)):
            with self.subTest(mode=mode, first_contact=first):
                memory, report = learning.fit_empirical([tape], mode=mode, first_contact=first)
                self.assertEqual(sum(sum(counts.values()) for counts in memory.table.values()), expected)
                hashes.add(report['training_input_sha256'])
        self.assertEqual(len(hashes), 1)
        self.assertEqual(tape.digest(), before)

    def test_unsupported_control_is_not_a_zero_loss_and_evaluation_remains_strict_json(self):
        tape, memory = batch(6), DomainMemory('local')
        result = learning.replay(tape, memory=memory)
        self.assertFalse(bool(result['answered'].any() or result['scored'].any()))
        self.assertTrue(bool(torch.isnan(result['observed_log_likelihood']).all()))
        self.assertIsNone(result['loss'])
        for predictor in ({'memory': memory}, {'control': 'no_change'}):
            report = learning.evaluate([tape], **predictor)
            self.assertEqual(report['gate_g1'], 'NOT_ADMITTED')
            json.dumps(report, allow_nan=False)

    def test_synthetic_fit_checkpoint_load_and_fresh_evaluation_are_one_common_path(self):
        tapes = [batch(3, masked=False), batch(6, masked=False)]
        predictors = []
        for model in (DomainKernel(hidden=4), DomainFlatGRU(hidden=4)):
            report = learning.fit(model, tapes, updates=1, cpu_seconds=30)
            predictors.append(({'model': model}, report))
        memory, report = learning.fit_empirical(tapes, mode='contact')
        predictors.append(({'memory': memory, 'control': 'contact'}, report))
        predictors.append(({'control': 'no_change'}, {'training_input_sha256': report['training_input_sha256'],
                           'objective': 'no_change', 'completed_updates': 0}))
        with tempfile.TemporaryDirectory() as folder:
            for ordinal, (predictor, provenance) in enumerate(predictors):
                with self.subTest(predictor=ordinal):
                    path = Path(folder) / f'{ordinal}.json'
                    saved = checkpoint.save_checkpoint(path, **predictor, provenance=provenance)
                    restored = checkpoint.load_checkpoint(path, saved['sha256'])
                    fresh = {key: restored[key] for key in ('model', 'memory', 'control')}
                    for tape in tapes:
                        a, b = learning.replay(tape, **predictor), learning.replay(tape, **fresh)
                        for key in ('log_probabilities', 'answered', 'observed_log_likelihood', 'scored'):
                            torch.testing.assert_close(a[key], b[key], atol=0, rtol=0, equal_nan=True)
                        self.assertEqual(a['history_sha256'], b['history_sha256'])
                    report = learning.evaluate(tapes, **fresh)
                    self.assertEqual(report['gate_g1'], 'NOT_ADMITTED')
                    json.dumps(report, allow_nan=False)
                    scope = restored['metadata']['scope']
                    self.assertTrue(scope['fresh_episodes_only'])
                    self.assertFalse(scope['optimizer_resume'] or scope['live_session_resume'])

    def test_failed_continuation_retains_valid_forecasts_scores_and_planned_denominators(self):
        x = torch.zeros(3, 1, 6, dtype=DTYPE)
        masks = torch.ones_like(x, dtype=torch.bool)
        actions = torch.tensor([[OBSERVE]] * 2, dtype=torch.long)
        reference = learning.ObservedBatch(x, actions, masks, masks[1:].clone(), ('reference',))
        memory, _ = learning.fit_empirical([reference], mode='local')
        conflict = deepcopy(reference)
        conflict.observations[2, 0, -1] = 1
        for predictor in ({'model': DomainKernel(hidden=4, persistence=True)},
                          {'model': DomainFlatGRU(hidden=4, persistence=True)},
                          {'memory': memory}, {'control': 'no_change'}):
            with self.subTest(predictor=next(iter(predictor.values())).__class__.__name__):
                report = learning.evaluate([conflict], **predictor)
                self.assertEqual((report['planned_action_events'], report['observed_events'],
                                  report['answered_forecasts'], report['scored_events']), (2, 2, 2, 2))
                self.assertEqual((report['forecast_coverage'], report['observed_coverage']), (1., 1.))
                self.assertEqual(report['observed_nll'], 'positive_infinity')
                record = report['records'][0]
                self.assertEqual(record['observed_log_likelihood'], [[0.], ['negative_infinity']])
                self.assertEqual(record['answered'], [[True], [True]])
                self.assertEqual(record['scored'], [[True], [True]])
                self.assertEqual(len(record['log_probabilities']['values']), 2)
                if predictor.get('control') != 'no_change':
                    self.assertEqual(report['failed_batches'], 1)
                    self.assertEqual((record['status'], record['step'], record['phase']),
                                     ('REPLAY_ERROR', 1, 'feedback'))
                    with self.assertRaises(learning.ReplayFailure) as failure:
                        learning.replay(conflict, **predictor)
                    partial = failure.exception.result
                    self.assertEqual(partial['log_probabilities'].shape, (2, 1, 64))
                    self.assertTrue(bool(partial['scored'].all()))
                    self.assertTrue(bool(torch.isneginf(partial['observed_log_likelihood'][1, 0])))
                else:
                    self.assertEqual(report['failed_batches'], 0)
                json.dumps(report, allow_nan=False)
        resource = delayed_batch()
        resource.masks[1, 0, :-1] = True
        resource.observations[1, 0, :-1] = 0
        report = learning.evaluate([resource], model=DelayedBit(), expansion_limit=64)
        self.assertEqual((report['planned_action_events'], report['observed_events'],
                          report['answered_forecasts'], report['scored_events']), (3, 3, 1, 1))
        self.assertEqual((report['forecast_coverage'], report['observed_coverage']), (1 / 3, 1 / 3))
        self.assertIsNone(report['observed_nll'])
        self.assertAlmostEqual(report['conditional_observed_nll'], 0., places=12)
        record = report['records'][0]
        self.assertEqual((record['step'], record['phase']), (1, 'predict'))
        self.assertEqual(record['scored'], [[True]])
        self.assertEqual(len(record['log_probabilities']['values']), 1)
        json.dumps(report, allow_nan=False)

    def test_first_contact_policy_survives_default_replay_evaluation_and_checkpoint(self):
        x = torch.zeros(4, 1, 6, dtype=DTYPE)
        masks = torch.ones_like(x, dtype=torch.bool)
        tape = learning.ObservedBatch(x, torch.tensor([[(0, 0, 5, -1)]] * 3), masks,
                                      masks[1:].clone(), ('three-contacts',))
        memory, provenance = learning.fit_empirical([tape], mode='contact', first_contact=True)
        self.assertEqual(memory.control_name, 'first_contact')
        default = learning.replay(tape, memory=memory)
        explicit = learning.replay(tape, memory=memory, control='first_contact')
        self.assertTrue(bool(default['answered'].all()))
        self.assertTrue(torch.equal(default['log_probabilities'], explicit['log_probabilities']))
        report = learning.evaluate([tape], memory=memory)
        self.assertEqual((report['answered_forecasts'], report['scored_events']), (3, 3))
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'first-contact.json'
            saved = checkpoint.save_checkpoint(path, memory=memory, provenance=provenance)
            restored = checkpoint.load_checkpoint(path, saved['sha256'])
            self.assertEqual(restored['control'], 'first_contact')
            self.assertEqual(restored['memory'].control_name, 'first_contact')
            result = learning.replay(tape, memory=restored['memory'])
            self.assertTrue(torch.equal(result['log_probabilities'], default['log_probabilities']))
            for function in (lambda: learning.replay(tape, memory=memory, control='contact'),
                             lambda: learning.evaluate([tape], memory=memory, control='contact'),
                             lambda: checkpoint.save_checkpoint(Path(folder) / 'wrong.json', memory=memory,
                                         control='contact', provenance=provenance)):
                with self.assertRaises(ValueError):
                    function()

    def test_learning_after_checkpoint_load_refreshes_provenance_seen_by_direct_session(self):
        tape = batch(6)
        inherited = {'training_input_sha256': None, 'objective': 'untrained_or_inherited', 'completed_updates': 0}
        with tempfile.TemporaryDirectory() as folder:
            for index, original in enumerate((DomainKernel(hidden=4), DomainFlatGRU(hidden=4))):
                path = Path(folder) / f'{index}.json'
                saved = checkpoint.save_checkpoint(path, model=original, provenance=inherited)
                restored = checkpoint.load_checkpoint(path, saved['sha256'])
                model, original_metadata = restored['model'], deepcopy(restored['metadata'])
                self.assertIsNotNone(model.checkpoint_metadata)
                report = learning.fit(model, [tape], updates=1, cpu_seconds=30)
                self.assertIsNone(getattr(model, 'checkpoint_metadata', None))
                self.assertEqual(model.domain_adaptation['training_provenance'], report)
                self.assertEqual(model.training_provenance, report)
                self.assertEqual(restored['metadata'], original_metadata)
                names = list('abcdef')
                started = Session(model=model).handle({'op': 'start', 'episode': 'updated', 'ids': names,
                    'observation': dict(zip(names, map(int, tape.observations[0, 0].tolist()), strict=True))})
                identity = started['implementation']
                self.assertIsNone(identity['checkpoint'])
                self.assertEqual(identity['adaptation']['training_provenance'], report)
                self.assertEqual(identity['checkpoint_state_sha256'], old.fingerprint(model.state_dict()))
                self.assertNotEqual(identity['checkpoint_state_sha256'], original_metadata['state_sha256'])

    def test_evaluation_identity_does_not_relabel_training_history_or_optimizer_contract(self):
        training, held_out = batch(3, tag='train'), batch(6, tag='evaluation')
        model = DomainFlatGRU(hidden=4)
        report = learning.fit(model, [training], updates=1, cpu_seconds=30, learning_rate=.007,
                              limit=17, expansion_limit=128)
        self.assertEqual((report['optimizer'], report['learning_rate'], report['live_path_limit'],
                          report['candidate_expansion_limit']), ('Adam', .007, 17, 128))
        self.assertEqual(report['training_source_sha256'], sha256(Path(learning.__file__).read_bytes()).hexdigest())
        evaluation = learning.evaluate([held_out], model=model)
        expected = sha256(json.dumps([held_out.digest()], separators=(',', ':')).encode()).hexdigest()
        self.assertEqual(evaluation['evaluation_input_sha256'], expected)
        self.assertNotIn('training_input_sha256', evaluation)
        self.assertNotEqual(expected, report['training_input_sha256'])
        self.assertEqual(evaluation['training_provenance'], report)
        evaluation['training_provenance']['training_input_sha256'] = '0' * 64
        self.assertEqual(model.training_provenance, report)
        json.dumps(evaluation, allow_nan=False)


if __name__ == '__main__':
    unittest.main()
