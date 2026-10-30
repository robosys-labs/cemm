"""Real artifact export and existing acceptance/learning boundaries, without fitting."""
from hashlib import sha256
import json
import lzma
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from experiments.predictive_nucleus import acceptance_contract as contract
from experiments.predictive_nucleus.active_checkpoint import save_checkpoint
from experiments.predictive_nucleus.observed_io import load_batches
from experiments.predictive_nucleus import prospective_data as data


class ProspectiveIntegrationTests(unittest.TestCase):
    def test_export_is_byte_reproducible_and_joins_existing_contract_without_fake_weights(self):
        config = data.read_config()
        config['entity_counts'] = [3, 4]
        config['draws_per_family_entity'] = dict.fromkeys(data.SPLITS, 1)
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            left, right = root / 'left', root / 'right'
            first, second = data.write_assets(left, config), data.write_assets(right, config)
            self.assertEqual(first['manifest_sha256'], second['manifest_sha256'])
            self.assertEqual(first['artifact_count'], 11)
            for path in left.iterdir(): self.assertEqual(path.read_bytes(), (right / path.name).read_bytes())
            manifest = contract.load_json(left / 'manifest.json', first['manifest_sha256'])
            self.assertFalse(manifest['acceptance_plan_created'])
            archive = json.loads(lzma.decompress((left / 'asset-bundle.json.xz').read_bytes()))
            self.assertEqual(archive['bundle']['config'], config)
            self.assertFalse(archive['audit']['learned_model_evaluated'])
            for name, row in manifest['files'].items():
                raw = (left / name).read_bytes()
                self.assertEqual(sha256(raw).hexdigest(), row['sha256'])
                self.assertEqual(len(raw), row['bytes'])
                value = json.loads(lzma.decompress(raw) if name.endswith('.xz') else raw)
                self.assertEqual(contract.digest(value), row['content_sha256'])
            for split in data.SPLITS:
                name = split + '.inputs.json'
                batches = load_batches(left / name, manifest['files'][name]['sha256'])
                delivered = archive['bundle']['splits'][split]['inputs']['episodes']
                self.assertEqual(sum(len(b.episode_ids) for b in batches), len(delivered))
                self.assertEqual(sum(b.actions.shape[0] * b.actions.shape[1] for b in batches),
                                 sum(len(c['actions']) for c in delivered))

            # A synthetic compatibility join uses a real native control artifact.
            # The exporter itself never fabricates or emits an acceptance plan.
            saved = save_checkpoint(root / 'no-change.json', control='no_change',
                                    provenance={'objective': 'no_change', 'completed_updates': 0,
                                                'training_input_sha256': None})
            bundle = archive['bundle']; evaluation = bundle['splits']['evaluation']
            observed, oracle = evaluation['inputs'], evaluation['oracle']
            case_fields = ('episode', 'family', 'partition', 'lineage', 'pair_id', 'direction')
            plan = {'version': 'active-acceptance-plan-v1', 'contract_sha256': contract.contract_digest(),
                    'study_id': 'synthetic-export-compatibility', 'scope': 'SYNTHETIC_INVARIANTS',
                    'input_sha256': contract.digest(observed), 'oracle_sha256': contract.digest(oracle),
                    'oracle_source_sha256': oracle['source_sha256'],
                    'information_law_sha256': oracle['information_law_sha256'],
                    'software_sha256': contract.software_sources(), 'model_seeds': [7],
                    'participants': {'no_change': {'7': saved['sha256']}}, 'reference_participant': 'no_change',
                    'cases': [{key: row[key] for key in case_fields} for row in evaluation['cases']],
                    'split_lineage': {s: sorted({row['lineage'] for row in bundle['splits'][s]['cases']}) for s in data.SPLITS},
                    'development_families': config['development_families']}
            joined = contract.validate_bundle(plan, observed, oracle, [])
            self.assertEqual(len(joined['rows']), sum(len(c['actions']) for c in observed['episodes']))
            self.assertTrue(all(row['status'] == 'UNPRODUCED' for row in joined['rows']))
            self.assertFalse(joined['metadata']['scientific_admission'])
            with self.assertRaises(FileExistsError): data.write_assets(left, config)
            self.assertEqual(sha256((left / 'manifest.json').read_bytes()).hexdigest(), first['manifest_sha256'])

    def test_actual_cli_exports_default_inventory_and_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as folder:
            destination = Path(folder) / 'assets'
            command = [sys.executable, '-m', 'experiments.predictive_nucleus.prospective_data',
                       '--output', str(destination)]
            completed = subprocess.run(command, capture_output=True, text=True, timeout=90)
            self.assertEqual(completed.returncode, 0, completed.stderr)
            result = json.loads(completed.stdout)
            manifest = contract.load_json(destination / 'manifest.json', result['manifest_sha256'])
            audit = contract.load_json(destination / 'audit.json', manifest['files']['audit.json']['sha256'])
            self.assertEqual(audit['aggregate']['counts']['physical_draws'], 328)
            self.assertEqual(audit['aggregate']['counts']['episodes'], 624)
            self.assertEqual(audit['aggregate']['resources']['episodes_with_dense_bound_exceedance'], 0)
            self.assertEqual(result['gate_g1'], 'NOT_ADMITTED')
            before = (destination / 'manifest.json').read_bytes()
            repeated = subprocess.run(command, capture_output=True, text=True, timeout=30)
            self.assertNotEqual(repeated.returncode, 0)
            self.assertEqual((destination / 'manifest.json').read_bytes(), before)


if __name__ == '__main__':
    unittest.main()
