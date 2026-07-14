"""Tests for PerceptToSurfaceEvidence bridge and SemanticComposer wiring (Phase 4).

Verifies that:
- PerceptToSurfaceEvidence correctly converts MeaningPerceptPacket to SurfaceEvidence
- SurfaceEvidence preserves raw text, token offsets, negation, contractions
- SemanticComposer produces a CandidateGraph from the bridge output
- Runtime exposes v3.4 components and populates trace fields
- Unknown content stays unknown — not converted to generic entities
"""
from __future__ import annotations

import pytest
from unittest.mock import Mock, MagicMock

from cemm.kernel.understanding.percept_bridge import PerceptToSurfaceEvidence
from cemm.language.interfaces import SurfaceEvidence
from cemm.language.stream import TokenStream, Token, TokenKind


class TestPerceptToSurfaceEvidence:
    """Test the legacy-to-v3.4 bridge adapter."""

    def _make_percept(
        self,
        raw_text: str = "Alice knows Bob",
        tokens: list[str] | None = None,
        normalized_tokens: list[str] | None = None,
        cased_tokens: list[str] | None = None,
        language: str = "en",
        referents: list[Any] | None = None,
        predicate_phrases: list[Any] | None = None,
        actions: list[Any] | None = None,
        intents: list[Any] | None = None,
        affect_markers: list[Any] | None = None,
        confidence: float = 0.8,
    ) -> Mock:
        from typing import Any
        percept = Mock()
        percept.raw_text = raw_text
        percept.tokens = tokens or raw_text.split()
        percept.normalized_tokens = normalized_tokens or [t.lower() for t in percept.tokens]
        percept.cased_tokens = cased_tokens or percept.tokens
        percept.normalized_forms = percept.normalized_tokens
        percept.language = language
        percept.referents = referents or []
        percept.predicate_phrases = predicate_phrases or []
        percept.actions = actions or []
        percept.relations = []
        percept.intents = intents or []
        percept.affect_markers = affect_markers or []
        percept.spans = []
        percept.punctuation_features = {}
        percept.confidence = confidence
        percept.signal_id = "sig:test:001"
        return percept

    def test_basic_conversion_produces_surface_evidence(self):
        percept = self._make_percept(raw_text="Alice knows Bob")
        bridge = PerceptToSurfaceEvidence()
        evidence = bridge.convert(percept)

        assert isinstance(evidence, SurfaceEvidence)
        assert evidence.token_stream.raw_text == "Alice knows Bob"
        assert len(evidence.token_stream.tokens) == 3

    def test_preserves_raw_form_and_offsets(self):
        percept = self._make_percept(
            raw_text="Alice knows Bob",
            tokens=["Alice", "knows", "Bob"],
            cased_tokens=["Alice", "knows", "Bob"],
        )
        bridge = PerceptToSurfaceEvidence()
        evidence = bridge.convert(percept)

        tokens = evidence.token_stream.tokens
        assert tokens[0].raw_form == "Alice"
        assert tokens[1].raw_form == "knows"
        assert tokens[2].raw_form == "Bob"
        assert tokens[0].start_offset == 0
        assert tokens[0].end_offset == 5
        assert tokens[1].start_offset == 6
        assert tokens[1].end_offset == 11

    def test_negation_detected_as_token_kind(self):
        percept = self._make_percept(
            raw_text="I do not know",
            tokens=["I", "do", "not", "know"],
        )
        bridge = PerceptToSurfaceEvidence()
        evidence = bridge.convert(percept)

        negation_tokens = [t for t in evidence.token_stream.tokens if t.is_negation]
        assert len(negation_tokens) == 1
        assert negation_tokens[0].raw_form.lower() == "not"
        assert evidence.token_stream.has_negation is True

    def test_contraction_decomposition_preserved(self):
        percept = self._make_percept(
            raw_text="I don't know",
            tokens=["I", "don't", "know"],
        )
        bridge = PerceptToSurfaceEvidence()
        evidence = bridge.convert(percept)

        contraction_tokens = [t for t in evidence.token_stream.tokens if t.contraction is not None]
        assert len(contraction_tokens) == 1
        assert contraction_tokens[0].raw_form == "don't"
        assert contraction_tokens[0].contraction.components == ("do", "not")

    def test_question_mark_infers_ask_force(self):
        percept = self._make_percept(
            raw_text="What is Alice?",
            tokens=["What", "is", "Alice", "?"],
        )
        bridge = PerceptToSurfaceEvidence()
        evidence = bridge.convert(percept)

        assert len(evidence.communicative_candidates) > 0
        assert evidence.communicative_candidates[0].force == "ask"

    def test_referents_become_lexical_candidates(self):
        from typing import Any
        ref = Mock()
        ref.surface = "Alice"
        ref.entity_type = "person"
        ref.confidence = 0.9

        percept = self._make_percept(
            raw_text="Alice knows Bob",
            tokens=["Alice", "knows", "Bob"],
            referents=[ref],
        )
        bridge = PerceptToSurfaceEvidence()
        evidence = bridge.convert(percept)

        assert len(evidence.lexical_sense_candidates) == 1
        candidate = evidence.lexical_sense_candidates[0]
        assert candidate.lexical_form_ref.surface == "Alice"
        assert candidate.semantic_key == "entity:person:alice"
        assert candidate.confidence == 0.9

    def test_predicate_phrases_become_construction_candidates(self):
        pp = Mock()
        pp.surface = "knows"
        pp.predicate_key = "knows"
        pp.confidence = 0.8
        pp.actor_role = "Alice"
        pp.object_role = "Bob"

        percept = self._make_percept(
            raw_text="Alice knows Bob",
            tokens=["Alice", "knows", "Bob"],
            predicate_phrases=[pp],
        )
        bridge = PerceptToSurfaceEvidence()
        evidence = bridge.convert(percept)

        assert len(evidence.construction_candidates) == 1
        constr = evidence.construction_candidates[0]
        assert constr.predicate_schema_ref == "schema:knows"
        assert "actor" in constr.role_mappings
        assert constr.role_mappings["actor"] == 0  # Alice is token 0

    def test_intents_become_communicative_candidates(self):
        intent = Mock()
        intent.intent_key = "question"
        intent.is_question = True
        intent.confidence = 0.9
        intent.surface = "What is Alice"

        percept = self._make_percept(
            raw_text="What is Alice",
            tokens=["What", "is", "Alice"],
            intents=[intent],
        )
        bridge = PerceptToSurfaceEvidence()
        evidence = bridge.convert(percept)

        assert len(evidence.communicative_candidates) == 1
        assert evidence.communicative_candidates[0].force == "ask"

    def test_affect_markers_become_pragmatic_cues(self):
        marker = {"kind": "emotion", "value": "curious", "confidence": 0.7}

        percept = self._make_percept(
            raw_text="Alice knows Bob",
            tokens=["Alice", "knows", "Bob"],
            affect_markers=[marker],
        )
        bridge = PerceptToSurfaceEvidence()
        evidence = bridge.convert(percept)

        assert len(evidence.pragmatic_cues) == 1
        cue = evidence.pragmatic_cues[0]
        assert cue.cue_kind == "emotion"
        assert cue.value == "curious"
        assert cue.replaces_content is False

    def test_unknown_tokens_preserved_as_unknown(self):
        percept = self._make_percept(
            raw_text="Alice xyzzy Bob",
            tokens=["Alice", "xyzzy", "Bob"],
        )
        percept.punctuation_features = {"unknown_tokens": ["xyzzy"]}

        bridge = PerceptToSurfaceEvidence()
        evidence = bridge.convert(percept)

        unknown_tokens = [t for t in evidence.token_stream.tokens if t.is_unknown]
        assert len(unknown_tokens) == 1
        assert unknown_tokens[0].raw_form == "xyzzy"
        assert unknown_tokens[0].kind == TokenKind.UNKNOWN

    def test_empty_percept_produces_valid_evidence(self):
        percept = self._make_percept(raw_text="", tokens=[])
        bridge = PerceptToSurfaceEvidence()
        evidence = bridge.convert(percept)

        assert isinstance(evidence, SurfaceEvidence)
        assert len(evidence.token_stream.tokens) == 0

    def test_adapter_id_set_correctly(self):
        percept = self._make_percept()
        bridge = PerceptToSurfaceEvidence()
        evidence = bridge.convert(percept)

        assert evidence.adapter_id == "percept_bridge"
        assert evidence.adapter_version == "1.0"


