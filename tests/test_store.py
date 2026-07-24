"""Test Store: DDL, import, authority_hash, rule_candidates."""
import unittest, tempfile, os
from cemm.store import Store

class TestStore(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False)
        self.tmp.close()
        self.store = Store(self.tmp.name)

    def tearDown(self):
        self.store.db.close()
        os.unlink(self.tmp.name)

    def test_store_initializes_with_generation_1(self):
        self.assertEqual(self.store.generation, 1)

    def test_authority_hash_excludes_world_atoms(self):
        h1 = self.store.authority_hash()
        self.store.exact("atoms", ["ref","kind","metadata","generation","authority_scope"],
                         ["atom:test","entity","{}",self.store.generation,"world"],
                         ["ref"], {"generation"})
        self.store.db.commit()
        h2 = self.store.authority_hash()
        self.assertEqual(h1, h2)

    def test_rule_candidate_evidence_increments(self):
        g = self.store.generation
        ref = "cand:test:abc"
        self.store.add_rule_candidate(ref, "definition", '{"a":1}', '{"b":2}', 0.9, g)
        self.store.add_rule_candidate(ref, "definition", '{"a":1}', '{"b":2}', 0.9, g)
        row = self.store.db.execute("SELECT evidence_count FROM rule_candidates WHERE candidate_ref=?", (ref,)).fetchone()
        self.assertEqual(row["evidence_count"], 2)

    def test_import_data_loads_base_json(self):
        self.store.import_data("reference/mvp_v4/knowledge/base.json")
        # Should have operator_roles populated
        count = self.store.db.execute("SELECT count(*) FROM operator_roles").fetchone()[0]
        self.assertGreater(count, 0)

if __name__ == "__main__":
    unittest.main()
