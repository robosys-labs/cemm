from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from cemm.context import ParticipantFrame
from cemm.interpreter import Delexer
from cemm.model import lit
from cemm.runtime import Runtime
from cemm.state import StateProjector
from cemm.store import Store

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "cemm/data/base.json"
EN = ROOT / "cemm/language_packs/en.json"


class Phase1To4Tests(unittest.TestCase):
    def make_store(self):
        td = tempfile.TemporaryDirectory()
        store = Store(Path(td.name) / "x.sqlite")
        store.import_data(BASE)
        return td, store

    def import_fixture(self, store: Store, payload: dict) -> None:
        path = Path(tempfile.mkdtemp()) / "fixture.json"
        path.write_text(json.dumps(payload), encoding="utf-8")
        store.import_data(path)

    def test_participant_requirements_resolve_from_frame_not_lexical_identity(self):
        td, s = self.make_store()
        try:
            inbound = ParticipantFrame(
                self_ref="participant:system",
                speaker_ref="participant:user",
                addressee_ref="participant:system",
            )
            _, ph_in, _ = Delexer(s, "en").run("I asked you.", inbound)
            self.assertIn("participant:user", ph_in.values())
            self.assertIn("participant:system", ph_in.values())

            outbound = ParticipantFrame(
                self_ref="participant:system",
                speaker_ref="participant:system",
                addressee_ref="participant:user",
            )
            _, ph_out, _ = Delexer(s, "en").run("I asked you.", outbound)
            self.assertIn("participant:system", ph_out.values())
            self.assertIn("participant:user", ph_out.values())

            rows = s.db.execute(
                "SELECT surface,bound_ref,features FROM reference_forms "
                "WHERE language='en' AND lower(surface) IN ('i','me','my','you','your')"
            ).fetchall()
            self.assertTrue(rows)
            self.assertTrue(all(not r["bound_ref"] for r in rows))
            self.assertTrue(all(json.loads(r["features"]).get("participant_role") for r in rows))
        finally:
            s.db.close()
            td.cleanup()

    def test_unknown_parse_and_read_only_query_have_no_durable_side_effect(self):
        td, s = self.make_store()
        try:
            rt = Runtime(s, EN)
            frame = rt.session.input_frame()
            before = s.snapshot_hash()
            counts_before = tuple(
                s.db.execute(f"SELECT count(*) FROM {t}").fetchone()[0]
                for t in ("atoms", "applications", "observations", "claims", "frontiers", "generations")
            )
            packet, news, uses, trace = rt.i.parse("flarble", frame)
            self.assertIsNone(packet)
            self.assertEqual(news, [])
            self.assertEqual(trace["reason"], "unknown_form")
            self.assertTrue(trace["unknown_form_evidence"])
            self.assertGreater(len(trace["unknown_form_evidence"][0]["semantic_kind_candidates"]), 1)
            self.assertNotIn("selected_kind", trace["unknown_form_evidence"][0])
            self.assertEqual(before, s.snapshot_hash())

            result = rt.process("flarble", learn=False)
            self.assertEqual(result["status"], "frontier")
            self.assertEqual(before, s.snapshot_hash())
            counts_after = tuple(
                s.db.execute(f"SELECT count(*) FROM {t}").fetchone()[0]
                for t in ("atoms", "applications", "observations", "claims", "frontiers", "generations")
            )
            self.assertEqual(counts_before, counts_after)
        finally:
            s.db.close()
            td.cleanup()

    def test_recursive_type_inheritance_entitles_dimensions_without_type_schema(self):
        td, s = self.make_store()
        try:
            self.import_fixture(
                s,
                {
                    "atoms": [
                        {"ref": "concept:living", "kind": "concept"},
                        {"ref": "concept:animal", "kind": "concept"},
                        {"ref": "concept:cat", "kind": "concept"},
                        {"ref": "entity:milo", "kind": "entity"},
                        {"ref": "dim:energy", "kind": "state_dimension", "metadata": {"cardinality": "one"}},
                        {"ref": "cap:communicate", "kind": "capability"},
                        {"ref": "resource:channel", "kind": "resource"},
                    ],
                    "facts": [
                        {"operator": "op:relation", "args": {"role:subject": "concept:cat", "role:relation": "rel:subtype_of", "role:object": "concept:animal"}},
                        {"operator": "op:relation", "args": {"role:subject": "concept:animal", "role:relation": "rel:subtype_of", "role:object": "concept:living"}},
                        {"operator": "op:relation", "args": {"role:subject": "concept:living", "role:relation": "rel:entitles_state_dimension", "role:object": "dim:energy"}},
                        {"operator": "op:relation", "args": {"role:subject": "concept:living", "role:relation": "rel:entitles_capability", "role:object": "cap:communicate"}},
                        {"operator": "op:relation", "args": {"role:subject": "cap:communicate", "role:relation": "rel:depends_on", "role:object": "resource:channel"}},
                        {"operator": "op:relation", "args": {"role:subject": "dim:energy", "role:relation": "rel:dimension_domain", "role:object": "domain:continuous"}},
                        {"operator": "op:type", "args": {"role:instance": "entity:milo", "role:class": "concept:cat"}},
                    ],
                },
            )
            p = StateProjector(s, authority_generation=s.generation).project("entity:milo")
            self.assertEqual(set(p.type_facet_closure), {"concept:cat", "concept:animal", "concept:living"})
            self.assertEqual([d.dimension_ref for d in p.dimensions], ["dim:energy"])
            self.assertEqual(p.dimensions[0].domain_type, "continuous")
            self.assertEqual(p.dimensions[0].status, "missing")
            self.assertEqual(p.capabilities, ("cap:communicate",))
            self.assertIn(
                {"subject": "cap:communicate", "depends_on": "resource:channel"},
                p.dependency_edges,
            )
        finally:
            s.db.close()
            td.cleanup()

    def test_general_state_timelines_preserve_native_domains_and_resolution_status(self):
        td, s = self.make_store()
        try:
            self.import_fixture(
                s,
                {
                    "atoms": [
                        {"ref": "concept:device", "kind": "concept"},
                        {"ref": "entity:device", "kind": "entity"},
                        {"ref": "dim:load", "kind": "state_dimension", "metadata": {"cardinality": "one"}},
                        {"ref": "dim:tags", "kind": "state_dimension", "metadata": {"cardinality": "many"}},
                        {"ref": "dim:mode", "kind": "state_dimension", "metadata": {"cardinality": "one"}},
                        {"ref": "dim:signal", "kind": "state_dimension", "metadata": {"cardinality": "one"}},
                        {"ref": "dim:last_seen", "kind": "state_dimension", "metadata": {"cardinality": "one", "stale_after_seconds": 1}},
                        {"ref": "dim:missing", "kind": "state_dimension", "metadata": {"cardinality": "one"}},
                        {"ref": "value:red", "kind": "value"},
                        {"ref": "value:blue", "kind": "value"},
                        {"ref": "value:on", "kind": "value"},
                        {"ref": "value:weak", "kind": "value"},
                        {"ref": "value:seen", "kind": "value"},
                    ],
                    "facts": [
                        {"operator": "op:type", "args": {"role:instance": "entity:device", "role:class": "concept:device"}},
                        *[
                            {"operator": "op:relation", "args": {"role:subject": "concept:device", "role:relation": "rel:entitles_state_dimension", "role:object": d}}
                            for d in ("dim:load", "dim:tags", "dim:mode", "dim:signal", "dim:last_seen", "dim:missing")
                        ],
                        {"operator": "op:relation", "args": {"role:subject": "dim:load", "role:relation": "rel:dimension_domain", "role:object": "domain:continuous"}},
                        {"operator": "op:relation", "args": {"role:subject": "dim:tags", "role:relation": "rel:dimension_domain", "role:object": "domain:set_valued"}},
                        {"operator": "op:relation", "args": {"role:subject": "dim:mode", "role:relation": "rel:dimension_domain", "role:object": "domain:categorical"}},
                        {"operator": "op:relation", "args": {"role:subject": "dim:signal", "role:relation": "rel:dimension_domain", "role:object": "domain:categorical"}},
                        {"operator": "op:relation", "args": {"role:subject": "dim:last_seen", "role:relation": "rel:dimension_domain", "role:object": "domain:categorical"}},
                        {"operator": "op:relation", "args": {"role:subject": "dim:missing", "role:relation": "rel:dimension_domain", "role:object": "domain:categorical"}},
                    ],
                },
            )

            def add(dim, value, stance="support", confidence=1.0):
                with s.db:
                    g = s.begin(f"state:{dim}")
                    obs = s.add_observation(dim, {"context_ref": "context:test"}, "und", "test", g)
                    app = s.insert_app(
                        "op:state",
                        {"role:subject": "entity:device", "role:dimension": dim, "role:value": value},
                        g,
                        obs,
                        stance,
                        confidence,
                    )
                    s.finish(g)
                return app, obs

            first, _ = add("dim:load", lit(0.2, "float"))
            add("dim:load", lit(0.8, "float"))
            old = s.db.execute("SELECT valid_to FROM claims WHERE app_ref=? AND stance='support'", (first,)).fetchone()
            self.assertIsNotNone(old[0])

            add("dim:tags", "value:red")
            add("dim:tags", "value:blue")
            add("dim:mode", "value:on", "support")
            add("dim:mode", "value:on", "deny")
            add("dim:signal", "value:weak", confidence=0.3)
            _, stale_obs = add("dim:last_seen", "value:seen")
            s.db.execute("UPDATE observations SET observed_at='2000-01-01T00:00:00+00:00' WHERE observation_ref=?", (stale_obs,))
            s.db.commit()

            p = StateProjector(s, authority_generation=s.generation).project("entity:device")
            dims = {d.dimension_ref: d for d in p.dimensions}
            self.assertEqual(dims["dim:load"].status, "resolved")
            self.assertEqual(dims["dim:load"].values, (lit(0.8, "float"),))
            self.assertEqual(set(dims["dim:tags"].values), {"value:red", "value:blue"})
            self.assertEqual(dims["dim:tags"].status, "resolved")
            self.assertEqual(dims["dim:mode"].status, "conflicting")
            self.assertTrue(dims["dim:mode"].contradiction_lineage)
            self.assertEqual(dims["dim:signal"].status, "uncertain")
            self.assertEqual(dims["dim:last_seen"].status, "stale")
            self.assertEqual(dims["dim:missing"].status, "missing")
        finally:
            s.db.close()
            td.cleanup()


if __name__ == "__main__":
    unittest.main(verbosity=2)
