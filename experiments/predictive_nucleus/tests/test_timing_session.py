"""Synthetic timing transport checks: endpoint evidence, binding and atomicity."""
from copy import deepcopy
import math
import unittest
from unittest.mock import patch

import torch

from experiments.predictive_nucleus.acceptance_contract import receipt
from experiments.predictive_nucleus.domain_kernel import DomainKernel
from experiments.predictive_nucleus.joint_objective import DTYPE, fingerprint
from experiments.predictive_nucleus.timing_kernel import TimingKernel
from experiments.predictive_nucleus.timing_session import Session


ANCHOR = {'a': 0, 'b': 1, 'c': 0}
CONTACT = {'kind': 'contact', 'participants': ['a', 'b']}


def group(timing='common_snapshot'):
    return {'kind': 'contact_group', 'timing': timing, 'contacts': [['a', 'b'], ['b', 'c']]}


def start(session):
    return session.handle({'op': 'start', 'episode': 'synthetic', 'ids': ['c', 'a', 'b'],
                           'observation': ANCHOR.copy()})


def predict(session, action, step=0):
    return session.handle({'op': 'predict', 'episode': 'synthetic', 'step': step,
                           'action': action, 'sensor_ids': ['b', 'c', 'a']})


def feedback(session, forecast, observation):
    return session.handle({'op': 'feedback', 'episode': 'synthetic', 'step': forecast['step'],
                           'receipt': forecast['receipt'], 'observation': observation})


def logs(forecast):
    return torch.tensor([[-math.inf if x is None else x for x in forecast['log']['values'][0]]], dtype=DTYPE)


