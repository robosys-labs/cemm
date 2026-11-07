"""Synthetic recovery, published-reference and public-custody regressions."""
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from experiments.predictive_nucleus import acceptance_contract as c
from experiments.predictive_nucleus import coordinate_persistence_run_v1 as run


def fixture():
    frame = {'version': 'coordinate-transport-v1', 'language_sha256': 'a' * 64,
             'registry_sha256': 'b' * 64, 'world_sha256': 'c' * 64,
             'lexical_id': sha256(b'novel').hexdigest(),
             'transforms': [list(pair) for pair in run.TRANSFORMS], 'view': 'intact'}
    projections, public = [], []
    for number, destinations in enumerate(((0, 0, 1, 1), (0, 1, 0, 1), (2, 3, 4, 5))):
        roster = [f'{number}-a', f'{number}-b', f'{number}-c']
        record = {'id': f'event-{number}', 'entities': roster, 'anchor': [0, 0, 0], 'context': []}
        text = roster[0] + ' novel ' + roster[1]
        if number < 2:
            record['utterances'] = [{'text': text, 'reading': [0, 0, number]}]
        else:
            record['text'] = text
        public.append(record)
        prefix = run.prefix(record)
        likelihood = [[float(y == destination) for y in range(8)] for destination in destinations]
        projections.append({'evidence_id': prefix.pop('id'), 'prefix_digest': c.digest(prefix),
            'entities': roster, 'actions': [[0, 0, 1, -1], [0, 1, 0, -1], [1, 0, -1, 1], [1, 1, -1, 1]],
            'endpoint_encoding': run.ENDPOINT_ENCODING,
            'action_probabilities': [[float(h == a) for a in range(4)] for h in range(4)],
            'native_likelihood': likelihood, 'likelihood': deepcopy(likelihood),
            'frame': deepcopy(frame), 'frame_digest': c.digest(frame)})
    # Independent exact golden values: first observation selects h0/h1; second selects h1/h3.
    beliefs = {'reset': [.25, .25, .25, .25], 'first': [.5, .5, 0., 0.],
               'latest': [0., .5, 0., .5], 'retained': [0., 1., 0., 0.]}
    predictions = {}
    for name, belief in beliefs.items():
        endpoints = [0., 0., *belief, 0., 0.]
        predictions[name] = {'endpoint_probabilities': endpoints, 'action_probabilities': belief,
                             'endpoint_action': endpoints.index(max(endpoints)),
                             'physical_action': belief.index(max(belief))}
    policies = []
    for name in ('retained', 'reset'):
        for index, fee in enumerate(run.FEES):
            ask = index == 0
            before, after = (.5, 1.) if name == 'retained' else (.25, .5)
            state = ('retained' if ask else 'first') if name == 'retained' else ('latest' if ask else 'reset')
            consumed = [projections[0]['evidence_id']] if name == 'retained' else []
            if ask:
                consumed.append(projections[1]['evidence_id'])
            policies.append({'prior': name, 'fee_index': index, 'fee': fee, 'action': 2, 'ask': ask,
                'expected_before': before, 'expected_after': after, 'value': after - before,
                'posterior': beliefs[state], 'consumed_ids': consumed,
                'endpoint_probabilities': predictions[state]['endpoint_probabilities'],
                'target_selected_endpoint': predictions[state]['endpoint_action']})
    reference = {'beliefs': beliefs, 'predictions': predictions, 'policies': policies,
                 'receipts': deepcopy(projections)}
    for receipt, endpoint in zip(reference['receipts'][:2], (0, 1), strict=True):
        receipt['observed_endpoint'] = endpoint
    context = {'key': 'nand/7/intact/synthetic', 'condition': 'nand/7/intact',
               'frame': frame, 'source_sha256': 'd' * 64, 'projections': projections,
               'endpoints': (0, 1), 'reference': reference}
    model = {**{key: frame[key] for key in ('language_sha256', 'registry_sha256', 'world_sha256')},
             'new_ids': [frame['lexical_id']]}
    return context, public, model


def workspace(path):
    for phase in ('first', 'retained'):
        (path / phase).mkdir()


