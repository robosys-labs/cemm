"""Hand-authored decision and native transport invariants; no fitting or study run."""
from contextlib import redirect_stdout
from copy import deepcopy
import io
import math
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from experiments.predictive_nucleus import acceptance_contract as contract, acceptance_runner as runner
from experiments.predictive_nucleus import acceptance_scoring as scoring, alias_evidence_run as run
from experiments.predictive_nucleus.active_checkpoint import save_checkpoint
from experiments.predictive_nucleus.tests.test_acceptance_scoring import row
from experiments.predictive_nucleus.tests.test_continuation_run import synthetic_assets


def assets():
    inputs, oracle, cases = synthetic_assets()
    cases[-1].update(partition='in_family', self_prebit=0)
    case, target, meta = map(deepcopy, (inputs['episodes'][-1], oracle['episodes'][-1], cases[-1]))
    case['episode'] = target['episode'] = meta['episode'] = 'synthetic-self-one'
    meta.update(lineage='synthetic-self-one', self_prebit=1)
    # Deliberate no-change hand fixture, not a simulated self-contact claim.
    for observation in case['observations']: observation['a'] = 1
    for truth in target['truth']: truth['a'] = 1
    target['possible_worlds'] = [[8]]
    target['information_keys'] = [contract.information_key(case, 0)]
    inputs['episodes'].append(case); oracle['episodes'].append(target); cases.append(meta)
    oracle['input_sha256'] = contract.digest(inputs)
    return inputs, oracle, cases


def decision_rows(cases):
    rows = []
    for arm in run.ARMS:
        for seed in run.SEEDS:
            for c in cases:
                for step in range(c['contact_count']):
                    wrong = arm == 'ordinary' and c['query_scope'] == 'self_contact'
                    point = row(4, episode=c['episode'], step=step, participant=arm, seed=seed,
                        probabilities=[0., 1.] + [0.] * 14 if wrong else None,
                        family=c['family'], partition=c['partition'],
                        pair_id=c['pair_id'], direction=c['direction'])
                    point['lineage'] = c['lineage']; rows.append(point)
    return rows


