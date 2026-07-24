"""Tests for autonomous unknown-form discovery (weakness #11 fix).

v4 required a reviewer to supply mention-kind anchors for unknown vocabulary.
v1 infers the semantic kind autonomously, eliminating the manual anchor
requirement while preserving the exact semantic authority boundary.
"""
from __future__ import annotations
import sys, tempfile
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import cemm.codec as _codec
import cemm.interpreter as _interp
from cemm.store import Store
from cemm.runtime import Runtime
from cemm.config import Config

BASE = ROOT / "cemm/data/base.json"
FAMILY = ROOT / "cemm/data/family_knowledge.json"
EN = ROOT / "cemm/language_packs/en.json"


def make(config=None):
    td = tempfile.TemporaryDirectory()
    s = Store(Path(td.name) / "autonomous.sqlite")
    s.import_data(BASE)
    s.import_data(FAMILY)
    rt = Runtime(s, EN, config or Config())
    return td, s, rt


class AutonomousAcquisitionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        _codec.CACHE.clear()
        _interp.MODEL_CACHE.clear()
        td, s, rt = make()
        try:
            rt.process("What is evidence?")
        finally:
            s.db.close()
            td.cleanup()

    def test_autonomous_acquisition_not_frontier(self):
        """Unknown forms are acquired autonomously; result is not a frontier."""
        td, s, rt = make(Config(autonomous_acquisition=True))
        try:
            h0 = s.authority_hash(s.generation)
            r = rt.process("Zorblax is energy.", learn=True)
            self.assertNotEqual(r["status"], "frontier")
            # Designation for Zorblax exists in the database
            des = s.db.execute(
                "SELECT 1 FROM designation_index "
                "WHERE lower(surface) = lower('Zorblax') "
                "AND language IN ('en', 'und') LIMIT 1"
            ).fetchone()
            self.assertIsNotNone(des)
            # Acquired atom is world-scope (never authority)
            ref = s.resolve_label("Zorblax", "en")
            self.assertIsNotNone(ref)
            atom = s.atom(ref)
            self.assertEqual(atom["authority_scope"], "world")
            # Authority hash did not change
            self.assertEqual(h0, s.authority_hash(s.generation))
        finally:
            s.db.close()
            td.cleanup()

    def test_autonomous_disabled_returns_frontier(self):
        """With autonomous acquisition disabled, unknown forms still frontier."""
        td, s, rt = make(Config(autonomous_acquisition=False))
        try:
            r = rt.process("Zorblax is energy.", learn=True)
            self.assertEqual(r["status"], "frontier")
        finally:
            s.db.close()
            td.cleanup()

    def test_autonomous_acquired_atom_kind_inferred(self):
        """Acquired atoms get a kind via the KIND_INFERENCE table or default concept."""
        td, s, rt = make(Config(autonomous_acquisition=True))
        try:
            rt.process("Zorblax is energy.", learn=True)
            ref = s.resolve_label("Zorblax", "en")
            self.assertIsNotNone(ref)
            atom = s.atom(ref)
            # Kind should be entity (inferred from op:type role:instance) or concept (default)
            self.assertIn(atom["kind"], ("entity", "concept"))
        finally:
            s.db.close()
            td.cleanup()


if __name__ == "__main__":
    unittest.main()
