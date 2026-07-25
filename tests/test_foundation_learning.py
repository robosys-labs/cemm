from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from pydantic import ValidationError

from cemm.context import SessionContext
from cemm.forms import FormPack, FormProcessor
from cemm.runtime import MODE_NORMAL, MODE_READ_ONLY, Runtime
from cemm.store import Store
from cemm.web_demo import AcquisitionMention


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "cemm" / "data" / "base.json"
CONVERSATION = ROOT / "cemm" / "data" / "conversation_foundation.json"
PACK = ROOT / "cemm" / "language_packs" / "en.json"
FORM_PACK = ROOT / "cemm" / "form_packs" / "en.json"


class FoundationLearningTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = Store(Path(self.tmp.name) / "cemm.sqlite")
        self.store.import_bundle((BASE, CONVERSATION))
        self.runtime = Runtime(self.store, PACK)

    def tearDown(self):
        self.store.db.close()
        self.tmp.cleanup()

    def test_contraction_is_reversible_and_semantically_equivalent(self):
        lattice = self.runtime.i.observe(
            "What's your name?", self.runtime.session.input_frame()
        )
        resolved = lattice.resolved_form_lattice
        texts = {item.text.casefold() for item in resolved.normalization_candidates}
        self.assertIn("what's your name?", texts)
        self.assertIn("what is your name?", texts)
        result = self.runtime.process("What's your name?", mode=MODE_READ_ONLY)
        self.assertEqual(result["response_csir"]["action"], "answer_bindings")
        self.assertEqual(result["response"], "The name is CEMM.")
        self.assertTrue(result["realization_proof"]["verified"])

    def test_known_learning_query_searches_seed_before_probing(self):
        result = self.runtime.process(
            "lol, what does that mean?", mode=MODE_READ_ONLY
        )
        self.assertEqual(result["query_result"]["status"], "answered")
        self.assertEqual(result["response_csir"]["action"], "answer_bindings")
        self.assertIn("laughing out loud", result["response"].casefold())
        stage8 = result["stage_trace"]["records"][8]
        self.assertEqual(stage8["artifact_counts"]["queries"], 1)

    def test_unknown_learning_query_is_first_class_query(self):
        result = self.runtime.process(
            "quux, what does that mean?", mode=MODE_READ_ONLY
        )
        self.assertEqual(result["query_result"]["status"], "unknown")
        self.assertEqual(
            result["response_csir"]["action"], "request_learning_evidence"
        )
        self.assertEqual(
            result["response_csir"]["qualifiers"]["learning_operation"],
            "resolve_designation",
        )
        self.assertIsNotNone(
            result["response_csir"]["qualifiers"]["learning_query"]
        )
        self.assertIn("quux", result["response"].casefold())

    def test_unknown_discourse_does_not_erase_name_claim(self):
        result = self.runtime.process("Well my name is Opata", mode=MODE_NORMAL)
        self.assertIsNotNone(result["packet"])
        self.assertEqual(result["packet"]["apps"][0]["operator"], "op:designation")
        self.assertEqual(
            result["packet"]["apps"][0]["args"]["role:target"],
            "participant:user",
        )
        self.assertFalse(result["frontier_graph"]["frontiers"])
        answer = self.runtime.process("what is my name?", mode=MODE_READ_ONLY)
        self.assertEqual(answer["response_csir"]["action"], "answer_bindings")
        self.assertEqual(answer["response"], "The name is Opata.")

    def test_form_matching_is_bounded_and_not_regex_per_label(self):
        processor = FormProcessor(
            self.store,
            "en",
            self.store.generation,
            FormPack(FORM_PACK),
            semantic_function_forms=self.runtime.pack.function_forms,
        )
        lattice = processor.resolve(
            "Well my name is Opata", self.runtime.session.input_frame()
        )
        self.assertFalse(lattice.bounded["regex_per_stored_surface"])
        self.assertLessEqual(
            len(lattice.grounding_hypotheses),
            lattice.bounded["max_grounding_hypotheses"],
        )
        self.assertLessEqual(
            len(lattice.normalization_candidates),
            lattice.bounded["max_normalizations"],
        )

    def test_web_acquisition_has_no_concept_default(self):
        with self.assertRaises(ValidationError):
            AcquisitionMention(surface="quux")

    def test_seed_is_substantial_and_uses_only_fixed_operator_abi(self):
        data = json.loads(CONVERSATION.read_text(encoding="utf-8"))
        self.assertGreaterEqual(len(data["atoms"]), 100)
        self.assertGreaterEqual(len(data["facts"]), 150)
        operators = {item["operator"] for item in data["facts"]}
        self.assertLessEqual(
            operators,
            {"op:designation", "op:type", "op:relation", "op:state", "op:event"},
        )
        self.assertTrue(
            any(
                item["operator"] == "op:designation"
                and item["args"].get("role:target") == "participant:system"
                and item["args"].get("role:label_type") == "label:name"
                for item in data["facts"]
            )
        )


if __name__ == "__main__":
    unittest.main()
