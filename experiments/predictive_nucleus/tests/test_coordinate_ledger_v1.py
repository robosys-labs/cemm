"""Synthetic transformed-frame custody, failure preservation and recovery checks."""
from copy import deepcopy
from hashlib import sha256
import json
import os
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from experiments.predictive_nucleus import acceptance_contract as c
from experiments.predictive_nucleus import coordinate_ledger_v1 as adapter
from experiments.predictive_nucleus import physical_ledger_v1 as physical
from experiments.predictive_nucleus.physical_query_v1 import posterior


def state(memory):
    return (c.digest(memory.snapshot()), memory.posterior, memory.failure_evidence_id, memory.receipt_count)


class CoordinateLedgerTests(unittest.TestCase):
    def setUp(self):
        self.frame = {'version': 'coordinate-transport-v1', 'language_sha256': 'a' * 64,
                      'registry_sha256': 'b' * 64, 'world_sha256': 'c' * 64,
                      'lexical_id': 'd' * 64, 'transforms': [[1, 1], [1, -1], [-1, 1], [-1, -1]],
                      'view': 'intact'}
        self.source, self.prior = 'e' * 64, (.25,) * 4
        self.memory = adapter.CoordinateLedger(self.frame, self.source, self.prior)
        self.directory = TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / 'checkpoint.json'

    def projection(self, evidence_id='event-z', roster=None, a=0, b=1, native=None):
        native = native if native is not None else [[p, 1 - p] + [0.] * 6 for p in (.8, .2, .6, .4)]
        return {'evidence_id': evidence_id, 'prefix_digest': 'f' * 64,
                'entities': roster or ['A', 'B', 'C'],
                'actions': [[0, a, b, -1], [0, b, a, -1], [1, a, -1, 1], [1, b, -1, 1]],
                'endpoint_encoding': adapter.ENDPOINT_ENCODING,
                'action_probabilities': [[float(h == a) for a in range(4)] for h in range(4)],
                'native_likelihood': deepcopy(native), 'likelihood': deepcopy(native),
                'frame': deepcopy(self.frame), 'frame_digest': c.digest(self.frame)}

    def load(self, digest):
        return adapter.CoordinateLedger.load(self.path, digest, self.frame, self.source)

    def write_snapshot(self, snapshot):
        raw = json.dumps(snapshot, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()
        self.path.write_bytes(raw)
        return sha256(raw).hexdigest()

    def test_fresh_rosters_and_local_menus_share_hypotheses_and_replay_in_delivery_order(self):
        first = self.projection()
        second = self.projection('event-a', ['X', 'Y', 'Z'], 2, 0,
                                 [[p, 1 - p] + [0.] * 6 for p in (.3, .9, .4, .7)])
        expected = self.prior
        for projection, endpoint in ((first, 0), (second, 1)):
            self.assertTrue(self.memory.add(projection, endpoint))
            expected = posterior(expected, projection['likelihood'], endpoint)
            self.assertEqual(self.memory.belief, expected)
        snapshot = self.memory.snapshot()
        self.assertEqual(set(snapshot), {'version', 'frame', 'source_sha256', 'initial_prior', 'deliveries'})
        self.assertEqual(snapshot['version'], adapter.VERSION)
        self.assertEqual(snapshot['deliveries'], [{'projection': first, 'endpoint': 0},
                                                  {'projection': second, 'endpoint': 1}])
        digest = self.memory.save(self.path)
        raw = self.path.read_bytes()
        recovered = self.load(digest)
        self.assertEqual(state(recovered), state(self.memory))
        self.assertEqual(recovered.snapshot(), snapshot)
        self.assertEqual(recovered.save(self.path), digest)
        self.assertEqual(self.path.read_bytes(), raw)

    def test_duplicate_payload_is_idempotent_but_distinct_event_ids_are_not_deduplicated(self):
        projection = self.projection()
        self.memory.add(projection, 0)
        before = state(self.memory)
        duplicate = deepcopy(projection)
        for name in ('action_probabilities', 'native_likelihood', 'likelihood'):
            duplicate[name] = tuple(map(tuple, duplicate[name]))
        self.assertFalse(self.memory.add(duplicate, 0))
        self.assertEqual(state(self.memory), before)
        self.assertTrue(self.memory.add({**projection, 'evidence_id': 'another-observation'}, 0))
        self.assertEqual(self.memory.belief, posterior(before[1], projection['likelihood'], 0))
        self.assertEqual(self.memory.receipt_count, 2)

    def test_complete_metadata_and_probability_conflicts_reject_atomically(self):
        original = self.projection()
        self.memory.add(original, 0)
        before = state(self.memory)
        changed_weights = deepcopy(original)
        changed_weights['action_probabilities'] = original['action_probabilities'][1:] + original['action_probabilities'][:1]
        changed_weights['likelihood'] = original['likelihood'][1:] + original['likelihood'][:1]
        unchanged_projection = deepcopy(original)
        unchanged_projection['action_probabilities'] = changed_weights['action_probabilities']
        unchanged_projection['native_likelihood'] = original['native_likelihood'][-1:] + original['native_likelihood'][:-1]
        changed_native = self.projection(native=list(reversed(original['native_likelihood'])))
        changed_menu = self.projection(a=1, b=2)
        variants = [(original, 1), ({**original, 'prefix_digest': '0' * 64}, 0),
                    ({**original, 'entities': ['C', 'B', 'A']}, 0), (changed_menu, 0),
                    (changed_weights, 0), (changed_native, 0), (unchanged_projection, 0)]
        for index, (projection, endpoint) in enumerate(variants):
            with self.subTest(variant=index), self.assertRaises(ValueError):
                self.memory.add(projection, endpoint)
            self.assertEqual(state(self.memory), before)

    def test_every_frame_binding_rejects_cross_frame_delivery_and_recovery(self):
        original = self.projection()
        self.memory.add(original, 0)
        before, digest = state(self.memory), self.memory.save(self.path)
        changes = [(name, '0' * 64) for name in
                   ('language_sha256', 'registry_sha256', 'world_sha256', 'lexical_id')]
        changes += [('version', 'another-version'), ('view', 'zero_layout'),
                    ('transforms', list(reversed(self.frame['transforms'])))]
        for name, value in changes:
            frame = {**self.frame, name: value}
            projection = {**original, 'frame': frame, 'frame_digest': c.digest(frame)}
            with self.subTest(field=name), self.assertRaises(ValueError):
                self.memory.add(projection, 0)
            with self.subTest(recovery=name), self.assertRaises(ValueError):
                adapter.CoordinateLedger.load(self.path, digest, frame, self.source)
            self.assertEqual(state(self.memory), before)
        with self.assertRaises(ValueError):
            adapter.CoordinateLedger.load(self.path, digest, self.frame, '0' * 64)

    def test_constructor_rejects_malformed_frame_signs_hashes_and_prior(self):
        variants = [{**self.frame, 'extra': 1}, {k: v for k, v in self.frame.items() if k != 'view'},
                    {**self.frame, 'view': 0}, {**self.frame, 'view': 'unknown'}]
        for name in ('language_sha256', 'registry_sha256', 'world_sha256', 'lexical_id'):
            variants.append({**self.frame, name: 'A' * 64})
        for coordinate in (True, 1., 0):
            signs = deepcopy(self.frame['transforms'])
            signs[0][0] = coordinate
            variants.append({**self.frame, 'transforms': signs})
        variants.extend({**self.frame, 'transforms': signs} for signs in ([], [[1, 1]],
                        tuple(self.frame['transforms']), [[1, 1]] * 4))
        for index, frame in enumerate(variants):
            with self.subTest(frame=index), self.assertRaises(ValueError):
                adapter.CoordinateLedger(frame, self.source, self.prior)
        for source in (None, '', True, 'A' * 64):
            with self.subTest(source=source), self.assertRaises(ValueError):
                adapter.CoordinateLedger(self.frame, source, self.prior)
        for prior in ([], [.5, .5], [True, 0., 0., 0.], [.2] * 4, [float('nan')] * 4, [10 ** 400] * 4):
            with self.subTest(prior=prior), self.assertRaises(ValueError):
                adapter.CoordinateLedger(self.frame, self.source, prior)

    def test_projection_bounds_and_numeric_types_reject_without_mutation(self):
        original = self.projection()
        self.memory.add(original, 0)
        before = state(self.memory)
        changes = [('evidence_id', ''), ('evidence_id', 'a' * 129), ('prefix_digest', ''),
                   ('entities', ['A', 'A', 'C']), ('entities', ['A', 'B']),
                   ('entities', ['A', 'B', 'x' * 129]), ('frame_digest', '0' * 64),
                   ('endpoint_encoding', 'another-encoding'), ('actions', [[0, 0, 1, -1]] * 4)]
        for name, value in changes:
            with self.subTest(field=name, value=value), self.assertRaises(ValueError):
                self.memory.add({**original, name: value}, 0)
            self.assertEqual(state(self.memory), before)
        for coordinate in (True, 0., 3, -1):
            actions = deepcopy(original['actions'])
            actions[0][1] = coordinate
            with self.subTest(coordinate=coordinate), self.assertRaises(ValueError):
                self.memory.add({**original, 'actions': actions}, 0)
            self.assertEqual(state(self.memory), before)
        for name in ('action_probabilities', 'native_likelihood', 'likelihood'):
            for value in ([], {}, [[.5, .5]], [[0.]] * 4):
                with self.subTest(matrix=name, value=value), self.assertRaises(ValueError):
                    self.memory.add({**original, name: value}, 0)
            for value in (True, float('nan'), float('inf'), 10 ** 400, -.1, 1.1):
                matrix = deepcopy(original[name])
                matrix[0][0] = value
                with self.subTest(matrix=name, number=value), self.assertRaises(ValueError):
                    self.memory.add({**original, name: matrix}, 0)
                self.assertEqual(state(self.memory), before)
        for projection in ({**original, 'observed_endpoint': 0},
                           {k: v for k, v in original.items() if k != 'entities'}):
            with self.assertRaises(ValueError):
                self.memory.add(projection, 0)
        for endpoint in (True, 0., -1, 8):
            with self.subTest(endpoint=endpoint), self.assertRaises(ValueError):
                self.memory.add(original, endpoint)
        self.assertEqual(state(self.memory), before)

    def test_projection_and_uniform_hypothesis_invariants_are_enforced(self):
        mismatch = self.projection()
        mismatch['likelihood'][0] = list(reversed(mismatch['likelihood'][0]))
        nonuniform = self.projection()
        nonuniform['action_probabilities'] = [[1., 0., 0., 0.]] * 4
        nonuniform['likelihood'] = [nonuniform['native_likelihood'][0]] * 4
        before = state(self.memory)
        for projection in (mismatch, nonuniform):
            with self.assertRaises(ValueError):
                self.memory.add(projection, 0)
            self.assertEqual(state(self.memory), before)

    def test_input_and_snapshot_nested_mutation_cannot_change_retained_evidence(self):
        frame, prior = deepcopy(self.frame), list(self.prior)
        memory = adapter.CoordinateLedger(frame, self.source, prior)
        projection = self.projection()
        memory.add(projection, 0)
        before = state(memory)
        frame['transforms'][0][0] = 9
        frame['language_sha256'] = '0' * 64
        prior[0] = 0.
        for target in (projection, memory.snapshot()['deliveries'][0]['projection']):
            target['entities'][0] = 'changed'
            target['actions'][0][1] = 2
            target['frame']['transforms'][0][0] = 7
            for name in ('action_probabilities', 'native_likelihood', 'likelihood'):
                target[name][0][0] = .1
        snapshot = memory.snapshot()
        snapshot['frame']['view'] = 'cycled_layout'
        snapshot['initial_prior'][0] = 1.
        snapshot['deliveries'].clear()
        self.assertEqual(state(memory), before)

    def test_raw_probability_values_survive_normalization_and_checkpoint_replay(self):
        prior = [.2500000000125] * 4
        native = [[1.00000000005] + [0.] * 7 for _ in range(4)]
        projection = self.projection(native=native)
        memory = adapter.CoordinateLedger(self.frame, self.source, prior)
        memory.add(projection, 0)
        self.assertEqual(memory.belief, self.prior)
        self.assertEqual(memory.snapshot()['initial_prior'], prior)
        self.assertEqual(memory.snapshot()['deliveries'][0]['projection'], projection)
        recovered = self.load(memory.save(self.path))
        self.assertEqual(state(recovered), state(memory))

    def test_zero_support_retains_failed_and_later_evidence_across_recovery(self):
        impossible = self.projection('first-failure', native=[[1.] + [0.] * 7 for _ in range(4)])
        self.assertTrue(self.memory.add(impossible, 1))
        self.assertTrue(self.memory.add(self.projection('later'), 0))
        self.assertTrue(self.memory.add({**impossible, 'evidence_id': 'second-failure'}, 1))
        for memory in (self.memory, self.load(self.memory.save(self.path))):
            self.assertEqual(memory.receipt_count, 3)
            self.assertEqual(memory.failure_evidence_id, 'first-failure')
            self.assertIsNone(memory.posterior)
            with self.assertRaises(ValueError):
                _ = memory.belief
            before = state(memory)
            self.assertFalse(memory.add(impossible, 1))
            with self.assertRaises(ValueError):
                memory.add(impossible, 0)
            self.assertEqual(state(memory), before)

    def test_capacity_keeps_duplicates_idempotent_and_rejects_new_deliveries(self):
        projection = self.projection(native=[[.5, .5] + [0.] * 6 for _ in range(4)])
        for index in range(physical.MAX_RECEIPTS):
            self.assertTrue(self.memory.add({**projection, 'evidence_id': str(index)}, 0))
        before = state(self.memory)
        self.assertFalse(self.memory.add({**projection, 'evidence_id': '0'}, 0))
        with self.assertRaises(ValueError):
            self.memory.add({**projection, 'evidence_id': 'over-capacity'}, 0)
        self.assertEqual(state(self.memory), before)
        self.assertEqual(state(self.load(self.memory.save(self.path))), before)

    def test_recovery_revalidates_version_bounds_full_payload_and_duplicate_ids(self):
        self.memory.add(self.projection(), 0)
        snapshot = self.memory.snapshot()
        variants = [{**snapshot, 'version': 'future-ledger'}, {**snapshot, 'posterior': list(self.prior)},
                    {k: v for k, v in snapshot.items() if k != 'deliveries'},
                    {**snapshot, 'deliveries': {}}, {**snapshot, 'deliveries': snapshot['deliveries'] * 2},
                    {**snapshot, 'deliveries': snapshot['deliveries'] * (physical.MAX_RECEIPTS + 1)},
                    {**snapshot, 'initial_prior': [.2] * 4}, {**snapshot, 'source_sha256': '0' * 64},
                    {**snapshot, 'frame': {**self.frame, 'lexical_id': '0' * 64}},
                    {**snapshot, 'deliveries': [{'projection': self.projection(), 'endpoint': True}]},
                    {**snapshot, 'deliveries': [{**snapshot['deliveries'][0], 'posterior': list(self.prior)}]}]
        for index, variant in enumerate(variants):
            with self.subTest(variant=index), self.assertRaises(ValueError):
                self.load(self.write_snapshot(variant))

    def test_corrupt_duplicate_key_nonfinite_hash_and_size_checks(self):
        digest = self.memory.save(self.path)
        raw = self.path.read_bytes()
        for expected in ('0' * 64, None, True, ''):
            with self.subTest(expected=expected), self.assertRaises(ValueError):
                self.load(expected)
        malformed = [raw[:-2], b'{"version":"shadow",' + raw[1:]]
        for number in (float('nan'), float('inf'), -float('inf')):
            malformed.append(json.dumps({**self.memory.snapshot(), 'initial_prior': [number] * 4}).encode())
        for index, content in enumerate(malformed):
            self.path.write_bytes(content)
            with self.subTest(content=index), self.assertRaises(ValueError):
                self.load(sha256(content).hexdigest())
        self.path.write_bytes(raw)
        with patch.object(c, 'MAX_BYTES', len(raw) - 1), self.assertRaises(ValueError):
            self.load(digest)

    def test_inherited_checkpoint_writer_preserves_previous_file_on_fault(self):
        self.memory.add(self.projection(), 0)
        old_state = state(self.memory)
        digest = self.memory.save(self.path)
        raw = self.path.read_bytes()
        self.memory.add(self.projection('next'), 1)
        current = state(self.memory)
        # Base writer tests cover each I/O stage; this checks the adapted snapshot's integration.
        with patch.object(physical.os, 'replace', side_effect=OSError('checkpoint fault')), self.assertRaises(OSError):
            self.memory.save(self.path)
        self.assertEqual(self.path.read_bytes(), raw)
        self.assertEqual(set(self.path.parent.iterdir()), {self.path})
        self.assertEqual(state(self.load(digest)), old_state)
        self.assertEqual(state(self.memory), current)

    def test_fresh_interpreter_recovers_full_projection_and_failed_belief(self):
        self.memory.add(self.projection(), 0)
        failed = adapter.CoordinateLedger(self.frame, self.source, self.prior)
        failed.add(self.projection(native=[[1.] + [0.] * 7 for _ in range(4)]), 1)
        requests = []
        for index, memory in enumerate((self.memory, failed)):
            path = self.path.with_name(f'cold-{index}.json')
            requests.append({'path': str(path), 'sha': memory.save(path), 'frame': self.frame, 'source': self.source})
        script = '''
import json, os, sys
from experiments.predictive_nucleus.coordinate_ledger_v1 import CoordinateLedger
rows = []
for r in json.load(sys.stdin):
    m = CoordinateLedger.load(r['path'], r['sha'], r['frame'], r['source'])
    d = m.snapshot()['deliveries'][0]
    rows.append({'snapshot': m.snapshot(), 'posterior': m.posterior, 'failure': m.failure_evidence_id,
                 'count': m.receipt_count, 'duplicate': m.add(d['projection'], d['endpoint'])})
print(json.dumps({'pid': os.getpid(), 'rows': rows}, allow_nan=False))
'''
        result = subprocess.run([sys.executable, '-c', script], input=json.dumps(requests), text=True,
                                capture_output=True, cwd=Path(__file__).resolve().parents[3], timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr)
        recovered = json.loads(result.stdout)
        self.assertNotEqual(recovered['pid'], os.getpid())
        for memory, row in zip((self.memory, failed), recovered['rows'], strict=True):
            self.assertEqual(c.digest(row['snapshot']), c.digest(memory.snapshot()))
            self.assertEqual(row['posterior'], list(memory.posterior) if memory.posterior else None)
            self.assertEqual(row['failure'], memory.failure_evidence_id)
            self.assertEqual(row['count'], memory.receipt_count)
            self.assertFalse(row['duplicate'])
