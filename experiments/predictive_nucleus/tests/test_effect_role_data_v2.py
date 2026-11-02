"""New structures only; exact training reuse and no learned forecasts."""
from collections import Counter
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from experiments.predictive_nucleus import effect_role_data_v2 as data
from experiments.predictive_nucleus import acceptance_contract as c, continuation_run as io
from experiments.predictive_nucleus.tests import test_effect_role_data as previous


class EffectRoleDataV2Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.assets = data.build_assets()

    def test_all_four_training_artifacts_are_exact_published_bytes(self):
        frozen = io._read(data.PARENT / 'freeze.json')
        with tempfile.TemporaryDirectory() as folder:
            for key, name in data.TRAINING_FILES.items():
                path = Path(folder) / name; io._write(path, self.assets[key])
                self.assertEqual(path.read_bytes(), (data.PARENT / name).read_bytes())
                self.assertEqual(io._hash(path), frozen['artifacts'][name]['sha256'])
        audit = self.assets['audit']
        self.assertEqual((audit['teach_forecasts'], audit['rehearsal_forecasts']), (16, 1152))
        self.assertEqual(audit['new_words'], []); self.assertEqual(audit['new_lexical_layout_cells'], [])
        self.assertEqual(audit['training_withheld_but_opened_cells'], [['lights', 'vos'], ['zef', 'vos']])
        self.assertEqual(audit['teaching_identifiability'], io._read(data.PARENT / 'audit.json')['teaching_identifiability'])

    def test_deterministic_new_counts_and_unchanged_observation_oracle_abis(self):
        self.assertEqual(self.assets, data.build_assets())
        for law, bank in self.assets['laws'].items():
            counts = self.assets['audit'][law]
            self.assertEqual([counts[k] for k in ('episodes', 'forecasts', 'identifiable_forecasts', 'ambiguous_forecasts',
                'held_new_word_forecasts', 'goal_groups', 'goal_decisions')], [1536, 6912, 6144, 768, 1152, 384, 1536])
            self.assertEqual(counts['families'], {'hub_return4': 768, 'triangle_fan5': 768})
            self.assertEqual(bank['inputs']['version'], 'bilingual-input-v1')
            self.assertEqual(bank['oracle']['version'], 'effect-role-oracle-v1')
            self.assertNotEqual(bank['oracle']['source_sha256'], data.prior.source_digest())
            self.assertNotEqual(bank['oracle']['information_law_sha256'], data.prior.law_digest(law))
            strata = Counter((g['family'], g['mode'], g['direction'], g['layout'], g['context_mode'], g['phase'], g['final_choice'])
                             for g in bank['oracle']['episodes'])
            self.assertEqual(set(strata.values()), {4})  # Four anchors in every design cell.
            self.assertEqual(len(strata), 384)

    def test_all_conditional_forecasts_and_pairing_reuse_independent_invariants(self):
        # These unchanged invariants independently enumerate Boolean transitions;
        # only their observed/evaluator inputs are the new in-memory assets.
        previous.EffectRoleDataTests.test_independent_boolean_rollout_and_full_conditional_oracle(self)
        previous.EffectRoleDataTests.test_parallel_branches_role_and_translation_pairing(self)
        previous.EffectRoleDataTests.test_information_keys_do_not_read_current_or_future_outcomes(self)

    def test_novel_even_without_time_and_rejects_renamed_old_v1_graphs(self):
        audit = self.assets['audit']
        self.assertEqual((audit['prior_recipe_entries'], audit['prior_distinct_ordered_shapes']), (70, 44))
        self.assertEqual((audit['ordered_overlap'], audit['unordered_multigraph_overlap']), (0, 0))
        self.assertEqual(audit['new_ordered_shapes'], {'hub_return4': [[0, 1], [0, 2], [0, 3], [0, 1]],
            'triangle_fan5': [[0, 1], [0, 2], [1, 2], [1, 3], [1, 4]]})
        for name, (n, edges) in data.prior.SCHEDULES.items():
            renamed = tuple((n - 1 - b, n - 1 - a) for a, b in edges)
            with self.subTest(name=name), self.assertRaisesRegex(ValueError, 'previously opened'):
                data.novelty({'renamed': (n, renamed)})
        for values in audit['old_v1_challenge_overlap_by_law'].values(): self.assertEqual(set(values.values()), {0})
        self.assertEqual(set(audit['training_entity_overlap'].values()), {0})
        for law in data.LAWS:
            old = io._read(data.PARENT / (law + '-inputs.json.xz'))['episodes']
            new = self.assets['laws'][law]['inputs']['episodes']
            self.assertFalse({e['id'] for e in old} & {e['id'] for e in new})
            self.assertFalse({v for e in old for v in e['entities']} & {v for e in new for v in e['entities']})

    def test_goals_recomputed_from_conditional_worlds_with_all_impossible_goals(self):
        for law, bank in self.assets['laws'].items():
            gold = {g['id']: g for g in bank['oracle']['episodes']}; records = {r['id']: r for r in bank['inputs']['episodes']}
            for group in bank['goal_groups']:
                self.assertEqual({data.prior.prefix_key(records[e]) for e in group['episodes']}, {group['shared_prefix_sha256']})
                self.assertEqual([g['target_bits'] for g in group['goals']], [[0, 0], [0, 1], [1, 0], [1, 1]])
                a, b = group['participants']
                for goal in group['goals']:
                    bits = group['before'].copy(); bits[a], bits[b] = goal['target_bits']
                    target = sum(bit << (len(bits) - i - 1) for i, bit in enumerate(bits))
                    probabilities = [dict(zip(gold[e]['forecasts'][-1]['possible_worlds'],
                        gold[e]['forecasts'][-1]['probabilities'], strict=True)).get(target, 0.) for e in group['episodes']]
                    self.assertEqual(goal['oracle_utilities'], probabilities)
                    self.assertEqual(goal['attainable'], max(probabilities) > 0)
                    self.assertEqual(goal['effect_sensitive'], max(probabilities[:2]) != max(probabilities[2:]))
            expected = (582, 558, 186, 372, 1380) if law == 'nand' else (480, 702, 288, 414, 2808)
            self.assertEqual(tuple(self.assets['audit'][law][k] for k in ('impossible_goals', 'effect_sensitive_goals',
                'set_required_goals', 'contact_required_goals', 'endpoint_identifiable_actions')), expected)

    def test_no_learner_import_and_frozen_sources_and_parent_artifacts_unchanged(self):
        code = ('import sys; from experiments.predictive_nucleus import effect_role_data_v2; '
                'assert "torch" not in sys.modules; '
                'assert not any(k.endswith(("effect_role_model", "effect_role_scoring")) for k in sys.modules)')
        subprocess.run([sys.executable, '-c', code], check=True)
        frozen = io._read(data.PARENT / 'freeze.json')
        for name, digest in frozen['sources'].items(): self.assertEqual(io._hash(data.ROOT / name), digest)
        for name, item in frozen['artifacts'].items(): self.assertEqual(io._hash(data.PARENT / name), item['sha256'])
        self.assertEqual(c.digest(self.assets['lexical_registry']),
                         c.digest(io._read(data.PARENT / data.TRAINING_FILES['lexical_registry'])))


if __name__ == '__main__': unittest.main()
