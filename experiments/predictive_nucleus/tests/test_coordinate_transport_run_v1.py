"""Synthetic common-history and terminal-query dataflow checks."""
from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from experiments.predictive_nucleus import acceptance_contract as c
from experiments.predictive_nucleus import coordinate_transport_run_v1 as runner
from experiments.predictive_nucleus.coordinate_transport_run_v1 import prefix, trace


def receipt(number, endpoints):
    likelihood = [[float(column == endpoint) for column in range(8)] for endpoint in endpoints]
    frame = {'version': 'synthetic-coordinate-frame', 'lexical_id': 'a' * 64}
    return {'evidence_id': f'instance-{number}/utterance/0', 'prefix_digest': str(number) * 64,
            'entities': [f'{number}-{slot}' for slot in range(3)],
            'actions': [[0, 0, 1, -1], [0, 1, 0, -1], [1, 0, -1, 1], [1, 1, -1, 1]],
            'endpoint_encoding': 'ordered-roster-msb-first-binary-v1',
            'action_probabilities': [[float(h == action) for action in range(4)] for h in range(4)],
            'native_likelihood': likelihood, 'likelihood': likelihood,
            'frame': frame, 'frame_digest': c.digest(frame)}


class CoordinateTransportRun(unittest.TestCase):
    def setUp(self):
        self.rows = [receipt(1, (0, 0, 1, 1)), receipt(2, (0, 1, 0, 1)), receipt(3, (2, 3, 4, 5))]

    def test_common_evidence_and_target_prediction_use_stable_hypotheses(self):
        original = deepcopy(self.rows)
        result = trace(self.rows, (0, 1))
        self.assertNotIn('failure', result)
        self.assertEqual(self.rows, original)
        beliefs = result['beliefs']
        self.assertEqual(beliefs['reset'], (.25,) * 4)
        self.assertEqual(beliefs['first'], (.5, .5, 0., 0.))
        self.assertEqual(beliefs['latest'], (0., .5, 0., .5))
        self.assertEqual(beliefs['retained'], (0., 1., 0., 0.))
        self.assertEqual(result['predictions']['retained']['endpoint_action'], 3)
        self.assertEqual(result['predictions']['retained']['physical_action'], 1)
        self.assertNotIn('observed_endpoint', result['receipts'][2])

    def test_terminal_query_uses_demonstration_to_predict_different_target(self):
        result = trace(self.rows, (0, 1))
        policies = {(row['prior'], row['fee_index']): row for row in result['policies']}
        self.assertEqual(len(policies), 6)
        bought = policies['retained', 0]
        self.assertTrue(bought['ask'])
        self.assertEqual(bought['value'], .5)
        self.assertEqual(bought['action'], 2)
        self.assertEqual(bought['target_selected_endpoint'], 3)
        self.assertEqual(bought['consumed_ids'], [row['evidence_id'] for row in self.rows[:2]])
        self.assertEqual(policies['reset', 0]['value'], .25)
        self.assertEqual(policies['reset', 0]['consumed_ids'], [self.rows[1]['evidence_id']])
        for prior in ('retained', 'reset'):
            for fee_index in (1, 2):
                held = policies[prior, fee_index]
                self.assertFalse(held['ask'])
                self.assertEqual(held['target_selected_endpoint'], 2)
                self.assertEqual(held['posterior'], result['beliefs']['first' if prior == 'retained' else 'reset'])

    def test_current_demonstration_endpoint_cannot_change_prequery_decision(self):
        left, right = trace(self.rows, (0, 0)), trace(self.rows, (0, 1))
        for a, b in zip(left['policies'], right['policies'], strict=True):
            for key in ('prior', 'fee_index', 'fee', 'action', 'ask', 'expected_before', 'expected_after', 'value'):
                self.assertEqual(a[key], b[key])
            if not a['ask']:
                self.assertEqual(a, b)

    def test_invalid_frame_and_duplicate_ids_reject_before_update(self):
        for key, value in (('frame_digest', 'f' * 64), ('evidence_id', self.rows[0]['evidence_id'])):
            rows = deepcopy(self.rows)
            rows[1][key] = value
            with self.subTest(field=key), self.assertRaises(ValueError):
                trace(rows, (0, 1))
        rows = deepcopy(self.rows)
        rows[1]['frame']['lexical_id'] = 'f' * 64
        with self.assertRaises(ValueError):
            trace(rows, (0, 1))

    def test_failed_update_keeps_receipts_and_failed_identity_visible(self):
        rows = deepcopy(self.rows)
        rows[1]['likelihood'] = [[1.] + [0.] * 7 for _ in range(4)]
        result = trace(rows, (0, 1))
        self.assertEqual(result['failure']['evidence_id'], rows[1]['evidence_id'])
        self.assertEqual(len(result['receipts']), 3)
        self.assertEqual(result['receipts'][1]['observed_endpoint'], 1)
        self.assertIsNone(result['predictions']['retained'])
        self.assertIsNotNone(result['predictions']['first'])

    def test_unsupported_unbought_endpoint_preserves_hold_decisions(self):
        supported, unsupported = trace(self.rows, (0, 1)), trace(self.rows, (0, 7))
        self.assertEqual(len(unsupported['policies']), 6)
        for before, after in zip(supported['policies'], unsupported['policies'], strict=True):
            for key in ('action', 'ask', 'value', 'expected_before', 'expected_after'):
                self.assertEqual(before[key], after[key])
            if before['ask']:
                self.assertIsNone(after['posterior'])
                self.assertIsNone(after['target_selected_endpoint'])
                self.assertEqual(after['failure']['evidence_id'], self.rows[1]['evidence_id'])
            else:
                self.assertEqual(before, after)

    def test_unpublished_source_is_rejected_even_when_tracked_tree_is_clean(self):
        with patch.object(runner.io, '_git', return_value=''), \
             patch.object(runner.io, '_hash', return_value=runner.PROTOCOL_SHA256), \
             patch.object(runner, 'published', side_effect=ValueError('unpublished')) as published:
            with self.assertRaises(ValueError):
                runner.source_receipt()
        published.assert_called_once_with(runner.io.ROOT / runner.SOURCES[0])

    def test_native_prefix_interface_excludes_endpoint_and_hidden_fields(self):
        record = {'id': 'instance', 'entities': ['a', 'b', 'c'], 'anchor': [0, 0, 0],
                  'context': [], 'utterances': [{'text': 'a word b', 'reading': [1, 0, 0]}],
                  'meaning': 3, 'target_action': [1, 0, -1, 1]}
        actual = prefix(record)
        record['utterances'][0]['reading'] = [0, 1, 1]
        record['meaning'] = 0
        self.assertEqual(prefix(record), actual)
        self.assertEqual(set(actual), {'id', 'entities', 'anchor', 'context', 'text'})
        self.assertEqual(actual['id'], 'instance/utterance/0')
        self.assertEqual(prefix({**record, 'text': 'a word b'}), actual)

    def test_native_repetition_requires_distinct_invocations_and_equal_numerical_bytes(self):
        sources = {'protocol_commit': 'a' * 40, 'protocol_sha256': 'b' * 64,
                   'source_commit': 'c' * 40, 'source_sha256': {'runner.py': 'd' * 64}}
        with TemporaryDirectory() as temporary, patch.object(runner, 'source_receipt', return_value=sources):
            directories = [Path(temporary) / name for name in ('first', 'second', 'changed', 'copied')]
            for index, directory in enumerate(directories):
                directory.mkdir()
                artifact = runner.io._write(directory / 'raw.json.xz', {'forecast': index == 2})
                runner.io._write(directory / 'manifest.json', {**sources, 'complete': True,
                    'failed_checks': [], 'shards': [{'file': 'raw.json.xz', **artifact}]})
                runner.io._write(directory / 'execution.json', {**sources, 'pid': 2,
                    'invocation_id': 'run-' + str(index if index < 3 else 0)})
            first, second, changed, copied = directories
            result = runner.replicate(first, second, Path(temporary) / 'equal.json')
            self.assertTrue(result['byte_identical'])
            self.assertEqual(len(result['runs']), 2)
            self.assertFalse(runner.replicate(first, changed, Path(temporary) / 'different.json')['byte_identical'])
            for other in (first, copied):
                with self.assertRaises(ValueError):
                    runner.replicate(first, other, Path(temporary) / 'invalid.json')

    def test_scoring_preserves_incomplete_collection_failures_after_publication(self):
        sources = {'protocol_sha256': 'b' * 64, 'source_sha256': {'runner.py': 'd' * 64}}
        manifest = {**sources, 'complete': False, 'failed_checks': [{'message': 'native failure'}],
                    'inputs_sha256': 'e' * 64, 'shards': []}
        replication = {'version': 'coordinate-transport-replication-v1', 'byte_identical': False,
                       'runs': [{'manifest': manifest, 'manifest_sha256': 'f' * 64,
                                 'execution': {'invocation_id': 'run-1'}},
                                {'manifest': manifest, 'execution': {'invocation_id': 'run-2'}}]}
        freeze = {'artifacts': {'inputs.json.xz': {'sha256': 'e' * 64},
                                'evaluator.json.xz': {'sha256': 'f' * 64}}}
        assets = {'manifest.json': manifest, 'replication.json': replication, 'freeze.json': freeze,
                  'evaluator.json.xz': {'version': 'synthetic'}}
        with patch.object(runner, 'source_receipt', return_value=sources), \
             patch.object(runner, 'published') as published, \
             patch.object(runner.io, '_read', side_effect=lambda path: assets[path.name]), \
             patch.object(runner.io, '_hash', return_value='f' * 64), \
             patch.object(runner.io, '_git', return_value='a' * 40), \
             patch.object(runner.io, '_write'), \
             patch('experiments.predictive_nucleus.coordinate_transport_scoring_v1.score',
                   return_value={'decision': 'REVISE_TRANSPORT_PREFLIGHT'}) as evaluate:
            result = runner.score(Path('data'), Path('raw'), Path('score.json'))
        self.assertEqual(result['decision'], 'REVISE_TRANSPORT_PREFLIGHT')
        self.assertEqual([row['message'] for row in evaluate.call_args.kwargs['collection_failures']],
                         ['native failure', 'incomplete native collection', 'native repetitions differ'])
        self.assertLess(published.call_args_list.index(unittest.mock.call(Path('raw/replication.json'))),
                        published.call_args_list.index(unittest.mock.call(Path('data/evaluator.json.xz'))))
