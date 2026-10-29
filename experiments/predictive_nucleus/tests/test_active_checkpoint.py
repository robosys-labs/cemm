"""Portable learned-state invariants on synthetic tensors and measured histories."""
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import torch

from experiments.predictive_nucleus import active_checkpoint as checkpoint
from experiments.predictive_nucleus.domain_contract import DomainMemory, domain_context
from experiments.predictive_nucleus.domain_flat import DomainFlatGRU
from experiments.predictive_nucleus.domain_kernel import DomainKernel
from experiments.predictive_nucleus.joint_objective import JointKernel, fingerprint


UNTRAINED = {'training_input_sha256': None, 'objective': 'untrained_or_inherited', 'completed_updates': 0}
COUNTS = {'training_input_sha256': 'a' * 64, 'objective': 'observed_counts', 'completed_updates': 0}


def measured(entities):
    return SimpleNamespace(
        observations=torch.tensor([[[0] * entities], [[1] * entities], [[i % 2 for i in range(entities)]]],
                                  dtype=torch.float64),
        actions=torch.tensor([[[0, entities - 1, entities - 1, -1]], [[0, 0, entities - 1, -1]]]))


def trace(model, entities):
    pre = torch.tensor([[i % 2 for i in range(entities)]], dtype=torch.float64)
    state, output = model.initial(1), []
    actions = [[0, entities - 1, entities - 1, -1], [1, 0, -1, 1], [0, 0, entities - 1, -1]]
    for action in actions:
        logs, pending = model.predict(pre, torch.tensor([action]), state)
        output.append(logs.detach().clone())
        # A represented complete reading is a synthetic interface witness, not an oracle score.
        world = int(logs.argmax(-1))
        pre = torch.tensor([[(world >> (entities - 1 - i)) & 1 for i in range(entities)]], dtype=torch.float64)
        state = model.receive(pending, pre)
    return output, state.detach().clone()


