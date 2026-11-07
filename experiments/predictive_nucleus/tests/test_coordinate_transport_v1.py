"""Synthetic learned-frame projection, custody and restoration regressions."""
from copy import deepcopy
import json
import unittest
from unittest.mock import patch

import torch

from experiments.predictive_nucleus import coordinate_transport_v1 as transport
from experiments.predictive_nucleus import effect_role_lexical as lexical
from experiments.predictive_nucleus import effect_role_model as physical
from experiments.predictive_nucleus.binding_layout_coordinates import coordinate_encoder
from experiments.predictive_nucleus.domain_kernel import DomainKernel
from experiments.predictive_nucleus.joint_objective import DTYPE, fingerprint
from experiments.predictive_nucleus.tests.test_effect_role_model import bank


class CoordinateTransport(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.threads = torch.get_num_threads()
        torch.set_num_threads(1)

    @classmethod
    def tearDownClass(cls):
        torch.set_num_threads(cls.threads)

    def setUp(self):
        self.registry = physical.create_registry([bank(), bank(('novel_a', 'novel_b'))])
        parent = coordinate_encoder(7)
        with torch.no_grad():
            parent.layout[0].weight.copy_(torch.tensor([[-2., 1., -.5]], dtype=DTYPE))
            parent.order.weight.copy_(torch.tensor([[[1.]], [[-1.]]], dtype=DTYPE))
            parent.order.bias.copy_(torch.tensor([10., -10.], dtype=DTYPE))
        self.net = lexical.encoder(7, parent.state_dict(), self.registry, lexical.inherited_ids(self.registry))
        self.initial_sha = fingerprint(self.net.state_dict())
        with torch.no_grad():
            for word, coordinates in (('novel_a', (1.3, 2.)), ('novel_b', (-.8, -1.1))):
                index = self.net.new_ids.index(self.registry['tokens'][word]['id'])
                self.net.new_coordinates[index].copy_(torch.tensor(coordinates, dtype=DTYPE))
        self.net.eval().requires_grad_(False)
        with torch.random.fork_rng(devices=[]):
            torch.manual_seed(481)
            self.world = DomainKernel(hidden=3, role_tying=False).eval().requires_grad_(False)
        self.records = [
            {'id': 'z-svo', 'entities': ['A', 'B', 'C'], 'anchor': [0, 0, 0],
             'context': [{'action': [1, 2, -1, 1], 'reading': [0, 0, 1]}], 'text': 'A novel_a B'},
            {'id': 'a-osv', 'entities': ['X', 'Y', 'Z'], 'anchor': [0, 0, 0],
             'context': [{'action': [1, 2, -1, 1], 'reading': [0, 0, 1]}], 'text': 'Y X novel_a'},
            {'id': 'm-vos', 'entities': ['U', 'V', 'W'], 'anchor': [0, 0, 0],
             'context': [{'action': [1, 2, -1, 1], 'reading': [0, 0, 1]},
                         {'action': [1, 0, -1, 1], 'reading': [1, 0, 1]}], 'text': 'novel_a V U'},
            {'id': 'b-other', 'entities': ['P', 'Q', 'R'], 'anchor': [0, 0, 0],
             'context': [{'action': [1, 2, -1, 1], 'reading': [0, 0, 1]}], 'text': 'P novel_b Q'},
        ]

    def project(self, view='intact', records=None):
        return transport.project(self.net, self.world, self.registry,
                                 self.records if records is None else records, view)

    def test_projection_native_mixture_uniform_average_and_frame_binding(self):
        rows, checks = self.project()
        self.assertEqual(set(rows), {record['id'] for record in self.records})
        self.assertEqual({key: checks[key] for key in ('records', 'endpoint_complement_checks',
                         'projection_checks', 'uniform_hypothesis_checks')},
                         {'records': 4, 'endpoint_complement_checks': 4,
                          'projection_checks': 16, 'uniform_hypothesis_checks': 4})
        self.assertLessEqual(checks['maximum_projection_error'], 1e-12)
        self.assertLessEqual(checks['maximum_uniform_error'], 1e-12)
        self.assertTrue(checks['language_unchanged'] and checks['world_unchanged'])
        for record in self.records:
            row = rows[record['id']]
            action = torch.tensor(row['action_probabilities'], dtype=DTYPE)
            native = torch.tensor(row['native_likelihood'], dtype=DTYPE)
            likelihood = torch.tensor(row['likelihood'], dtype=DTYPE)
            self.assertEqual((action.shape, native.shape, likelihood.shape), ((4, 4), (4, 8), (4, 8)))
            torch.testing.assert_close(likelihood, action @ native, atol=1e-12, rtol=0.)
            torch.testing.assert_close(action.mean(0), torch.full((4,), .25, dtype=DTYPE), atol=1e-12, rtol=0.)
            for values in (action, native, likelihood):
                self.assertTrue(bool(torch.isfinite(values).all() and (values >= 0).all()))
                torch.testing.assert_close(values.sum(-1), torch.ones(4, dtype=DTYPE), atol=1e-12, rtol=0.)
            features, mentions = physical.tokenize_batch([record['text']], [record['entities']], self.registry)
            torch.testing.assert_close(action[0], self.net(features)[0].exp(), atol=1e-14, rtol=0.)
            self.assertEqual(row['actions'], physical.action_candidates(mentions)[0].tolist())
            self.assertEqual(row['entities'], record['entities'])
            frame = row['frame']
            self.assertEqual(frame['language_sha256'], fingerprint(self.net.state_dict()))
            self.assertEqual(frame['world_sha256'], fingerprint(self.world.state_dict()))
            self.assertEqual(frame['registry_sha256'], transport.c.digest(self.registry))
            self.assertEqual(frame['transforms'], [list(signs) for signs in transport.TRANSFORMS])
            self.assertEqual(row['frame_digest'], transport.c.digest(frame))
        self.assertEqual(rows['z-svo']['frame'], rows['m-vos']['frame'])
        self.assertNotEqual(rows['z-svo']['frame_digest'], rows['b-other']['frame_digest'])
        self.assertEqual(len({row['prefix_digest'] for row in rows.values()}), 4)
        json.dumps(rows, allow_nan=False)

    def test_sign_order_and_layout_views_follow_learned_response(self):
        recorded = {}
        for view in transport.VIEWS:
            rows, _ = self.project(view)
            recorded[view] = rows
            layout = self.net.parent.layout[0].weight[0].clone()
            if view == 'zero_layout':
                layout.zero_()
            elif view == 'cycled_layout':
                layout = layout.roll(1)
            for record in self.records:
                tokens = record['text'].split()
                position = next(i for i, token in enumerate(tokens) if token not in record['entities'])
                identity = self.registry['tokens'][tokens[position]]['id']
                effect, role = self.net.new_coordinates[self.net.new_ids.index(identity)]
                expected = []
                for effect_sign, role_sign in transport.TRANSFORMS:
                    family = torch.stack((torch.zeros_like(effect), effect_sign * effect)).softmax(-1)
                    roles = (self.net.parent.order.weight[:, 0, 0] * role_sign * role * layout[position]).softmax(-1)
                    expected.append((family[:, None] * roles[None, :]).flatten())
                torch.testing.assert_close(torch.tensor(rows[record['id']]['action_probabilities'], dtype=DTYPE),
                                           torch.stack(expected), atol=1e-14, rtol=0.)
        intact = recorded['intact']['z-svo']
        for view in ('zero_layout', 'cycled_layout'):
            changed = recorded[view]['z-svo']
            self.assertEqual(changed['native_likelihood'], intact['native_likelihood'])
            self.assertNotEqual(changed['action_probabilities'], intact['action_probabilities'])
            self.assertNotEqual(changed['frame_digest'], intact['frame_digest'])

    def test_parameters_registry_inputs_rng_and_returned_frames_are_detached(self):
        before = (fingerprint(self.net.state_dict()), fingerprint(self.world.state_dict()),
                  transport.c.digest(self.registry), deepcopy(self.records), torch.random.get_rng_state())
        for view in transport.VIEWS:
            rows, _ = self.project(view)
        self.assertEqual(fingerprint(self.net.state_dict()), before[0])
        self.assertEqual(fingerprint(self.world.state_dict()), before[1])
        self.assertEqual(transport.c.digest(self.registry), before[2])
        self.assertEqual(self.records, before[3])
        self.assertTrue(torch.equal(torch.random.get_rng_state(), before[4]))
        rows['z-svo']['frame']['transforms'][0][0] = 9
        rows['z-svo']['entities'][0] = 'changed'
        self.assertEqual(rows['a-osv']['frame']['transforms'][0], [1, 1])
        self.assertEqual(self.records, before[3])
        self.assertEqual(transport.TRANSFORMS[0], (1, 1))

    def test_record_and_group_order_are_joined_by_evidence_id(self):
        expected, checks = self.project()
        actual, reordered_checks = self.project(records=list(reversed(self.records)))
        self.assertEqual(actual, expected)
        self.assertEqual(reordered_checks, checks)
        real_pack = transport.pack

        def reverse_complement_groups(inputs, world, registry):
            groups = real_pack(inputs, world, registry)
            if inputs['episodes'][0]['utterances'][0]['reading'] == [1, 1, 1]:
                groups.reverse()
            return groups

        with patch.object(transport, 'pack', side_effect=reverse_complement_groups):
            actual, other_checks = self.project()
        self.assertEqual(actual, expected)
        self.assertEqual(other_checks, checks)

    def test_endpoint_complement_checks_all_preobservation_fields(self):
        real_pack = transport.pack
        for field in ('state', 'features', 'mentions', 'likelihood'):
            def changed_complement(inputs, world, registry):
                groups = real_pack(inputs, world, registry)
                if inputs['episodes'][0]['utterances'][0]['reading'] == [1, 1, 1]:
                    group = groups[0]
                    if field == 'state':
                        group['state'][0, 0] += .01
                    elif field == 'mentions':
                        event = group['events'][0]
                        event[field][0, 0] = (event[field][0, 0] + 1) % 3
                    else:
                        group['events'][0][field].reshape(-1)[0] += .01
                return groups

            with self.subTest(field=field), patch.object(transport, 'pack', side_effect=changed_complement):
                with self.assertRaisesRegex(ValueError, 'endpoint placeholder'):
                    self.project()

    def test_prefix_schema_and_acquired_identity_scope_reject_hidden_or_invalid_inputs(self):
        bad = [[], self.records * 2, [{**self.records[0], 'reading': [1, 1, 1]}],
               [{**self.records[0], 'meaning': 2}], [{**self.records[0], 'text': 'A touches B'}],
               [{**self.records[0], 'text': 'A unknown B'}],
               [{**self.records[0], 'entities': ['A', 'B', 'C', 'D']}],
               [{**self.records[0], 'context': []}]]
        leaked_context = deepcopy(self.records[0])
        leaked_context['context'][0]['mode'] = 1
        bad.append([leaked_context])
        for index, records in enumerate(bad):
            with self.subTest(case=index), self.assertRaises(ValueError):
                self.project(records=records)
        for view in ('unregistered', True, None):
            with self.subTest(view=view), self.assertRaises(ValueError):
                self.project(view)

    def test_frozen_language_world_and_registry_binding_are_required(self):
        self.net.new_coordinates.requires_grad_(True)
        with self.assertRaises(ValueError):
            self.project()
        self.net.requires_grad_(False)
        self.net.train()
        with self.assertRaises(ValueError):
            self.project()
        self.net.eval()
        self.world.train()
        with self.assertRaises(ValueError):
            self.project()
        self.world.eval()
        self.net.registry_sha256 = 'f' * 64
        with self.assertRaises(ValueError):
            self.project()

    def restore_fixture(self):
        protected = fingerprint(self.net.parent.state_dict())
        saved = {'arm': 'grounded', 'seed': 7, 'state_sha256': fingerprint(self.net.state_dict()),
                 'state': {name: value.tolist() for name, value in self.net.state_dict().items()}}
        report = {'initial_sha256': self.initial_sha, 'final_sha256': saved['state_sha256'],
                  'new_ids': list(self.net.new_ids), 'legacy_ids': list(self.net.legacy_ids),
                  'registry_sha256': transport.c.digest(self.registry),
                  'protected_initial_sha256': protected, 'protected_final_sha256': protected,
                  'world_sha256': fingerprint(self.world.state_dict())}
        other_world = deepcopy(self.world)
        with torch.no_grad():
            next(other_world.parameters()).add_(.01)
        worlds = {'nand': self.world, 'nor': other_world}
        freeze = {'version': 'effect-role-v3', 'artifacts': {'lexical-registry.json': {'sha256': 'b' * 64}},
                  'world_checkpoints': {f'{law}/7': {'state_sha256': fingerprint(world.state_dict())}
                                        for law, world in worlds.items()}}
        training = {'version': 'effect-role-v3', 'complete': True, 'freeze_sha256': 'a' * 64,
                    'reports': {'grounded/7': report},
                    'checkpoints': {'grounded/7': {'file': 'grounded-7.json', 'sha256': 'c' * 64}}}
        values = {'training.json': (transport.TRAINING_SHA256, training), 'freeze.json': ('a' * 64, freeze),
                  'lexical-registry.json': ('b' * 64, self.registry), 'grounded-7.json': ('c' * 64, saved)}

        def read(path, digest):
            expected, value = values[path.name]
            self.assertEqual(digest, expected)
            return deepcopy(value)

        def load_world(actual_freeze, law, seed):
            self.assertEqual(actual_freeze, freeze)
            self.assertEqual(seed, 7)
            return deepcopy(worlds[law])

        return values, read, load_world

    def test_restore_verifies_pinned_chain_and_distinct_requested_world(self):
        _, read, load_world = self.restore_fixture()
        with patch.object(transport, 'read_locked', side_effect=read) as reader, \
                patch.object(transport, 'world_for', side_effect=load_world):
            recovered = [transport.restore(7, law) for law in ('nand', 'nor')]
        self.assertEqual(reader.call_count, 8)
        for net, world, registry, metadata in recovered:
            self.assertEqual(fingerprint(net.state_dict()), fingerprint(self.net.state_dict()))
            self.assertEqual(registry, self.registry)
            self.assertEqual(metadata['world_sha256'], fingerprint(world.state_dict()))
            self.assertEqual(metadata['registry_sha256'], transport.c.digest(registry))
            self.assertEqual(metadata['new_ids'], list(net.new_ids))
            self.assertFalse(net.training or world.training)
            self.assertTrue(all(not p.requires_grad and p.grad is None
                                for p in (*net.parameters(), *world.parameters())))
        self.assertNotEqual(recovered[0][3]['world_sha256'], recovered[1][3]['world_sha256'])

    def test_restore_rejects_wrong_bindings_and_invalid_requests(self):
        for field in ('new_ids', 'protected_final_sha256', 'world_sha256'):
            values, read, load_world = self.restore_fixture()
            report = values['training.json'][1]['reports']['grounded/7']
            report[field] = list(reversed(report[field])) if field == 'new_ids' else 'f' * 64
            with self.subTest(field=field), patch.object(transport, 'read_locked', side_effect=read), \
                    patch.object(transport, 'world_for', side_effect=load_world), self.assertRaises(ValueError):
                transport.restore(7, 'nor')
        with patch.object(transport, 'read_locked') as reader:
            for seed, law in ((True, 'nand'), (8, 'nand'), (7, 'xor'), (7, None)):
                with self.subTest(seed=seed, law=law), self.assertRaises(ValueError):
                    transport.restore(seed, law)
            reader.assert_not_called()
