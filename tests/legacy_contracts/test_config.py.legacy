"""Test configurable thresholds (weakness #4 fix)."""
import unittest
from cemm.config import Config

class TestConfig(unittest.TestCase):
    def test_defaults_match_v4(self):
        c = Config()
        self.assertEqual(c.settler_posterior_threshold, 0.48)
        self.assertEqual(c.settler_margin_threshold, 0.06)
        self.assertEqual(c.settler_rounds, 4)
        self.assertEqual(c.rule_evidence_threshold, 2)
        self.assertEqual(c.salience_decay, 0.55)
        self.assertEqual(c.workspace_top_k, 24)
        self.assertEqual(c.inference_max_rounds, 8)
        self.assertEqual(c.inference_max_facts, 200)
        self.assertEqual(c.inference_timeout_seconds, 30.0)
        self.assertEqual(c.model_cache_limit, 8)
        self.assertEqual(c.structured_net_seed, 41)
        self.assertEqual(c.rule_net_seed, 73)

    def test_custom_overrides(self):
        c = Config(workspace_top_k=32, rule_evidence_threshold=3)
        self.assertEqual(c.workspace_top_k, 32)
        self.assertEqual(c.rule_evidence_threshold, 3)
        self.assertEqual(c.settler_posterior_threshold, 0.48)

    def test_autonomous_acquisition_default_true(self):
        c = Config()
        self.assertTrue(c.autonomous_acquisition)

if __name__ == "__main__":
    unittest.main()