class CheckpointTests(unittest.TestCase):
    def setUp(self):
        self.directory = TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / 'learned.json'

    def write_variant(self, document):
        raw = json.dumps(document, sort_keys=True, allow_nan=False).encode()
        path = self.path.with_name('changed.json')
        path.write_bytes(raw)
        return path, sha256(raw).hexdigest()

    def test_all_model_configurations_round_trip_tensors_and_fresh_forecasts(self):
        configurations = [DomainKernel(), DomainKernel(persistence=True), DomainKernel(role_tying=False),
                          DomainKernel(memory=False), DomainFlatGRU(), DomainFlatGRU(persistence=True)]
        for number, source in enumerate(configurations):
            with self.subTest(kind=type(source).__name__, number=number):
                path = self.path.with_name(f'model-{number}.json')
                source.train()
                before, rng = fingerprint(source.state_dict()), torch.random.get_rng_state().clone()
                summary = checkpoint.save_checkpoint(path, model=source, provenance=UNTRAINED)
                restored = checkpoint.load_checkpoint(path, summary['sha256'])
                self.assertTrue(torch.equal(rng, torch.random.get_rng_state()))
                self.assertTrue(source.training)
                self.assertFalse(restored['model'].training)
                self.assertEqual(fingerprint(source.state_dict()), before)
                self.assertEqual(fingerprint(restored['model'].state_dict()), before)
                self.assertEqual(summary['state_sha256'], before)
                for entities in range(3, 7):
                    left, ls = trace(source, entities); right, rs = trace(restored['model'], entities)
                    self.assertTrue(all(torch.equal(a, b) for a, b in zip(left, right, strict=True)))
                    self.assertTrue(torch.equal(ls, rs))

    def test_empirical_modes_preserve_aliases_counts_origins_and_abstention(self):
        for mode in ('prefix', 'local', 'contact'):
            source = DomainMemory(mode).fit(measured(3))
            source.table.update(DomainMemory(mode).fit(measured(6)).table)
            source.origin_digest = 'b' * 64
            before = deepcopy(source.table), source.digest()
            controls = (mode, 'first_contact') if mode == 'contact' else (mode,)
            for control in controls:
                path = self.path.with_name(control + '.json')
                saved = checkpoint.save_checkpoint(path, memory=source, control=control, provenance=COUNTS)
                restored = checkpoint.load_checkpoint(path, saved['sha256'])
                memory = restored['memory']
                self.assertEqual(restored['control'], control)
                self.assertEqual(checkpoint.predictor_spec(memory=memory)['control'], control)
                self.assertEqual(memory.table, before[0])
                self.assertEqual(memory.digest(), before[1])
                self.assertEqual(memory.origin_digest, 'b' * 64)
                for entities in (3, 6):
                    pre, action = (0,) * entities, (0, entities - 1, entities - 1, -1)
                    self.assertEqual(source.predict(pre, action, ()), memory.predict(pre, action, ()))
                    self.assertIsNone(memory.predict(pre, (0, entities - 1, 0, -1), ()))
                self.assertIsNone(memory.predict((0,) * 4, (2, -1, -1, -1), ()))
            self.assertEqual((source.table, source.digest()), before)

    def test_bound_empirical_policy_cannot_be_overridden_during_save(self):
        source = DomainMemory('contact').fit(measured(3))
        source.control_name = 'first_contact'
        saved = checkpoint.save_checkpoint(self.path, memory=source, provenance=COUNTS)
        restored = checkpoint.load_checkpoint(self.path, saved['sha256'])
        self.assertEqual(restored['control'], 'first_contact')
        self.assertEqual(restored['memory'].control_name, 'first_contact')
        with self.assertRaises(ValueError):
            checkpoint.save_checkpoint(self.path.with_name('wrong.json'), memory=source,
                                       control='contact', provenance=COUNTS)
        self.assertFalse(self.path.with_name('wrong.json').exists())

    def test_no_change_is_explicitly_stateless_and_cannot_resume_an_episode(self):
        provenance = {'training_input_sha256': None, 'objective': 'no_change', 'completed_updates': 0}
        saved = checkpoint.save_checkpoint(self.path, control='no_change', provenance=provenance)
        loaded = checkpoint.load_checkpoint(self.path, saved['sha256'])
        self.assertIsNone(loaded['model']); self.assertIsNone(loaded['memory'])
        self.assertEqual(loaded['control'], 'no_change')
        self.assertEqual(loaded['metadata']['scope'], checkpoint.SCOPE)
        document = json.loads(self.path.read_text())
        for name in ('optimizer', 'live_session', 'pending_forecast'):
            altered = deepcopy(document); altered[name] = {}
            with self.assertRaises(ValueError): checkpoint.load_checkpoint(*self.write_variant(altered))

    def test_fitted_legacy_origin_is_separate_from_current_state_and_metadata_detached(self):
        source = DomainKernel.from_legacy(JointKernel())
        original_adaptation = deepcopy(source.domain_adaptation)
        with torch.no_grad(): next(source.parameters()).add_(.125)
        current = fingerprint(source.state_dict())
        provenance = {'training_input_sha256': 'c' * 64, 'objective': 'observed_joint_nll',
                      'completed_updates': 1, 'details': {'scope': 'synthetic parameter-change witness'}}
        saved = checkpoint.save_checkpoint(self.path, model=source, provenance=provenance)
        self.assertEqual(source.domain_adaptation, original_adaptation)
        provenance['details']['scope'] = 'caller mutation'
        loaded = checkpoint.load_checkpoint(self.path, saved['sha256'])
        model, meta = loaded['model'], loaded['metadata']
        self.assertEqual(meta['origin']['source_full_state_sha256'], original_adaptation['source_full_state_sha256'])
        self.assertNotEqual(meta['origin']['source_learned_parameters_sha256'], current)
        self.assertEqual(model.domain_adaptation['active_learned_parameters_sha256'], current)
        self.assertNotIn('extended_domain_training', model.domain_adaptation)
        self.assertEqual(model.checkpoint_metadata['provenance']['details']['scope'], 'synthetic parameter-change witness')
        meta['provenance']['details']['scope'] = 'response mutation'
        self.assertEqual(model.checkpoint_metadata['provenance']['details']['scope'], 'synthetic parameter-change witness')
        self.assertEqual(model.training_provenance['details']['scope'], 'synthetic parameter-change witness')
        self.assertEqual(model.training_provenance, model.domain_adaptation['training_provenance'])
        second = checkpoint.save_checkpoint(self.path.with_name('second.json'), model=model,
                                            provenance=model.checkpoint_metadata['provenance'])
        self.assertEqual(second['metadata']['origin'], saved['metadata']['origin'])

    def test_expected_hash_is_mandatory_and_local_source_must_match(self):
        saved = checkpoint.save_checkpoint(self.path, model=DomainKernel(), provenance=UNTRAINED)
        for expected in (None, '', 'A' * 64, '0' * 64, True):
            with self.assertRaises(ValueError): checkpoint.load_checkpoint(self.path, expected)
        with self.assertRaises(TypeError): checkpoint.load_checkpoint(self.path)
        sources = deepcopy(saved['metadata']['predictor']['source_sha256'])
        sources['domain_kernel.py'] = '0' * 64
        with patch.object(checkpoint, '_sources', return_value=sources):
            with self.assertRaises(ValueError): checkpoint.load_checkpoint(self.path, saved['sha256'])
        with patch.object(checkpoint, 'MAX_BYTES', 10):
            with self.assertRaises(ValueError): checkpoint.load_checkpoint(self.path, saved['sha256'])

    def test_schema_configuration_geometry_and_tensor_types_fail_closed(self):
        checkpoint.save_checkpoint(self.path, model=DomainFlatGRU(), provenance=UNTRAINED)
        base = json.loads(self.path.read_text())
        variations = []
        for target, value in [('kind', '__import__'), ('configuration', {'hidden': True, 'persistence': False}),
                              ('control', 'flat')]:
            doc = deepcopy(base); doc['predictor'][target] = value; variations.append(doc)
        for field in ('scope', 'state'):
            doc = deepcopy(base); doc[field]['unexpected'] = None; variations.append(doc)
        doc = deepcopy(base); doc['scope']['fresh_episodes_only'] = 1; variations.append(doc)
        doc = deepcopy(base); doc['predictor']['domain']['self_contact'] = 1; variations.append(doc)
        doc = deepcopy(base); doc['predictor']['supplied_biases']['existence_mask'] = 1; variations.append(doc)
        doc = deepcopy(base); doc['state_sha256'] = '0' * 64; variations.append(doc)
        key = next(iter(base['state']))
        for target, value in [('shape', [1]), ('dtype', 'torch.float32'), ('values', [False])]:
            doc = deepcopy(base); doc['state'][key][target] = value; variations.append(doc)
        doc = deepcopy(base); doc['state'][key]['values'][0] = False; variations.append(doc)
        for index, document in enumerate(variations):
            with self.subTest(index=index), self.assertRaises(ValueError):
                checkpoint.load_checkpoint(*self.write_variant(document))

    def test_duplicate_json_fields_and_nonfinite_values_are_rejected(self):
        saved = checkpoint.save_checkpoint(self.path, model=DomainKernel(), provenance=UNTRAINED)
        raw = self.path.read_bytes().decode()
        malformed = ['{"version":"duplicate",' + raw[1:], raw.replace('"completed_updates":0', '"completed_updates":NaN')]
        for number, value in enumerate(malformed):
            path = self.path.with_name(f'bad-{number}.json'); path.write_text(value)
            with self.assertRaises(ValueError): checkpoint.load_checkpoint(path, sha256(path.read_bytes()).hexdigest())
        self.assertEqual(saved['sha256'], sha256(self.path.read_bytes()).hexdigest())

    def test_provenance_matches_predictor_kind_and_never_claims_authentication(self):
        variants = [{}, {**UNTRAINED, 'completed_updates': True}, {**UNTRAINED, 'objective': 'full_truth'},
                    {**UNTRAINED, 'objective': 'observed_joint_nll'}, {**UNTRAINED, 'completed_updates': 1},
                    {**UNTRAINED, 'completed_updates': -1}, {**UNTRAINED, 'extra': float('inf')},
                    {**UNTRAINED, 'extra': object()}, {**UNTRAINED, 'training_input_sha256': 'A' * 64}, COUNTS]
        for provenance in variants:
            with self.subTest(provenance=str(provenance)), self.assertRaises(ValueError):
                checkpoint.save_checkpoint(self.path, model=DomainKernel(), provenance=provenance)
            self.assertFalse(self.path.exists())
        saved = checkpoint.save_checkpoint(self.path, model=DomainKernel(), provenance=UNTRAINED)
        self.assertFalse(saved['metadata']['scope']['provenance_authenticated'])

    def test_bad_empirical_counts_keys_and_duplicate_contexts_are_rejected(self):
        memory = DomainMemory('contact').fit(measured(6))
        checkpoint.save_checkpoint(self.path, memory=memory, provenance=COUNTS)
        base = json.loads(self.path.read_text())
        variants = []
        for value in (True, 0, -1, 1.5):
            doc = deepcopy(base); doc['state']['rows'][0][1][0][1] = value; variants.append(doc)
        doc = deepcopy(base); doc['state']['rows'].append(deepcopy(doc['state']['rows'][0])); variants.append(doc)
        doc = deepcopy(base); doc['state']['rows'][0][1].append(deepcopy(doc['state']['rows'][0][1][0])); variants.append(doc)
        doc = deepcopy(base); doc['state']['rows'][0][0][0] = 7; variants.append(doc)
        doc = deepcopy(base); doc['state']['rows'][0][0][3] = [1, 1]; variants.append(doc)
        doc = deepcopy(base); doc['state']['rows'][0][1][0][0][0] = True; variants.append(doc)
        doc = deepcopy(base); doc['state']['origin_table_sha256'] = 'bad'; variants.append(doc)
        for number, document in enumerate(variants):
            with self.subTest(number=number), self.assertRaises(ValueError):
                checkpoint.load_checkpoint(*self.write_variant(document))

    def test_exclusive_creation_and_validation_preserve_existing_state(self):
        self.path.write_bytes(b'unchanged original')
        with self.assertRaises(FileExistsError):
            checkpoint.save_checkpoint(self.path, model=DomainKernel(), provenance=UNTRAINED)
        self.assertEqual(self.path.read_bytes(), b'unchanged original')
        class Unsupported(DomainKernel): pass
        for source in (Unsupported(), JointKernel(), DomainKernel().float()):
            with self.assertRaises(ValueError):
                checkpoint.save_checkpoint(self.path.with_name('invalid.json'), model=source, provenance=UNTRAINED)
        source = DomainKernel(); source.pair[1] = torch.nn.ReLU()
        with self.assertRaises(ValueError):
            checkpoint.save_checkpoint(self.path.with_name('invalid.json'), model=source, provenance=UNTRAINED)
        source = DomainKernel(); source.supports_self_contact = False
        with self.assertRaises(ValueError):
            checkpoint.save_checkpoint(self.path.with_name('invalid.json'), model=source, provenance=UNTRAINED)
        self.assertFalse(self.path.with_name('invalid.json').exists())


if __name__ == '__main__':
    unittest.main()
