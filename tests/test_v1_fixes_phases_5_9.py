from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from cemm.cognition import DiscourseAct, QueryStructure, SemanticVariable
from cemm.compiler import ExactStructuredCompiler
from cemm.epistemics import AdmissionClass, EpistemicPolicy
from cemm.inference import Inference
from cemm.model import Fact, stable
from cemm.realizer import LanguagePack
from cemm.runtime import Runtime
from cemm.store import Store
from cemm.workspace import Workspace

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "cemm/data/base.json"
FAMILY = ROOT / "cemm/data/family_knowledge.json"
EN = ROOT / "cemm/language_packs/en.json"


class Phase5To9Tests(unittest.TestCase):
    def make(self, family=False):
        td = tempfile.TemporaryDirectory()
        store = Store(Path(td.name) / "x.sqlite")
        store.import_data(BASE)
        if family:
            store.import_data(FAMILY)
        return td, store, Runtime(store, EN)

    def import_fixture(self, store, payload):
        path = Path(tempfile.mkdtemp()) / "fixture.json"
        path.write_text(json.dumps(payload), encoding="utf-8")
        store.import_data(path)

    def test_workspace_does_not_emit_synthetic_self_facts(self):
        td, store, _ = self.make()
        try:
            selected, trace = Workspace(store).build([])
            self.assertEqual(selected, [])
        finally:
            store.db.close()
            td.cleanup()

    def test_language_pack_has_explicit_force_dimension_and_function_forms(self):
        pack = LanguagePack(EN)
        self.assertIn("role:dimension", pack.data["roles"])
        self.assertIn("Q0", pack.data["source_classes"])
        self.assertIn("directive", pack.data["forces"])
        self.assertIn("how", pack.function_forms)
        self.assertNotIn("mother", pack.function_forms)
        self.assertTrue(pack.hash)

    def test_compiler_accepts_all_required_state_query_variable_shapes(self):
        td, store, _ = self.make()
        try:
            compiler = ExactStructuredCompiler(store)
            shapes = [
                {
                    "role:subject": "participant:system",
                    "role:dimension": "dim:response_state",
                    "role:value": "?q0",
                },
                {
                    "role:subject": "participant:system",
                    "role:dimension": "?q0",
                    "role:value": "?q1",
                },
                {
                    "role:subject": "participant:system",
                    "role:dimension": "?q0",
                    "role:value": "value:ready",
                },
            ]
            for args in shapes:
                variables = [
                    {"ref": value, "filler_kind": "atom", "role_ref": role}
                    for role, value in args.items()
                    if isinstance(value, str) and value.startswith("?")
                ]
                packet, _ = compiler.compile(
                    {
                        "force": "query",
                        "query": {
                            "restrictions": [{"operator": "op:state", "args": args}],
                            "variables": variables,
                            "projection": [item["ref"] for item in variables],
                        },
                    }
                )
                self.assertEqual(packet["force"], "query")
                self.assertEqual(len(packet["query"]["restrictions"]), 1)
        finally:
            store.db.close()
            td.cleanup()

    def test_query_execution_returns_bindings_coverage_and_proof_refs(self):
        td, store, _ = self.make()
        try:
            fact = Fact(
                "fact:self-ready",
                "op:state",
                {
                    "role:subject": "participant:system",
                    "role:dimension": "dim:response_state",
                    "role:value": "value:ready",
                },
            )
            query = QueryStructure(
                "query:self-response",
                (
                    {
                        "operator": "op:state",
                        "args": {
                            "role:subject": "participant:system",
                            "role:dimension": "dim:response_state",
                            "role:value": "?q0",
                        },
                    },
                ),
                (SemanticVariable("?q0", "state_value", "role:value"),),
                ("?q0",),
            )
            result = Inference(store).execute_query(query, [fact], {fact.ref: fact})
            self.assertEqual(result.status, "answered")
            self.assertEqual(result.coverage, 1.0)
            self.assertEqual(result.bindings[0].values["?q0"], "value:ready")
            self.assertEqual(result.bindings[0].proof_refs, ("fact:self-ready",))
        finally:
            store.db.close()
            td.cleanup()

    def test_learn_permission_never_rewrites_query_force(self):
        td, store, runtime = self.make()
        try:
            packet = {
                "force": "query",
                "apps": [],
                "query": {
                    "restrictions": [
                        {
                            "operator": "op:state",
                            "args": {
                                "role:subject": "participant:system",
                                "role:dimension": "dim:response_state",
                                "role:value": "value:ready",
                            },
                        }
                    ],
                    "variables": [],
                    "projection": [],
                },
                "directive": None,
                "describe": None,
            }
            runtime.i.parse = lambda *_args, **_kwargs: (
                packet,
                [],
                [],
                {"interpretation_assessment": {"status": "resolved"}},
            )
            before = tuple(
                store.db.execute(f"SELECT count(*) FROM {table}").fetchone()[0]
                for table in ("applications", "claims", "claim_occurrences", "epistemic_placements")
            )
            result = runtime.process("query with no punctuation", learn=True)
            after = tuple(
                store.db.execute(f"SELECT count(*) FROM {table}").fetchone()[0]
                for table in ("applications", "claims", "claim_occurrences", "epistemic_placements")
            )
            self.assertIn("query_result", result)
            self.assertEqual(before, after)
        finally:
            store.db.close()
            td.cleanup()

    def test_unknown_form_is_scoped_frontier_not_global_self_corruption(self):
        td, store, runtime = self.make()
        try:
            before = store.snapshot_hash()
            result = runtime.process("flarble", learn=False)
            self.assertEqual(result["status"], "frontier")
            self.assertEqual(result["self_state"], {})
            self.assertTrue(result["self_runtime_view"]["process_available"])
            self.assertEqual(result["interpretation"]["status"], "unresolved")
            self.assertEqual(before, store.snapshot_hash())
        finally:
            store.db.close()
            td.cleanup()

    def test_partial_interpretation_preserves_resolved_clause(self):
        td, store, runtime = self.make(family=True)
        try:
            packet, _news, _uses, trace = runtime.i.parse(
                "Ada is a doctor. flarble.", runtime.session.input_frame()
            )
            self.assertIsNotNone(packet)
            self.assertEqual(trace["interpretation_assessment"]["status"], "partial")
            self.assertTrue(packet["apps"])
            self.assertTrue(trace["unknown_form_evidence"])
        finally:
            store.db.close()
            td.cleanup()

    def test_directive_is_goal_input_not_claim_or_effect(self):
        td, store, runtime = self.make()
        try:
            packet = {
                "force": "directive",
                "apps": [],
                "query": None,
                "directive": {
                    "content": [
                        {
                            "operator": "op:state",
                            "args": {
                                "role:subject": "participant:system",
                                "role:dimension": "dim:response_state",
                                "role:value": "value:ready",
                            },
                        }
                    ]
                },
                "describe": None,
            }
            runtime.i.parse = lambda *_args, **_kwargs: (
                packet,
                [],
                [],
                {"interpretation_assessment": {"status": "resolved"}},
            )
            before = store.snapshot_hash()
            result = runtime.process("directive", learn=True)
            self.assertEqual(result["status"], "interpreted_directive")
            self.assertTrue(result["blocks_effect"])
            self.assertEqual(result["transition_candidates"], [])
            self.assertEqual(before, store.snapshot_hash())
        finally:
            store.db.close()
            td.cleanup()

    def test_epistemic_placement_is_separate_from_world_belief(self):
        td, store, runtime = self.make()
        try:
            self.import_fixture(
                store,
                {
                    "atoms": [
                        {
                            "ref": "entity:sensitive",
                            "kind": "entity",
                            "metadata": {"high_risk_no_auto_admission": True},
                        },
                        {"ref": "concept:condition", "kind": "concept"},
                    ]
                },
            )
            act = DiscourseAct(
                "act:test",
                "claim",
                "participant:user",
                "participant:system",
                (
                    {
                        "operator": "op:type",
                        "args": {
                            "role:instance": "entity:sensitive",
                            "role:class": "concept:condition",
                        },
                    },
                ),
            )
            placement = EpistemicPolicy(store).place(act)
            self.assertEqual(placement.admission_class, AdmissionClass.HIGH_RISK_NO_AUTO_ADMISSION)
            self.assertFalse(placement.admitted)

            with store.db:
                generation = store.begin("placement-test")
                observation = store.add_observation("claim", {}, "en", "participant:user", generation)
                occurrence = store.add_claim_occurrence(observation, act, generation)
                store.add_epistemic_placement(occurrence, placement, generation)
                store.finish(generation)
            self.assertEqual(len(store.claim_occurrence_records()), 1)
            self.assertEqual(len(store.epistemic_placement_records()), 1)
            self.assertFalse(store.epistemic_placement_records()[0]["admitted"])
            self.assertFalse(
                any(
                    fact.operator == "op:type"
                    and fact.args.get("role:instance") == "entity:sensitive"
                    for fact in store.base_facts()
                )
            )
        finally:
            store.db.close()
            td.cleanup()

    def test_query_response_inputs_preserve_phase10_and_phase13_contracts(self):
        td, store, runtime = self.make()
        try:
            packet = {
                "force": "query",
                "apps": [],
                "query": {
                    "restrictions": [
                        {
                            "operator": "op:state",
                            "args": {
                                "role:subject": "participant:system",
                                "role:dimension": "dim:response_state",
                                "role:value": "?q0",
                            },
                        }
                    ],
                    "variables": [
                        {"ref": "?q0", "filler_kind": "state_value", "role_ref": "role:value"}
                    ],
                    "projection": ["?q0"],
                },
                "directive": None,
                "describe": None,
            }
            runtime.i.parse = lambda *_args, **_kwargs: (
                packet,
                [],
                [],
                {"interpretation_assessment": {"status": "resolved"}},
            )
            result = runtime.process("state query", learn=False)
            inputs = result["response_inputs"]
            self.assertIn("query_result", inputs)
            self.assertIn("epistemic_assessment", inputs)
            self.assertIn("state_space_projections", inputs)
            self.assertEqual(inputs["transition_candidates"], [])
        finally:
            store.db.close()
            td.cleanup()


if __name__ == "__main__":
    unittest.main(verbosity=2)