class CoordinatePersistenceRunner(unittest.TestCase):
    def setUp(self):
        self.context, self.public, self.model = fixture()
        self.expected = {self.context['condition']: 1}

    def test_complete_pipeline_preserves_independent_reference_and_all_branch_histories(self):
        with TemporaryDirectory() as temporary:
            path = Path(temporary)
            workspace(path)
            previous = None
            reports = []
            for stage in run.STAGES:
                previous = run.stage_report(stage, path, [self.context], previous, self.expected)
                self.assertEqual(previous['failed_checks'], [])
                reports.append(previous)
            produce, resume, recover = reports
            self.assertEqual(produce['records'][0]['posterior'], (.5, .5, 0., 0.))
            self.assertEqual(recover['records'][0]['posterior'], (0., 1., 0., 0.))
            self.assertEqual(resume['counts']['policy_checks'], 6)
            self.assertEqual(resume['counts']['hold_branches'], 4)
            self.assertEqual(resume['counts']['retained_purchases'], 1)
            self.assertEqual(resume['counts']['reset_purchases'], 1)
            self.assertEqual(recover['counts']['idempotent_duplicates'], 2)
            for kind in ('prefix', 'endpoint', 'roster'):
                self.assertEqual(recover['counts'][kind + '_conflict_rejections'], 2)
            self.assertEqual(resume['records'][0]['policies_sha256'], c.digest(self.context['reference']['policies']))
            self.assertEqual(len(list(path.glob('*/*.json'))), 2)

    def test_worker_chain_crosses_three_real_interpreter_boundaries(self):
        with TemporaryDirectory() as temporary:
            directory = Path(temporary)
            workspace(directory)
            previous_sha, pids = None, set()
            for stage in run.STAGES:
                code = (
                    'from pathlib import Path\n'
                    'from experiments.predictive_nucleus import coordinate_persistence_run_v1 as r\n'
                    'from experiments.predictive_nucleus.tests.test_coordinate_persistence_run_v1 import fixture\n'
                    'context, _, _ = fixture()\n'
                    'r.source_receipt = lambda: {"source_commit": "synthetic-worker-test"}\n'
                    'r.native_contexts = lambda: iter([context])\n'
                    'r.EXPECTED = {context["condition"]: 1}\n'
                    f'raise SystemExit(r._worker({stage!r}, Path({str(directory)!r}), {previous_sha!r}))\n')
                child = subprocess.run([sys.executable, '-c', code], cwd=run.io.REPO,
                                       capture_output=True, text=True, timeout=30)
                self.assertEqual(child.returncode, 0, child.stdout + child.stderr)
                execution = json.loads(child.stdout)
                self.assertNotIn(execution['pid'], pids)
                pids.add(execution['pid'])
                previous_sha = execution['report_sha256']
                report = c.load_json(directory / (stage + '.json'), previous_sha)
                self.assertEqual(report['failed_checks'], [])
            self.assertEqual(len(pids), 3)

    def test_failed_case_is_retained_and_later_context_still_executes(self):
        bad = deepcopy(self.context)
        bad['key'] += '-wrong-reference'
        bad['reference']['beliefs']['first'] = [.25] * 4
        with TemporaryDirectory() as temporary:
            path = Path(temporary)
            workspace(path)
            report = run.stage_report('produce', path, [bad, self.context], None,
                                      {self.context['condition']: 2})
        self.assertEqual(len(report['records']), 2)
        self.assertIn('failure', report['records'][0])
        self.assertNotIn('failure', report['records'][1])
        self.assertEqual(report['counts']['completed'], 1)
        self.assertEqual(report['failed_checks'][0]['key'], bad['key'])

    def test_wrong_published_policy_cannot_be_replaced_with_self_generated_success(self):
        bad = deepcopy(self.context)
        bad['reference']['policies'][0]['ask'] = False
        with TemporaryDirectory() as temporary:
            path = Path(temporary)
            workspace(path)
            producer = run.stage_report('produce', path, [bad], None, self.expected)
            report = run.stage_report('resume', path, [bad], producer, self.expected)
        self.assertIn('cold policy branch', report['failed_checks'][0]['message'])

    def test_cold_load_rejects_changed_checkpoint_even_with_self_consistent_frame(self):
        with TemporaryDirectory() as temporary:
            path = Path(temporary)
            workspace(path)
            producer = run.stage_report('produce', path, [self.context], None, self.expected)
            checkpoint = path / producer['records'][0]['checkpoint']['file']
            checkpoint.write_bytes(checkpoint.read_bytes() + b' ')
            report = run.stage_report('resume', path, [self.context], producer, self.expected)
        self.assertIn('hash mismatch', report['failed_checks'][0]['message'])

    def test_public_binding_rejects_endpoint_prefix_menu_and_frame_aliases(self):
        archived = self.context['reference']['receipts'][0]
        projected, endpoint = run._public_projection(archived, self.public[0], self.model, 'intact', True)
        self.assertEqual(projected, self.context['projections'][0])
        self.assertEqual(endpoint, 0)
        changes = []
        for field, value in (('observed_endpoint', 1), ('prefix_digest', '0' * 64),
                             ('entities', list(reversed(archived['entities']))),
                             ('actions', [[0, 1, 0, -1], [0, 0, 1, -1], [1, 1, -1, 1], [1, 0, -1, 1]])):
            changed = deepcopy(archived)
            changed[field] = value
            changes.append(changed)
        changed = deepcopy(archived)
        changed['frame']['language_sha256'] = 'e' * 64
        changed['frame_digest'] = c.digest(changed['frame'])
        changes.append(changed)
        for changed in changes:
            with self.subTest(changed=changed), self.assertRaises(ValueError):
                run._public_projection(changed, self.public[0], self.model, 'intact', True)
        target = deepcopy(self.context['projections'][2])
        target['observed_endpoint'] = 3
        with self.assertRaises(ValueError):
            run._public_projection(target, self.public[2], self.model, 'intact', False)

    def test_missing_or_duplicate_condition_cannot_qualify(self):
        with TemporaryDirectory() as temporary:
            path = Path(temporary)
            workspace(path)
            missing = run.stage_report('produce', path, [], None, self.expected)
            duplicate = run.stage_report('produce', path, [self.context, self.context], None,
                                         {self.context['condition']: 2})
        self.assertTrue(missing['failed_checks'])
        self.assertTrue(duplicate['failed_checks'])
        self.assertEqual(duplicate['counts']['completed'], 1)

    def test_unpublished_source_fails_even_when_index_is_clean(self):
        with patch.object(run.io, '_hash', return_value=run.PROTOCOL_SHA256), \
             patch.object(run.io, '_git', return_value=''), \
             patch.object(run.subprocess, 'check_output', return_value=b'not-the-source'):
            with self.assertRaisesRegex(ValueError, 'unpublished source'):
                run.source_receipt()


if __name__ == '__main__':
    unittest.main()
