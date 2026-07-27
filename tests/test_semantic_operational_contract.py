from __future__ import annotations

import ast
import copy
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from cemm.capability import CapabilityAssessment, CapabilityEvaluator, RuntimeObservation
from cemm.cognition import QueryBinding, QueryResult
from cemm.dialogue import DialogueState
from cemm.goals import GoalArbiter, GoalCandidate, GoalDecision
from cemm.interpreter import Interpreter
from cemm.form_algebra import AtomicConstructionAssembler, SchemaValidationError
from cemm.forms import FormPack, HeuristicProperNameProvider, NormalizationCandidate, TokenEvidence
from cemm.model import Fact
from cemm.operational import (
    CANONICAL_RUNTIME_RESOURCES,
    OperationalProviderExecutionError,
    OperationalSnapshotIntegrityError,
    OperationalUsageLedger,
    RuntimeResourceObservation,
    OperationalInvariantChecker,
    OperationalInvariantError,
    OperationalProviderContractError,
    RuntimeServiceRegistry,
    StateAssertion,
    declared_operation_resources,
    TransitionReceipt,
)
from cemm.realizer import PointerRealizer
from cemm.reference import CanonicalResponseRealizer
from cemm.response import ResponseBuilder, ResponseCSIR, pointerize_response
from cemm.retrieval import SemanticRetriever
from cemm.settler import SemanticSettler
from cemm.semantic_coverage import (
    COVERAGE_ABI_VERSION,
    CoverageIntegrityError,
    CoveragePolicy,
    InterpretationCoverage,
    coverage_from_dict,
)
from cemm.surface_plans import ExactSurfacePlanIndex
from tools.apply_semantic_operational_source_rewrite import (
    REWRITE_MARKERS,
    RewriteError,
    _begin_file_rewrite,
    _seal_file_rewrite,
    prove_idempotence_on_isolated_copy,
    validate_postconditions,
    validate_rewrite_seals,
)
from tools.authority_ownership import (
    AuthorityOwnershipError,
    AuthorityOwnershipIndex,
    validate_repository_authority,
)
from tools.migrate_semantic_operational_assets import migrate_language_pack, migrate_seed
from tools.generate_en_form_pack_v6 import build_pack, build_lexeme_index, replay_units


REJECTED_REFS = {
    "dim:operational_condition",
    "dim:runtime_support",
    "value:operating_normally",
    "value:degraded",
    "rel:attributed_property",
    "concept:surface_pattern_matching",
}


class Unit:
    def __init__(
        self,
        ref,
        kind,
        surface,
        *,
        features=None,
        semantic_ref=None,
        atom_kind=None,
        source_kind=None,
        index=0,
    ):
        self.unit_ref = ref
        self.kind = kind
        self.surface = surface
        self.normalized = surface.casefold()
        self.token_start = index
        self.token_end = index + 1
        self.char_start = index * 3
        self.char_end = self.char_start + len(surface)
        self.features = dict(features or {})
        self.semantic_ref = semantic_ref
        self.atom_kind = atom_kind
        self.source_kind = source_kind

    def as_dict(self):
        return vars(self)


class FakeStore:
    labels = {
        "participant:system": "CEMM",
        "participant:user": "Chibueze Opata",
        "label:name": "name",
        "label:type": "type",
        "concept:digital_agent": "digital agent",
        "rel:knows": "know",
    }

    def preferred(self, ref, language, context=None):
        return self.labels.get(ref, ref)

    def atom(self, ref):
        metadata = {
            "dim:runtime_process_support": {"min": 0.0, "max": 1.0},
            "dim:semantic_runtime_support": {"min": 0.0, "max": 1.0},
            "dim:language_realizer_support": {"min": 0.0, "max": 1.0},
            "dim:critical_blocker_count": {
                "min": 0.0,
                "max": 1000000.0,
                "positive_direction": "lower",
            },
        }.get(ref)
        return None if metadata is None else {"metadata": json.dumps(metadata)}


class SemanticOperationalContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.repo = Path(__file__).resolve().parents[1]
        cls.form_data = json.loads(
            (cls.repo / "cemm/form_packs/en.json").read_text(encoding="utf-8")
        )
        cls.form_pack = SimpleNamespace(schemas=tuple(cls.form_data["schemas"]))
        cls.assembler = AtomicConstructionAssembler(cls.form_pack, max_matches=64)
        cls.form_seed = json.loads(
            (cls.repo / "cemm/training/en_form_schema_seed.json").read_text(encoding="utf-8")
        )
        cls.lexeme_index = build_lexeme_index(cls.form_seed["lexemes"])

    def match(self, units, family):
        hypothesis = SimpleNamespace(
            hypothesis_ref=f"hypothesis:{family}",
            units=tuple(units),
            score=0.0,
        )
        lattice = SimpleNamespace(grounding_hypotheses=(hypothesis,))
        return next(
            item
            for item in self.assembler.evidence_records(lattice)
            if item.schema_ref == f"en:schema:{family}"
        )

    def frame(self, dialogue_context=None):
        return SimpleNamespace(
            speaker_ref="participant:user",
            addressee_ref="participant:system",
            self_ref="participant:system",
            conversation_ref="conversation:test",
            dialogue_context=dict(dialogue_context or {}),
        )

    def output_frame(self):
        return SimpleNamespace(
            speaker_ref="participant:system",
            addressee_ref="participant:user",
            self_ref="participant:system",
            conversation_ref="conversation:test",
            channel="text",
        )

    def language_pack(self):
        data = json.loads(
            (self.repo / "cemm/language_packs/en.json").read_text(encoding="utf-8")
        )
        return SimpleNamespace(
            data=data,
            language="en",
            hash=data["pack_hash"],
            grammar=set(data.get("grammar_tokens", ())),
            function_forms=set(data.get("function_forms", ())),
        )

    def replay_match(self, family, *, example_index=0):
        examples = [
            item for item in self.form_seed["examples"]
            if item["family"] == family
        ]
        units = replay_units(examples[example_index], self.lexeme_index)
        return self.match(units, family)

    @staticmethod
    def _learning_response(surface, *, goal_ref):
        return ResponseCSIR(
            f"response:{surface}",
            "request_learning_evidence",
            "participant:user",
            evidence_literals=(surface,),
            qualifiers={
                "learning_operation": "resolve_designation",
                "learning_query": {"restrictions": [], "projection": ["?q0"]},
                "expected_answer_shape": {
                    "operation": "resolve_designation",
                    "surface_cardinality": "one",
                },
            },
            obligation_ref=goal_ref,
        )

    @staticmethod
    def _verified_surface_proof(response, chosen_surface):
        equivalence = {
            "receipt_ref": f"equivalence:{response.response_ref}",
            "response_ref": response.response_ref,
            "equivalent": True,
            "action_preserved": True,
            "obligation_preserved": True,
            "target_preserved": True,
            "query_kind_preserved": True,
            "payload_preserved": True,
            "source_signature": response.semantic_signature(),
            "realized_signature": response.semantic_signature(),
            "required_semantic_slots": [],
            "reason": "same_response_csir",
        }
        return {
            "verified": True,
            "response_equivalence": equivalence,
            "surface_decision": {
                "decision_ref": f"decision:{response.response_ref}",
                "response_ref": response.response_ref,
                "response_action": response.action,
                "obligation_ref": response.obligation_ref,
                "chosen_surface": chosen_surface,
                "grammar_rule_ref": "en:test",
                "reference_plan": {
                    "plan_ref": "reference-plan:test",
                    "speaker_ref": "participant:system",
                    "addressee_ref": "participant:user",
                    "choices": [],
                },
                "semantic_signature": response.semantic_signature(),
                "alternatives": [],
                "response_equivalence": equivalence,
            },
        }

    def test_actual_repository_authority_graph_is_valid(self):
        index = validate_repository_authority(self.repo)
        base = str((self.repo / "cemm/data/base.json").resolve())
        conversation = str(
            (self.repo / "cemm/data/conversation_foundation.json").resolve()
        )
        self.assertEqual(index.atom_owner["value:unknown"], base)
        self.assertNotIn("value:unknown", index.document_atoms[conversation])
        self.assertFalse(REJECTED_REFS.intersection(index.atom_owner))

    def test_cross_document_duplicate_atom_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            first = root / "a.json"
            second = root / "b.json"
            first.write_text(
                json.dumps({"atoms": [{"ref": "value:unknown", "kind": "value"}]}),
                encoding="utf-8",
            )
            second.write_text(
                json.dumps({"atoms": [{"ref": "value:unknown", "kind": "value"}]}),
                encoding="utf-8",
            )
            with self.assertRaises(AuthorityOwnershipError):
                AuthorityOwnershipIndex.build((first, second))

    def test_removal_only_seed_migration_preserves_surviving_atoms(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "conversation_foundation.json"
            knows = {
                "ref": "rel:knows",
                "kind": "relation_type",
                "metadata": {"foundational": True, "user_visible": True},
            }
            rejected = {
                "ref": "dim:operational_condition",
                "kind": "state_dimension",
                "metadata": {"runtime_derived": True},
            }
            path.write_text(
                json.dumps(
                    {
                        "atoms": [knows, rejected],
                        "facts": [
                            {
                                "fact_ref": "bad:state",
                                "operator": "op:state",
                                "args": {
                                    "role:subject": "participant:system",
                                    "role:dimension": "dim:operational_condition",
                                    "role:value": "value:operating_normally",
                                },
                                "authority_status": "reviewed",
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            report = migrate_seed(path)
            migrated = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(migrated["atoms"], [knows])
            self.assertEqual(migrated["facts"], [])
            self.assertEqual(report["added_atom_count"], 0)
            self.assertEqual(report["modified_atom_count"], 0)
            first_bytes = path.read_bytes()
            second_report = migrate_seed(path)
            self.assertEqual(path.read_bytes(), first_bytes)
            self.assertEqual(second_report, report)

    def test_language_pack_migration_removes_legacy_slotless_grammar(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            pack_path = root / "en.json"
            form_path = root / "form.json"
            form_path.write_bytes(
                (self.repo / "cemm/form_packs/en.json").read_bytes()
            )
            legacy = {
                "version": 6,
                "language": "en",
                "response_grammar": [
                    {
                        "ref": "en:response:operational",
                        "when": {"action": "answer_bindings"},
                        "template": "{subject} {copula} {value}.",
                        "required_slots": ["subject", "copula", "value"],
                    }
                ],
                "response_examples": [],
                "grammar_tokens": [],
            }
            material = dict(legacy)
            legacy["pack_hash"] = __import__("hashlib").sha256(
                json.dumps(
                    material,
                    sort_keys=True,
                    ensure_ascii=False,
                    separators=(",", ":"),
                ).encode()
            ).hexdigest()
            pack_path.write_text(json.dumps(legacy), encoding="utf-8")
            migrate_language_pack(pack_path, form_path)
            migrated = json.loads(pack_path.read_text(encoding="utf-8"))
            refs = {item["ref"] for item in migrated["response_grammar"]}
            self.assertNotIn("en:response:operational", refs)
            self.assertIn("en:response:operational-normal", refs)
            self.assertTrue(
                all("semantic_slots" in item for item in migrated["response_grammar"])
            )

    def test_language_pack_migration_is_byte_idempotent(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            pack_path = root / "en.json"
            form_path = root / "form.json"
            pack_path.write_bytes((self.repo / "cemm/language_packs/en.json").read_bytes())
            form_path.write_bytes((self.repo / "cemm/form_packs/en.json").read_bytes())
            migrate_language_pack(pack_path, form_path)
            first = pack_path.read_bytes()
            migrate_language_pack(pack_path, form_path)
            self.assertEqual(pack_path.read_bytes(), first)

    def test_seed_migration_rejects_base_owned_redefinition(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "conversation_foundation.json"
            path.write_text(
                json.dumps(
                    {
                        "atoms": [
                            {
                                "ref": "value:unknown",
                                "kind": "value",
                                "metadata": {"runtime_derived": True},
                            }
                        ],
                        "facts": [],
                    }
                ),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "base-owned"):
                migrate_seed(path)

    def test_form_pack_has_only_atomic_feature_schemas(self):
        self.assertNotIn("constructions", self.form_data)
        families = {item["family"] for item in self.form_data["schemas"]}
        self.assertEqual(
            families,
            {
                "designation_claim",
                "designation_confirmation",
                "designation_query",
                "meaning_query",
                "contextual_meaning_query",
                "operational_condition_query",
                "relation_surface_query",
                "surface_choice_explanation_query",
                "attributed_open_predication_claim",
                "type_query",
            },
        )
        def keys(value):
            if isinstance(value, dict):
                for key, item in value.items():
                    yield key
                    yield from keys(item)
            elif isinstance(value, list):
                for item in value:
                    yield from keys(item)

        step_keys = set(
            keys([item["steps"] for item in self.form_data["schemas"]])
        )
        self.assertFalse(
            {"literal", "surface", "regex", "pattern_text"}.intersection(step_keys)
        )
        self.assertEqual(
            self.form_data["training_receipt"]["surface_matcher_key_count"], 0
        )

    def test_name_assertion_consumes_full_literal_span(self):
        units = [
            Unit("u0", "anchor", "my", features={"category": "reference", "possessive": True}, semantic_ref="participant:user", atom_kind="participant", index=0),
            Unit("u1", "function", "name", features={"category": "property_marker", "property_kind": "designation", "property_ref": "label:name"}, index=1),
            Unit("u2", "function", "is", features={"category": "verb", "lemma": "be", "predicate": True, "copular": True, "semantic_port": "predication"}, index=2),
            Unit("u3", "span", "Chibueze Opata", features={"span_type": "named_entity", "proposal_only": True}, index=3),
        ]
        match = self.match(units, "designation_claim")
        self.assertTrue(match.coverage.complete)
        packet = self.assembler.instantiate(match, self.frame(), "en")
        application = packet["apps"][0]
        self.assertEqual(application["args"]["role:target"], "participant:user")
        self.assertEqual(
            application["args"]["role:surface"]["literal"]["value"],
            "Chibueze Opata",
        )

    def test_optional_own_emphasis_is_noncritical(self):
        units = [
            Unit("u0", "function", "what", features={"category": "interrogative", "discourse_force": "query", "question_domain": "open"}, index=0),
            Unit("u1", "function", "is", features={"category": "verb", "lemma": "be", "predicate": True, "copular": True, "semantic_port": "predication"}, index=1),
            Unit("u2", "anchor", "your", features={"category": "reference", "participant_role": "addressee", "person": "second", "possessive": True}, semantic_ref="participant:system", atom_kind="participant", index=2),
            Unit("u3", "function", "own", features={"category": "emphasis", "emphasis": True, "focus_only": True}, index=3),
            Unit("u4", "function", "name", features={"category": "property_marker", "property_kind": "designation", "property_ref": "label:name"}, index=4),
        ]
        match = self.match(units, "designation_query")
        self.assertTrue(match.coverage.complete)
        self.assertFalse(match.coverage.critical_residuals)

    def test_relation_query_preserves_predicate_and_multi_token_object(self):
        units = [
            Unit("u0", "function", "Do", features={"category": "auxiliary", "lemma": "do", "auxiliary": True}, index=0),
            Unit("u1", "anchor", "you", semantic_ref="participant:system", atom_kind="participant", index=1),
            Unit("u2", "function", "know", features={"category": "verb", "lemma": "know", "predicate": True, "semantic_port": "relation_query", "relation_ref": "rel:knows"}, index=2),
            Unit("u3", "span", "Donald Trump", features={"span_type": "named_entity", "proposal_only": True}, index=3),
        ]
        match = self.match(units, "relation_surface_query")
        self.assertTrue(match.coverage.complete)
        packet = self.assembler.instantiate(match, self.frame(), "en")
        restrictions = packet["query"]["restrictions"]
        self.assertEqual([item["operator"] for item in restrictions], ["op:designation", "op:relation"])
        self.assertEqual(
            restrictions[0]["args"]["role:surface"]["literal"]["value"],
            "Donald Trump",
        )
        self.assertEqual(restrictions[1]["args"]["role:relation"], "rel:knows")
        self.assertEqual(packet["query"]["qualifiers"]["subject_ref"], "participant:system")
        self.assertEqual(packet["query"]["projection"], [])

    def test_operational_query_uses_existing_base_dimensions(self):
        units = [
            Unit("u0", "function", "how", features={"category": "interrogative", "discourse_force": "query", "question_domain": "state_summary"}, index=0),
            Unit("u1", "function", "are", features={"category": "verb", "lemma": "be", "predicate": True, "copular": True, "semantic_port": "predication"}, index=1),
            Unit("u2", "anchor", "you", semantic_ref="participant:system", atom_kind="participant", index=2),
        ]
        packet = self.assembler.instantiate(
            self.match(units, "operational_condition_query"), self.frame(), "en"
        )
        dimensions = {
            item["args"]["role:dimension"]
            for item in packet["query"]["restrictions"]
        }
        self.assertEqual(
            dimensions,
            {
                "dim:runtime_process_support",
                "dim:semantic_runtime_support",
                "dim:language_realizer_support",
                "dim:critical_blocker_count",
            },
        )
        self.assertFalse(REJECTED_REFS.intersection(json.dumps(packet)))

    def test_critical_residual_cannot_be_instantiated(self):
        units = [
            Unit("u0", "function", "how", features={"category": "interrogative", "discourse_force": "query", "question_domain": "state_summary"}, index=0),
            Unit("u1", "function", "are", features={"category": "verb", "lemma": "be", "predicate": True, "copular": True, "semantic_port": "predication"}, index=1),
            Unit("u2", "anchor", "you", semantic_ref="participant:system", atom_kind="participant", index=2),
            Unit("u3", "unknown", "quantumly", index=3),
        ]
        match = self.match(units, "operational_condition_query")
        self.assertFalse(match.coverage.complete)
        with self.assertRaises(SchemaValidationError):
            self.assembler.instantiate(match, self.frame(), "en")

    def _full_registry(self, overrides=None):
        overrides = dict(overrides or {})
        registry = RuntimeServiceRegistry()
        for ref in CANONICAL_RUNTIME_RESOURCES:
            registry.register(ref, overrides.get(ref, lambda: True))
        registry.validate_resources()
        return registry

    def test_registry_rejects_duplicate_and_missing_services(self):
        registry = RuntimeServiceRegistry()
        registry.register("resource:runtime_process", lambda: True)
        with self.assertRaises(ValueError):
            registry.register("resource:runtime_process", lambda: True)
        with self.assertRaises(ValueError):
            registry.validate_resources()

    def test_unknown_resource_stays_unknown_and_is_not_numeric_zero(self):
        registry = self._full_registry(
            {"resource:inference_engine": lambda: None}
        )
        snapshot = registry.capture(
            self_ref="participant:system",
            cycle_ref="cycle:unknown",
            authority_generation=1,
            world_revision=1,
        )
        self.assertEqual(snapshot.state("resource:inference_engine"), "unknown")
        self.assertIsNone(snapshot.by_resource["resource:inference_engine"].score)
        self.assertNotIn("resource:inference_engine", snapshot.critical_blockers)
        self.assertEqual(snapshot.assess().status, "unknown")
        self.assertIsNone(snapshot.assess().score)
        dimensions = {
            fact.args["role:dimension"]: fact.args["role:value"]
            for fact in snapshot.semantic_facts()
        }
        self.assertNotIn("dim:semantic_runtime_support", dimensions)
        with self.assertRaises(OperationalInvariantError):
            OperationalInvariantChecker.require_resource(
                snapshot, "resource:inference_engine", stage=10
            )

    def test_observed_unavailable_resource_is_a_blocker(self):
        registry = self._full_registry(
            {"resource:inference_engine": lambda: False}
        )
        snapshot = registry.capture(
            self_ref="participant:system",
            cycle_ref="cycle:unavailable",
            authority_generation=1,
            world_revision=1,
        )
        self.assertIn("resource:inference_engine", snapshot.critical_blockers)
        self.assertEqual(snapshot.assess().status, "unavailable")

    def test_capability_unknown_dependency_is_explicit_blocker(self):
        evaluator = CapabilityEvaluator(FakeStore())
        projection = {
            "dimensions": [],
            "dependency_edges": [
                {"subject": "cap:query", "depends_on": "resource:inference_engine"}
            ],
            "capabilities": ["cap:query"],
        }
        assessment = evaluator.evaluate(
            "participant:system",
            projection,
            (
                RuntimeObservation(
                    "resource:inference_engine", None, "provider:test", "unknown"
                ),
            ),
        )[0]
        self.assertEqual(assessment.status, "unknown")
        self.assertIsNone(assessment.score)
        self.assertEqual(assessment.blockers, ())
        self.assertIn(
            "resource:inference_engine", assessment.proof["unknown_dependencies"]
        )

    def test_state_modes_and_transition_commit_evidence_are_enforced(self):
        for mode in ("predicted", "simulated", "desired"):
            with self.assertRaises(ValueError):
                StateAssertion(
                    f"state:{mode}",
                    "participant:system",
                    "dim:runtime_process_support",
                    {"literal": {"type": "float", "value": 1.0}},
                    mode,
                    "source:test",
                    durable=True,
                )
        with self.assertRaises(ValueError):
            TransitionReceipt(
                "receipt:test",
                "preview:test",
                "committed",
                True,
                (),
                committed_fact_refs=("fact:test",),
            )

    def test_pending_learning_queue_is_single_expiring_and_commit_bound(self):
        state = DialogueState(max_pending=1, expiry_turns=2)
        response = self._learning_response("Alpha", goal_ref="goal:Alpha")
        state.observe_response(
            response,
            self._verified_surface_proof(response, "What does Alpha refer to here?"),
            cycle_ref="cycle:1",
            turn_index=1,
        )
        self.assertEqual(len(state.context(1)["pending_learning_obligations"]), 1)
        pending = state.pending
        self.assertIsNotNone(pending)
        with self.assertRaisesRegex(ValueError, "consume_after_commit"):
            state.consume(pending.obligation_ref)
        with self.assertRaisesRegex(ValueError, "commit receipt"):
            state.consume_after_commit(pending.obligation_ref, commit_receipt_ref=None)
        consumed = state.consume_after_commit(
            pending.obligation_ref, commit_receipt_ref="receipt:commit"
        )
        self.assertEqual(consumed.surface, "Alpha")
        self.assertIsNone(state.pending)
        state.observe_response(
            self._learning_response("Beta", goal_ref="goal:Beta"),
            self._verified_surface_proof(
                self._learning_response("Beta", goal_ref="goal:Beta"),
                "What does Beta refer to here?",
            ),
            turn_index=2,
        )
        self.assertEqual(state.context(5)["pending_learning_obligations"], [])

    def test_unverified_response_does_not_create_dialogue_obligation(self):
        state = DialogueState()
        response = ResponseCSIR(
            "response:failed-learning",
            "request_learning_evidence",
            "participant:user",
            evidence_literals=("UnknownName",),
            qualifiers={"learning_operation": "resolve_designation"},
            obligation_ref="goal:failed-learning",
        )
        state.observe_response(
            response,
            {"verified": False, "surface_decision": {"surface": "not-shown"}},
            cycle_ref="cycle:failed",
            turn_index=1,
        )
        self.assertEqual(state.pending_all, ())
        self.assertEqual(state.context()["last_surface_decision"], {})

    def test_exact_surface_plan_is_case_sensitive(self):
        pack = SimpleNamespace(
            data={
                "response_examples": [
                    {"semantic": "RESPONSE greet", "surface_plan": "Hello."}
                ]
            }
        )
        index = ExactSurfacePlanIndex(pack, "response_examples")
        self.assertTrue(index.realize("RESPONSE greet")[1]["authorized_transform"])
        self.assertFalse(index.realize("response greet")[1]["authorized_transform"])

    def test_pointer_substitution_does_not_collide_on_prefixes(self):
        realizer = PointerRealizer.__new__(PointerRealizer)
        realizer.s = FakeStore()
        realizer.pack = SimpleNamespace(
            language="en", grammar={"and"}, hash="pack:test"
        )
        text, proof = realizer._verify_and_substitute(
            "@A1 and @A10",
            {"authorized_transform": True},
            {
                "@A1": {"kind": "atom", "value": "participant:system"},
                "@A10": {"kind": "atom", "value": "participant:user"},
            },
        )
        self.assertEqual(text, "CEMM and Chibueze Opata")
        self.assertTrue(proof["verified"])

    def test_perspective_aware_name_realization(self):
        language_data = json.loads(
            (self.repo / "cemm/language_packs/en.json").read_text(encoding="utf-8")
        )
        pack = SimpleNamespace(
            data=language_data, language="en", hash=language_data["pack_hash"]
        )
        response = ResponseCSIR(
            "response:name",
            "answer_bindings",
            "participant:user",
            facts=(
                Fact(
                    "fact:name",
                    "op:designation",
                    {
                        "role:target": "participant:system",
                        "role:label_type": "label:name",
                        "role:surface": {"literal": {"type": "text", "value": "CEMM"}},
                        "role:language": {"literal": {"type": "text", "value": "en"}},
                    },
                ),
            ),
            bindings=({"?q0": {"literal": {"type": "text", "value": "CEMM"}}},),
            qualifiers={"query_ref": "query:name", "query_kind": "designation_property", "property_ref": "label:name", "subject_ref": "participant:system"},
            obligation_ref="goal:name",
        )
        frame = SimpleNamespace(
            speaker_ref="participant:system", addressee_ref="participant:user"
        )
        text, proof = CanonicalResponseRealizer(FakeStore(), pack).realize(
            response, frame
        )
        self.assertEqual(text, "My name is CEMM.")
        self.assertTrue(proof["verified"])

    def test_missing_semantic_slot_contract_blocks_surface(self):
        pack = SimpleNamespace(
            language="en",
            hash="pack:test",
            data={
                "response_grammar": [
                    {
                        "ref": "en:test",
                        "when": {"action": "answer_bindings", "query_kind": "type_query"},
                        "template": "{subject} is a {value}.",
                        "required_slots": ["subject", "value"],
                        "semantic_slots": ["subject_ref", "value"],
                    }
                ],
                "reference_realization": [],
                "predicate_realization": [],
                "orthography": {"sentence_initial_capitalization": True},
            },
        )
        response = ResponseCSIR(
            "response:missing",
            "answer_bindings",
            "participant:user",
            qualifiers={"query_ref": "query:missing", "query_kind": "type_query", "subject_ref": "participant:system"},
            obligation_ref="goal:missing",
        )
        frame = SimpleNamespace(
            speaker_ref="participant:system", addressee_ref="participant:user"
        )
        text, proof = CanonicalResponseRealizer(FakeStore(), pack).realize(
            response, frame
        )
        self.assertEqual(text, "")
        self.assertFalse(proof["verified"])
        self.assertTrue(proof["unresolved_semantic_payload"])

    def test_operational_response_is_structured_snapshot_assessment(self):
        snapshot = self._full_registry().capture(
            self_ref="participant:system",
            cycle_ref="cycle:response",
            authority_generation=1,
            world_revision=1,
        )
        goal = SimpleNamespace(
            kind="answer_query", goal_ref="goal:operational",
            source_ref="query:operational", payload={}
        )
        decision = SimpleNamespace(selected=goal, reason="test")
        query_result = SimpleNamespace(
            qualifiers={"query_kind": "operational_condition_query"},
            status="answered",
            query_ref="query:operational",
            bindings=(),
            unresolved_variables=(),
            coverage=1.0,
        )
        response = ResponseBuilder().build(
            audience_ref="participant:user",
            goal_decision=decision,
            query_result=query_result,
            operational_snapshot=snapshot,
        )
        self.assertEqual(response.action, "report_operational_condition")
        self.assertEqual(response.facts, ())
        self.assertEqual(response.qualifiers["assessment_status"], "operating_normally")
        self.assertEqual(response.qualifiers["snapshot_ref"], snapshot.snapshot_ref)

    def test_retrieval_rejects_operator_only_but_accepts_bound_multi_clause_query(self):
        config = SimpleNamespace(
            retrieval_max_seed_facts=100,
            retrieval_max_rules=32,
            retrieval_max_depth=3,
        )
        retriever = SemanticRetriever(None, config, 1)
        broad = retriever.plan(
            ({"operator": "op:state", "args": {}, "stance": "support"},)
        )
        self.assertFalse(broad.selective)
        selective = retriever.plan(
            (
                {
                    "operator": "op:state",
                    "args": {
                        "role:subject": "participant:system",
                        "role:dimension": "dim:runtime_process_support",
                        "role:value": "?q0",
                    },
                    "stance": "support",
                },
                {
                    "operator": "op:state",
                    "args": {
                        "role:subject": "participant:system",
                        "role:dimension": "dim:critical_blocker_count",
                        "role:value": "?q1",
                    },
                    "stance": "support",
                },
            )
        )
        self.assertTrue(selective.selective)
        self.assertGreaterEqual(len(selective.indexed_constraints), 4)

    def test_retrieval_never_broadens_to_all_facts_mentioning_a_referent(self):
        class Store:
            def __init__(self):
                self.facts_mentioning_called = False

            def matching_facts(self, restrictions, limit):
                return ()

            def relevant_rules(self, **kwargs):
                return ()

            def decode_rule_side(self, value):
                return ()

            def facts_mentioning(self, refs, limit):
                self.facts_mentioning_called = True
                raise AssertionError("broad referent expansion is forbidden")

        config = SimpleNamespace(
            retrieval_max_seed_facts=100,
            retrieval_max_rules=32,
            retrieval_max_depth=3,
        )
        store = Store()
        result = SemanticRetriever(store, config, 1).retrieve(
            (
                {
                    "operator": "op:type",
                    "args": {
                        "role:instance": "participant:system",
                        "role:class": "?q0",
                    },
                    "stance": "support",
                },
            )
        )
        self.assertFalse(store.facts_mentioning_called)
        self.assertEqual(result.facts, ())


    def test_provider_contract_error_is_not_hidden_as_unavailability(self):
        registry = self._full_registry(
            {
                "resource:inference_engine": lambda: {
                    "state": "unknown",
                    "score": 0.0,
                }
            }
        )
        with self.assertRaises(OperationalProviderContractError):
            registry.capture(
                self_ref="participant:system",
                cycle_ref="cycle:provider-contract",
                authority_generation=1,
                world_revision=1,
            )

    def test_runtime_and_capability_value_objects_enforce_unknown_none(self):
        with self.assertRaises(ValueError):
            RuntimeObservation(
                "resource:test", 0.0, "provider:test", "unknown"
            )
        with self.assertRaises(ValueError):
            CapabilityAssessment(
                "assessment:test",
                "participant:system",
                "cap:test",
                0.0,
                "unknown",
                {},
                (),
                {},
            )

    def test_unknown_capability_pointerization_has_no_numeric_score(self):
        response = ResponseCSIR(
            "response:capability-unknown",
            "report_capability",
            "participant:user",
            target_ref="cap:query",
            qualifiers={"status": "unknown", "score": None},
            obligation_ref="goal:capability-unknown",
        )
        semantic, mapping = pointerize_response(response)
        self.assertNotIn(" SCORE ", f" {semantic} ")
        self.assertFalse(any(key.startswith("@N") for key in mapping))

    def test_literal_colon_is_not_treated_as_internal_semantic_ref(self):
        realizer = PointerRealizer.__new__(PointerRealizer)
        realizer.s = FakeStore()
        realizer.pack = SimpleNamespace(
            language="en", grammar={"see"}, hash="pack:test"
        )
        text, proof = realizer._verify_and_substitute(
            "See @E0",
            {"authorized_transform": True},
            {
                "@E0": {
                    "kind": "evidence",
                    "value": "https://example.com/a:b",
                    "literal_type": "text",
                    "context": "response:evidence",
                }
            },
        )
        self.assertTrue(text)
        self.assertTrue(proof["verified"])
        self.assertFalse(proof["internal_id_leak"])

    def test_relation_uncertainty_realizes_structured_subject_and_relation(self):
        language_data = json.loads(
            (self.repo / "cemm/language_packs/en.json").read_text(encoding="utf-8")
        )
        pack = SimpleNamespace(
            data=language_data, language="en", hash=language_data["pack_hash"]
        )
        response = ResponseCSIR(
            "response:relation-unknown",
            "report_target_uncertainty",
            "participant:user",
            qualifiers={
                "query_ref": "query:relation-unknown",
                "query_kind": "relation_query",
                "subject_ref": "participant:system",
                "relation_ref": "rel:knows",
                "object_surface": "Donald Trump",
            },
            obligation_ref="goal:relation",
        )
        frame = SimpleNamespace(
            speaker_ref="participant:system", addressee_ref="participant:user"
        )
        text, proof = CanonicalResponseRealizer(FakeStore(), pack).realize(
            response, frame
        )
        self.assertEqual(
            text, "I do not have evidence that I know Donald Trump."
        )
        self.assertTrue(proof["verified"])

    def test_operational_response_target_must_be_output_speaker(self):
        language_data = json.loads(
            (self.repo / "cemm/language_packs/en.json").read_text(encoding="utf-8")
        )
        pack = SimpleNamespace(
            data=language_data, language="en", hash=language_data["pack_hash"]
        )
        response = ResponseCSIR(
            "response:wrong-operational-target",
            "report_operational_condition",
            "participant:user",
            target_ref="participant:user",
            qualifiers={
                "query_ref": "query:operational-target",
                "query_kind": "operational_condition_query",
                "assessment_status": "operating_normally",
                "snapshot_ref": "snapshot:test",
            },
            obligation_ref="goal:operational-target",
        )
        frame = SimpleNamespace(
            speaker_ref="participant:system", addressee_ref="participant:user"
        )
        text, proof = CanonicalResponseRealizer(FakeStore(), pack).realize(
            response, frame
        )
        self.assertEqual(text, "")
        self.assertFalse(proof["verified"])
        self.assertFalse(proof["response_equivalence"]["target_preserved"])

    def test_extra_consumed_unit_ref_invalidates_coverage(self):
        units = [Unit("u0", "function", "own", features={"emphasis": True})]
        coverage = CoveragePolicy.build(units, ("u0", "u-does-not-exist"))
        self.assertFalse(coverage.complete)
        self.assertFalse(coverage.invariants["all_units_accounted_for"])
        self.assertEqual(coverage.silent_unit_refs, ())
        self.assertEqual(
            coverage.extraneous_consumed_unit_refs, ("u-does-not-exist",)
        )

    def test_duplicate_unit_refs_are_explicit_and_non_executable(self):
        units = [
            Unit("u0", "unknown", "alpha"),
            Unit("u0", "unknown", "beta", index=1),
        ]
        coverage = CoveragePolicy.build(units, ())
        self.assertFalse(coverage.complete)
        self.assertEqual(coverage.duplicate_input_unit_refs, ("u0",))
        self.assertFalse(coverage.invariants["unique_input_unit_refs"])

    def test_unknown_and_unavailable_both_block_use_without_collapsing(self):
        unknown_registry = self._full_registry(
            {"resource:inference_engine": lambda: None}
        )
        unavailable_registry = self._full_registry(
            {"resource:inference_engine": lambda: False}
        )
        unknown = unknown_registry.capture(
            self_ref="participant:system",
            cycle_ref="cycle:unknown-distinct",
            authority_generation=1,
            world_revision=1,
        )
        unavailable = unavailable_registry.capture(
            self_ref="participant:system",
            cycle_ref="cycle:unavailable-distinct",
            authority_generation=1,
            world_revision=1,
        )
        self.assertEqual(unknown.state("resource:inference_engine"), "unknown")
        self.assertEqual(
            unavailable.state("resource:inference_engine"), "unavailable"
        )
        self.assertIsNone(unknown.score("resource:inference_engine"))
        self.assertEqual(unavailable.score("resource:inference_engine"), 0.0)
        with self.assertRaisesRegex(OperationalInvariantError, "without resolved"):
            OperationalInvariantChecker.require_resource(
                unknown, "resource:inference_engine", stage=10
            )
        with self.assertRaisesRegex(OperationalInvariantError, "observed unavailability"):
            OperationalInvariantChecker.require_resource(
                unavailable, "resource:inference_engine", stage=10
            )

    def test_dialogue_require_rejects_absent_or_expired_obligation(self):
        state = DialogueState(expiry_turns=1)
        with self.assertRaises(ValueError):
            state.require("obligation:missing")
        response = self._learning_response("Alpha", goal_ref="goal:learning-require")
        state.observe_response(
            response,
            self._verified_surface_proof(response, "What does Alpha refer to here?"),
            turn_index=1,
        )
        ref = state.pending.obligation_ref
        self.assertEqual(state.require(ref).obligation_ref, ref)
        state.expire(3)
        with self.assertRaises(ValueError):
            state.require(ref)



    def test_designation_query_generalizes_across_participant_perspective(self):
        schema = next(
            item for item in self.form_data["schemas"]
            if item["family"] == "designation_query"
        )
        target = next(step for step in schema["steps"] if step["slot"] == "target")
        self.assertEqual(target["features"].get("possessive"), True)
        self.assertNotIn("participant_role", target["features"])
        self.assertNotIn("person", target["features"])
        examples = [
            item for item in self.form_seed["examples"]
            if item["family"] == "designation_query"
        ]
        self.assertTrue(any(item["tokens"] == ["what", "is", "my", "name"] for item in examples))
        for example in examples:
            matches = [
                item for item in self.assembler.evidence_records(
                    SimpleNamespace(grounding_hypotheses=(SimpleNamespace(
                        hypothesis_ref="hypothesis:designation-query-generalization",
                        units=replay_units(example, self.lexeme_index),
                        score=0.0,
                    ),))
                )
                if item.schema_family == "designation_query" and item.coverage.executable
            ]
            self.assertGreaterEqual(len(matches), 1)

    def test_contextual_meaning_query_is_feature_driven_and_complete(self):
        match = self.replay_match("contextual_meaning_query")
        self.assertTrue(match.coverage.executable)
        self.assertEqual(match.coverage.critical_residual_refs, ())
        schema = next(
            item for item in self.form_data["schemas"]
            if item["family"] == "contextual_meaning_query"
        )
        self.assertFalse(any(
            key in {"literal", "surface", "regex", "phrase", "tokens"}
            for step in schema["steps"]
            for key in step
        ))

    def test_named_entity_proposals_defer_to_structural_lexical_forms(self):
        pack = FormPack(self.repo / "cemm/form_packs/en.json")
        provider = HeuristicProperNameProvider(
            protected_forms=pack.named_entity_blocked_forms
        )
        candidate = NormalizationCandidate(
            "normalization:test", "I", "I", 0.0
        )
        pronoun = TokenEvidence(
            "token:i", "I", "i", 0, 1, 0, 1, "word"
        )
        self.assertEqual(tuple(provider.propose(candidate, (pronoun,))), ())
        name_candidate = NormalizationCandidate(
            "normalization:name", "Opata", "Opata", 0.0
        )
        name = TokenEvidence(
            "token:opata", "Opata", "opata", 0, 5, 0, 5, "word"
        )
        proposals = tuple(provider.propose(name_candidate, (name,)))
        self.assertEqual(len(proposals), 1)
        self.assertEqual(proposals[0].surface, "Opata")


    def test_contextual_learning_probe_preserves_antecedent_surface(self):
        interpreter = object.__new__(Interpreter)
        interpreter._candidate_unknown_kinds_cache = ("concept", "entity")
        packet = {
            "qualifiers": {"learning_operation": "resolve_designation"},
            "query": {
                "restrictions": [{
                    "operator": "op:designation",
                    "args": {
                        "role:surface": {"literal": {"type": "text", "value": "lol"}}
                    },
                }],
                "projection": ["?q0", "?q1"],
            },
        }
        probes = interpreter._learning_frontier_for_packet(
            packet,
            {
                "captures": {
                    "antecedent": {"literal": {"type": "text", "value": "lol"}}
                },
                "coverage": {"coverage_ref": "coverage:contextual"},
                "construction_ref": "en:schema:contextual_meaning_query",
                "hypothesis_ref": "hypothesis:contextual",
                "match_seed_ref": "seed:contextual",
                "construction_evidence_ref": "match:contextual",
            },
        )
        self.assertEqual(len(probes), 1)
        self.assertEqual(probes[0]["surface"], "lol")
        self.assertEqual(
            probes[0]["probe_query"]["restrictions"][0]["args"]["role:surface"]["literal"]["value"],
            "lol",
        )

    def test_strict_coverage_remains_enabled(self):
        source = (self.repo / "cemm/interpreter.py").read_text(encoding="utf-8")
        self.assertIn("require_coverage=True", source)
        self.assertNotIn("require_coverage=False", source)

    def test_designation_resource_is_gated_by_declared_use_not_fixture_shape(self):
        source = (
            self.repo / "tools/apply_semantic_operational_source_rewrite.py"
        ).read_text(encoding="utf-8")
        self.assertIn("designation_index_status", source)
        self.assertIn("designation_index_store_handle_unavailable", source)
        self.assertIn("SELECT count(*) FROM designation_index", source)
        self.assertIn("def _interpreter_resources(self, operation):", source)
        self.assertIn('self._interpreter_resources("observe")', source)
        self.assertNotIn(
            '("resource:semantic_runtime", "resource:designation_index")',
            source,
        )

    def test_reduced_interpreter_is_not_forced_to_use_designation_index(self):
        self.assertEqual(
            declared_operation_resources(
                SimpleNamespace(),
                "observe",
                baseline=("resource:semantic_runtime",),
            ),
            ("resource:semantic_runtime",),
        )
        actual = object.__new__(Interpreter)
        self.assertEqual(
            declared_operation_resources(
                actual,
                "observe",
                baseline=("resource:semantic_runtime",),
            ),
            ("resource:designation_index", "resource:semantic_runtime"),
        )
        invalid = SimpleNamespace(
            operational_resources_for=lambda _operation: ("resource:not-in-abi",)
        )
        with self.assertRaisesRegex(
            OperationalProviderContractError, "outside runtime ABI"
        ):
            declared_operation_resources(
                invalid,
                "observe",
                baseline=("resource:semantic_runtime",),
            )

    def test_real_interpreter_declares_designation_index_use(self):
        interpreter = object.__new__(Interpreter)
        self.assertEqual(
            interpreter.operational_resources_for("observe"),
            ("resource:designation_index",),
        )
        self.assertEqual(
            interpreter.operational_resources_for("delex_for_rule"),
            ("resource:designation_index",),
        )
        with self.assertRaisesRegex(ValueError, "unsupported interpreter operation"):
            interpreter.operational_resources_for("invented")

    def test_source_rewrite_matches_audited_one_line_response_anchor(self):
        source = (
            self.repo / "tools/apply_semantic_operational_source_rewrite.py"
        ).read_text(encoding="utf-8")
        audited = (
            '            epistemic_placement=placement,\n'
            '        )\n'
            '        stages.add(Stage.RESPONSE_CSIR, counts={"responses": 1}, '
            'refs=(response_csir.response_ref,))\n'
        )
        self.assertIn(audited, source)
        self.assertNotIn(
            '        stages.add(Stage.RESPONSE_CSIR,\n',
            source,
        )

    def test_windows_paths_are_normalized_in_validator(self):
        source = (
            self.repo / "tools/validate_semantic_operational_contract.py"
        ).read_text(encoding="utf-8")
        self.assertIn("path.relative_to(repo).as_posix()", source)

    def test_response_examples_are_deduplicated_by_semantic_identity(self):
        source = (
            self.repo / "tools/migrate_semantic_operational_assets.py"
        ).read_text(encoding="utf-8")
        self.assertIn('lambda item: canonical(item.get("semantic"))', source)
        self.assertNotIn(
            'lambda item: canonical((item.get("semantic"), item.get("surface_plan")))',
            source,
        )

    def test_generator_receipt_is_computed_and_version_aligned(self):
        receipt = self.form_data["training_receipt"]
        self.assertEqual(self.form_data["feature_algebra_version"], COVERAGE_ABI_VERSION)
        self.assertEqual(receipt["feature_algebra_version"], COVERAGE_ABI_VERSION)
        self.assertEqual(receipt["receipt_version"], COVERAGE_ABI_VERSION)
        self.assertEqual(receipt["example_count"], len(receipt["positive_replay"]))
        self.assertEqual(receipt["family_count"], len(self.form_data["schemas"]))
        self.assertEqual(receipt["annotated_replay_coverage"], 1.0)
        self.assertTrue(all(row["blocked"] for row in receipt["critical_slot_mutations"]))
        self.assertTrue(all(row["blocked"] for row in receipt["negative_probes"]))
        self.assertTrue(all(
            row["intended_family"] in row["executable_families"]
            for row in receipt["cross_family_collision_matrix"]
        ))
        self.assertTrue(all(
            row["mode"] in {"leave_one_out", "leave_one_out_partial", "reviewed_singleton"}
            for row in receipt["family_holdouts"]
        ))

    def test_generator_is_byte_deterministic_and_hash_bound(self):
        first = build_pack(self.repo / "cemm/training/en_form_schema_seed.json")
        second = build_pack(self.repo / "cemm/training/en_form_schema_seed.json")
        self.assertEqual(first, second)
        material = {key: value for key, value in first.items() if key != "pack_hash"}
        expected_hash = hashlib.sha256(
            json.dumps(material, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()
        ).hexdigest()
        self.assertEqual(first["pack_hash"], expected_hash)
        self.assertEqual(first, self.form_data)

    def test_coverage_missing_receipt_fails_closed(self):
        with self.assertRaisesRegex(CoverageIntegrityError, "missing"):
            coverage_from_dict(None)
        with self.assertRaisesRegex(CoverageIntegrityError, "expected units"):
            coverage_from_dict({
                "abi_version": COVERAGE_ABI_VERSION,
                "coverage_ref": "coverage:empty",
                "expected_unit_refs": [],
            })

    def test_coverage_tampering_is_rejected(self):
        units = [
            Unit("u0", "anchor", "you", semantic_ref="participant:system"),
            Unit("u1", "unknown", "know", features={"predicate": True}, index=1),
        ]
        coverage = CoveragePolicy.build(
            units,
            ("u0",),
            role_by_unit_ref={"u0": "subject"},
            required_semantic_roles=("subject", "predicate"),
        )
        data = coverage.as_dict()
        self.assertFalse(data["complete"])
        forged = copy.deepcopy(data)
        forged["complete"] = True
        forged["critical_residual_refs"] = []
        forged["missing_semantic_roles"] = []
        forged["invariants"]["semantic_roles_satisfied"] = True
        with self.assertRaises(CoverageIntegrityError):
            coverage_from_dict(forged)

    def test_coverage_explicitly_reports_duplicate_consumed_refs(self):
        unit = Unit("u0", "anchor", "you", semantic_ref="participant:system")
        coverage = CoveragePolicy.build(
            [unit],
            ("u0", "u0"),
            role_by_unit_ref={"u0": "subject"},
            required_semantic_roles=("subject",),
        )
        self.assertEqual(coverage.duplicate_consumed_unit_refs, ("u0",))
        self.assertFalse(coverage.executable)

    def test_coverage_missing_required_role_blocks_execution(self):
        unit = Unit("u0", "anchor", "you", semantic_ref="participant:system")
        coverage = CoveragePolicy.build(
            [unit],
            ("u0",),
            role_by_unit_ref={"u0": "subject"},
            required_semantic_roles=("subject", "predicate", "object"),
        )
        self.assertEqual(coverage.missing_semantic_roles, ("object", "predicate"))
        self.assertFalse(coverage.executable)

    def test_donald_trump_query_cannot_match_without_relation_and_object(self):
        only_you = [
            Unit(
                "u0", "anchor", "you",
                semantic_ref="participant:system", atom_kind="participant",
                features={"category": "reference", "person": "second"},
            )
        ]
        hypothesis = SimpleNamespace(hypothesis_ref="hypothesis:you-only", units=tuple(only_you), score=0.0)
        lattice = SimpleNamespace(grounding_hypotheses=(hypothesis,))
        executable = [item for item in self.assembler.evidence_records(lattice) if item.coverage.executable]
        self.assertEqual(executable, [])

    def test_surface_choice_explanation_preserves_quoted_choices(self):
        match = self.replay_match("surface_choice_explanation_query")
        packet = self.assembler.instantiate(match, self.frame({
            "last_surface_decision_ref": "decision:prior",
        }), "en")
        qualifiers = packet["qualifiers"]
        self.assertEqual(qualifiers["surface_choice_a"]["literal"]["value"], "the")
        self.assertEqual(qualifiers["surface_choice_b"]["literal"]["value"], "my")
        self.assertEqual(qualifiers["surface_decision_ref"], "decision:prior")

    def test_attributed_pattern_matching_claim_preserves_open_predicate(self):
        match = self.replay_match("attributed_open_predication_claim")
        packet = self.assembler.instantiate(match, self.frame(), "en")
        self.assertEqual(packet["force"], "claim")
        self.assertEqual(packet["qualifiers"]["subject_ref"], "replay:anchor:subject")
        self.assertEqual(packet["qualifiers"]["predicate_surface"]["literal"]["value"], "pattern matching")
        self.assertEqual(packet["qualifiers"]["claim_kind"], "attributed_open_predication")

    def test_registry_provider_exception_is_not_outage_evidence(self):
        def boom():
            raise RuntimeError("provider bug")
        registry = self._full_registry({"resource:inference_engine": boom})
        with self.assertRaises(OperationalProviderExecutionError):
            registry.capture(
                self_ref="participant:system",
                cycle_ref="cycle:provider-fault",
                authority_generation=1,
                world_revision=1,
            )

    def test_registry_object_missing_attribute_is_contract_fault(self):
        registry = RuntimeServiceRegistry()
        owner = SimpleNamespace()
        for ref in CANONICAL_RUNTIME_RESOURCES:
            if ref == "resource:inference_engine":
                registry.register_object(ref, owner, "missing")
            else:
                registry.register(ref, lambda: True)
        with self.assertRaisesRegex(OperationalProviderContractError, "no attribute"):
            registry.capture(
                self_ref="participant:system",
                cycle_ref="cycle:missing-attribute",
                authority_generation=1,
                world_revision=1,
            )

    def test_operational_snapshot_rejects_mixed_cycle_and_duplicate_resource(self):
        snapshot = self._full_registry().capture(
            self_ref="participant:system",
            cycle_ref="cycle:clean",
            authority_generation=1,
            world_revision=1,
        )
        first = snapshot.observations[0]
        mixed = RuntimeResourceObservation(
            first.observation_ref + ":mixed",
            first.resource_ref,
            first.state,
            first.score,
            first.provider_ref,
            first.observed_at,
            "cycle:other",
            first.authority_generation,
            first.world_revision,
            first.evidence,
        )
        with self.assertRaises(OperationalSnapshotIntegrityError):
            type(snapshot)(
                snapshot.snapshot_ref,
                snapshot.self_ref,
                snapshot.cycle_ref,
                snapshot.authority_generation,
                snapshot.world_revision,
                (mixed,) + snapshot.observations[1:],
                snapshot.required_resources,
                snapshot.critical_blockers,
                snapshot.captured_at,
            )
        with self.assertRaises(OperationalSnapshotIntegrityError):
            type(snapshot)(
                snapshot.snapshot_ref,
                snapshot.self_ref,
                snapshot.cycle_ref,
                snapshot.authority_generation,
                snapshot.world_revision,
                snapshot.observations + (snapshot.observations[0],),
                snapshot.required_resources,
                snapshot.critical_blockers,
                snapshot.captured_at,
            )

    def test_stage_resource_ledger_is_snapshot_bound_and_idempotent(self):
        snapshot = self._full_registry().capture(
            self_ref="participant:system", cycle_ref="cycle:ledger",
            authority_generation=1, world_revision=1,
        )
        ledger = OperationalUsageLedger(snapshot)
        first = OperationalInvariantChecker.require_resource(
            snapshot, "resource:inference_engine", stage=10, ledger=ledger
        )
        second = OperationalInvariantChecker.require_resource(
            snapshot, "resource:inference_engine", stage=10, ledger=ledger
        )
        self.assertEqual(first.use_ref, second.use_ref)
        self.assertEqual(len(ledger.uses), 1)
        self.assertEqual(ledger.as_dict()["snapshot_ref"], snapshot.snapshot_ref)

    def test_degraded_resource_requires_explicit_stage_policy(self):
        snapshot = self._full_registry({
            "resource:inference_engine": lambda: {"state": "degraded", "score": 0.6}
        }).capture(
            self_ref="participant:system", cycle_ref="cycle:degraded",
            authority_generation=1, world_revision=1,
        )
        with self.assertRaisesRegex(OperationalInvariantError, "degraded"):
            OperationalInvariantChecker.require_resource(
                snapshot, "resource:inference_engine", stage=10
            )
        receipt = OperationalInvariantChecker.require_resource(
            snapshot, "resource:inference_engine", stage=10,
            allow_degraded=True, minimum_score=0.5,
        )
        self.assertEqual(receipt.observed_state, "degraded")

    def test_goal_arbiter_never_selects_blocked_answer(self):
        query_result = SimpleNamespace(
            query_ref="query:blocked",
            unresolved_variables=("?q0",),
            blocking_frontiers=("frontier:critical",),
            as_dict=lambda: {},
        )
        frontier = SimpleNamespace(
            frontier_ref="frontier:critical",
            blocks=("interpretation", "answer"),
            as_dict=lambda: {"frontier_ref": "frontier:critical"},
        )
        candidates = GoalArbiter().candidates(
            act=None, query_result=query_result, frontiers=(frontier,)
        )
        decision = GoalArbiter.decide(candidates)
        self.assertEqual(decision.selected.kind, "clarify")
        self.assertTrue(next(x for x in candidates if x.kind == "answer_query").blockers)

    def test_goal_arbiter_selects_none_when_all_goals_blocked(self):
        decision = GoalArbiter.decide((
            GoalCandidate("goal:a", "answer_query", "query:a", 1.0, blockers=("blocked",)),
            GoalCandidate("goal:b", "handle_directive", "act:b", 2.0, blockers=("blocked",)),
        ))
        self.assertIsNone(decision.selected)
        self.assertEqual(decision.reason, "all_goals_blocked")

    def test_retrieval_rejects_disconnected_unbound_clause(self):
        config = SimpleNamespace(
            retrieval_max_seed_facts=10,
            retrieval_max_rules=5,
            retrieval_max_depth=2,
        )
        plan = SemanticRetriever(None, config, 1).plan((
            {"operator": "op:type", "args": {"role:instance": "participant:system", "role:class": "?t"}},
            {"operator": "op:relation", "args": {"role:subject": "?x", "role:relation": "?r", "role:object": "?y"}},
        ))
        self.assertFalse(plan.selective)
        self.assertIn("disconnected_unbound_restrictions", plan.underconstrained_reason)

    def test_retrieval_rechecks_and_rejects_store_rows(self):
        good = Fact("fact:good", "op:type", {"role:instance": "participant:system", "role:class": "concept:digital_agent"})
        bad = Fact("fact:bad", "op:type", {"role:instance": "participant:user", "role:class": "concept:person"})
        class Store:
            def matching_facts(self, restrictions, limit):
                return (bad, good)
            def relevant_rules(self, **kwargs): return ()
            def decode_rule_side(self, value): return ()
        config = SimpleNamespace(retrieval_max_seed_facts=10, retrieval_max_rules=0, retrieval_max_depth=0)
        result = SemanticRetriever(Store(), config, 1).retrieve((
            {"operator": "op:type", "args": {"role:instance": "participant:system", "role:class": "?t"}},
        ), salient_refs=("participant:user",))
        self.assertEqual(tuple(x.ref for x in result.facts), ("fact:good",))
        self.assertEqual(result.trace["rejected_store_rows"], 1)
        self.assertFalse(result.trace["salience_broadening"])

    def test_settler_merges_provenance_equivalent_candidates_before_posterior(self):
        class Compiler:
            def compile(self, packet, _prefix):
                return copy.deepcopy(packet), []

        config = SimpleNamespace(
            settler_rounds=4,
            settler_posterior_threshold=0.48,
            settler_margin_threshold=0.06,
            settler_top_k=10,
        )
        candidates = []
        for index in range(8):
            unit = Unit(
                f"u{index}", "function", "name",
                features={"property_marker": True}, index=index,
            )
            coverage = CoveragePolicy.build(
                (unit,), (unit.unit_ref,),
                role_by_unit_ref={unit.unit_ref: "property"},
                required_semantic_roles=("property",),
                schema_ref="en:schema:designation_query",
                hypothesis_ref=f"hypothesis:{index}",
                match_seed_ref=f"seed:{index}",
            )
            candidates.append(SimpleNamespace(
                packet={
                    "force": "query",
                    "apps": [],
                    "query": {
                        "query_ref": "query:name",
                        "restrictions": [{
                            "operator": "op:designation",
                            "args": {
                                "role:target": "participant:system",
                                "role:label_type": "label:name",
                                "role:surface": "?q0",
                            },
                        }],
                        "variables": [{"ref": "?q0"}],
                        "projection": ["?q0"],
                        "qualifiers": {"query_kind": "designation_property"},
                    },
                    "qualifiers": {
                        "construction_family": "designation_query",
                        "construction_schema_ref": "en:schema:designation_query",
                        "coverage_ref": coverage.coverage_ref,
                        "construction_evidence_ref": f"match:{index}",
                    },
                },
                score=1.0 - index * 0.001,
                trace={
                    "candidate_ref": f"match:{index}",
                    "construction_evidence_ref": f"match:{index}",
                    "coverage": coverage.as_dict(),
                },
            ))
        settled, trace = SemanticSettler(None, Compiler(), config).settle(
            candidates, require_coverage=True
        )
        self.assertIsNotNone(settled, trace)
        self.assertEqual(trace["status"], "settled")
        self.assertEqual(len(trace["candidates"]), 1)
        self.assertEqual(len(trace["candidates"][0]["equivalent_candidate_refs"]), 8)

    def test_settler_keeps_meaning_bearing_qualifiers_as_real_alternatives(self):
        class Compiler:
            def compile(self, packet, _prefix):
                return copy.deepcopy(packet), []

        config = SimpleNamespace(
            settler_rounds=4,
            settler_posterior_threshold=0.48,
            settler_margin_threshold=0.06,
            settler_top_k=10,
        )
        candidates = []
        for index, query_kind in enumerate(("designation_property", "type_query")):
            unit = Unit(
                f"alt{index}", "function", "what",
                features={"interrogative": True}, index=index,
            )
            coverage = CoveragePolicy.build(
                (unit,), (unit.unit_ref,),
                role_by_unit_ref={unit.unit_ref: "interrogative"},
                required_semantic_roles=("interrogative",),
                schema_ref=f"schema:{query_kind}",
                hypothesis_ref=f"hypothesis:alt:{index}",
                match_seed_ref=f"seed:alt:{index}",
            )
            candidates.append(SimpleNamespace(
                packet={
                    "force": "query", "apps": [],
                    "query": {
                        "query_ref": f"query:{query_kind}",
                        "restrictions": [{"operator": "op:type", "args": {}}],
                        "variables": [], "projection": [],
                        "qualifiers": {"query_kind": query_kind},
                    },
                    "qualifiers": {
                        "construction_schema_ref": f"schema:{query_kind}",
                        "coverage_ref": coverage.coverage_ref,
                    },
                },
                score=1.0,
                trace={"candidate_ref": f"alt:{index}", "coverage": coverage.as_dict()},
            ))
        settled, trace = SemanticSettler(None, Compiler(), config).settle(
            candidates, require_coverage=True
        )
        self.assertIsNone(settled)
        self.assertEqual(trace["status"], "ambiguous")
        self.assertEqual(len(trace["candidates"]), 2)

    def test_response_builder_rejects_goal_query_mismatch(self):
        goal = SimpleNamespace(kind="answer_query", goal_ref="goal:q", source_ref="query:expected", payload={})
        decision = SimpleNamespace(selected=goal, reason="test")
        result = SimpleNamespace(
            query_ref="query:other", qualifiers={"query_kind": "type_query"},
            status="unknown", coverage=0.0, unresolved_variables=(), bindings=(),
        )
        with self.assertRaisesRegex(ValueError, "exact QueryResult"):
            ResponseBuilder().build(
                audience_ref="participant:user", goal_decision=decision,
                query_result=result,
            )

    def test_response_builder_preserves_multiple_bindings_without_first_result_fallback(self):
        goal = SimpleNamespace(kind="answer_query", goal_ref="goal:multi", source_ref="query:multi", payload={})
        decision = SimpleNamespace(selected=goal, reason="test")
        binding_type = lambda values: SimpleNamespace(values=values, proof_refs=())
        result = SimpleNamespace(
            query_ref="query:multi",
            qualifiers={"query_kind": "type_query", "subject_ref": "participant:system"},
            status="answered", coverage=1.0, unresolved_variables=(),
            bindings=(binding_type({"?q0": "concept:digital_agent"}), binding_type({"?q0": "concept:agent"})),
        )
        response = ResponseBuilder().build(
            audience_ref="participant:user", goal_decision=decision, query_result=result
        )
        self.assertEqual(response.action, "report_multiple_bindings")
        self.assertEqual(len(response.bindings), 2)

    def test_surface_choice_response_requires_exact_verified_prior_decision(self):
        goal = SimpleNamespace(
            kind="explain_surface_choice", goal_ref="goal:meta", source_ref="act:meta",
            payload={"surface_decision_ref": "decision:prior", "surface_choice_a": "the", "surface_choice_b": "my"},
        )
        decision = SimpleNamespace(selected=goal, reason="test")
        with self.assertRaisesRegex(ValueError, "exact prior decision"):
            ResponseBuilder().build(
                audience_ref="participant:user", goal_decision=decision,
                dialogue_context={"last_surface_decision": {"decision_ref": "decision:other"}},
            )
        prior = {
            "decision_ref": "decision:prior",
            "response_ref": "response:prior",
            "response_action": "answer_bindings",
            "chosen_surface": "The name is CEMM.",
            "reference_plan": {"speaker_ref": "participant:system"},
            "response_equivalence": {"equivalent": True},
        }
        response = ResponseBuilder().build(
            audience_ref="participant:user", goal_decision=decision,
            dialogue_context={"last_surface_decision": prior},
        )
        self.assertEqual(response.action, "explain_surface_choice")
        self.assertEqual(response.qualifiers["prior_response_ref"], "response:prior")

    def test_attributed_claim_response_never_substitutes_operational_state(self):
        goal = SimpleNamespace(
            kind="acknowledge_attributed_claim", goal_ref="goal:critique", source_ref="act:critique",
            payload={
                "act_ref": "act:critique",
                "subject_ref": "participant:system",
                "predicate_surface": {"literal": {"type": "text", "value": "pattern matching"}},
                "epistemic_stance": "user_attributed",
            },
        )
        response = ResponseBuilder().build(
            audience_ref="participant:user",
            goal_decision=SimpleNamespace(selected=goal, reason="test"),
        )
        self.assertEqual(response.action, "acknowledge_attributed_claim")
        self.assertEqual(response.qualifiers["predicate_surface"], "pattern matching")
        text, proof = CanonicalResponseRealizer(FakeStore(), self.language_pack()).realize(
            response, self.output_frame()
        )
        self.assertIn("pattern matching", text)
        self.assertTrue(proof["verified"])

    def test_learned_surface_cannot_replace_canonical_same_csir_surface(self):
        response = ResponseCSIR(
            "response:type", "answer_bindings", "participant:user",
            bindings=({"?q0": "concept:digital_agent"},),
            qualifiers={
                "query_ref": "query:type", "query_kind": "type_query",
                "subject_ref": "participant:system",
            },
            obligation_ref="goal:type",
        )
        realizer = PointerRealizer.__new__(PointerRealizer)
        realizer.s = FakeStore()
        realizer.pack = self.language_pack()
        realizer.canonical_response = CanonicalResponseRealizer(realizer.s, realizer.pack)
        class Codec:
            def realize(self, semantic):
                return "CEMM is a digital agent.", {"authorized_transform": True}
        realizer.response_codec = Codec()
        text, proof = realizer.response(response, self.output_frame())
        self.assertEqual(text, "I am a digital agent.")
        self.assertEqual(proof["verification_mode"], "same_response_csir_grammar")
        self.assertFalse(proof["rejected_learned_transform"]["surface_equal_to_canonical"])

    def test_dialogue_rejects_silent_pending_obligation_replacement(self):
        state = DialogueState()
        first = self._learning_response("Alpha", goal_ref="goal:alpha")
        state.observe_response(first, self._verified_surface_proof(first, "What does Alpha refer to here?"), turn_index=1)
        second = self._learning_response("Beta", goal_ref="goal:beta")
        with self.assertRaisesRegex(ValueError, "cannot be silently replaced"):
            state.observe_response(second, self._verified_surface_proof(second, "What does Beta refer to here?"), turn_index=2)
        self.assertEqual(state.pending.surface, "Alpha")

    def test_coverage_receipt_is_bound_to_selected_candidate_provenance(self):
        match = self.replay_match("designation_claim")
        receipt = coverage_from_dict(match.coverage.as_dict())
        receipt.assert_provenance(
            schema_ref=match.schema_ref,
            hypothesis_ref=match.hypothesis_ref,
            match_seed_ref=match.match_seed_ref,
        )
        with self.assertRaisesRegex(CoverageIntegrityError, "provenance"):
            receipt.assert_provenance(
                schema_ref="en:schema:type_query",
                hypothesis_ref=match.hypothesis_ref,
                match_seed_ref=match.match_seed_ref,
            )

    def test_diagnostic_coverage_roundtrip_is_verified_but_non_executable(self):
        diagnostic = InterpretationCoverage.unresolved(
            seed="test",
            schema_ref="diagnostic:test",
            hypothesis_ref="hypothesis:none",
        )
        loaded = coverage_from_dict(diagnostic.as_dict())
        self.assertTrue(loaded.diagnostic_only)
        self.assertFalse(loaded.complete)
        self.assertFalse(loaded.executable)
        self.assertEqual(loaded.expected_unit_refs, ())

    def test_unanswered_exact_query_creates_one_query_bound_learning_goal(self):
        result = QueryResult(
            "query:meaning-alpha",
            "unknown",
            (),
            0.0,
            0,
            0,
            (),
            (),
            (),
            {"query_kind": "meaning_query"},
        )
        probe = {
            "query_ref": result.query_ref,
            "surface": "Alpha",
            "learning_operation": "resolve_designation",
            "probe_query": {"query_ref": result.query_ref},
            "semantic_kind_candidates": ["concept", "entity"],
            "original_candidate_ref": "match:alpha",
            "unresolved_span_ref": "coverage:alpha",
        }
        act = SimpleNamespace(force="query", evidence={}, act_ref="act:alpha")
        candidates = GoalArbiter().candidates(
            act=act, query_result=result, learning_probe=(probe,)
        )
        learning = [item for item in candidates if item.kind == "request_learning_evidence"]
        self.assertEqual(len(learning), 1)
        decision = GoalArbiter.decide(candidates)
        self.assertEqual(decision.selected.kind, "request_learning_evidence")
        response = ResponseBuilder().build(
            audience_ref="participant:user",
            goal_decision=decision,
            query_result=result,
        )
        self.assertEqual(response.action, "request_learning_evidence")
        self.assertEqual(response.evidence_literals, ("Alpha",))
        self.assertEqual(response.qualifiers["query_ref"], result.query_ref)
        state = DialogueState()
        state.observe_response(
            response,
            self._verified_surface_proof(response, "What does Alpha refer to here?"),
            cycle_ref="cycle:alpha",
            turn_index=1,
        )
        self.assertEqual(state.pending.surface, "Alpha")
        self.assertEqual(state.pending.source_goal_ref, response.obligation_ref)

    def test_answered_query_never_opens_learning_obligation(self):
        result = QueryResult(
            "query:known-alpha",
            "answered",
            (QueryBinding({"?q0": "concept:alpha"}, ("fact:alpha",)),),
            1.0,
            1,
            0,
            (),
            (),
            (),
            {"query_kind": "meaning_query"},
        )
        probe = {
            "query_ref": result.query_ref,
            "surface": "Alpha",
            "learning_operation": "resolve_designation",
        }
        act = SimpleNamespace(force="query", evidence={}, act_ref="act:known-alpha")
        candidates = GoalArbiter().candidates(
            act=act, query_result=result, learning_probe=(probe,)
        )
        self.assertFalse(any(item.kind == "request_learning_evidence" for item in candidates))

    def test_blocking_frontier_prevents_post_query_learning_handoff(self):
        result = QueryResult(
            "query:blocked", "unknown", (), 0.0, 0, 0, (), (),
            ("frontier:critical",), {"query_kind": "meaning_query"},
        )
        act = SimpleNamespace(force="query", evidence={}, act_ref="act:blocked")
        candidates = GoalArbiter().candidates(
            act=act,
            query_result=result,
            learning_probe=({
                "query_ref": result.query_ref,
                "surface": "Alpha",
                "learning_operation": "resolve_designation",
            },),
        )
        self.assertFalse(
            any(item.kind == "request_learning_evidence" for item in candidates)
        )

    def test_contextual_designation_learning_is_licensed_end_to_end(self):
        result = QueryResult(
            "query:contextual-quux", "unknown", (), 0.0, 0, 0, (), (), (),
            {"query_kind": "designation_learning"},
        )
        goal = GoalCandidate(
            "goal:contextual-quux", "request_learning_evidence",
            result.query_ref, 1.15,
            {
                "query_ref": result.query_ref,
                "surface": "quux",
                "learning_operation": "resolve_designation",
                "probe_query": {"query_ref": result.query_ref},
                "semantic_kind_candidates": ["concept", "entity"],
            },
        )
        response = ResponseBuilder().build(
            audience_ref="participant:user",
            goal_decision=GoalDecision("decision:contextual-quux", goal, (), "test"),
            query_result=result,
        )
        self.assertEqual(response.action, "request_learning_evidence")
        self.assertEqual(response.evidence_literals, ("quux",))
        self.assertEqual(response.qualifiers["query_kind"], "designation_learning")
        self.assertEqual(response.qualifiers["query_ref"], result.query_ref)

    def test_learning_response_rejects_missing_query_kind(self):
        result = QueryResult(
            "query:no-kind", "unknown", (), 0.0, 0, 0, (), (), (), {},
        )
        goal = GoalCandidate(
            "goal:no-kind", "request_learning_evidence", result.query_ref, 1.15,
            {
                "query_ref": result.query_ref,
                "surface": "Alpha",
                "learning_operation": "resolve_designation",
            },
        )
        decision = GoalDecision("decision:no-kind", goal, (), "test")
        with self.assertRaisesRegex(ValueError, "immutable query kind"):
            ResponseBuilder().build(
                audience_ref="participant:user",
                goal_decision=decision,
                query_result=result,
            )

    def test_learning_response_rejects_unlicensed_operation(self):
        result = QueryResult(
            "query:meaning", "unknown", (), 0.0, 0, 0, (), (), (),
            {"query_kind": "meaning_query"},
        )
        goal = GoalCandidate(
            "goal:bad-op", "request_learning_evidence", result.query_ref, 1.15,
            {
                "query_ref": result.query_ref,
                "surface": "Alpha",
                "learning_operation": "invent_atom",
            },
        )
        decision = GoalDecision("decision:bad-op", goal, (), "test")
        with self.assertRaisesRegex(ValueError, "not licensed"):
            ResponseBuilder().build(
                audience_ref="participant:user",
                goal_decision=decision,
                query_result=result,
            )

    def test_learning_probe_query_mismatch_is_rejected(self):
        result = QueryResult(
            "query:expected", "unknown", (), 0.0, 0, 0, (), (), (),
            {"query_kind": "meaning_query"},
        )
        act = SimpleNamespace(force="query", evidence={}, act_ref="act:mismatch")
        with self.assertRaisesRegex(ValueError, "exactly one query-bound probe"):
            GoalArbiter().candidates(
                act=act,
                query_result=result,
                learning_probe=({
                    "query_ref": "query:different",
                    "surface": "Alpha",
                    "learning_operation": "resolve_designation",
                },),
            )

    def test_integrated_source_rewrite_ast_postconditions(self):
        validate_postconditions(self.repo)

    def test_source_modules_have_no_neural_or_supporting_fact_response_fallback(self):
        interpreter = ast.parse((self.repo / "cemm/interpreter.py").read_text(encoding="utf-8"))
        realizer_source = (self.repo / "cemm/realizer.py").read_text(encoding="utf-8")
        names = {node.id for node in ast.walk(interpreter) if isinstance(node, ast.Name)}
        self.assertNotIn("StructuredSemanticCodec", names)
        self.assertNotIn("torch", names)
        self.assertNotIn("supporting_fact", realizer_source)
        self.assertNotIn("facts_mentioning", (self.repo / "cemm/retrieval.py").read_text(encoding="utf-8"))

    def test_conflicting_exact_surface_supervision_is_rejected(self):
        pack = SimpleNamespace(
            data={
                "response_examples": [
                    {"semantic": "RESPONSE greet", "surface_plan": "Hello."},
                    {"semantic": "RESPONSE greet", "surface_plan": "Hi."},
                ]
            }
        )
        with self.assertRaises(ValueError):
            ExactSurfacePlanIndex(pack, "response_examples")


    def test_source_rewrite_seal_prevents_cross_pass_anchor_collision(self):
        marker = REWRITE_MARKERS["cemm/runtime.py"]
        later_generated_anchor = (
            'stages.add(Stage.COMMON_GROUND, counts={"entries": 1}, '
            'refs=(common_ground["entry_ref"],), durable_write=True)\n'
            '            else:\n'
        )
        sealed = _seal_file_rewrite(
            "# rewritten runtime\n" + later_generated_anchor + later_generated_anchor,
            marker,
        )
        self.assertIsNone(
            _begin_file_rewrite(
                sealed, marker, label="runtime rewrite seal regression"
            )
        )
        self.assertEqual(sealed.count(later_generated_anchor), 2)

    def test_duplicate_source_rewrite_seal_is_integrity_fault(self):
        marker = REWRITE_MARKERS["cemm/runtime.py"]
        with self.assertRaisesRegex(RewriteError, "zero or one rewrite seal"):
            _begin_file_rewrite(
                marker + "\n" + marker + "\n",
                marker,
                label="duplicate runtime rewrite seal",
            )

    def test_isolated_idempotence_proof_never_reenters_anchor_engine(self):
        with tempfile.TemporaryDirectory() as temporary:
            repo = Path(temporary)
            for relative, marker in REWRITE_MARKERS.items():
                path = repo / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                collision = (
                    'stages.add(Stage.COMMON_GROUND, counts={"entries": 1}, '
                    'refs=(common_ground["entry_ref"],), durable_write=True)\n'
                    '            else:\n'
                    if relative == "cemm/runtime.py"
                    else "legacy anchor that must never be revisited\n"
                )
                path.write_text(collision + "\n" + marker + "\n", encoding="utf-8")
            before = {
                relative: hashlib.sha256((repo / relative).read_bytes()).hexdigest()
                for relative in REWRITE_MARKERS
            }
            validate_rewrite_seals(repo)
            prove_idempotence_on_isolated_copy(repo)
            after = {
                relative: hashlib.sha256((repo / relative).read_bytes()).hexdigest()
                for relative in REWRITE_MARKERS
            }
            self.assertEqual(before, after)

if __name__ == "__main__":
    unittest.main()
