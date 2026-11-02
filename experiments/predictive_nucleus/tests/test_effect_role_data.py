"""Prospective generator checks only; no fitted model or real forecasts."""
from collections import Counter, defaultdict
from copy import deepcopy
from itertools import product
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from experiments.predictive_nucleus import effect_role_data as data
from experiments.predictive_nucleus import acceptance_contract as c, continuation_run as io


def step(before, action, mode, law):
    after = before.copy()
    if action[0]:
        after[action[1]] = action[3]
    else:
        source, target = action[1 + mode], action[2 - mode]
        after[target] = int(not (before[source] and before[target])) if law == 'nand' else int(
            not (before[source] or before[target]))
    return after


def distribution(before, action, modes, law):
    counts = Counter(tuple(step(before, action, m, law)) for m in modes)
    return {sum(b << (len(bits) - i - 1) for i, b in enumerate(bits)): n / len(modes)
            for bits, n in counts.items()}


class EffectRoleDataTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.assets = data.build_assets()

    def test_exact_rehearsal_and_cross_context_teaching_identification(self):
        a = self.assets
        with tempfile.TemporaryDirectory() as folder:
            saved = Path(folder) / 'train.json.xz'; io._write(saved, a['rehearsal'])
            self.assertEqual(saved.read_bytes(), data.REHEARSAL.read_bytes())
        self.assertEqual(sum(len(e['utterances']) for e in a['rehearsal']['episodes']), 1152)
        self.assertEqual(len(a['teach']['episodes']), 16)
        self.assertEqual(len({c.digest(e) for e in a['teach']['episodes']}), 16)
        self.assertEqual({v for row in a['parser_labels']['rehearsal'].values() for v in row}, {0, 1})
        for word, layout in product(data.NEW_WORDS, ('svo', 'osv')):
            proof = a['audit']['teaching_identifiability'][word + '/' + layout]
            self.assertEqual(len(proof['episodes']), 4)
            self.assertTrue(all(len(x) > 1 for x in proof['compatible_actions']))
            self.assertEqual(set.intersection(*map(set, proof['compatible_actions'])), {proof['action_index']})
            self.assertEqual(proof['intersection'], [3 if layout == 'svo' else 2])
        injected = deepcopy(a['teach']); injected['episodes'][0]['mode'] = 0
        with self.assertRaisesRegex(ValueError, 'fields'): data.validate_inputs(injected)

    def test_determinism_denominators_and_training_withheld_layout(self):
        self.assertEqual(self.assets, data.build_assets())
        for law in data.LAWS:
            audit = self.assets['audit'][law]
            self.assertEqual([audit[k] for k in ('episodes', 'forecasts', 'identifiable_forecasts',
                'ambiguous_forecasts', 'held_new_word_forecasts', 'goal_groups', 'goal_decisions')],
                [1536, 6912, 6144, 768, 1152, 384, 1536])
            self.assertEqual(audit['families'], {'interleaved_return4': 768, 'cycle_tail5': 768})
            for gold in self.assets['laws'][law]['oracle']['episodes']:
                self.assertEqual({cell['layout'] for cell in gold['cells']}, set(data.LAYOUTS))
                self.assertEqual(gold['layout'], gold['cells'][-1]['layout'])
                for cell in gold['cells']:
                    self.assertEqual(cell['held_layout'], cell['new_word'] and cell['layout'] == 'vos')
        for e in self.assets['teach']['episodes']:
            self.assertNotIn(e['utterances'][0]['text'].split()[0], data.NEW_WORDS)

    def test_independent_boolean_rollout_and_full_conditional_oracle(self):
        for law in data.LAWS:
            bank = self.assets['laws'][law]
            for record, gold in zip(bank['inputs']['episodes'], bank['oracle']['episodes'], strict=True):
                self.assertEqual(record['id'], gold['id'])
                before, modes = record['anchor'], [0, 1]
                for event in record['context']:
                    modes = [m for m in modes if step(before, event['action'], m, law) == event['reading']]
                    before = event['reading']
                self.assertEqual(modes, [gold['mode']] if gold['context_mode'] == 'established' else [0, 1])
                for t, (event, action, target, index) in enumerate(zip(record['utterances'], gold['actions'],
                        gold['forecasts'], gold['action_indices'], strict=True)):
                    expected = distribution(before, action, modes, law)
                    self.assertEqual(dict(zip(target['possible_worlds'], target['probabilities'])), expected)
                    self.assertEqual(target['surviving_modes'], modes)
                    self.assertEqual(event['reading'], step(before, action, gold['mode'], law))
                    mentions = [record['entities'].index(w) for w in event['text'].split() if w in record['entities']]
                    a, b = mentions; menu = [[0, a, b, -1], [0, b, a, -1], [1, a, -1, 1], [1, b, -1, 1]]
                    self.assertEqual(menu[index], action)
                    self.assertEqual(target['equivalent_action_indices'], [i for i, candidate in enumerate(menu)
                        if distribution(before, candidate, modes, law) == expected])
                    self.assertEqual(target['information_key'], data.prefix_key(record, t))
                    modes = [m for m in modes if step(before, action, m, law) == event['reading']]
                    before = event['reading']

    def test_information_keys_do_not_read_current_or_future_outcomes(self):
        original = self.assets['laws']['nand']['inputs']['episodes'][0]
        changed = deepcopy(original)
        for event in changed['utterances'][1:]: event['reading'] = [1 - bit for bit in event['reading']]
        self.assertEqual(data.prefix_key(original, 1), data.prefix_key(changed, 1))
        self.assertNotEqual(data.prefix_key(original, 2), data.prefix_key(changed, 2))
        changed['utterances'][1]['text'] = changed['utterances'][1]['text'].replace('lights', 'zef')
        if original['utterances'][1]['text'] != changed['utterances'][1]['text']:
            self.assertNotEqual(data.prefix_key(original, 1), data.prefix_key(changed, 1))

    def test_parallel_branches_role_and_translation_pairing(self):
        for law in data.LAWS:
            bank = self.assets['laws'][law]; records = {r['id']: r for r in bank['inputs']['episodes']}
            for field, size in (('role_pair_id', 2), ('translation_group_id', 3), ('effect_pair_id', 2)):
                groups = defaultdict(list)
                for g in bank['oracle']['episodes']: groups[g[field]].append(g)
                self.assertEqual(set(map(len, groups.values())), {size})
                for members in groups.values():
                    left = members[0]; first = records[left['id']]
                    for right in members[1:]:
                        second = records[right['id']]
                        self.assertEqual([first[k] for k in ('entities', 'anchor', 'context')],
                                         [second[k] for k in ('entities', 'anchor', 'context')])
                        if field == 'role_pair_id':
                            for a, b in zip(left['actions'], right['actions'], strict=True):
                                self.assertEqual(a[0], b[0])
                                if a[0] == 0: self.assertEqual(a[1:3], b[1:3][::-1])
                                else: self.assertNotEqual(a[1], b[1])
                        elif field == 'translation_group_id':
                            self.assertEqual(left['actions'], right['actions'])
                            self.assertEqual(left['truth'], right['truth'])
                        else:
                            self.assertEqual(first['utterances'][:-1], second['utterances'][:-1])
                            mentions = lambda r: [w for w in r['utterances'][-1]['text'].split() if w in r['entities']]
                            self.assertEqual(mentions(first), mentions(second))
                            self.assertNotEqual(left['actions'][-1][0], right['actions'][-1][0])

    def test_all_goal_utilities_from_conditional_worlds_and_spectator_preservation(self):
        for law in data.LAWS:
            bank = self.assets['laws'][law]; gold = {g['id']: g for g in bank['oracle']['episodes']}
            records = {r['id']: r for r in bank['inputs']['episodes']}
            for group in bank['goal_groups']:
                self.assertEqual([gold[e]['final_choice'] for e in group['episodes']], [0, 1, 2, 3])
                self.assertEqual({data.prefix_key(records[e]) for e in group['episodes']}, {group['shared_prefix_sha256']})
                self.assertEqual([g['target_bits'] for g in group['goals']], [[0, 0], [0, 1], [1, 0], [1, 1]])
                a, b = group['participants']; n = len(group['before'])
                for goal in group['goals']:
                    desired = group['before'].copy(); desired[a], desired[b] = goal['target_bits']
                    world = sum(bit << (n - i - 1) for i, bit in enumerate(desired)); utilities = []
                    for eid in group['episodes']:
                        f = gold[eid]['forecasts'][-1]
                        utilities.append(dict(zip(f['possible_worlds'], f['probabilities'])).get(world, 0.))
                    self.assertEqual(goal['oracle_utilities'], utilities)
                    self.assertEqual(goal['attainable'], max(utilities) > 0)
                    self.assertEqual(goal['optimal_choices'], [i for i, u in enumerate(utilities) if u == max(utilities)])
                    self.assertEqual(goal['effect_sensitive'], max(utilities[:2]) != max(utilities[2:]))
            expected = (582, 558, 186, 372) if law == 'nand' else (474, 714, 294, 420)
            self.assertEqual(tuple(self.assets['audit'][law][k] for k in
                ('impossible_goals', 'effect_sensitive_goals', 'set_required_goals', 'contact_required_goals')), expected)

    def test_fresh_identities_and_canonical_shapes_against_opened_banks(self):
        fresh = self.assets['teach']['episodes'] + self.assets['laws']['nand']['inputs']['episodes']
        names = {name for r in fresh for name in r['entities']}; ids = {r['id'] for r in fresh}
        for study in ('bilingual', 'lexical', 'binding', 'saturation', 'centering', 'coordinate'):
            for filename in ('train-inputs.json.xz', 'nand-inputs.json.xz'):
                path = io.ROOT / 'data' / (study + '-v1') / filename
                if not path.exists(): continue  # coordinate retains the exact saturation TRAIN pointer.
                prior = io._read(path)['episodes']
                self.assertFalse(names & {name for r in prior for name in r['entities']})
                self.assertFalse(ids & {r['id'] for r in prior})
        for family, (n, edges) in data.SCHEDULES.items():
            renamed = tuple((n - 1 - b, n - 1 - a) for a, b in edges)
            self.assertEqual(data.centering_data.ordered_shape(edges), data.centering_data.ordered_shape(renamed))
        source = ('from experiments.predictive_nucleus import effect_role_data; import sys; '
                  'assert "torch" not in sys.modules; '
                  'assert not any(k.endswith("effect_role_model") for k in sys.modules)')
        subprocess.run([sys.executable, '-c', source], check=True)


if __name__ == '__main__': unittest.main()
