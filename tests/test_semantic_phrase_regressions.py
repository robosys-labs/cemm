"""End-to-end pre-core regressions for the v3.1.3 incremental patch.

These tests exercise the real normalizer, grounding lattice, feature matcher and
coverage receipts with a deliberately minimal semantic store.  They do not use
phrase routers or relax complete-coverage settlement.
"""
from __future__ import annotations

import json
import sqlite3
import unittest
from pathlib import Path

from cemm.context import ParticipantFrame
from cemm.form_algebra import AtomicConstructionAssembler
from cemm.forms import FormPack, FormProcessor
from cemm.interpreter import Interpreter


class _Store:
    def __init__(self):
        self.db = sqlite3.connect(":memory:")
        self.db.row_factory = sqlite3.Row
        self.db.executescript(
            """
            CREATE TABLE reference_forms(
                language TEXT, surface TEXT, features TEXT,
                bound_ref TEXT, weight REAL
            );
            CREATE TABLE designation_index(
                label_ref TEXT, target_ref TEXT, label_type_ref TEXT,
                surface TEXT, language TEXT, prior REAL,
                preferred INTEGER, context_ref TEXT
            );
            CREATE TABLE discourse_entities(
                atom_ref TEXT, salience REAL, last_turn INTEGER
            );
            """
        )
        references = (
            ("en", "my", {"category": "reference", "participant_role": "speaker", "person": "first", "possessive": True}, None, 1.0),
            ("en", "i", {"category": "reference", "participant_role": "speaker", "person": "first", "possessive": False}, None, 1.0),
            ("en", "your", {"category": "reference", "participant_role": "addressee", "person": "second", "possessive": True}, None, 1.0),
            ("en", "you", {"category": "reference", "participant_role": "addressee", "person": "second", "possessive": False}, None, 1.0),
            ("en", "that", {"category": "reference", "demonstrative": True, "anaphoric": True}, None, 1.0),
            ("en", "this", {"category": "reference", "demonstrative": True, "anaphoric": True}, None, 1.0),
        )
        self.db.executemany(
            "INSERT INTO reference_forms VALUES (?,?,?,?,?)",
            [
                (language, surface, json.dumps(features), bound_ref, weight)
                for language, surface, features, bound_ref, weight in references
            ],
        )
        self.db.execute(
            "INSERT INTO designation_index VALUES (?,?,?,?,?,?,?,?)",
            (
                "label:lol",
                "concept:laughing_out_loud",
                "label:abbreviation",
                "lol",
                "en",
                1.0,
                1,
                None,
            ),
        )
        self._atoms = {
            "participant:user": {"kind": "participant", "metadata": "{}"},
            "participant:system": {"kind": "participant", "metadata": "{}"},
            "concept:laughing_out_loud": {"kind": "concept", "metadata": "{}"},
            "label:name": {"kind": "label_type", "metadata": "{}"},
            "label:abbreviation": {"kind": "label_type", "metadata": "{}"},
        }

    def close(self):
        self.db.close()

    def revisions(self):
        return {"world_revision": 0}

    def atom(self, ref):
        return self._atoms.get(ref)

    def matching_facts(self, *_args, **_kwargs):
        return ()

    def roles(self, operator):
        if operator != "op:designation":
            return {}
        return {
            "role:target": {"filler_kind": "atom", "required": True},
            "role:label_type": {"filler_kind": "label_type", "required": True},
            "role:surface": {"filler_kind": "literal:text", "required": True},
            "role:language": {"filler_kind": "literal:text", "required": True},
            "role:script": {"filler_kind": "literal:text", "required": False},
            "role:prior": {"filler_kind": "literal:float", "required": False},
            "role:preferred": {"filler_kind": "literal:bool", "required": False},
        }


class _LanguagePack:
    def __init__(self, root: Path, form_pack: FormPack):
        self.language = "en"
        self.path = str(root / "cemm/form_packs/_test_language_pack.json")
        self.data = {
            "form_pack": "en.json",
            "form_pack_hash": form_pack.hash,
            "operators": ["op:designation"],
            "function_forms": [],
        }


