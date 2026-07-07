from __future__ import annotations

from dataclasses import dataclass, field
from types import SimpleNamespace

from cemm.response.realization.slot_binder import SlotBinder
from cemm.response.transformers.plan_gate_and_ranker import PlanGateAndRanker
from cemm.response.types import ResponseCandidatePlan, ResponseEvidencePacket, ResponseMove, ResponseSituation, StyleVector


@dataclass
class Obligation:
    obligation_kind: str = "answer_user_profile"
    evidence_policy: str = "none"
    write_policy: str = "none"
    response_mode: str = "evidence_answer"
    required_slots: list = field(default_factory=list)
    blocked_by: list = field(default_factory=list)
    confidence: float = 0.8
    context: dict = field(default_factory=dict)


def test_score_safety_is_not_constant_noop():
    ranker = PlanGateAndRanker()
    situation = ResponseSituation(
        obligation_frame=Obligation(obligation_kind="abstain_policy"),
        safety_frame=SimpleNamespace(category="violence", severity="high"),
    )
    weak = ResponseCandidatePlan(
        plan_id="weak",
        moves=[ResponseMove(move_type="safety_refusal", safety_required=True, priority=0)],
        framing_variant="sharp_refusal",
        safety_tags=["violence"],
        required_components={"explicit_negative", "no_instruction", "no_endorsement"},
        satisfied_components={"explicit_negative"},
        style=StyleVector(),
        estimated_cost_ms=1.0,
    )
    strong = ResponseCandidatePlan(
        plan_id="strong",
        moves=[ResponseMove(move_type="safety_refusal", safety_required=True, priority=0)],
        framing_variant="deescalating_refusal",
        safety_tags=["violence"],
        required_components={"explicit_negative", "no_instruction", "no_endorsement"},
        satisfied_components={"explicit_negative", "no_instruction", "no_endorsement", "deescalate"},
        style=StyleVector(),
        estimated_cost_ms=1.0,
    )

    weak_score = ranker._safety_score(weak, situation)
    strong_score = ranker._safety_score(strong, situation)

    assert 0.0 <= weak_score < strong_score <= 1.0
    assert strong_score == 1.0


def test_clean_value_escapes_html_and_removes_control_chars():
    dirty = "<script>alert(1)</script>\x00 <b>Name</b>"
    clean = SlotBinder._clean_value(dirty)

    assert "<script>" not in clean
    assert "<b>" not in clean
    assert "\x00" not in clean
    assert "&lt;script&gt;" in clean
    assert "&lt;b&gt;Name&lt;/b&gt;" in clean


def test_selected_slots_preserve_features_and_refs():
    selected_slot = SimpleNamespace(
        value="Chibu",
        relation_key="has_property",
        slot_kind="profile",
        confidence=0.88,
        source_relation_id="rel1",
        features={"property_dimension": "nickname", "semantic_dimension": "identity"},
    )
    situation = ResponseSituation(
        evidence=ResponseEvidencePacket(selected_slots={"answer": selected_slot}),
    )

    slots = SlotBinder().bind(situation)

    assert slots["answer"].value == "Chibu"
    assert slots["answer"].relation_key == "has_property"
    assert slots["answer"].slot_kind == "profile"
    assert slots["answer"].source_refs == ["rel1"]
    assert slots["answer"].features["property_dimension"] == "nickname"
    assert slots["answer"].features["semantic_dimension"] == "identity"


def test_selected_slots_dict_carriers_preserve_features():
    situation = ResponseSituation(
        evidence=ResponseEvidencePacket(selected_slots={
            "answer": {
                "value": "Ada",
                "slot_kind": "profile",
                "confidence": 0.91,
                "source_refs": ["record1"],
                "features": {"relation_key": "has_name", "property_dimension": "name"},
            }
        }),
    )

    slots = SlotBinder().bind(situation)

    assert slots["answer"].relation_key == "has_name"
    assert slots["answer"].source_refs == ["record1"]
    assert slots["answer"].features["property_dimension"] == "name"
