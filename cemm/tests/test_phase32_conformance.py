"""Golden trace conformance tests for Phase 3.2 implementation.

Tests cover the six validated failure classes and new type/contract behavior:
1. Feature preservation through patch -> durable -> query -> frame
2. Profile write and query round-trip
3. Feedback not stored as durable memory
4. Dismissal not stored as durable memory
5. Concept definition query does not fall back to unrelated relations
6. Evidence explanation gating (conditional rendering)
7. Blocked plan gate (no realization, no action proposals)
8. Operational meaning frame classification
9. Obligation contract compilation
10. State transmutation frame validation
"""

from __future__ import annotations

from dataclasses import dataclass, field
from types import SimpleNamespace

from cemm.memory.durable_semantic_store import DurableSemanticStore, DurableRelationRecord
from cemm.types.graph_patch import GraphPatch, PatchOperation
from cemm.types.relation_frame import RelationFrame, RelationArgument
from cemm.types.operational_meaning import (
    OperationalMeaningFrame,
    OperationalEffect,
    MeaningArbitrationResult,
    is_writable_frame,
)
from cemm.types.state_transmutation import (
    StateTransmutationFrame,
    StateOccupancyFrame,
    StateDeltaFrame,
)
from cemm.types.obligation_contract import (
    ObligationContract,
    QueryContract,
    WriteContract,
    ReactionContract,
    SafetyContract,
)
from cemm.kernel.operational_meaning_compiler import OperationalMeaningCompiler
from cemm.kernel.obligation_contract_builder import ObligationContractBuilder
from cemm.kernel.query_contract_builder import QueryContractBuilder
from cemm.kernel.write_contract_builder import WriteContractBuilder
from cemm.kernel.reaction_contract_builder import ReactionContractBuilder
from cemm.response.primitive_goal_composer import PrimitiveGoalComposer
from cemm.response.types import (
    PrimitiveResponseGoal,
    ResponseEvidencePacket,
    ResponseSituation,
    StyleVector,
    TemperatureState,
)


# ── 0. Runtime integration: operational spine is authoritative ───────────────


def test_runtime_profile_round_trip_uses_operational_contracts_without_evidence_leak():
    """Profile write/query should flow through 3.2 frames/contracts and keep
    evidence explanation internal for a simple high-confidence answer."""
    from cemm.kernel.semantic_kernel_runtime import SemanticKernelRuntime

    runtime = SemanticKernelRuntime()
    context_id = "phase32-runtime-profile"

    write_result = runtime.run_text("my name is Chibueze", context_id=context_id)
    assert any(
        frame.frame_type == "profile_assertion"
        for frame in write_result.operational_meaning_frames
    )
    assert write_result.obligation_contract is not None
    assert write_result.obligation_contract.has_write
    assert write_result.obligation_contract.write_contract.write_kind == "profile_upsert"

    query_result = runtime.run_text("what's my name?", context_id=context_id)
    assert query_result.obligation_contract is not None
    assert query_result.obligation_contract.has_query
    assert query_result.obligation_contract.query_contract.query_kind == "profile_dimension"
    assert query_result.obligation_contract.query_contract.dimension == "name"
    assert query_result.answer_binding is not None
    assert query_result.answer_binding.has_answer
    assert "Chibueze" in query_result.realized_output
    assert "(via:" not in query_result.realized_output


def test_runtime_feedback_dismissal_and_user_state_do_not_commit_durable_memory():
    """Feedback, dismissal, and user state reports are session/reaction state,
    not concept-lattice writes."""
    from cemm.kernel.semantic_kernel_runtime import SemanticKernelRuntime

    cases = [
        ("you're so robotic", {"style_feedback", "response_feedback"}),
        ("go away", {"session_exit"}),
        ("I'm great", {"user_state_report"}),
    ]

    for text, expected_frame_types in cases:
        runtime = SemanticKernelRuntime()
        before = runtime.durable_semantic_store.relation_count()
        result = runtime.run_text(text, context_id=f"phase32-runtime-{text}")
        after = runtime.durable_semantic_store.relation_count()

        frame_types = {frame.frame_type for frame in result.operational_meaning_frames}
        assert frame_types & expected_frame_types
        assert result.obligation_contract is not None
        assert not result.obligation_contract.has_write
        assert getattr(result.obligation_frame, "write_policy", "") == "none"
        assert getattr(result.obligation_frame, "obligation_kind", "") != "store_patch"
        assert after == before
        assert "stored" not in result.realized_output.lower()


