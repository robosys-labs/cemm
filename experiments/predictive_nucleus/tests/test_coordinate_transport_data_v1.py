"""Small synthetic recipe checks without preparing the complete prospective bank."""
from copy import deepcopy
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from experiments.predictive_nucleus import acceptance_contract as c, continuation_run as io
from experiments.predictive_nucleus import coordinate_transport_data_v1 as data


class CoordinateTransportDataTests(unittest.TestCase):
    def ticket(self, number=1000000, law='nand', pattern=0, modes=(0, 1, 0)):
        # These fixture counters are outside the registered 0..1535 trial bank.
        return data._public_ticket(number, law, 'lights', ('svo', 'osv', 'vos'), pattern, modes)

    def fixture(self):
        public, oracle = data._realize(self.ticket(), 0)
        return {'inputs': {'version': data.VERSION, 'trials': [public]},
                'evaluator': {'version': data.VERSION, 'trials': [oracle]},
                'audit': {'trials': 1, 'instances': 3, 'historical_sha256': {}}}

    def test_public_schema_withholds_target_truth_and_hidden_metadata(self):
        public, oracle = data._realize(self.ticket(), 2)
        self.assertEqual(set(public), {'id', 'law', 'demonstrations', 'query'})
        self.assertEqual(set(public['query']), {'id', 'entities', 'anchor', 'context', 'text'})
        self.assertEqual(len(public['demonstrations']), 2)
        for record in public['demonstrations']:
            self.assertEqual(set(record), {'id', 'entities', 'anchor', 'context', 'utterances'})
            self.assertEqual(len(record['utterances']), 1)
            self.assertEqual(set(record['utterances'][0]), {'text', 'reading'})
        self.assertEqual(data.validate_inputs({'version': 'bilingual-input-v1',
            'episodes': public['demonstrations']})['episodes'], public['demonstrations'])
        self.assertEqual(oracle['meaning'], 2)
        self.assertEqual(oracle['evidence_ids'], [value + '/utterance/0' for value in oracle['instance_ids']])
        self.assertEqual(oracle['instance_ids'],
                         [record['id'] for record in (*public['demonstrations'], public['query'])])

    def test_meaning_assignment_cannot_change_public_identifiers_or_surfaces(self):
        ticket = self.ticket()
        before = deepcopy(ticket)
        realized = [data._realize(ticket, meaning) for meaning in range(4)]
        self.assertEqual(ticket, before)
        reference = realized[0][0]
        for public, oracle in realized:
            self.assertEqual(public['id'], reference['id'])
            self.assertEqual(public['query'], reference['query'])
            for record, expected in zip(public['demonstrations'], reference['demonstrations'], strict=True):
                self.assertEqual({key: value for key, value in record.items() if key != 'utterances'},
                                 {key: value for key, value in expected.items() if key != 'utterances'})
                self.assertEqual(record['utterances'][0]['text'], expected['utterances'][0]['text'])
            self.assertEqual(oracle['outcomes_by_meaning'], realized[0][1]['outcomes_by_meaning'])
        for stage in range(3):
            self.assertEqual({row['action_indices'][stage] for _, row in realized}, set(range(4)))
            self.assertEqual(len({tuple(row['physical_actions'][stage]) for _, row in realized}), 4)

    def test_patterns_follow_canonical_participants_through_roster_rotation(self):
        rotated = False
        for pattern in (0, 1):
            ticket = self.ticket(pattern=pattern)
            for stage, (prefix, (a, b)) in enumerate(zip(ticket['prefixes'], ticket['participants'], strict=True)):
                spectator = next(slot for slot in range(3) if slot not in (a, b))
                before = prefix['context'][-1]['reading']
                self.assertEqual(tuple(before[slot] for slot in (a, b, spectator)), data.PATTERNS[pattern][stage])
                layout = ticket['metadata']['layouts'][stage]
                first, second = prefix['entities'][a], prefix['entities'][b]
                expected = {'svo': [first, 'lights', second], 'osv': [second, first, 'lights'],
                            'vos': ['lights', second, first]}[layout]
                self.assertEqual(prefix['text'].split(), expected)
                rotated |= (a, b) != (0, 1)
        self.assertTrue(rotated)

    def test_each_instance_exposes_its_own_independent_physical_mode(self):
        for modes in ((0, 1, 0), (1, 0, 1)):
            ticket = self.ticket(modes=modes)
            for prefix, mode in zip(ticket['prefixes'], modes, strict=True):
                self.assertEqual(prefix['anchor'], [0, 0, 0])
                self.assertEqual(len(prefix['context']), 4)
                self.assertEqual(prefix['context'][0]['action'], [0, 0, 1, -1])
                self.assertEqual(prefix['context'][0]['reading'], [int(mode == 1), int(mode == 0), 0])
                self.assertEqual([event['action'][1] for event in prefix['context'][1:]], [0, 1, 2])

    def test_primitive_truth_and_all_counterfactuals_match_independent_boolean_rollout(self):
        self.assertEqual(data.MEANINGS, ((0, 0, 1, -1), (0, 1, 0, -1), (1, 0, -1, 1), (1, 1, -1, 1)))
        for law in ('nand', 'nor'):
            for modes in ((0, 1, 0), (1, 0, 1)):
                ticket = self.ticket(law=law, modes=modes)
                for meaning in range(4):
                    public, oracle = data._realize(ticket, meaning)
                    self.assertEqual(oracle['canonical_action'], list(data.MEANINGS[meaning]))
                    for stage, (prefix, (a, b), mode) in enumerate(zip(
                            ticket['prefixes'], ticket['participants'], modes, strict=True)):
                        physical_actions = [[0, a, b, -1], [0, b, a, -1], [1, a, -1, 1], [1, b, -1, 1]]
                        self.assertEqual(oracle['physical_actions'][stage], physical_actions[meaning])
                        mentions = [prefix['entities'].index(token) for token in prefix['text'].split()
                                    if token in prefix['entities']]
                        first, second = mentions
                        menu = [[0, first, second, -1], [0, second, first, -1],
                                [1, first, -1, 1], [1, second, -1, 1]]
                        self.assertEqual(oracle['action_indices'][stage], menu.index(physical_actions[meaning]))
                        expected = []
                        for alternative in range(4):
                            bits = prefix['context'][-1]['reading'].copy()
                            if alternative < 2:
                                pair = (a, b) if alternative == 0 else (b, a)
                                source, target = pair[mode], pair[1 - mode]
                                value = (bits[source] & bits[target]) if law == 'nand' else (bits[source] | bits[target])
                                bits[target] = 1 - value
                            else:
                                bits[(a, b)[alternative - 2]] = 1
                            expected.append(bits[0] * 4 + bits[1] * 2 + bits[2])
                        self.assertEqual(oracle['outcomes_by_meaning'][stage], expected)
                        self.assertEqual(oracle['endpoints'][stage], expected[meaning])
                        if stage < 2:
                            reading = public['demonstrations'][stage]['utterances'][0]['reading']
                            self.assertEqual(reading[0] * 4 + reading[1] * 2 + reading[2], expected[meaning])

    def test_public_tickets_are_deterministic_and_participants_are_disjoint(self):
        first, second = self.ticket(), self.ticket(number=1000001)
        self.assertEqual(first, self.ticket())
        self.assertNotEqual(first['id'], second['id'])
        instances = first['prefixes'] + second['prefixes']
        self.assertEqual(len({prefix['id'] for prefix in instances}), 6)
        self.assertEqual(len({name for prefix in instances for name in prefix['entities']}), 18)

    def test_simulator_oracle_disagreement_stops_generation(self):
        with patch.object(data.physical, '_distribution', return_value=([0], [1.])):
            with self.assertRaisesRegex(ValueError, 'simulator and table oracle disagree'):
                self.ticket()

    def test_exclusive_preparation_writes_bounded_fixture_and_hashes(self):
        assets = self.fixture()
        sources = {name: io._hash(io.ROOT / name) for name in data.SOURCE_FILES}
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / 'prepared'
            with patch.object(data, 'build_assets', return_value=assets), \
                    patch.object(data, '_source_state', return_value=('a' * 40, sources)):
                frozen = data.prepare(output)
                with self.assertRaisesRegex(ValueError, 'already exists'):
                    data.prepare(output)
            self.assertEqual(set(path.name for path in output.iterdir()),
                             {'inputs.json.xz', 'evaluator.json.xz', 'audit.json', 'freeze.json'})
            for key, filename in (('inputs', 'inputs.json.xz'), ('evaluator', 'evaluator.json.xz'), ('audit', 'audit.json')):
                self.assertEqual(io._read(output / filename), assets[key])
                self.assertEqual(io._hash(output / filename), frozen['artifacts'][filename]['sha256'])
                self.assertEqual((output / filename).stat().st_size, frozen['artifacts'][filename]['bytes'])
            self.assertEqual(io._read(output / 'freeze.json'), frozen)
            self.assertEqual(frozen['source_commit'], 'a' * 40)
            self.assertEqual(frozen['input_content_sha256'], c.digest(assets['inputs']))
            self.assertEqual(frozen['evaluator_content_sha256'], c.digest(assets['evaluator']))

    def test_changed_sources_and_unpublished_sources_block_preparation(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / 'unwritten'
            sources = {name: '0' * 64 for name in data.SOURCE_FILES}
            with patch.object(data, 'build_assets', return_value=self.fixture()), \
                    patch.object(data, '_source_state', return_value=('a' * 40, sources)), \
                    self.assertRaisesRegex(ValueError, 'source changed'):
                data.prepare(output)
            self.assertFalse(output.exists())
        with patch.object(data.io, '_git', side_effect=['a' * 40, '']), \
                patch.object(data.subprocess, 'check_output', return_value=b'unpublished'), \
                self.assertRaisesRegex(ValueError, 'unpublished data-generation source'):
            data._source_state()

    def test_historical_custody_and_absence_of_learner_imports(self):
        with patch.object(data.io, '_hash', return_value='0' * 64), \
                self.assertRaisesRegex(ValueError, 'training receipt differs'):
            data._historical()
        script = ('import sys; from experiments.predictive_nucleus import coordinate_transport_data_v1; '
                  'assert "torch" not in sys.modules; '
                  'assert not any(name.endswith(("effect_role_model", "effect_role_lexical")) for name in sys.modules)')
        subprocess.run([sys.executable, '-c', script], cwd=Path(__file__).resolve().parents[3], check=True)


if __name__ == '__main__':
    unittest.main()
