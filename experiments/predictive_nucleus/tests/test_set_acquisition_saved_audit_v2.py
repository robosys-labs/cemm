"""Independent saved-record arithmetic on synthetic fixtures only; no study runs."""
from copy import deepcopy
import subprocess
import sys
import unittest
from unittest.mock import patch

from experiments.predictive_nucleus import audit_bilingual_saved as h
from experiments.predictive_nucleus import audit_set_acquisition_v2 as a
from experiments.predictive_nucleus.set_acquisition_retention_v2 import retention
from experiments.predictive_nucleus.set_acquisition_scoring import analyze_native
from experiments.predictive_nucleus.tests.test_set_acquisition_run import language_fixture
from experiments.predictive_nucleus.tests.test_set_acquisition_scoring import fixture, LIMITS


class SetAcquisitionSavedAuditV2Tests(unittest.TestCase):
    def test_all_saved_native_and_retention_arithmetic_on_synthetic_records(self):
        bundle, traces = fixture(); original = deepcopy((bundle, traces))
        report = analyze_native(bundle, traces, LIMITS); audit = h.Audit()
        records = {e['episode']: e for e in bundle['inputs']['episodes']}
        meta = {e['episode']: e for e in bundle['cases']}
        gold = {e['episode']: e for e in bundle['oracle']['episodes']}
        info = {e['episode']: e for e in bundle['information']['episodes']}
        measured, summaries = {}, {}
        with patch.object(a, 'h', h, create=True):
            for arm in a.ARMS:
                rows = a.index_rows(traces[arm], records)
                measured[arm] = a.measured_native(rows, records, gold, info, meta, audit)
                summaries[arm] = a.summarize(list(measured[arm].values()), {'pair': ['left', 'right']})
                audit.equal(summaries[arm], report['reports'][arm], arm)
            changes = {arm: a.changes(measured['acquired'], measured[arm]) for arm in ('parent', 'no_change')}
            audit.equal(changes, report['comparisons'], 'changes')
            audit.equal(a.native_checks(summaries['acquired'], changes, LIMITS), report['checks'], 'native checks')
            inputs, old = language_fixture(); observed = {r['id']: r for r in inputs['episodes']}
            limits = {'max_retention_logp_change': 1e-10, 'max_retention_order_logp_change': 1e-10}
            for variant in ('same', 'roundoff', 'order_reversal', 'world_change', 'zero_probability'):
                current = deepcopy(old)
                if variant == 'roundoff': current['order_logp'] = [v + 5e-15 for v in old['order_logp']]
                elif variant == 'order_reversal': current['order_logp'].reverse()
                elif variant == 'world_change': current['logp'].reverse()
                elif variant == 'zero_probability': current['logp'] = [0.] + ['negative_infinity'] * 7
                expected = retention(inputs, [current], [old], limits)
                rebuilt = a.retained(a.index_rows([current], observed, True),
                    a.index_rows([old], observed, True), observed, limits)
                audit.equal(rebuilt, expected, 'retention/' + variant)
        self.assertEqual(audit.discrepancy_count, 0, audit.discrepancies)
        self.assertEqual(audit.checks, 6620)
        self.assertEqual((bundle, traces), original)

    def test_pre_score_input_only_index_rejects_bad_inventory_and_probabilities(self):
        bundle, traces = fixture()
        records = {e['episode']: e for e in bundle['inputs']['episodes']}
        for defect in ('missing', 'duplicate', 'foreign', 'bool_step', 'geometry', 'mass', 'nan'):
            rows = deepcopy(traces['acquired'])
            if defect == 'missing': rows.pop()
            elif defect == 'duplicate': rows.append(deepcopy(rows[0]))
            elif defect == 'foreign': rows[0]['id'] = 'foreign'
            elif defect == 'bool_step': rows[0]['step'] = True
            elif defect == 'geometry': rows[0]['logp'].pop()
            elif defect == 'mass': rows[0]['logp'] = [0.] * 8
            else: rows[0]['logp'][0] = float('nan')
            with self.subTest(defect=defect), patch.object(a, 'h', h, create=True):
                with self.assertRaises(ValueError): a.index_rows(rows, records)

    def test_auditor_import_does_not_import_models_or_study_scorers(self):
        code = ('import sys; import experiments.predictive_nucleus.audit_set_acquisition_v2; '
                'assert "torch" not in sys.modules; '
                'assert "experiments.predictive_nucleus.set_acquisition_scoring" not in sys.modules; '
                'assert "experiments.predictive_nucleus.set_acquisition_retention_v2" not in sys.modules')
        subprocess.run([sys.executable, '-c', code], check=True)


if __name__ == '__main__': unittest.main()