def test_runtime_concept_definition_query_never_projects_unrelated_profile_fact():
    """A concept-definition query must not use broad durable/profile fallback."""
    from cemm.kernel.semantic_kernel_runtime import SemanticKernelRuntime

    runtime = SemanticKernelRuntime()
    context_id = "phase32-runtime-concept-query"
    runtime.run_text("my name is Chibueze", context_id=context_id)

    result = runtime.run_text("Do you know what the word president means?", context_id=context_id)

    assert any(
        frame.frame_type == "concept_definition_query"
        for frame in result.operational_meaning_frames
    )
    assert result.obligation_contract is not None
    assert result.obligation_contract.has_query
    assert result.obligation_contract.query_contract.query_kind == "concept_definition"
    assert "Chibueze" not in result.realized_output
    assert not (result.answer_binding and result.answer_binding.has_answer)


# ── 1. Feature preservation through patch -> durable -> query -> frame ──────


def test_features_preserved_through_patch_to_durable_to_frame():
    """Patch with features should produce a DurableRelationRecord with features,
    and _record_to_frame should reconstruct RelationFrame with those features."""
    store = DurableSemanticStore()
    patch = GraphPatch(
        source_graph_id="g1",
        target="concept_lattice",
        operations=[
            PatchOperation(
                operation="upsert_relation_candidate",
                target_id="relation:has_property:user:concept:name",
                fields={
                    "relation_key": "has_property",
                    "relation_family": "property",
                    "subject_entity_id": "user",
                    "subject_surface": "user",
                    "object_concept_id": "concept:name",
                    "object_surface": "Chibu",
                    "source_atom_ids": ["a1", "a2"],
                    "inverse_keys": [],
                    "features": {"property_dimension": "name", "relation_scope": "user_profile"},
                    "dimension": "name",
                    "relation_scope": "user_profile",
                },
                confidence=0.9,
                reason="test",
            )
        ],
    )
    validation = SimpleNamespace(accepted=True, rejected_operations=[])
    result = store.apply_validated_patch(patch, validation)

    assert result.status == "committed"
    assert len(result.created_records) == 1

    rec = store._relations[result.created_records[0]]
    assert rec.features.get("property_dimension") == "name"
    assert rec.dimension == "name"
    assert rec.relation_scope == "user_profile"

    frame = store._record_to_frame(rec)
    assert frame is not None
    assert frame.features.get("property_dimension") == "name"


def test_features_preserved_through_inverse_query():
    """Inverse relation query should preserve features from the original record."""
    store = DurableSemanticStore()
    store.add_relation(
        relation_key="taught_by",
        relation_family="taxonomy",
        subject_concept_id="concept:dog",
        object_concept_id="concept:animal",
        inverse_keys=["is_a"],
        features={"property_dimension": "species"},
        dimension="species",
    )

    inverse_results = store._query_inverse_relations("is_a", "concept:animal", "concept:dog")
    assert len(inverse_results) == 1
    assert inverse_results[0].features.get("property_dimension") == "species"
    assert inverse_results[0].dimension == "species"


def test_features_preserved_through_inherited_query():
    """Inherited relation query should preserve features from parent record."""
    store = DurableSemanticStore()
    store.add_relation(
        relation_key="has_property",
        relation_family="property",
        subject_concept_id="concept:animal",
        object_concept_id="concept:mammal",
        features={"property_dimension": "class"},
        dimension="class",
    )

    inherited = store.query_inherited("concept:dog", "concept:animal")
    assert len(inherited) == 1
    assert inherited[0].features.get("property_dimension") == "class"


# ── 2. Profile write and query round-trip ───────────────────────────────────


