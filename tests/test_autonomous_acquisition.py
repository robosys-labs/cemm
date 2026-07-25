"""Tests for unknown-form handling after Phase 2 (pure parsing).

Phase 2 of the v1-fixes plan removed autonomous acquisition from the
interpreter. Unknown forms now produce typed frontiers without durable
side effects. Explicit acquisition remains available via the `acquire`
command and reviewed workflow.
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


class UnknownFormTests(unittest.TestCase):
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

    def test_unknown_form_returns_frontier(self):
        """Unknown forms produce a frontier, not a silent acquisition."""
        td, s, rt = make(Config(autonomous_acquisition=True))
        try:
            r = rt.process("Zorblax is energy.", learn=True)
            self.assertEqual(r["status"], "frontier")
        finally:
            s.db.close()
            td.cleanup()

    def test_unknown_form_no_durable_side_effects(self):
        """Parsing unknown forms must not create atoms, designations, or generations."""
        td, s, rt = make(Config(autonomous_acquisition=True))
        try:
            h0 = s.authority_hash(s.generation)
            g0 = s.generation
            atom_count_before = s.db.execute("SELECT count(*) FROM atoms").fetchone()[0]
            des_count_before = s.db.execute("SELECT count(*) FROM designation_index").fetchone()[0]

            rt.process("Zorblax is energy.", learn=True)

            atom_count_after = s.db.execute("SELECT count(*) FROM atoms").fetchone()[0]
            des_count_after = s.db.execute("SELECT count(*) FROM designation_index").fetchone()[0]
            self.assertEqual(atom_count_before, atom_count_after,
                             "Unknown forms must not create atoms during parsing")
            self.assertEqual(des_count_before, des_count_after,
                             "Unknown forms must not create designations during parsing")
            self.assertEqual(h0, s.authority_hash(s.generation),
                             "Authority hash must not change from unknown form parsing")
            self.assertEqual(g0, s.generation,
                             "Generation must not advance from unknown form parsing")
        finally:
            s.db.close()
            td.cleanup()

    def test_disabled_autonomous_acquisition_also_frontiers(self):
        """With autonomous acquisition disabled, unknown forms still frontier."""
        td, s, rt = make(Config(autonomous_acquisition=False))
        try:
            r = rt.process("Zorblax is energy.", learn=True)
            self.assertEqual(r["status"], "frontier")
        finally:
            s.db.close()
            td.cleanup()


if __name__ == "__main__":
    unittest.main()
