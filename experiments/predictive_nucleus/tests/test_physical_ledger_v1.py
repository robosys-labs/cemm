"""Synthetic evidence custody and cold-process recovery regressions."""
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
from experiments.predictive_nucleus import physical_ledger_v1 as ledger
from experiments.predictive_nucleus.physical_query_v1 import choose, posterior


def state(memory):
    return (c.digest(memory.snapshot()), memory.posterior,
            memory.failure_evidence_id, memory.receipt_count)


class PhysicalLedger(unittest.TestCase):
    def setUp(self):
        self.binding = {'interpretation_sha256': 'a' * 64, 'world_sha256': 'b' * 64,
                        'source_sha256': 'c' * 64, 'actions': [[0, 1], [1, 0]],
                        'endpoint_encoding': 'synthetic-endpoints-v1', 'endpoint_count': 2}
        self.memory = ledger.Ledger(self.binding, (.5, .5))
        self.directory = TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / 'ledger.json'

    def receipt(self, evidence_id='event-z', likelihood=None, endpoint=0):
        return {'evidence_id': evidence_id, 'prefix_digest': 'd' * 64,
                'binding_digest': c.digest(self.binding), 'kind': 'physical_endpoint',
                'likelihood': deepcopy(likelihood) if likelihood is not None else [[.8, .2], [.2, .8]],
                'endpoint': endpoint}

    def write_snapshot(self, snapshot):
        raw = json.dumps(snapshot, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()
        self.path.write_bytes(raw)
        return sha256(raw).hexdigest()

    def test_duplicate_identity_and_distinct_equal_valued_events(self):
        receipt = self.receipt()
        self.assertTrue(self.memory.add(receipt))
        expected = posterior((.5, .5), receipt['likelihood'], 0)
        self.assertEqual(self.memory.belief, expected)
        before = state(self.memory)
        duplicate = deepcopy(receipt)
        duplicate['likelihood'] = tuple(map(tuple, duplicate['likelihood']))
        self.assertFalse(self.memory.add(duplicate))
        self.assertEqual(state(self.memory), before)
        distinct = {**receipt, 'evidence_id': 'event-a'}
        self.assertTrue(self.memory.add(distinct))
        self.assertEqual(self.memory.belief, posterior(expected, receipt['likelihood'], 0))
        self.assertEqual(self.memory.receipt_count, 2)
        self.assertIsNone(self.memory.failure_evidence_id)

    def test_conflicting_id_reuse_rejects_atomically(self):
        receipt = self.receipt()
        self.memory.add(receipt)
        before = state(self.memory)
        changes = {'prefix_digest': 'e' * 64, 'endpoint': 1,
                   'likelihood': [[.2, .8], [.2, .8]]}
        for field, value in changes.items():
            with self.subTest(field=field), self.assertRaises(ValueError):
                self.memory.add({**receipt, field: value})
            self.assertEqual(state(self.memory), before)

    def test_binding_receipt_and_snapshot_inputs_are_detached(self):
        binding, prior = deepcopy(self.binding), [.5, .5]
        memory = ledger.Ledger(binding, prior)
        receipt = self.receipt()
        memory.add(receipt)
        before = state(memory)
        binding['actions'][0][0] = 99
        binding['world_sha256'] = 'f' * 64
        prior[0] = 1.
        receipt['likelihood'][0][0] = .1
        snapshot = memory.snapshot()
        snapshot['binding']['actions'][0][0] = 77
        snapshot['initial_prior'][0] = 0.
        snapshot['receipts'][0]['likelihood'][0][0] = .3
        snapshot['receipts'].append({})
        self.assertEqual(state(memory), before)

    def test_raw_probabilities_survive_normalized_updates(self):
        prior = [.500000000025, .500000000025]
        likelihood = [prior[:], prior[:]]
        memory = ledger.Ledger(self.binding, prior)
        self.assertEqual(memory.belief, (.5, .5))
        memory.add(self.receipt(likelihood=likelihood))
        snapshot = memory.snapshot()
        self.assertEqual(snapshot['initial_prior'], prior)
        self.assertEqual(snapshot['receipts'][0]['likelihood'], likelihood)
        self.assertEqual(memory.belief, (.5, .5))
        digest = memory.save(self.path)
        restored = ledger.Ledger.load(self.path, digest, self.binding)
        self.assertEqual(state(restored), state(memory))

    def test_delivery_order_and_deterministic_checkpoint_replay(self):
        receipts = [self.receipt('event-z'),
                    self.receipt('event-a', [[.6, .4], [.1, .9]], 1)]
        expected = (.5, .5)
        for receipt in receipts:
            self.memory.add(receipt)
            expected = posterior(expected, receipt['likelihood'], receipt['endpoint'])
        self.assertEqual(self.memory.belief, expected)
        snapshot = self.memory.snapshot()
        self.assertEqual(set(snapshot), {'version', 'binding', 'initial_prior', 'receipts'})
        self.assertEqual(snapshot['version'], ledger.VERSION)
        self.assertEqual([row['evidence_id'] for row in snapshot['receipts']], ['event-z', 'event-a'])
        digest = self.memory.save(self.path)
        raw = self.path.read_bytes()
        self.assertEqual(digest, sha256(raw).hexdigest())
        restored = ledger.Ledger.load(self.path, digest, self.binding)
        self.assertEqual(state(restored), state(self.memory))
        self.assertFalse(restored.add(receipts[0]))
        self.assertEqual(restored.save(self.path), digest)
        self.assertEqual(self.path.read_bytes(), raw)

    def test_zero_mass_and_later_receipts_are_retained(self):
        failed = self.receipt('failed', [[1., 0.], [1., 0.]], 1)
        self.assertTrue(self.memory.add(failed))
        self.assertIsNone(self.memory.posterior)
        self.assertEqual(self.memory.failure_evidence_id, 'failed')
        with self.assertRaises(ValueError):
            choose(self.memory.belief, [[.8, .2], [.2, .8]], [[1., 0.], [0., 1.]], .05)
        self.assertTrue(self.memory.add(self.receipt('later')))
        self.assertTrue(self.memory.add({**failed, 'evidence_id': 'another-failure'}))
        self.assertEqual(self.memory.receipt_count, 3)
        self.assertIsNone(self.memory.posterior)
        self.assertEqual(self.memory.failure_evidence_id, 'failed')
        before = state(self.memory)
        self.assertFalse(self.memory.add(failed))
        for field, value in (('likelihood', [[.4, .4], [.5, .5]]), ('endpoint', True),
                             ('binding_digest', 'e' * 64)):
            with self.subTest(field=field), self.assertRaises(ValueError):
                self.memory.add({**self.receipt('invalid-later'), field: value})
            self.assertEqual(state(self.memory), before)

    def test_positive_subnormal_likelihood_retains_failed_update(self):
        receipt = self.receipt('underflow', [[5e-324, 1.], [5e-324, 1.]])
        self.assertTrue(self.memory.add(receipt))
        self.assertIsNone(self.memory.posterior)
        self.assertEqual(self.memory.failure_evidence_id, 'underflow')
        self.assertEqual(self.memory.snapshot()['receipts'], [receipt])
        with self.assertRaises(ValueError):
            _ = self.memory.belief

    def test_capacity_rejection_preserves_idempotence(self):
        for index in range(ledger.MAX_RECEIPTS):
            receipt = self.receipt(f'event-{index}', [[.5, .5], [.5, .5]])
            self.assertTrue(self.memory.add(receipt))
        before = state(self.memory)
        self.assertFalse(self.memory.add(receipt))
        with self.assertRaises(ValueError):
            self.memory.add(self.receipt('overflow'))
        self.assertEqual(state(self.memory), before)
        self.assertEqual(self.memory.receipt_count, 256)

    def test_binding_bounds_and_initial_prior_validation(self):
        changes = [('interpretation_sha256', ''), ('world_sha256', 'A' * 64),
                   ('source_sha256', None), ('actions', []), ('actions', [[0], [0]]),
                   ('actions', [[0]]), ('actions', [[True], [1]]), ('actions', [[.0], [1]]),
                   ('actions', [[0] * 17, [1]]), ('actions', [[-(2 ** 31) - 1], [1]]),
                   ('actions', [[2 ** 31], [1]]), ('actions', [[i] for i in range(33)]),
                   ('endpoint_count', 0), ('endpoint_count', True), ('endpoint_count', 65),
                   ('endpoint_encoding', ''), ('endpoint_encoding', 'e' * 129)]
        for field, value in changes:
            with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                ledger.Ledger({**self.binding, field: value}, (.5, .5))
        for prior in ([], [.4, .4], [-.1, 1.1], [10 ** 400, 0], [float('nan'), .5], [float('inf'), 0.],
                      [True, 0.], [.5], {'a': .5, 'b': .5}):
            with self.subTest(prior=prior), self.assertRaises(ValueError):
                ledger.Ledger(self.binding, prior)
        with self.assertRaises(ValueError):
            ledger.Ledger({**self.binding, 'extra': 1}, (.5, .5))
        missing = deepcopy(self.binding)
        del missing['source_sha256']
        with self.assertRaises(ValueError):
            ledger.Ledger(missing, (.5, .5))

    def test_maximum_hypothesis_endpoint_and_coordinate_bounds_are_accepted(self):
        self.assertEqual((ledger.MAX_HYPOTHESES, ledger.MAX_ENDPOINTS), (32, 64))
        binding = {**self.binding, 'endpoint_count': ledger.MAX_ENDPOINTS,
                   'actions': [[i, -(2 ** 31), 2 ** 31 - 1] + [0] * 13
                               for i in range(ledger.MAX_HYPOTHESES)]}
        memory = ledger.Ledger(binding, [1 / 32] * 32)
        receipt = {**self.receipt(), 'binding_digest': c.digest(binding),
                   'likelihood': [[1.] + [0.] * 63 for _ in range(32)]}
        self.assertTrue(memory.add(receipt))
        self.assertEqual(memory.belief, (1 / 32,) * 32)

    def test_malformed_receipts_reject_without_mutation(self):
        class EqualText:
            def __eq__(self, other):
                return True

        self.memory.add(self.receipt())
        before = state(self.memory)
        changes = [('evidence_id', ''), ('evidence_id', 'e' * 129), ('prefix_digest', 'invalid'),
                   ('binding_digest', 'f' * 64), ('binding_digest', EqualText()),
                   ('kind', 'text_claim'), ('kind', EqualText()), ('endpoint', -1),
                   ('endpoint', 2), ('endpoint', True), ('likelihood', []),
                   ('likelihood', [[1.], [.5, .5]]), ('likelihood', [[.5, .5]]),
                   ('likelihood', [[-.1, 1.1], [.5, .5]]),
                   ('likelihood', [[.5, .4], [.5, .5]]),
                   ('likelihood', [[10 ** 400, 0], [.5, .5]]),
                   ('likelihood', [[float('nan'), .5], [.5, .5]]),
                   ('likelihood', [[float('inf'), 0.], [.5, .5]]),
                   ('likelihood', [[True, 0.], [.5, .5]])]
        for field, value in changes:
            with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                self.memory.add({**self.receipt('new'), field: value})
            self.assertEqual(state(self.memory), before)
        for receipt in ({**self.receipt('new'), 'extra': 1},
                        {key: value for key, value in self.receipt('new').items() if key != 'kind'}):
            with self.assertRaises(ValueError):
                self.memory.add(receipt)
            self.assertEqual(state(self.memory), before)

    def test_recovery_rejects_changed_interpretation_model_source_and_coordinates(self):
        self.memory.add(self.receipt())
        digest = self.memory.save(self.path)
        changes = [('interpretation_sha256', 'e' * 64), ('world_sha256', 'e' * 64),
                   ('source_sha256', 'e' * 64), ('actions', list(reversed(self.binding['actions']))),
                   ('endpoint_encoding', 'another-encoding'), ('endpoint_count', 3)]
        for field, value in changes:
            with self.subTest(field=field), self.assertRaises(ValueError):
                ledger.Ledger.load(self.path, digest, {**self.binding, field: value})
        for expected in (None, '', True, '0' * 64):
            with self.subTest(hash=expected), self.assertRaises(ValueError):
                ledger.Ledger.load(self.path, expected, self.binding)

    def test_recovery_rejects_malformed_snapshots_and_repeated_ids(self):
        self.memory.add(self.receipt())
        snapshot = self.memory.snapshot()
        variants = [{**snapshot, 'version': 'future-ledger'}, {**snapshot, 'posterior': [.5, .5]},
                    {key: value for key, value in snapshot.items() if key != 'receipts'},
                    {**snapshot, 'receipts': {}}, {**snapshot, 'receipts': snapshot['receipts'] * 2},
                    {**snapshot, 'receipts': snapshot['receipts'] * 257},
                    {**snapshot, 'initial_prior': [.4, .4]},
                    {**snapshot, 'receipts': [{**snapshot['receipts'][0], 'endpoint': True}]}]
        for index, variant in enumerate(variants):
            digest = self.write_snapshot(variant)
            with self.subTest(variant=index), self.assertRaises(ValueError):
                ledger.Ledger.load(self.path, digest, self.binding)

    def test_recovery_rejects_duplicate_json_keys_nonfinite_values_and_truncation(self):
        raw = json.dumps(self.memory.snapshot(), separators=(',', ':')).encode()
        malformed = [raw[:-1], b'{"version":"shadow",' + raw[1:]]
        for value in (float('nan'), float('inf'), -float('inf')):
            malformed.append(json.dumps({**self.memory.snapshot(), 'initial_prior': [value, .5]}).encode())
        for index, content in enumerate(malformed):
            self.path.write_bytes(content)
            with self.subTest(variant=index), self.assertRaises(ValueError):
                ledger.Ledger.load(self.path, sha256(content).hexdigest(), self.binding)

    def test_checkpoint_failures_preserve_previous_file_and_remove_temporary(self):
        self.memory.add(self.receipt())
        previous_state = state(self.memory)
        digest = self.memory.save(self.path)
        raw = self.path.read_bytes()
        self.memory.add(self.receipt('new-event'))
        current_state = state(self.memory)
        factory = ledger.tempfile.NamedTemporaryFile
        for operation in ('write', 'flush', 'fsync', 'replace'):
            def broken_file(*args, **kwargs):
                stream = factory(*args, **kwargs)

                def fail(*values):
                    if operation == 'write':
                        stream.file.write(values[0][:8])
                    raise OSError('injected checkpoint failure')

                setattr(stream, operation, fail)
                return stream

            fault = (patch.object(ledger.tempfile, 'NamedTemporaryFile', side_effect=broken_file)
                     if operation in ('write', 'flush') else
                     patch.object(ledger.os, operation, side_effect=OSError('injected checkpoint failure')))
            with self.subTest(operation=operation), fault, self.assertRaises(OSError):
                self.memory.save(self.path)
            self.assertEqual(self.path.read_bytes(), raw)
            self.assertEqual(set(self.path.parent.iterdir()), {self.path})
            self.assertEqual(state(self.memory), current_state)
            self.assertEqual(state(ledger.Ledger.load(self.path, digest, self.binding)), previous_state)

    def test_fresh_process_recovers_supported_and_failed_beliefs(self):
        self.memory.add(self.receipt())
        failed = ledger.Ledger(self.binding, (.5, .5))
        failed.add(self.receipt('failed', [[1., 0.], [1., 0.]], 1))
        failed.add(self.receipt('later'))
        requests = []
        for index, memory in enumerate((self.memory, failed)):
            path = self.path.with_name(f'cold-{index}.json')
            requests.append({'path': str(path), 'sha256': memory.save(path), 'binding': self.binding})
        script = '''
import json, os, sys
from experiments.predictive_nucleus.physical_ledger_v1 import Ledger
from experiments.predictive_nucleus.physical_query_v1 import choose
results = []
for request in json.load(sys.stdin):
    memory = Ledger.load(request['path'], request['sha256'], request['binding'])
    try:
        decision = choose(memory.belief, ((.8, .2), (.2, .8)), ((1., 0.), (0., 1.)), .05)
        blocked = False
    except ValueError:
        decision, blocked = None, True
    duplicate = memory.add(memory.snapshot()['receipts'][0])
    results.append({'snapshot': memory.snapshot(), 'posterior': memory.posterior,
                    'failure': memory.failure_evidence_id, 'count': memory.receipt_count,
                    'decision': decision, 'blocked': blocked, 'duplicate': duplicate})
print(json.dumps({'pid': os.getpid(), 'results': results}, allow_nan=False))
'''
        result = subprocess.run([sys.executable, '-c', script], input=json.dumps(requests), text=True,
                                capture_output=True, cwd=Path(__file__).resolve().parents[3], timeout=20)
        self.assertEqual(result.returncode, 0, result.stderr)
        recovered = json.loads(result.stdout)
        self.assertNotEqual(recovered['pid'], os.getpid())
        for memory, row in zip((self.memory, failed), recovered['results'], strict=True):
            self.assertEqual(c.digest(row['snapshot']), c.digest(memory.snapshot()))
            self.assertEqual(row['posterior'], list(memory.posterior) if memory.posterior else None)
            self.assertEqual(row['failure'], memory.failure_evidence_id)
            self.assertEqual(row['count'], memory.receipt_count)
            self.assertFalse(row['duplicate'])
        self.assertFalse(recovered['results'][0]['blocked'])
        self.assertEqual(recovered['results'][0]['decision'],
                         choose(self.memory.belief, ((.8, .2), (.2, .8)), ((1., 0.), (0., 1.)), .05))
        self.assertTrue(recovered['results'][1]['blocked'])
        self.assertIsNone(recovered['results'][1]['decision'])