def test_profile_write_and_query_round_trip():
    """Writing a profile assertion and querying it should return the stored value."""
    store = DurableSemanticStore()
    patch = GraphPatch(
        source_graph_id="g1",
        target="concept_lattice",
        operations=[
            PatchOperation(
                operation="upsert_relation_candidate",
                target_id="relation:has_property:user:concept:name",
                fields={
                    "relation_key": "has_property",
                    "relation_family": "property",
                    "subject_entity_id": "user",
                    "subject_surface": "user",
                    "object_concept_id": "concept:name",
                    "object_surface": "Chibu",
                    "source_atom_ids": ["a1", "a2"],
                    "inverse_keys": [],
                    "features": {"property_dimension": "name"},
                    "dimension": "name",
                },
                confidence=0.9,
                reason="profile_assertion",
            )
        ],
    )
    validation = SimpleNamespace(accepted=True, rejected_operations=[])
    store.apply_validated_patch(patch, validation)

    frames = store.query_relations(relation_key="has_property", subject_entity_id="user")
    assert len(frames) >= 1
    found = any(f.features.get("property_dimension") == "name" for f in frames)
    assert found, "Profile query should return frame with property_dimension feature"


# ── 3. Feedback not stored as durable memory ────────────────────────────────


def test_style_feedback_does_not_produce_write_contract():
    """A style_feedback frame should not produce a WriteContract."""
    frame = OperationalMeaningFrame(
        frame_id="omf_test",
        graph_id="g1",
        group_id="grp1",
        frame_type="style_feedback",
        target_scope="previous_response",
        persistence_policy="session_state",
        confidence=0.8,
    )
    builder = WriteContractBuilder()
    contract = builder.build(frame)
    assert contract is None, "style_feedback should not produce a write contract"


def test_response_feedback_does_not_produce_write_contract():
    """A response_feedback frame should not produce a WriteContract."""
    frame = OperationalMeaningFrame(
        frame_id="omf_test",
        graph_id="g1",
        group_id="grp1",
        frame_type="response_feedback",
        target_scope="previous_response",
        persistence_policy="session_state",
        confidence=0.8,
    )
    builder = WriteContractBuilder()
    contract = builder.build(frame)
    assert contract is None, "response_feedback should not produce a write contract"


# ── 4. Dismissal not stored as durable memory ───────────────────────────────


def test_session_exit_does_not_produce_write_contract():
    """A session_exit frame should not produce a WriteContract."""
    frame = OperationalMeaningFrame(
        frame_id="omf_test",
        graph_id="g1",
        group_id="grp1",
        frame_type="session_exit",
        target_scope="conversation_state",
        persistence_policy="session_state",
        confidence=0.95,
    )
    assert not is_writable_frame(frame), "session_exit should not be writable"


def test_social_act_does_not_produce_write_contract():
    """A social_act frame should not produce a WriteContract."""
    frame = OperationalMeaningFrame(
        frame_id="omf_test",
        graph_id="g1",
        group_id="grp1",
        frame_type="social_act",
        target_scope="ephemeral_social",
        persistence_policy="ephemeral_trace",
        confidence=0.7,
    )
    assert not is_writable_frame(frame), "social_act should not be writable"


# ── 5. Evidence explanation gating ──────────────────────────────────────────


@dataclass
class MockObligation:
    obligation_kind: str = "answer_user_profile"
    evidence_policy: str = "required"
    write_policy: str = "none"
    response_mode: str = "evidence_answer"
    required_slots: list = field(default_factory=list)
    blocked_by: list = field(default_factory=list)
    confidence: float = 0.8
    context: dict = field(default_factory=dict)


@dataclass
class MockBinding:
    has_answer: bool = True
    confidence: float = 0.9
    abstention_reason: str = ""
    slot_fills: list = field(default_factory=list)


def test_evidence_explanation_suppressed_when_confidence_high():
    """When answer confidence is high and no user request for source,
    evidence explanation should NOT be rendered."""
    composer = PrimitiveGoalComposer()
    situation = ResponseSituation(
        obligation_frame=MockObligation(evidence_policy="required"),
        evidence=ResponseEvidencePacket(evidence_refs=["e1"]),
        answer_binding=MockBinding(has_answer=True, confidence=0.95),
        style=StyleVector(detail=0.3),
        temperature=TemperatureState(user_detail_appetite=0.3),
    )
    goals = composer.compose(situation)
    goal_types = [g.goal_type for g in goals]
    assert "assert" in goal_types
    assert "explain_evidence" not in goal_types, (
        "Evidence explanation should be suppressed when confidence is high and no user request"
    )


