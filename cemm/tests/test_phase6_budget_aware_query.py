from __future__ import annotations

from dataclasses import dataclass, field
from types import SimpleNamespace

from cemm.budget import BudgetController
from cemm.query import BudgetAwareSemanticQueryEngine, QueryBudgetPolicyBuilder
from cemm.response.types import BudgetFrame, ResponseSituation, TemperatureState


@dataclass
class Constraint:
    concept_id: str = ""
    entity_id: str = ""


@dataclass
class Query:
    relation_key: str = "has_name"
    subject_constraint: Constraint = field(default_factory=lambda: Constraint(entity_id="user"))
    object_constraint: Constraint = field(default_factory=Constraint)
    allow_inverse: bool = True
    allow_inheritance: bool = True
    allow_composition: bool = True
    evidence_policy: str = "required"


@dataclass
class Arg:
    entity_id: str = ""
    concept_id: str = ""


@dataclass
class Frame:
    relation_id: str
    relation_key: str = "has_name"
    subject: Arg = field(default_factory=lambda: Arg(entity_id="user"))
    object: Arg = field(default_factory=Arg)
    answerable: bool = True
    structural: bool = False
    confidence: float = 0.5
    evidence_refs: list[str] = field(default_factory=list)


@dataclass
class Fill:
    surface: str
    confidence: float
    source_frame_ids: list[str]
    evidence_refs: list[str]
    explanation_path: list[str] = field(default_factory=lambda: ["a", "b", "c"])


@dataclass
class Binding:
    slot_fills: list[Fill]
    has_answer: bool = True
    confidence: float = 0.0
    matched_frame_ids: list[str] = field(default_factory=list)
    explanation_paths: list[list[str]] = field(default_factory=list)


@dataclass
class Obligation:
    obligation_kind: str = "answer_user_profile"
    evidence_policy: str = "required"
    confidence: float = 0.8


class BaseEngine:
    def build_query(self, obligation, relation_frames, program=None, uol_graph=None):
        return Query(evidence_policy=getattr(obligation, "evidence_policy", ""))

    def execute(self, query, relation_frames):
        fills = [
            Fill(surface=f.relation_id, confidence=f.confidence, source_frame_ids=[f.relation_id], evidence_refs=f.evidence_refs)
            for f in relation_frames
            if f.relation_key == query.relation_key
        ]
        return Binding(slot_fills=fills, has_answer=bool(fills), confidence=max((f.confidence for f in fills), default=0.0))

    def build_contract(self, obligation, binding, program=None):
        return SimpleNamespace(binding_id="contract", slot_count=len(binding.slot_fills))


def test_phase6_tight_budget_disables_expansion_and_stops_on_sufficient_evidence():
    situation = ResponseSituation(
        obligation_frame=Obligation(),
        budget_frame=BudgetFrame(remaining_time_ms=80, latency_target_ms=50, required_confidence=0.6),
        temperature=TemperatureState(user_urgency=0.95),
    )
    decision = BudgetController().decide(situation)
    frames = [
        Frame("weak", confidence=0.4, evidence_refs=["ev0"]),
        Frame("strong", confidence=0.9, evidence_refs=["ev1"]),
        Frame("extra", confidence=0.8, evidence_refs=["ev2"]),
    ]
    query, binding, _contract, trace = BudgetAwareSemanticQueryEngine(BaseEngine()).run(
        Obligation(), frames, budget_decision=decision
    )

    assert query.allow_inverse is False
    assert query.allow_inheritance is False
    assert getattr(query, "stop_on_first_sufficient") is True
    assert len(binding.slot_fills) == 1
    assert binding.slot_fills[0].surface == "strong"
    assert trace.selected_fill_count == 1
    assert "stop_on_first_sufficient" in trace.reasons


def test_phase6_relaxed_budget_keeps_multiple_results_and_expansion_flags():
    situation = ResponseSituation(
        obligation_frame=Obligation(evidence_policy="speaker_asserted"),
        budget_frame=BudgetFrame(remaining_time_ms=10000, latency_target_ms=50, max_candidate_plans=8, required_confidence=0.3),
    )
    decision = BudgetController().decide(situation)
    frames = [Frame(f"f{i}", confidence=0.4 + i * 0.05, evidence_refs=[]) for i in range(5)]
    query, binding, _contract, trace = BudgetAwareSemanticQueryEngine(BaseEngine()).run(
        Obligation(evidence_policy="speaker_asserted"), frames, budget_decision=decision
    )

    assert query.allow_inverse is True
    assert query.allow_inheritance is True
    assert len(binding.slot_fills) > 1
    assert trace.selected_frame_count == len(frames)


def test_phase6_high_risk_requires_evidence_and_min_confidence():
    decision = BudgetController().decide(ResponseSituation(
        safety_frame=SimpleNamespace(category="violence", severity="high"),
        budget_frame=BudgetFrame(remaining_time_ms=10000, required_confidence=0.4),
    ))
    policy = QueryBudgetPolicyBuilder().build(budget_decision=decision, evidence_policy="required")

    assert policy.require_evidence_refs is True
    assert policy.min_confidence >= 0.7
    assert policy.max_results <= 4
    assert policy.stop_on_first_sufficient is True
