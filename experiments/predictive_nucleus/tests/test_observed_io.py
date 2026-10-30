"""Coordinate, missingness and causal replay checks for observed-file ingestion."""
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import torch

from experiments.predictive_nucleus import acceptance_contract as contract
from experiments.predictive_nucleus import active_learning as learning
from experiments.predictive_nucleus.active_participant import Session
from experiments.predictive_nucleus.domain_flat import DomainFlatGRU
from experiments.predictive_nucleus.observed_io import as_batches, load_batches


def case(n=3, name='observed'):
    ids = [f'z{i}' for i in reversed(range(n))]
    anchor = dict.fromkeys(ids, 0)
    middle = {**anchor, 'z0': 1, 'z1': None}
    after = {**anchor, 'z0': 1, 'z1': 1}
    return {'episode': name, 'ids': ids,
            'observations': [anchor, middle, after, deepcopy(after)],
            'actions': [{'kind': 'set', 'participants': ['z0'], 'value': 1},
                        {'kind': 'contact', 'participants': ['z1', 'z1']},
                        {'kind': 'observe', 'participants': []}],
            'coverage': [ids.copy() for _ in range(3)]}


def data(*cases):
    return {'version': 'active-acceptance-input-v1', 'episodes': list(cases)}


class ObservedIOTests(unittest.TestCase):
    def test_coordinate_alias_and_absence_encoding_preserve_delivered_tape(self):
        original = data(case())
        before = contract.digest(original)
        batch, = as_batches(original)
        self.assertEqual(batch.observations[:, 0].tolist(), [[0, 0, 0], [1, -1, 0], [1, 1, 0], [1, 1, 0]])
        self.assertEqual(batch.actions[:, 0].tolist(), [[1, 0, -1, 1], [0, 1, 1, -1], [2, -1, -1, -1]])
        self.assertFalse(batch.masks[1, 0, 1])
        self.assertTrue(batch.coverage[0, 0, 1])
        batch.observations.fill_(0)
        self.assertEqual(contract.digest(original), before)

    def test_mixed_geometries_keep_every_episode_and_do_not_pad_time(self):
        cases = [case(4, 'four'), case(3, 'three-a'), case(3, 'three-b')]
        short = case(3, 'short')
        for key in ('actions', 'coverage'): short[key] = short[key][:1]
        short['observations'] = short['observations'][:2]
        batches = as_batches(data(*cases, short), batch_size=1)
        self.assertEqual([x.episode_ids for x in batches], [('short',), ('three-a',), ('three-b',), ('four',)])
        self.assertEqual([(len(x.actions), x.observations.shape[-1]) for x in batches], [(1, 3), (3, 3), (3, 3), (3, 4)])
        for invalid in (True, 0, 1025, 1.5):
            with self.subTest(batch_size=invalid), self.assertRaises(ValueError):
                as_batches(data(case()), batch_size=invalid)

    def test_exact_file_hash_and_observed_schema_reject_privileged_fields(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'observed.json'
            sha = contract.write_json(path, data(case()))
            loaded, = load_batches(path, sha)
            self.assertEqual(loaded.episode_ids, ('observed',))
            with self.assertRaises(ValueError): load_batches(path, '0' * 64)
            for field in ('truth', 'possible_worlds', 'hidden_source_slot', 'family'):
                bad = data(case()); bad['episodes'][0][field] = 0
                with self.subTest(field=field), self.assertRaises(ValueError): as_batches(bad)
            path.write_bytes(b'{"version":"x","version":"y","episodes":[]}')
            with self.assertRaises(ValueError): load_batches(path, sha256(path.read_bytes()).hexdigest())

    def test_converted_neural_replay_matches_direct_wire_forecasts_at_every_size(self):
        state = torch.random.get_rng_state()
        self.addCleanup(torch.random.set_rng_state, state)
        torch.manual_seed(193)
        for n in range(3, 7):
            cases = [case(n, f'{n}-{j}') for j in range(2)]
            batch, = as_batches(data(*cases))
            model = DomainFlatGRU(hidden=2).eval()
            replay = learning.replay(batch, model=model)
            for column, item in enumerate(cases):
                session = Session(model=deepcopy(model))
                session.handle({'op': 'start', 'episode': item['episode'], 'ids': item['ids'],
                                'observation': item['observations'][0]})
                for t, action in enumerate(item['actions']):
                    response = session.handle({'op': 'predict', 'episode': item['episode'], 'step': t,
                                               'action': action, 'sensor_ids': item['coverage'][t]})
                    logs = torch.tensor(response['log']['values'][0], dtype=torch.float64)
                    torch.testing.assert_close(logs, replay['log_probabilities'][t, column], rtol=0, atol=1e-12)
                    session.handle({'op': 'feedback', 'episode': item['episode'], 'step': t,
                                    'receipt': response['receipt'], 'observation': item['observations'][t + 1]})
                session.handle({'op': 'end', 'episode': item['episode']})

    def test_import_does_not_load_data_generator_or_oracle(self):
        code = ('import sys; import experiments.predictive_nucleus.observed_io; '
                'assert not any(x in sys.modules for x in ['
                '"experiments.predictive_nucleus.world",'
                '"experiments.predictive_nucleus.prospective_data",'
                '"experiments.predictive_nucleus.prospective_oracle",'
                '"experiments.predictive_nucleus.prospective_audit"])')
        completed = subprocess.run([sys.executable, '-c', code], capture_output=True, text=True, timeout=30)
        self.assertEqual(completed.returncode, 0, completed.stderr)


if __name__ == '__main__':
    unittest.main()
