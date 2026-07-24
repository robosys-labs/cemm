"""Test inference timeout (weakness #6 fix).

Verifies that the threading.Timer-based timeout in cemm/inference.py
raises InferenceTimeoutError when a rule chain would otherwise run forever.
"""
import os
import tempfile
import time
import unittest

from cemm.config import Config
from cemm.inference import Inference, InferenceTimeoutError
from cemm.model import canonical
from cemm.store import Store


class TestTimeout(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False)
        self.tmp.close()
        self.store = Store(self.tmp.name)
        g = self.store.generation
        # Minimal schema: op:relation operator + its roles + a loop relation type + a seed atom.
        for ref, kind in [
            ("op:relation", "operator"),
            ("role:subject", "role"),
            ("role:relation", "role"),
            ("role:object", "role"),
            ("rel:loop", "relation_type"),
            ("atom:test", "entity"),
        ]:
            self.store.exact(
                "atoms",
                ["ref", "kind", "metadata", "generation", "authority_scope"],
                [ref, kind, "{}", g, "authority"],
                ["ref"],
                {"generation"},
            )
        for op, role, required, fk in [
            ("op:relation", "role:subject", 1, "atom"),
            ("op:relation", "role:relation", 1, "relation_type"),
            ("op:relation", "role:object", 1, "atom"),
        ]:
            self.store.exact(
                "operator_roles",
                ["operator_ref", "role_ref", "required", "cardinality", "filler_kind"],
                [op, role, required, "one", fk],
                ["operator_ref", "role_ref"],
            )
        self.store.db.commit()

    def tearDown(self):
        self.store.db.close()
        os.unlink(self.tmp.name)

    def _seed_fact(self):
        g = self.store.generation
        obs = self.store.add_observation("seed", {}, "und", "seed", g)
        self.store.insert_app(
            "op:relation",
            {
                "role:subject": "atom:test",
                "role:relation": "rel:loop",
                "role:object": "atom:test",
            },
            g,
            obs,
            "support",
            1.0,
            "reviewed",
        )
        self.store.db.commit()

    def _chain_rule(self):
        """A rule that generates an infinite chain of new facts.

        antecedent: relation(?v0, rel:loop, ?v1)
        consequent: relation(?v1, rel:loop, !e0)

        Each round binds ?v1 to the previous object and produces a fresh
        existential witness !e0, so every round adds at least one new fact
        and the closure never terminates naturally.
        """
        g = self.store.generation
        ant = canonical(
            [
                {
                    "operator": "op:relation",
                    "args": {
                        "role:subject": "?v0",
                        "role:relation": "rel:loop",
                        "role:object": "?v1",
                    },
                }
            ]
        )
        con = canonical(
            [
                {
                    "operator": "op:relation",
                    "args": {
                        "role:subject": "?v1",
                        "role:relation": "rel:loop",
                        "role:object": "!e0",
                    },
                }
            ]
        )
        self.store.exact(
            "rules",
            [
                "rule_ref",
                "rule_kind",
                "antecedent",
                "consequent",
                "confidence",
                "authority_status",
                "generation",
            ],
            ["rule:loop-chain", "entailment", ant, con, 1.0, "reviewed", g],
            ["rule_ref"],
            {"generation"},
        )
        self.store.db.commit()

    def test_timeout_raises_on_infinite_chain(self):
        """An infinite rule chain must raise InferenceTimeoutError within the timeout."""
        self._chain_rule()
        self._seed_fact()

        config = Config(inference_timeout_seconds=0.5, inference_max_rounds=100000)
        inf = Inference(self.store, config)
        start = time.time()
        with self.assertRaises(InferenceTimeoutError):
            inf.closure()
        elapsed = time.time() - start
        self.assertLess(elapsed, 2.0, f"Timeout took too long: {elapsed}s")

    def test_normal_closure_completes_without_timeout(self):
        """With no pathological rule, closure completes well under the timeout."""
        self._seed_fact()
        config = Config(inference_timeout_seconds=30.0, inference_max_rounds=8)
        inf = Inference(self.store, config)
        start = time.time()
        facts, byref = inf.closure()
        elapsed = time.time() - start
        self.assertFalse(inf.incomplete, "closure should complete without incomplete flag")
        self.assertGreaterEqual(len(facts), 1)
        self.assertLess(elapsed, 5.0, f"Normal closure took too long: {elapsed}s")


if __name__ == "__main__":
    unittest.main()
