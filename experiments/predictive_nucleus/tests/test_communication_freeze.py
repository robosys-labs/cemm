"""Lifecycle invariants on temporary synthetic outputs, with publication mocked."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from experiments.predictive_nucleus import communication_freeze as f


class CommunicationFreezeTests(unittest.TestCase):
    def test_partial_failure_remains_and_blocks_second_attempt(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(f, 'RESULTS', Path(tmp)), \
                patch.object(f, '_preflight', return_value='synthetic'):
            with self.assertRaisesRegex(RuntimeError, 'interrupted'):
                with f.published_stage('fit') as dest:
                    f.write_json(dest / 'partial.json', {'example': 1})
                    raise RuntimeError('interrupted')
            self.assertEqual(f.io._read(dest / 'receipt.json')['status'], 'failed')
            self.assertTrue((dest / 'partial.json').is_file())
            with self.assertRaises(FileExistsError):
                with f.published_stage('fit'):
                    self.fail('stage reopened')

    def test_completed_stage_binds_actual_payload_and_input_commit(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(f, 'RESULTS', Path(tmp)), \
                patch.object(f, '_preflight', return_value='synthetic'):
            with f.published_stage('collect') as dest:
                f.write_json(dest / 'example.json.xz', [1])
            receipt = f.io._read(dest / 'receipt.json')
            self.assertEqual(receipt['outputs'], {'example.json.xz': f.io._hash(dest / 'example.json.xz')})
            self.assertEqual(f.io._read(dest / 'attempt.json')['input_head'], 'synthetic')
            self.assertEqual(receipt['status'], 'complete')

    def test_preflight_failure_creates_no_attempt(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(f, 'RESULTS', Path(tmp)), \
                patch.object(f, '_preflight', side_effect=ValueError('unpublished')):
            with self.assertRaisesRegex(ValueError, 'unpublished'):
                with f.published_stage('fit'):
                    self.fail('unpublished input admitted')
            self.assertEqual(list(Path(tmp).iterdir()), [])