def test_evidence_explanation_rendered_when_confidence_borderline():
    """When answer confidence is borderline, evidence explanation should be rendered."""
    composer = PrimitiveGoalComposer()
    situation = ResponseSituation(
        obligation_frame=MockObligation(evidence_policy="required"),
        evidence=ResponseEvidencePacket(evidence_refs=["e1"]),
        answer_binding=MockBinding(has_answer=True, confidence=0.6),
        style=StyleVector(detail=0.3),
        temperature=TemperatureState(user_detail_appetite=0.3),
    )
    goals = composer.compose(situation)
    goal_types = [g.goal_type for g in goals]
    assert "explain_evidence" in goal_types, (
        "Evidence explanation should be rendered when confidence is borderline"
    )


def test_evidence_explanation_rendered_when_user_requests_source():
    """When user explicitly requests source/reason, evidence explanation should be rendered."""
    composer = PrimitiveGoalComposer()
    situation = ResponseSituation(
        obligation_frame=MockObligation(
            evidence_policy="required",
            context={"response_act_hints": ["source_request"]},
        ),
        evidence=ResponseEvidencePacket(evidence_refs=["e1"]),
        answer_binding=MockBinding(has_answer=True, confidence=0.95),
        style=StyleVector(detail=0.3),
        temperature=TemperatureState(user_detail_appetite=0.3),
    )
    goals = composer.compose(situation)
    goal_types = [g.goal_type for g in goals]
    assert "explain_evidence" in goal_types, (
        "Evidence explanation should be rendered when user requests source"
    )


def test_evidence_explanation_rendered_when_style_detail_high():
    """When style.detail is high, evidence explanation should be rendered."""
    composer = PrimitiveGoalComposer()
    situation = ResponseSituation(
        obligation_frame=MockObligation(evidence_policy="required"),
        evidence=ResponseEvidencePacket(evidence_refs=["e1"]),
        answer_binding=MockBinding(has_answer=True, confidence=0.95),
        style=StyleVector(detail=0.8),
        temperature=TemperatureState(user_detail_appetite=0.3),
    )
    goals = composer.compose(situation)
    goal_types = [g.goal_type for g in goals]
    assert "explain_evidence" in goal_types


# ── 6. Blocked plan gate ────────────────────────────────────────────────────


def test_blocked_plan_does_not_realize():
    """When a plan is blocked, the response formation engine should skip
    realization and action proposal."""
    from cemm.response.response_formation_engine import ResponseFormationEngine
    from cemm.response.types import ResponseCandidatePlan, ResponseMove

    engine = ResponseFormationEngine()
    blocked_plan = ResponseCandidatePlan(
        plan_id="blocked",
        moves=[ResponseMove(move_type="safety_refusal", safety_required=True)],
        blocked_reason="safety_risk",
        required_components={"explicit_negative"},
        satisfied_components=set(),
    )

    situation = ResponseSituation(
        obligation_frame=MockObligation(obligation_kind="abstain_policy"),
    )
    situation.budget_decision = SimpleNamespace(
        pressure=0.5, task_size="small", risk_level="low",
        reasons=[], stage_budget=SimpleNamespace(
            candidate_plan_limit=5, realized_candidate_limit=3,
            selector_mode="best", detail_level=0.5,
            query_result_limit=10, attention_focus_limit=5,
            diagnostics={},
        ),
    )

    text = engine._blocked_fallback("safety_risk")
    assert "No." in text or "can't help" in text

    dummy = engine._dummy_realized()
    assert dummy.grammar_trace.get("blocked") is True


# ── 7. Operational meaning frame validation ─────────────────────────────────


def test_operational_meaning_frame_validates_frame_type():
    """OperationalMeaningFrame should reject unknown frame types."""
    try:
        OperationalMeaningFrame(
            frame_id="test",
            graph_id="g1",
            group_id="grp1",
            frame_type="invalid_type",
            target_scope="user_profile",
        )
        assert False, "Should have raised ValueError"
    except ValueError:
        pass


def test_operational_meaning_frame_validates_target_scope():
    """OperationalMeaningFrame should reject unknown target scopes."""
    try:
        OperationalMeaningFrame(
            frame_id="test",
            graph_id="g1",
            group_id="grp1",
            frame_type="social_act",
            target_scope="invalid_scope",
        )
        assert False, "Should have raised ValueError"
    except ValueError:
        pass


def test_operational_meaning_frame_is_writable():
    """profile_assertion with patch_candidate persistence should be writable."""
    frame = OperationalMeaningFrame(
        frame_id="test",
        graph_id="g1",
        group_id="grp1",
        frame_type="profile_assertion",
        target_scope="user_profile",
        persistence_policy="patch_candidate",
        confidence=0.8,
    )
    assert frame.is_writable