class AliasEvidenceRunTests(unittest.TestCase):
    def setUp(self): self.config = run.protocol()

    def test_only_recognized_impossible_model_feedback_counts_as_executed(self):
        good = {'phase': 'feedback', 'error_type': 'ValueError', 'message': 'visible evidence outside model support',
                'evidence': {'impossible_observation': True}}
        report = {'metadata': {'failure_records': [good], 'incomplete_inventory': []}}
        self.assertTrue(run.execution_complete(report))
        for key, value in [('phase', 'predict'), ('error_type', 'RuntimeError'), ('message', 'unrelated error'),
                           ('evidence', {'impossible_observation': False})]:
            failed = deepcopy(report); failed['metadata']['failure_records'][0][key] = value
            self.assertFalse(run.execution_complete(failed))
        report['metadata']['incomplete_inventory'] = ['missing-trial']
        self.assertFalse(run.execution_complete(report))

    def test_both_bits_and_every_seed_are_gated_with_no_deleted_query_or_ambiguity_bypass(self):
        _, _, cases = assets(); rows = decision_rows(cases)
        analyze = lambda values, complete=True: run.analyze(scoring.score_rows(values), cases, complete, self.config)
        good = analyze(rows)
        self.assertEqual(good['decision']['decision'], 'KEEP_EVIDENCE_FIX')
        self.assertEqual(analyze(rows, False)['decision']['decision'], 'STOP_INCOMPLETE_EXECUTION')
        for bit, status in [(0, 'ANSWERED'), (1, 'ABSTAIN'), (1, 'UNPRODUCED')]:
            bad = deepcopy(rows)
            p = next(r for r in bad if r['participant'] == 'alias' and r['model_seed'] == 53 and
                     r['episode'] == cases[-2 + bit]['episode'])
            if status == 'ANSWERED': p.update(log_probabilities=[-math.inf, 0.] + [-math.inf] * 14, possible_worlds=[0, 1])
            else: p.update(status=status, log_probabilities=None)
            result = analyze(bad); metrics = result['by_arm']['alias']['by_seed']['53']['self_contact']
            self.assertEqual((metrics['planned_points'], metrics['correct']), (2, 1))
            self.assertEqual(metrics['mean_nll'], 'positive_infinity' if status == 'ANSWERED' else None)
            self.assertEqual(result['decision']['decision'], 'REVISE_EVIDENCE_FIX')
            self.assertFalse(result['decision']['competence_checks']['53']['self_both_bits'])
            with self.assertRaises(ValueError): analyze([r for r in bad if r is not p])
        bad = deepcopy(rows)
        p = next(r for r in bad if r['participant'] == 'alias' and r['model_seed'] == 53 and
                 r['family'] == 'two_contacts' and r['step'] == 1)
        p.update(log_probabilities=[-math.inf, 0.] + [-math.inf] * 14, previous_truth=[0, 0, 0, 1])
        settings = deepcopy(self.config); settings['analysis']['accuracy_each_seed'] = .8
        result = run.analyze(scoring.score_rows(bad), cases, True, settings)
        checks = result['decision']['competence_checks']['53']
        self.assertFalse(checks['no_new_continuation_errors'])
        self.assertTrue(all(value for key, value in checks.items() if key != 'no_new_continuation_errors'))
        self.assertEqual(result['decision']['decision'], 'REVISE_EVIDENCE_FIX')

    def test_native_bind_collect_keeps_artifact_identity_and_incomplete_execution_distinct(self):
        inputs, oracle, cases = assets()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); data, fitted, output = (root / n for n in ('data', 'fit', 'result'))
            data.mkdir(); fitted.mkdir()
            for name, value in [('evaluation-inputs', inputs), ('evaluation-oracle', oracle), ('prefit', {}),
                ('cases', {'train': [], 'selection': [], 'calibration': [], 'evaluation': cases})]:
                run.io._write(data / (name + '.json'), value)
            saved = save_checkpoint(fitted / 'control.json', control='no_change', provenance={
                'objective': 'no_change', 'completed_updates': 0, 'training_input_sha256': None})
            run.io._write(fitted / 'training.json', {'checkpoints': {arm: {str(seed): {'file': 'control.json', **saved}
                for seed in run.SEEDS} for arm in run.ARMS}, 'all_prescribed_updates_completed': True})
            with patch.object(run, 'verify', return_value=self.config), patch.object(run.io, '_runtime', return_value={}), \
                patch.object(run.io, '_committed'), patch.object(run.io, '_git', return_value='synthetic-commit'), \
                patch.object(run, 'PREFIT', data / 'prefit.json'), redirect_stdout(io.StringIO()):
                run.bind(data, fitted); plan = run.io._read(fitted / 'plan.json')
                self.assertEqual(plan['participants']['ordinary'], dict.fromkeys(map(str, run.SEEDS), saved['sha256']))
                run.collect(data, fitted, output); result = run.io._read(output / 'summary.json.xz')
                self.assertEqual(result['decision']['decision'], 'NO_MATERIAL_EVIDENCE_EFFECT')
                self.assertEqual(result['decision']['gate_g1'], 'NOT_ADMITTED')
                self.assertEqual(len(result['collection_costs']), 10)
                for arm in result['by_arm'].values():
                    for entry in arm['by_seed'].values():
                        self.assertEqual((entry['all_action']['planned_points'], entry['continuation']['planned_points'],
                                          entry['self_contact']['planned_points']), (32, 18, 2))
                manifest = run.io._read(output / 'manifest.json')
                for name, info in manifest['artifacts'].items(): self.assertEqual(run.io._hash(output / name), info['sha256'])
                with self.assertRaises(FileExistsError): run.collect(data, fitted, output)
                class EndFailure(runner.Session):
                    def _handle(self, request):
                        if request['op'] == 'end': raise RuntimeError('synthetic interruption after final forecast')
                        return super()._handle(request)
                with patch.object(runner, 'Session', EndFailure): run.collect(data, fitted, root / 'failed')
                failed = run.io._read(root / 'failed' / 'summary.json.xz')
                self.assertEqual(failed['decision']['decision'], 'STOP_INCOMPLETE_EXECUTION')
                self.assertTrue(failed['metadata']['failure_records'])
                self.assertEqual(failed['metadata']['incomplete_inventory'], [])


if __name__ == '__main__': unittest.main()