class TimingSessionTests(unittest.TestCase):
    def setUp(self):
        self.rng = torch.random.get_rng_state()
        torch.manual_seed(31067)

    def tearDown(self):
        torch.random.set_rng_state(self.rng)

    def test_single_then_group_then_suffix_conditions_only_real_endpoints(self):
        model = DomainKernel().eval()
        session = Session(model)
        identity = fingerprint(model.state_dict())
        started = start(session)
        self.assertEqual(started['ids'], ['a', 'b', 'c'])
        reference_world, reference_state = session.world.clone(), session.state.clone()
        with patch.object(model, 'receive', wraps=model.receive) as receive:
            first = predict(session, deepcopy(CONTACT))
            raw, pending = model.predict(reference_world, torch.tensor([[0, 0, 1, -1]]), reference_state)
            torch.testing.assert_close(logs(first), raw - raw.logsumexp(-1, keepdim=True), atol=1e-12, rtol=0)
            self.assertEqual(receive.call_count, 0)
            self.assertTrue(torch.equal(session.world, reference_world))
            self.assertTrue(torch.equal(session.state, reference_state))
            observed = {'a': 1, 'b': 0, 'c': 0}
            reference_world = torch.tensor([[1., 0., 0.]], dtype=DTYPE)
            reference_state = model.receive(pending, reference_world)
            receive.reset_mock()
            feedback(session, first, observed)
            self.assertEqual(receive.call_count, 1)
            torch.testing.assert_close(session.state, reference_state, atol=1e-12, rtol=0)
            receive.reset_mock()
            compound = predict(session, group('ordered'), step=1)
            raw, pending = TimingKernel(model).predict(reference_world,
                torch.tensor([[[0, 0, 1, -1], [0, 1, 2, -1]]]), 'ordered', reference_state)
            self.assertEqual(receive.call_count, 0)
            self.assertTrue(torch.equal(session.world, reference_world))
            self.assertTrue(torch.equal(session.state, reference_state))
            torch.testing.assert_close(logs(compound), raw - raw.logsumexp(-1, keepdim=True), atol=1e-12, rtol=0)
            self.assertEqual(session.step, 1)  # Two hypothetical contacts are not two feedback events.
            reference_world = torch.tensor([[0., 1., 1.]], dtype=DTYPE)
            reference_state = model.receive(pending, reference_world)
            receive.reset_mock()
            feedback(session, compound, {'a': 0, 'b': 1, 'c': 1})
            self.assertEqual(receive.call_count, 1)
            torch.testing.assert_close(session.state, reference_state, atol=1e-12, rtol=0)
            suffix = predict(session, {'kind': 'contact', 'participants': ['c', 'a']}, step=2)
            raw, _ = model.predict(reference_world, torch.tensor([[0, 2, 0, -1]]), reference_state)
            torch.testing.assert_close(logs(suffix), raw - raw.logsumexp(-1, keepdim=True), atol=1e-12, rtol=0)
            feedback(session, suffix, {'a': 0, 'b': 1, 'c': 0})
        ended = session.handle({'op': 'end', 'episode': 'synthetic'})
        self.assertEqual((ended['predictions'], ended['feedback_steps'], ended['pending_forecast']), (3, 3, False))
        self.assertEqual(identity, fingerprint(model.state_dict()))

    def test_receipts_bind_timing_contacts_coverage_and_scheduler_identity(self):
        model = DomainKernel().eval()
        forecasts = []
        for timing in ('ordered', 'common_snapshot'):
            session = Session(model)
            started = start(session)
            forecast = predict(session, group(timing))
            forecasts.append(forecast)
            self.assertEqual(forecast['implementation_sha256'], started['implementation_sha256'])
            self.assertEqual(forecast['receipt'], receipt(forecast))
            self.assertEqual(forecast['sensor_ids'], ['a', 'b', 'c'])
            for mutate in (
                lambda f: f['action'].__setitem__('timing', 'changed'),
                lambda f: f['action']['contacts'][0].reverse(),
                lambda f: f['sensor_ids'].pop(),
                lambda f: f.__setitem__('implementation_sha256', '0' * 64),
            ):
                changed = deepcopy(forecast)
                mutate(changed)
                self.assertNotEqual(receipt(changed), forecast['receipt'])
        self.assertNotEqual(forecasts[0]['receipt'], forecasts[1]['receipt'])

    def test_returned_coordinates_and_request_actions_do_not_alias_internal_state(self):
        session = Session(DomainKernel().eval())
        started = start(session)
        started['ids'].reverse()
        self.assertEqual(list(session.ids), ['a', 'b', 'c'])
        action = group()
        result = predict(session, action)
        saved_action = deepcopy(result['action'])
        action['contacts'][0].reverse()
        self.assertEqual(result['action'], saved_action)
        result['ids'].reverse()
        result['sensor_ids'].pop()
        self.assertEqual(list(session.ids), ['a', 'b', 'c'])
        feedback(session, result, {'a': 1, 'b': 1, 'c': 0})
        self.assertTrue(torch.equal(session.world, torch.tensor([[1., 1., 0.]], dtype=DTYPE)))

    def test_invalid_feedback_never_commits_world_or_posterior(self):
        for mutation in ('receipt', 'step', 'partial', 'coverage', 'unknown', 'boolean'):
            session = Session(DomainKernel().eval())
            start(session)
            result = predict(session, group())
            before = session.world.clone(), session.state.clone(), session.pending.clone(), session.step
            request = {'op': 'feedback', 'episode': 'synthetic', 'step': 0,
                       'receipt': result['receipt'], 'observation': ANCHOR.copy()}
            if mutation == 'receipt': request['receipt'] = '0' * 64
            elif mutation == 'step': request['step'] = 1
            elif mutation == 'partial': request['observation']['b'] = None
            elif mutation == 'coverage': del request['observation']['c']
            elif mutation == 'unknown': request['physical_mode'] = 0
            else: request['observation']['a'] = False
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                session.handle(request)
            for old, current in zip(before[:3], (session.world, session.state, session.pending), strict=True):
                self.assertTrue(torch.equal(old, current))
            self.assertEqual(session.step, before[3])

    def test_nonunit_raw_mass_is_rejected_before_publishing_or_committing_forecast(self):
        session = Session(DomainKernel().eval())
        start(session)
        world, state = session.world.clone(), session.state.clone()
        native = session.kernel.predict
        def scaled(*args, **kwargs):
            raw, joint = native(*args, **kwargs)
            return raw + math.log(2.), joint + math.log(2.)
        with patch.object(session.kernel, 'predict', scaled), self.assertRaisesRegex(ValueError, 'mass'):
            predict(session, group())
        self.assertEqual((session.phase, session.step), ('READY', 0))
        self.assertFalse(hasattr(session, 'pending'))
        self.assertTrue(torch.equal(session.world, world))
        self.assertTrue(torch.equal(session.state, state))

    def test_impossible_endpoint_does_not_commit_and_group_has_no_intermediate_feedback(self):
        session = Session(DomainKernel(persistence=True).eval())
        start(session)
        result = predict(session, CONTACT)
        before = session.world.clone(), session.state.clone()
        with self.assertRaisesRegex(ValueError, 'outside model support'):
            feedback(session, result, {'a': 0, 'b': 1, 'c': 1})  # Spectator cannot change.
        self.assertTrue(torch.equal(session.world, before[0]))
        self.assertTrue(torch.equal(session.state, before[1]))
        self.assertEqual(session.step, 0)
        for action in (group(), {**group(), 'intermediate_observation': ANCHOR.copy()},
                       {**group(), 'physical_mode': 0}):
            session = Session(DomainKernel().eval())
            start(session)
            if len(action) > 3:
                with self.assertRaises(ValueError): predict(session, action)
                self.assertEqual(session.phase, 'READY')
            else:
                result = predict(session, action)
                with self.assertRaises(ValueError): predict(session, CONTACT)
                self.assertEqual(session.step, 0)
                with self.assertRaises(ValueError):
                    session.handle({'op': 'end', 'episode': 'synthetic'})


if __name__ == '__main__':
    unittest.main()