def test_operational_meaning_frame_is_query():
    """user_profile_query should be a query frame."""
    frame = OperationalMeaningFrame(
        frame_id="test",
        graph_id="g1",
        group_id="grp1",
        frame_type="user_profile_query",
        target_scope="user_profile",
        query_policy="profile_dimension_lookup",
        confidence=0.8,
    )
    assert frame.is_query


# ── 8. State transmutation frame validation ─────────────────────────────────


def test_state_transmutation_frame_validates_direction():
    """StateTransmutationFrame should reject unknown directions."""
    try:
        StateTransmutationFrame(
            transmutation_id="t1",
            source_frame_id="f1",
            target_ref="entity:user",
            state_family="identity",
            dimension="name",
            direction="invalid_direction",
        )
        assert False, "Should have raised ValueError"
    except ValueError:
        pass


def test_state_transmutation_frame_validates_state_family():
    """StateTransmutationFrame should reject unknown state families."""
    try:
        StateTransmutationFrame(
            transmutation_id="t1",
            source_frame_id="f1",
            target_ref="entity:user",
            state_family="invalid_family",
            dimension="name",
        )
        assert False, "Should have raised ValueError"
    except ValueError:
        pass


def test_state_transmutation_is_durable_candidate():
    """A transmutation with graph_patch_candidate persistence should be a durable candidate."""
    transmutation = StateTransmutationFrame(
        transmutation_id="t1",
        source_frame_id="f1",
        target_ref="entity:user",
        state_family="identity",
        dimension="name",
        persistence_policy="graph_patch_candidate",
    )
    assert transmutation.is_durable_candidate


def test_state_transmutation_is_rejected():
    """A transmutation with reject persistence should be rejected."""
    transmutation = StateTransmutationFrame(
        transmutation_id="t1",
        source_frame_id="f1",
        target_ref="entity:user",
        state_family="identity",
        dimension="name",
        persistence_policy="reject",
    )
    assert transmutation.is_rejected


# ── 9. Obligation contract compilation ──────────────────────────────────────


def test_obligation_contract_from_profile_assertion():
    """Building a contract from a profile_assertion frame should produce
    a write contract and store_profile obligation."""
    frame = OperationalMeaningFrame(
        frame_id="omf1",
        graph_id="g1",
        group_id="grp1",
        frame_type="profile_assertion",
        target_scope="user_profile",
        persistence_policy="patch_candidate",
        dimension="name",
        confidence=0.85,
        features={"property_dimension": "name"},
    )
    arbitration = MeaningArbitrationResult(
        selected_frame_ids=["omf1"],
        arbitration_reason="priority_selection",
        confidence=0.85,
    )
    builder = ObligationContractBuilder()
    contract = builder.build([frame], arbitration)

    assert contract.obligation_kind == "store_profile"
    assert contract.response_mode == "confirm_write"
    assert contract.has_write
    assert contract.write_contract is not None
    assert contract.write_contract.write_kind == "profile_upsert"
    assert "name" in contract.write_contract.required_features


def test_obligation_contract_from_user_profile_query():
    """Building a contract from a user_profile_query frame should produce
    a query contract and answer_user_profile obligation."""
    frame = OperationalMeaningFrame(
        frame_id="omf1",
        graph_id="g1",
        group_id="grp1",
        frame_type="user_profile_query",
        target_scope="user_profile",
        query_policy="profile_dimension_lookup",
        dimension="name",
        confidence=0.8,
    )
    arbitration = MeaningArbitrationResult(
        selected_frame_ids=["omf1"],
        arbitration_reason="priority_selection",
        confidence=0.8,
    )
    builder = ObligationContractBuilder()
    contract = builder.build([frame], arbitration)

    assert contract.obligation_kind == "answer_user_profile"
    assert contract.response_mode == "answer"
    assert contract.has_query
    assert contract.query_contract is not None
    assert contract.query_contract.query_kind == "profile_dimension"
    assert contract.query_contract.dimension == "name"


