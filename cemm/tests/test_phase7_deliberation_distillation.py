from __future__ import annotations

from dataclasses import dataclass, field
from types import SimpleNamespace

from cemm.budget import BudgetController
from cemm.deliberation import AnytimeDistiller, DeliberationPlanner, SourceMapper
from cemm.response.types import BudgetFrame, ResponseSituation, TemperatureState


@dataclass
class Source:
    source_id: str = "doc1"
    source_type: str = "pdf"
    token_count: int = 150_000
    metadata: dict = field(default_factory=dict)
    sections: list[dict] = field(default_factory=list)
    artifacts: list[dict] = field(default_factory=list)


def large_source() -> Source:
    sections = [
        {"section_id": "abstract", "role": "abstract", "index": 0, "salience": 1.0, "source_refs": ["p1"]},
        {"section_id": "toc", "role": "toc", "index": 1, "salience": 0.95, "source_refs": ["p2"]},
        {"section_id": "intro", "role": "intro", "index": 2, "salience": 0.9, "source_refs": ["p3"]},
        *[
            {"section_id": f"s{i}", "role": "body", "index": i + 3, "salience": 0.4 + (i % 5) * 0.1, "source_refs": [f"p{i+4}"]}
            for i in range(45)
        ],
        {"section_id": "conclusion", "role": "conclusion", "index": 99, "salience": 0.95, "source_refs": ["p99"]},
    ]
    artifacts = [{"artifact_id": f"t{i}", "artifact_type": "table", "salience": 0.8, "source_refs": [f"table{i}"]} for i in range(8)]
    return Source(sections=sections, artifacts=artifacts, metadata={"page_count": 80, "metadata_refs": ["meta"]})


def test_phase7_large_source_tight_budget_selects_rapid_skim():
    situation = ResponseSituation(
        budget_frame=BudgetFrame(remaining_time_ms=240_000, total_time_ms=300_000, coverage_target=0.8),
        temperature=TemperatureState(user_urgency=0.6),
    )
    plan = DeliberationPlanner().plan(situation, [large_source()])

    assert plan.strategy == "rapid_skim"
    assert plan.distillation_policy == "rapid_skim"
    assert "coverage_note" in plan.disclosure_requirements
    assert "large_source_tight_budget" in plan.reasons


def test_phase7_recursive_allowed_with_moderate_budget_selects_recursive_distill():
    situation = ResponseSituation(
        budget_frame=BudgetFrame(
            remaining_time_ms=600_000,
            total_time_ms=900_000,
            max_recursive_steps=3,
            allow_recursive_distillation=True,
            coverage_target=0.75,
        )
    )
    plan = DeliberationPlanner().plan(situation, [large_source()])

    assert plan.strategy == "recursive_distill"
    assert plan.max_recursive_steps >= 1
    assert plan.retrieval_policy == "sampled"


def test_phase7_safety_risk_bypasses_document_exploration():
    situation = ResponseSituation(
        safety_frame=SimpleNamespace(category="violence", severity="high"),
        budget_frame=BudgetFrame(remaining_time_ms=1_000_000),
    )
    plan = DeliberationPlanner().plan(situation, [large_source()])

    assert plan.strategy == "safety_first"
    assert plan.distillation_policy == "none"
    assert plan.source_ids == ["doc1"]


def test_phase7_anytime_distiller_reads_core_and_reports_partial_coverage():
    source = large_source()
    situation = ResponseSituation(
        budget_frame=BudgetFrame(remaining_time_ms=240_000, total_time_ms=300_000, coverage_target=0.85),
    )
    plan = DeliberationPlanner().plan(situation, [source])

    def provider(unit):
        return {"summary_atoms": [f"atom:{unit.unit_id}"], "evidence_refs": list(unit.source_refs), "confidence": 0.8}

    result = AnytimeDistiller().distill([source], plan, content_provider=provider, budget_ms=1200)

    assert result.strategy == "rapid_skim"
    assert result.units
    assert any(u.unit_type == "metadata" for u in result.units)
    assert any("abstract" in u.unit_id for u in result.units)
    assert result.partial is True
    assert "coverage_below_target" in result.blind_spots
    assert result.evidence_refs


def test_phase7_source_mapping_uses_structured_roles_not_surface_cues():
    source = Source(
        source_id="x",
        token_count=10,
        sections=[{"section_id": "a", "role": "abstract", "source_refs": ["r1"]}],
        artifacts=[],
    )
    doc = SourceMapper().map_document(source)

    assert doc.sections[0].role == "abstract"
    assert doc.sections[0].source_refs == ["r1"]
