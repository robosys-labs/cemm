"""Input custody and scoped-reference checks on independent synthetic receipts."""
from copy import deepcopy
import unittest
import torch

from experiments.predictive_nucleus import temporal_native_transfer_v1 as study


def fixture():
    def q(word, scope, stage):
        return study.descriptor('nand', 0, 'svo', 0, word, scope, -1 if stage < 8 else 1, str(stage))
    base = [{'query': q(word, 'parent', 4*word+i), 'endpoint': 0, 'source': 'physical'}
            for word in range(2) for i in range(4)]
    base.append({'query': q(0, 'local', 8), 'endpoint': 3, 'source': 'claim'})
    row = {'id': 'case', 'base': base, 'first': {'query': q(0, 'local', 9), 'endpoint': 1},
           'second': q(0, 'sibling', 10), 'target': q(0, 'local', 11), 'protected': q(1, 'local', 12)}
    likelihood = [[int(i == j) for j in range(8)] for i in range(4)]
    native = {r['query']['native_key']: {'likelihood': likelihood} for r in base}
    return row, native


class NativeTransferInputs(unittest.TestCase):
    def test_duplicate_delivery_and_conflicting_identity(self):
        row, _ = fixture()
        self.assertEqual(study.unique(row['base'] + [deepcopy(row['base'][0])]), row['base'])
        conflict = deepcopy(row['base'][0]); conflict['endpoint'] = 1
        with self.assertRaisesRegex(ValueError, 'conflicting evidence'):
            study.unique(row['base'] + [conflict])

    def test_actual_second_answer_and_identifiers_do_not_change_prefix_features(self):
        row, native = fixture()
        a = study.tensors([row], native, {'case': 2})
        row = deepcopy(row); row['id'] = 'renamed'
        for item in row['base']:
            item['query']['entities'] = ['X', 'Y', 'Z']
            item['query']['evidence_id'] += '-renamed'
        b = study.tensors([row], native, {'renamed': 3})
        for name in a:
            if name != 'second_y':
                self.assertTrue(torch.equal(a[name], b[name]), name)
        self.assertNotEqual(a['second_y'].item(), b['second_y'].item())

    def test_rule_revises_only_observed_scope_and_preserves_protected_word(self):
        row, native = fixture()
        data = study.tensors([row], native, {'case': 2})
        result = study.rule(data)
        self.assertEqual(result['predictions']['base_target'].argmax(-1).item(), 0)
        self.assertEqual(result['predictions']['after_first'].argmax(-1).item(), 1)
        self.assertEqual(result['predictions']['after_second'].argmax(-1).item(), 1)
        self.assertEqual(result['predictions']['protected'].argmax(-1).item(), 0)
        self.assertEqual(result['views']['cleared']['after_second'].argmax(-1).item(), 0)
        # The claim is an attributed message, never an authenticated correction.
        data['base'][:, 8, :] = 0
        changed = study.rule(data)
        for key in result['predictions']:
            self.assertTrue(torch.equal(result['predictions'][key], changed['predictions'][key]))

    def test_rule_branches_do_not_read_actual_optional_answer(self):
        row, native = fixture()
        a = study.rule(study.tensors([row], native, {'case': 2}))
        b = study.rule(study.tensors([row], native, {'case': 3}))
        for view in ('retained', 'cleared'):
            for key in ('probe', 'before', 'branches'):
                self.assertTrue(torch.equal(a['views'][view][key], b['views'][view][key]))


if __name__ == '__main__':
    unittest.main()