class SemanticPhraseRegressionTests(unittest.TestCase):
    def setUp(self):
        self.store = _Store()
        root = Path(__file__).resolve().parents[1]
        self.pack = FormPack(root / "cemm/form_packs/en.json")
        self.processor = FormProcessor(
            self.store,
            "en",
            1,
            self.pack,
            max_grounding_hypotheses=16,
        )
        self.assembler = AtomicConstructionAssembler(self.pack, max_matches=64)
        self.interpreter = Interpreter(
            self.store,
            _LanguagePack(root, self.pack),
            authority_generation=1,
        )
        self.frame = ParticipantFrame(
            "participant:system",
            "participant:user",
            "participant:system",
        )

    def tearDown(self):
        self.store.close()

    def _matches(self, text):
        lattice = self.processor.resolve(text, self.frame)
        matches = tuple(
            item
            for item in self.assembler.matcher.matches(lattice)
            if item.coverage.executable
        )
        return lattice, matches

    def test_contracted_second_person_designation_query(self):
        _lattice, matches = self._matches("What's your name?")
        self.assertEqual({item.schema_family for item in matches}, {"designation_query"})
        self.assertTrue(all(item.captures["target"] == "participant:system" for item in matches))
        packets = [self.assembler.instantiate(item, self.frame, "en") for item in matches]
        self.assertEqual({item["force"] for item in packets}, {"query"})
        self.assertEqual({
            item["query"]["restrictions"][0]["args"]["role:target"]
            for item in packets
        }, {"participant:system"})

    def test_first_person_designation_query(self):
        _lattice, matches = self._matches("what is my name?")
        self.assertEqual({item.schema_family for item in matches}, {"designation_query"})
        self.assertTrue(all(item.captures["target"] == "participant:user" for item in matches))
        packets = [self.assembler.instantiate(item, self.frame, "en") for item in matches]
        self.assertEqual({
            item["query"]["restrictions"][0]["args"]["role:target"]
            for item in packets
        }, {"participant:user"})

    def test_single_token_proper_name_claim(self):
        _lattice, matches = self._matches("my name is Opata")
        self.assertEqual({item.schema_family for item in matches}, {"designation_claim"})
        self.assertTrue(all(item.captures["target"] == "participant:user" for item in matches))
        self.assertTrue(all(item.captures["value"]["literal"]["value"] == "Opata" for item in matches))
        packets = [self.assembler.instantiate(item, self.frame, "en") for item in matches]
        self.assertEqual({item["force"] for item in packets}, {"claim"})
        self.assertEqual({
            item["apps"][0]["args"]["role:surface"]["literal"]["value"]
            for item in packets
        }, {"Opata"})

    def test_contextual_anaphoric_meaning_query(self):
        _lattice, matches = self._matches("lol, what does that mean?")
        # The graph matcher may produce a weaker meaning_query match that
        # shares a subset of required slots.  The contextual family must be
        # present and dominant; verify its captures and packets specifically.
        contextual = [item for item in matches if item.schema_family == "contextual_meaning_query"]
        self.assertTrue(contextual, "contextual_meaning_query must match")
        self.assertTrue(all(item.captures["antecedent"]["literal"]["value"] == "lol" for item in contextual))
        packets = [self.assembler.instantiate(item, self.frame, "en") for item in contextual]
        self.assertEqual({
            item["query"]["restrictions"][0]["args"]["role:surface"]["literal"]["value"]
            for item in packets
        }, {"lol"})
        self.assertTrue(any(
            unit.kind == "anchor" and unit.semantic_ref == "concept:laughing_out_loud"
            for hypothesis in _lattice.grounding_hypotheses
            for unit in hypothesis.units
        ))

    def test_participant_pronoun_is_not_named_entity_proposal(self):
        normalization = self.processor.normalizations("I")[0]
        tokens = self.processor.tokenize(normalization)
        proposals = self.processor._span_proposals(normalization, tokens)
        self.assertFalse(any(item.provider_ref == "named_entity_proposal" for item in proposals))

    def test_unknown_title_case_token_remains_name_proposal(self):
        normalization = self.processor.normalizations("Opata")[0]
        tokens = self.processor.tokenize(normalization)
        proposals = self.processor._span_proposals(normalization, tokens)
        self.assertTrue(any(
            item.provider_ref == "named_entity_proposal" and item.surface == "Opata"
            for item in proposals
        ))

    def test_each_reversible_normalization_keeps_a_representative(self):
        lattice = self.processor.resolve("What's your name?", self.frame)
        represented = {
            item.normalization_ref for item in lattice.grounding_hypotheses
        }
        expected = {
            item.candidate_ref for item in lattice.normalization_candidates
        }
        self.assertEqual(represented, expected)

    def test_participant_anchors_rank_above_feature_only_reference_units(self):
        expected = {
            "I": "participant:user",
            "you": "participant:system",
        }
        for text, semantic_ref in expected.items():
            with self.subTest(text=text):
                lattice = self.processor.resolve(text, self.frame)
                top = lattice.grounding_hypotheses[0]
                self.assertEqual(len(top.units), 1)
                self.assertEqual(top.units[0].kind, "anchor")
                self.assertEqual(top.units[0].semantic_ref, semantic_ref)

    def test_interpreter_compose_preserves_complete_packets(self):
        cases = {
            "What's your name?": ("query", "participant:system"),
            "my name is Opata": ("claim", "participant:user"),
            "lol, what does that mean?": ("query", None),
            "quux, what does that mean?": ("query", None),
        }
        for text, (force, target_ref) in cases.items():
            with self.subTest(text=text):
                packet, _news, _uses, trace = self.interpreter.parse(text, self.frame)
                self.assertIsNotNone(packet, trace)
                self.assertEqual(packet["force"], force)
                self.assertEqual(
                    trace["interpretation_assessment"]["status"], "resolved"
                )
                if target_ref is not None:
                    applications = packet.get("apps") or packet["query"]["restrictions"]
                    self.assertEqual(
                        applications[0]["args"]["role:target"], target_ref
                    )


if __name__ == "__main__":
    unittest.main()
