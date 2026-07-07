from __future__ import annotations

from types import SimpleNamespace

from cemm.learning import OutcomeSignal, ResponseBudgetLearningExtractor
from cemm.learning.patch_factory import LearningPatchFactory
from cemm.response import ResponseFormationEngine
from cemm.response.types import BudgetDecision, BudgetFrame, ResponseBundle, ResponseCandidatePlan, ResponseMove, ResponseSituation, StageBudget


def _social_situation_with_budget(pressure: float = 0.2) -> ResponseSituation:
    graph = SimpleNamespace(atoms={
        "i1": SimpleNamespace(id="atom:greeting", kind="intent", key="greeting", features={}, confidence=0.9)
    })
    return ResponseSituation(
        obligation_frame=SimpleNamespace(obligation_kind="social_reply", response_mode="social_response", context={}, evidence_policy="none"),
        uol_graph=graph,
        semantic_program=SimpleNamespace(entry_instruction=SimpleNamespace(atom_ids=["i1"], instruction_kind="social")),
        budget_frame=BudgetFrame(remaining_time_ms=5000, total_time_ms=5000),
        budget_decision=BudgetDecision(
            input_budget=BudgetFrame(),
            stage_budget=StageBudget(selector_mode="score", candidate_plan_limit=4),
            pressure=pressure,
            task_size=0.2,
            risk_level="normal",
            reasons=["test_budget"],
        ),
    )


def test_phase9_engine_returns_learning_patch_candidates_without_committing():
    situation = _social_situation_with_budget()
    result = ResponseFormationEngine().form(situation)

    assert result.learning_result is not None
    assert result.learning_patch_candidates
    assert result.diagnostics["learning"]["commit_performed"] is False
    assert result.diagnostics["learning"]["raw_text_persisted"] is False
    assert {p.target for p in result.learning_patch_candidates} >= {
        "response_construction_stats",
        "framing_success_stats",
        "budget_allocation_stats",
    }


def test_phase9_response_learning_uses_structured_outcome_not_raw_text():
    situation = _social_situation_with_budget()
    bundle = ResponseBundle(
        text="Hello!",
        language="en",
        moves=[ResponseMove(move_type="social_greet")],
        selected_plan_id="plan-1",
        evidence_refs=["frame:1"],
        obligation_kind="social_reply",
        budget_decision=situation.budget_decision,
        diagnostics={
            "candidate_count": 2,
            "selected_plan": {"framing_variant": "minimal"},
        },
    )
    learning = ResponseBudgetLearningExtractor().extract(
        situation=situation,
        bundle=bundle,
        explicit_outcome=OutcomeSignal(outcome_type="success", confidence=0.9, source_refs=["signal:reaction"]),
    )

    assert learning.observation.outcome.outcome_type == "success"
    assert all("text" not in p.payload for p in learning.patch_candidates)
    assert all("raw_text" not in p.payload for p in learning.patch_candidates)
    assert all(p.operation == "increment_stat" for p in learning.patch_candidates)


def test_phase9_coverage_complaint_updates_budget_and_distillation_stats():
    situation = _social_situation_with_budget(pressure=0.85)
    distillation = SimpleNamespace(coverage_estimate=0.35, partial=True, confidence=0.7, evidence_refs=["source:docmap"])
    situation.distillation_result = distillation
    bundle = ResponseBundle(
        language="en",
        moves=[ResponseMove(move_type="answer")],
        selected_plan_id="plan-doc",
        rejected_plans=[ResponseCandidatePlan(plan_id="r1")],
        evidence_refs=["frame:doc"],
        obligation_kind="answer_concept",
        budget_decision=situation.budget_decision,
        distillation_result=distillation,
        diagnostics={"candidate_count": 3, "selected_plan": {"framing_variant": "with_evidence"}},
    )
    learning = ResponseBudgetLearningExtractor().extract(
        situation=situation,
        bundle=bundle,
        explicit_outcome=OutcomeSignal(outcome_type="coverage_complaint", confidence=0.8, source_refs=["turn:next"]),
    )

    targets = {p.target for p in learning.patch_candidates}
    assert "budget_allocation_stats" in targets
    assert "distillation_strategy_stats" in targets
    budget_patch = next(p for p in learning.patch_candidates if p.target == "budget_allocation_stats")
    assert budget_patch.key[1] == "high_pressure"
    assert budget_patch.delta["coverage_complaint"] == 1.0


def test_phase9_patch_factory_redacts_raw_surface_payloads():
    patch = LearningPatchFactory().make(
        target="response_construction_stats",
        key=("answer_concept", "direct"),
        delta={"selected": 1},
        confidence=0.9,
        source_refs=["frame:1"],
        payload={"text": "raw user message", "safe_id": "frame:1", "label": "not an identifier with spaces"},
    )

    assert "text" not in patch.payload
    assert patch.payload["safe_id"] == "frame:1"
    assert patch.payload["label"] == "<redacted_surface>"


def test_phase9_rejects_unknown_learning_targets():
    from cemm.learning.learning_extractor import ResponseBudgetLearningExtractor
    from cemm.learning.learning_types import LearningPatchCandidate

    bad = LearningPatchCandidate(target="durable_memory_write", payload={})
    accepted, rejected = ResponseBudgetLearningExtractor._partition([bad])
    assert not accepted
    assert rejected == [bad]
