"""Test core model types."""
import unittest
from cemm.model import Fact, AmbiguousReferent, stable, canonical, norm_text, toks, surface, lit, isvar, isexist

class TestModel(unittest.TestCase):
    def test_fact_signature_is_deterministic(self):
        f1 = Fact(ref="r1", operator="op:type", args={"role:class": "concept:doctor", "role:instance": "entity:ada"})
        f2 = Fact(ref="r2", operator="op:type", args={"role:instance": "entity:ada", "role:class": "concept:doctor"})
        self.assertEqual(f1.signature(), f2.signature())

    def test_stable_is_deterministic(self):
        self.assertEqual(stable("test", "a", "b"), stable("test", "a", "b"))

    def test_norm_text_casefolds_unicode(self):
        # v4 norm_text does NFKC + casefold (no accent stripping);
        # uppercase accented should equal lowercase accented.
        self.assertEqual(norm_text("ÉVIDENCE"), norm_text("évidence"))

    def test_surface_capitalizes_first(self):
        self.assertTrue(surface(["hello", "."]).startswith("H"))

    def test_isvar_and_isexist(self):
        self.assertTrue(isvar("?v0"))
        self.assertTrue(isexist("!e0"))
        self.assertFalse(isvar("atom:abc"))

    def test_lit_returns_literal_dict(self):
        result = lit("hello", "text")
        self.assertEqual(result, {"literal": {"type": "text", "value": "hello"}})

if __name__ == "__main__":
    unittest.main()