class TestSemanticComposerWithBridge:
    """Test SemanticComposer consuming bridge output."""

    def test_compose_from_bridge_output(self):
        from cemm.kernel.schema.store import SemanticSchemaStore
        from cemm.kernel.understanding.composer import SemanticComposer

        ref = Mock()
        ref.surface = "Alice"
        ref.entity_type = "person"
        ref.confidence = 0.9

        pp = Mock()
        pp.surface = "knows"
        pp.predicate_key = "knows"
        pp.confidence = 0.8
        pp.actor_role = "Alice"
        pp.object_role = "Bob"

        percept = Mock()
        percept.raw_text = "Alice knows Bob"
        percept.tokens = ["Alice", "knows", "Bob"]
        percept.normalized_tokens = ["alice", "knows", "bob"]
        percept.cased_tokens = ["Alice", "knows", "Bob"]
        percept.normalized_forms = ["alice", "knows", "bob"]
        percept.language = "en"
        percept.referents = [ref]
        percept.predicate_phrases = [pp]
        percept.actions = []
        percept.relations = []
        percept.intents = []
        percept.affect_markers = []
        percept.spans = []
        percept.punctuation_features = {}
        percept.confidence = 0.8
        percept.signal_id = "sig:test:001"

        bridge = PerceptToSurfaceEvidence()
        evidence = bridge.convert(percept)

        store = SemanticSchemaStore()
        composer = SemanticComposer(store=store)
        graph = composer.compose(evidence)

        assert graph is not None
        # Should have some candidate predications or opaque lexemes
        assert (
            len(graph.candidate_predications) > 0
            or len(graph.opaque_lexeme_refs) > 0
        )

    def test_compose_unknown_tokens_as_opaque(self):
        from cemm.kernel.schema.store import SemanticSchemaStore
        from cemm.kernel.understanding.composer import SemanticComposer

        percept = Mock()
        percept.raw_text = "xyzzy"
        percept.tokens = ["xyzzy"]
        percept.normalized_tokens = ["xyzzy"]
        percept.cased_tokens = ["xyzzy"]
        percept.normalized_forms = ["xyzzy"]
        percept.language = "en"
        percept.referents = []
        percept.predicate_phrases = []
        percept.actions = []
        percept.relations = []
        percept.intents = []
        percept.affect_markers = []
        percept.spans = []
        percept.punctuation_features = {"unknown_tokens": ["xyzzy"]}

        bridge = PerceptToSurfaceEvidence()
        evidence = bridge.convert(percept)

        store = SemanticSchemaStore()
        composer = SemanticComposer(store=store)
        graph = composer.compose(evidence)

        # Unknown token should produce opaque lexeme ref
        assert len(graph.opaque_lexeme_refs) > 0