def test_obligation_contract_blocked_by_safety():
    """When safety_frame is present and primary is not safety_candidate,
    the contract should be blocked."""
    frame = OperationalMeaningFrame(
        frame_id="omf1",
        graph_id="g1",
        group_id="grp1",
        frame_type="concept_definition_query",
        target_scope="concept_lattice",
        query_policy="concept_definition_lookup",
        confidence=0.8,
    )
    arbitration = MeaningArbitrationResult(
        selected_frame_ids=["omf1"],
        arbitration_reason="priority_selection",
        confidence=0.8,
    )
    safety = SimpleNamespace(category="violence", severity="high", risk_level=0.9)
    builder = ObligationContractBuilder()
    contract = builder.build([frame], arbitration, safety_frame=safety)

    assert contract.is_blocked
    assert "safety_preemption" in contract.blocked_by


def test_obligation_contract_from_style_feedback():
    """Building a contract from style_feedback should produce a reaction contract
    and no write contract."""
    frame = OperationalMeaningFrame(
        frame_id="omf1",
        graph_id="g1",
        group_id="grp1",
        frame_type="style_feedback",
        target_scope="previous_response",
        persistence_policy="session_state",
        dimension="verbosity",
        confidence=0.7,
    )
    arbitration = MeaningArbitrationResult(
        selected_frame_ids=["omf1"],
        arbitration_reason="priority_selection",
        confidence=0.7,
    )
    builder = ObligationContractBuilder()
    contract = builder.build([frame], arbitration)

    assert contract.obligation_kind == "apply_style_feedback"
    assert not contract.has_write
    assert contract.has_reaction
    assert contract.reaction_contract.reaction_kind == "style_adjust"


# ── 10. Query contract builder ──────────────────────────────────────────────


def test_query_contract_builder_profile_query():
    """QueryContractBuilder should produce a profile_dimension query for user_profile_query."""
    frame = OperationalMeaningFrame(
        frame_id="omf1",
        graph_id="g1",
        group_id="grp1",
        frame_type="user_profile_query",
        target_scope="user_profile",
        query_policy="profile_dimension_lookup",
        dimension="name",
        confidence=0.8,
    )
    builder = QueryContractBuilder()
    contract = builder.build(frame)

    assert contract is not None
    assert contract.query_kind == "profile_dimension"
    assert contract.target_scope == "user_profile"
    assert contract.dimension == "name"


def test_query_contract_builder_concept_query():
    """QueryContractBuilder should produce a concept_definition query for concept_definition_query."""
    frame = OperationalMeaningFrame(
        frame_id="omf1",
        graph_id="g1",
        group_id="grp1",
        frame_type="concept_definition_query",
        target_scope="concept_lattice",
        query_policy="concept_definition_lookup",
        confidence=0.8,
    )
    builder = QueryContractBuilder()
    contract = builder.build(frame)

    assert contract is not None
    assert contract.query_kind == "concept_definition"
    assert contract.target_scope == "concept_lattice"


def test_query_contract_builder_returns_none_for_non_query():
    """QueryContractBuilder should return None for non-query frames."""
    frame = OperationalMeaningFrame(
        frame_id="omf1",
        graph_id="g1",
        group_id="grp1",
        frame_type="social_act",
        target_scope="ephemeral_social",
        confidence=0.7,
    )
    builder = QueryContractBuilder()
    contract = builder.build(frame)
    assert contract is None


# ── 11. Reaction contract builder ───────────────────────────────────────────


def test_reaction_contract_builder_style_feedback():
    """ReactionContractBuilder should produce a style_adjust for verbosity feedback."""
    frame = OperationalMeaningFrame(
        frame_id="omf1",
        graph_id="g1",
        group_id="grp1",
        frame_type="style_feedback",
        target_scope="previous_response",
        persistence_policy="session_state",
        dimension="verbosity",
        confidence=0.7,
    )
    builder = ReactionContractBuilder()
    contract = builder.build(frame)

    assert contract is not None
    assert contract.reaction_kind == "style_adjust"
    assert "detail" in contract.style_delta
    assert contract.style_delta["detail"] < 0.0


def test_reaction_contract_builder_returns_none_for_non_feedback():
    """ReactionContractBuilder should return None for non-feedback frames."""
    frame = OperationalMeaningFrame(
        frame_id="omf1",
        graph_id="g1",
        group_id="grp1",
        frame_type="profile_assertion",
        target_scope="user_profile",
        persistence_policy="patch_candidate",
        confidence=0.8,
    )
    builder = ReactionContractBuilder()
    contract = builder.build(frame)
    assert contract is None
