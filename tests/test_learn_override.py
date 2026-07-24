"""Test that learn=True overrides predicted query intent and stores the fact.

Root cause: codec misclassifies 'A cat is an animal.' as query (score -0.22)
instead of assert (score -1.62). When learn=True, the runtime should treat
the packet as an assertion, not a query.
"""
import unittest, tempfile, os, json
from cemm.store import Store
from cemm.runtime import Runtime
from cemm.config import Config


class TestLearnOverridesQuery(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False)
        self.tmp.close()
        self.store = Store(self.tmp.name)
        self.store.import_data("cemm/data/base.json")
        self.store.import_data("cemm/data/family_knowledge.json")
        self.rt = Runtime(self.store, "cemm/language_packs/en.json", Config())

    def tearDown(self):
        self.store.db.close()
        if os.path.exists(self.tmp.name):
            os.unlink(self.tmp.name)

    def test_learn_cat_is_animal_stores_fact(self):
        """Learn mode should store 'A cat is an animal.' as a fact, not query it."""
        r = self.rt.process("A cat is an animal.", learn=True, teach=False)
        self.assertEqual(r.get("status"), "learned",
                         f"Learn should return 'learned', got '{r.get('status')}' with response '{r.get('response')}'")

    def test_ask_after_learn_returns_fact(self):
        """After learning 'A cat is an animal.', asking 'What is a cat?' should return the fact."""
        self.rt.process("A cat is an animal.", learn=True, teach=False)
        r = self.rt.process("What is a cat?", learn=False, teach=False)
        self.assertNotEqual(r.get("status"), "unknown",
                            f"Should find the learned fact, got status='{r.get('status')}' response='{r.get('response')}'")
        # Response should mention cat and animal
        resp = r.get("response", "").lower()
        self.assertTrue("cat" in resp or "animal" in resp,
                        f"Response should mention cat or animal, got: {resp}")


if __name__ == "__main__":
    unittest.main()
