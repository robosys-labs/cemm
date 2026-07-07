from __future__ import annotations

from dataclasses import dataclass, field
from types import SimpleNamespace

from cemm.response.response_formation_engine import ResponseFormationEngine
from cemm.response.transformers import CandidateGenerator, PlanGateAndRanker
from cemm.response.types import ResponseMove, ResponseSituation, StyleVector, WriteOutcome


@dataclass
class Fill:
    surface: str = "Chibu"
    concept_id: str = ""
    entity_id: str = ""
    relation_key: str = "has_name"
    confidence: float = 0.9
    source_frame_ids: list[str] = field(default_factory=lambda: ["frame1"])
    evidence_refs: list[str] = field(default_factory=lambda: ["ev1"])
    explanation_path: list[str] = field(default_factory=lambda: ["frame1", "ev1"])
    features: dict = field(default_factory=lambda: {"property_dimension": "name"})


@dataclass
class Binding:
    has_answer: bool = True
    confidence: float = 0.9
    abstention_reason: str = ""
    slot_fills: list = field(default_factory=lambda: [Fill()])
    explanation_paths: list = field(default_factory=lambda: [["frame1", "ev1"]])


@dataclass
class Obligation:
    obligation_kind: str = "answer_user_profile"
    evidence_policy: str = "required"
    write_policy: str = "none"
    response_mode: str = "evidence_answer"
    required_slots: list = field(default_factory=list)
    blocked_by: list = field(default_factory=list)
    confidence: float = 0.8
    context: dict = field(default_factory=dict)


def test_phase4_generates_semantic_framing_variants_without_text_cues():
    situation = ResponseSituation(
        obligation_frame=Obligation(),
        answer_binding=Binding(),
        style=StyleVector(detail=0.85, warmth=0.75),
    )
    result = ResponseFormationEngine().form(situation)
    variants = {result.diagnostics["selected_plan"]["framing_variant"]}
    variants |= {p["framing_variant"] for p in result.diagnostics["rejected_plans"]}

    assert {"direct", "minimal", "with_evidence", "warm_followup"}.issubset(variants)
    assert result.text == "Your name is Chibu. (via: frame1 -> ev1)"


def test_phase4_safety_candidates_are_only_strict_refusal_framings():
    situation = ResponseSituation(
        obligation_frame=Obligation(obligation_kind="abstain_policy", evidence_policy="none"),
        safety_frame=SimpleNamespace(category="violence", severity="high"),
        style=StyleVector(warmth=0.9, detail=0.9),
    )
    result = ResponseFormationEngine().form(situation)
    variants = {result.diagnostics["selected_plan"]["framing_variant"]}
    variants |= {p["framing_variant"] for p in result.diagnostics["rejected_plans"]}

    assert variants <= {"sharp_refusal", "deescalating_refusal"}
    assert result.text.startswith("No.")


def test_phase4_gate_blocks_untruthful_write_confirmation():
    situation = ResponseSituation(
        obligation_frame=Obligation(obligation_kind="store_patch", evidence_policy="speaker_asserted"),
        write_outcome=WriteOutcome(commit_status="proposed", patch_count=1),
    )
    bad = ResponseMove(
        move_type="confirm_memory_write",
        required_components={"write_committed"},
        satisfied_components={"write_committed"},
        tags={"memory"},
    )
    plans = CandidateGenerator().generate([bad], situation)
    ranked = PlanGateAndRanker().rank(plans, situation)

    assert ranked[0].blocked_reason == "untruthful_write_confirmation"


def test_phase4_gate_blocks_internal_surface_leak():
    binding = Binding()
    binding.slot_fills[0].surface = "reply_obligation"
    situation = ResponseSituation(
        obligation_frame=Obligation(),
        answer_binding=binding,
    )
    result = ResponseFormationEngine().form(situation)

    assert result.text == "I don't have enough verified information to answer that."
    assert any(p.blocked_reason == "internal_surface_leak" for p in result.rejected_plans) or result.diagnostics["selected_plan"]["blocked_reason"] == "internal_surface_leak"
