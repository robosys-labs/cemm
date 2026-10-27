"""Independent public protocol preregistration, not a G1 acceptance test."""
from pathlib import Path
import tempfile
import unittest

from experiments.predictive_nucleus.stress_protocol import HERE, verify


class ProtocolTests(unittest.TestCase):
    def test_frozen_manifest_and_disjoint_source_seeds(self):
        d = verify()
        self.assertEqual(d["schema_version"], 3)
        self.assertEqual(d["decision"], "KEEP_DIAGNOSTIC_G1_UNADMITTED")
        self.assertTrue(d["frozen_g0_and_g1c_manifests_must_remain_unchanged"])

    def test_mutation_of_manifest_fails_lock(self):
        raw = (HERE / "stress_protocol_v3.json").read_text()
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "modified.json"
            out.write_text(raw.replace("PUBLIC_DEVELOPMENT_ONLY", "FALSE_CHALLENGE_OPENED"))
            with self.assertRaisesRegex(ValueError, "lock"):
                verify(out)


if __name__ == "__main__":
    unittest.main()