class TestRuntimeV34Wiring:
    """Test that the runtime exposes and populates v3.4 components."""

    def test_runtime_exposes_v34_properties(self):
        from cemm.kernel.semantic_kernel_runtime import SemanticKernelRuntime

        runtime = SemanticKernelRuntime()

        assert runtime.percept_bridge is not None
        assert runtime.semantic_composer is not None
        assert runtime.grounding_resolver is not None
        assert runtime.epistemic_evaluator is not None
        assert runtime.capability_evaluator is not None
        assert runtime.self_report_builder is not None

    def test_runtime_run_text_populates_v34_trace_fields(self):
        from cemm.kernel.semantic_kernel_runtime import SemanticKernelRuntime

        runtime = SemanticKernelRuntime()
        result = runtime.run_text("Alice knows Bob")

        # v3.4 trace fields should be populated
        assert result.surface_evidence is not None
        assert result.candidate_graph is not None

        # SurfaceEvidence should have correct raw text
        assert result.surface_evidence.token_stream.raw_text == "Alice knows Bob"

    def test_runtime_run_text_with_question(self):
        from cemm.kernel.semantic_kernel_runtime import SemanticKernelRuntime

        runtime = SemanticKernelRuntime()
        result = runtime.run_text("What is an engineer?")

        assert result.surface_evidence is not None
        assert result.candidate_graph is not None
        # Should detect question force
        forces = result.candidate_graph.candidate_communicative_forces
        assert any(f.force == "ask" for f in forces)

    def test_runtime_run_text_with_negation(self):
        from cemm.kernel.semantic_kernel_runtime import SemanticKernelRuntime

        runtime = SemanticKernelRuntime()
        result = runtime.run_text("I do not know Bob")

        assert result.surface_evidence is not None
        assert result.surface_evidence.token_stream.has_negation is True

    def test_runtime_v34_trace_does_not_break_legacy(self):
        from cemm.kernel.semantic_kernel_runtime import SemanticKernelRuntime

        runtime = SemanticKernelRuntime()
        result = runtime.run_text("Alice knows Bob")

        # Legacy fields should still be populated
        assert result.percept is not None
        assert result.uol_graph is not None
        assert result.realized_output  # Should produce some response

    def test_runtime_populates_grounding_assessments(self):
        from cemm.kernel.semantic_kernel_runtime import SemanticKernelRuntime

        runtime = SemanticKernelRuntime()
        result = runtime.run_text("Alice knows Bob")

        # GroundingResolver should produce assessments for lexical candidates
        assert result.grounding_assessments is not None
        # May be empty if no referents detected, but field should be a list
        assert isinstance(result.grounding_assessments, list)

    def test_runtime_populates_epistemic_assessments(self):
        from cemm.kernel.semantic_kernel_runtime import SemanticKernelRuntime

        runtime = SemanticKernelRuntime()
        result = runtime.run_text("Alice knows Bob")

        # EpistemicEvaluator should produce assessments for candidate propositions
        assert result.epistemic_assessments is not None
        assert isinstance(result.epistemic_assessments, list)

    def test_runtime_populates_capability_assessment(self):
        from cemm.kernel.semantic_kernel_runtime import SemanticKernelRuntime

        runtime = SemanticKernelRuntime()
        result = runtime.run_text("Alice knows Bob")

        # CapabilityEvaluator should produce a self-capability assessment
        assert result.capability_assessment is not None

    def test_runtime_exposes_learning_commit_common_ground(self):
        from cemm.kernel.semantic_kernel_runtime import SemanticKernelRuntime

        runtime = SemanticKernelRuntime()

        assert runtime.learning_coordinator is not None
        assert runtime.commit_coordinator is not None
        assert runtime.common_ground_manager is not None

    def test_runtime_cutover_verifier_registers_authorities(self):
        from cemm.kernel.semantic_kernel_runtime import SemanticKernelRuntime

        runtime = SemanticKernelRuntime()
        verifier = runtime.cutover_verifier

        # Key v3.4 authorities should be registered
        assert verifier.get_authority("surface_analysis") == "PerceptToSurfaceEvidence"
        assert verifier.get_authority("semantic_composition") == "SemanticComposer"
        assert verifier.get_authority("referent_sense_role_grounding") == "GroundingResolver"
        assert verifier.get_authority("schema_identity_version_resolution") == "SemanticSchemaStore"
        assert verifier.get_authority("truth_and_context_admissibility") == "EpistemicEvaluator"
        assert verifier.get_authority("current_capability") == "CapabilityEvaluator"
        assert verifier.get_authority("learning_lifecycle") == "LearningCoordinator"
        assert verifier.get_authority("persistent_mutation") == "CommitCoordinator"
        assert verifier.get_authority("common_ground") == "CommonGroundManager"
