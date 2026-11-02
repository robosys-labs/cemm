"""New structures only; exact training reuse and no learned forecasts."""
from collections import Counter
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from experiments.predictive_nucleus import effect_role_data_v3 as data
from experiments.predictive_nucleus import acceptance_contract as c, continuation_run as io
from experiments.predictive_nucleus.tests import test_effect_role_data as previous


class EffectRoleDataV3Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.assets = data.build_assets()

    def test_all_four_training_artifacts_are_exact_published_bytes(self):
        frozen = io._read(data.TRAINING_PARENT / 'freeze.json')
        with tempfile.TemporaryDirectory() as folder:
            for key, name in data.TRAINING_FILES.items():
                path = Path(folder) / name; io._write(path, self.assets[key])
                self.assertEqual(path.read_bytes(), (data.TRAINING_PARENT / name).read_bytes())
                self.assertEqual(path.read_bytes(), (data.PARENT / name).read_bytes())
                self.assertEqual(io._hash(path), frozen['artifacts'][name]['sha256'])
        audit = self.assets['audit']
        self.assertEqual((audit['teach_forecasts'], audit['rehearsal_forecasts']), (16, 1152))
        self.assertEqual(audit['new_words'], []); self.assertEqual(audit['new_lexical_layout_cells'], [])
        self.assertEqual(audit['training_withheld_but_opened_cells'], [['lights', 'vos'], ['zef', 'vos']])
        self.assertEqual(audit['teaching_identifiability'], io._read(data.TRAINING_PARENT / 'audit.json')['teaching_identifiability'])

    def test_deterministic_new_counts_and_unchanged_observation_oracle_abis(self):
        self.assertEqual(self.assets, data.build_assets())
        for law, bank in self.assets['laws'].items():
            counts = self.assets['audit'][law]
            self.assertEqual([counts[k] for k in ('episodes', 'forecasts', 'identifiable_forecasts', 'ambiguous_forecasts',
                'held_new_word_forecasts', 'goal_groups', 'goal_decisions')], [1536, 6912, 6144, 768, 1152, 384, 1536])
            self.assertEqual(counts['families'], {'path_return4': 768, 'branch_return5': 768})
            self.assertEqual(bank['inputs']['version'], 'bilingual-input-v1')
            self.assertEqual(bank['oracle']['version'], 'effect-role-oracle-v1')
            for old in (data.prior, data.previous):
                self.assertNotEqual(bank['oracle']['source_sha256'], old.source_digest())
                self.assertNotEqual(bank['oracle']['information_law_sha256'], old.law_digest(law))
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
        self.assertEqual((audit['prior_recipe_entries'], audit['prior_distinct_ordered_shapes']), (72, 46))
        self.assertEqual((audit['ordered_overlap'], audit['unordered_multigraph_overlap']), (0, 0))
        self.assertEqual(audit['new_ordered_shapes'], {'path_return4': [[0, 1], [0, 2], [2, 3], [0, 1]],
            'branch_return5': [[0, 1], [0, 2], [2, 3], [2, 4], [0, 2]]})
        for name, (n, edges) in {**data.prior.SCHEDULES, **data.previous.SCHEDULES}.items():
            renamed = tuple((n - 1 - b, n - 1 - a) for a, b in edges)
            with self.subTest(name=name), self.assertRaisesRegex(ValueError, 'previously opened'):
                data.novelty({'renamed': (n, renamed)})
        for version in data.HISTORY:
            for values in audit['old_' + version + '_challenge_overlap_by_law'].values(): self.assertEqual(set(values.values()), {0})
        self.assertEqual(audit['prior_distinct_unordered_multigraphs'], 35)
        self.assertEqual(audit['previous_schedule_sha256'], '0ce8e2c6acd6103943e8146d658c2ea8d970a4cc14f6bb875ac19a84872e0ba8')
        self.assertEqual(set(audit['training_entity_overlap'].values()), {0})
        for parent in data.HISTORY.values():
            for law in data.LAWS:
                old = io._read(parent / (law + '-inputs.json.xz'))['episodes']
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
                    self.assertEqual(goal['set_required'], max(probabilities[2:]) > max(probabilities[:2]))
                    self.assertEqual(goal['contact_required'], max(probabilities[:2]) > max(probabilities[2:]))
            expected = (552, 648, 216, 432, 1344) if law == 'nand' else (468, 708, 300, 408, 2688)
            self.assertEqual(tuple(self.assets['audit'][law][k] for k in ('impossible_goals', 'effect_sensitive_goals',
                'set_required_goals', 'contact_required_goals', 'endpoint_identifiable_actions')), expected)

    def test_no_learner_import_and_frozen_sources_and_parent_artifacts_unchanged(self):
        code = ('import sys; from experiments.predictive_nucleus import effect_role_data_v3; '
                'assert "torch" not in sys.modules; '
                'assert not any(k.endswith(("effect_role_model", "effect_role_scoring")) for k in sys.modules)')
        subprocess.run([sys.executable, '-c', code], check=True)
        self.assertEqual(set(data.SOURCE_FILES), {'effect_role_data_v3.py', *data.previous.SOURCE_FILES})
        self.assertEqual(len(data.SOURCE_FILES), 28)
        for parent in data.HISTORY.values():
            frozen = io._read(parent / 'freeze.json')
            for name, digest in frozen['sources'].items(): self.assertEqual(io._hash(data.ROOT / name), digest)
            for name, item in frozen['artifacts'].items(): self.assertEqual(io._hash(parent / name), item['sha256'])
        self.assertEqual(c.digest(self.assets['lexical_registry']),
                         c.digest(io._read(data.TRAINING_PARENT / data.TRAINING_FILES['lexical_registry'])))


if __name__ == '__main__': unittest.main()
