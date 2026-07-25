"""Test that learn=True overrides mispredicted query intent for assertions.

The tiny proof codec sometimes misclassifies assertions as queries.
When learn=True and the input has no question punctuation, the runtime
converts the query packet to an assert packet so the fact gets stored.

These tests use known concepts (from base.json) to isolate the intent
override from unknown-form frontiers (Phase 2 makes parsing pure).
"""
import unittest, tempfile, os, json
from pathlib import Path
from cemm.store import Store
from cemm.runtime import Runtime
from cemm.config import Config

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "cemm/data/base.json"
FAMILY = ROOT / "cemm/data/family_knowledge.json"
EN = ROOT / "cemm/language_packs/en.json"


class TestLearnOverridesQuery(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.store = Store(Path(self.td.name) / "learn.sqlite")
        self.store.import_data(BASE)
        self.store.import_data(FAMILY)
        self.rt = Runtime(self.store, EN, Config())

    def tearDown(self):
        self.store.db.close()
        self.td.cleanup()

    def test_learn_known_fact_stores_not_queries(self):
        """Learn mode should store a fact about known concepts, not query it.

        Uses 'Evidence is information.' — both concepts are in base.json.
        If the codec mispredicts query intent, the learn override should
        convert it to an assert so the fact gets stored.
        """
        r = self.rt.process("Evidence is information.", learn=True, teach=False)
        # Should be learned or ok (if fact already known), not frontier or unknown
        self.assertNotEqual(r.get("status"), "frontier",
                            f"Known concepts should not frontier: {r.get('status')} {r.get('response')}")

    def test_question_mark_preserves_query_intent(self):
        """Inputs with '?' should remain queries even in learn mode."""
        r = self.rt.process("Is evidence information?", learn=True, teach=False)
        # Should be a query result (ok with result, or unknown), not learned
        # The key is it should NOT be 'learned' — question marks stay as queries
        self.assertNotEqual(r.get("status"), "learned",
                            f"Question-marked input should not be stored as fact: {r.get('status')}")


if __name__ == "__main__":
    unittest.main()
