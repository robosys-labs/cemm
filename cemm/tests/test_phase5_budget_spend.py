from dataclasses import dataclass, field
from types import SimpleNamespace

from cemm.budget import BudgetController
from cemm.response.response_formation_engine import ResponseFormationEngine
from cemm.response.types import BudgetFrame, ResponseSituation, StyleVector, TemperatureState


@dataclass
class Fill:
    surface: str = "Paris"
    concept_id: str = ""
    entity_id: str = ""
    relation_key: str = "has_property"
    confidence: float = 0.9
    source_frame_ids: list[str] = field(default_factory=lambda: ["frame1"])
    evidence_refs: list[str] = field(default_factory=lambda: ["ev1"])
    explanation_path: list[str] = field(default_factory=lambda: ["frame1", "ev1"])
    features: dict = field(default_factory=lambda: {"property_dimension": "location"})


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


def test_high_urgency_reduces_candidate_spend_without_surface_parsing():
    situation = ResponseSituation(
        obligation_frame=Obligation(),
        answer_binding=Binding(),
        budget_frame=BudgetFrame(max_candidate_plans=8, max_realized_candidates=3),
        temperature=TemperatureState(user_urgency=0.95),
        style=StyleVector(detail=0.8),
    )
    result = ResponseFormationEngine().form(situation)
    assert result.diagnostics["budget"]["stage"]["candidate_plan_limit"] <= 2
    assert result.diagnostics["budget"]["stage"]["realized_candidate_limit"] == 1
    assert result.diagnostics["budget"]["stage"]["selector_mode"] == "first_good_enough"
    assert result.text


def test_relaxed_budget_allows_more_candidates():
    situation = ResponseSituation(
        obligation_frame=Obligation(),
        answer_binding=Binding(),
        budget_frame=BudgetFrame(remaining_time_ms=10000, latency_target_ms=50, max_candidate_plans=7, max_realized_candidates=3, coverage_target=0.9),
        temperature=TemperatureState(user_urgency=0.0),
        style=StyleVector(detail=0.9, warmth=0.8),
    )
    result = ResponseFormationEngine().form(situation)
    assert result.diagnostics["budget"]["stage"]["candidate_plan_limit"] == 7
    assert result.diagnostics["candidate_count"] > 1


def test_safety_budget_is_strict_even_under_relaxed_budget():
    safety = SimpleNamespace(category="violence", severity="high")
    situation = ResponseSituation(
        obligation_frame=Obligation(obligation_kind="abstain_policy", evidence_policy="none"),
        answer_binding=Binding(has_answer=False, slot_fills=[]),
        safety_frame=safety,
        budget_frame=BudgetFrame(remaining_time_ms=10000, max_candidate_plans=8, max_realized_candidates=3),
        style=StyleVector(detail=0.9),
    )
    result = ResponseFormationEngine().form(situation)
    assert result.diagnostics["budget"]["stage"]["selector_mode"] == "deterministic_strict"
    assert result.diagnostics["candidate_count"] == 1
    assert "safety_refusal" in [m.move_type for m in result.moves]
    assert result.text.startswith("No.")


def test_deadline_parser_uses_semantic_metadata_only():
    signal = SimpleNamespace(metadata={"time_budget_ms": 120})
    situation = ResponseSituation(signal=signal, budget_frame=BudgetFrame(total_time_ms=5000, remaining_time_ms=5000))
    decision = BudgetController().decide(situation)
    assert decision.input_budget.remaining_time_ms == 120
    assert "semantic_deadline" in decision.reasons
