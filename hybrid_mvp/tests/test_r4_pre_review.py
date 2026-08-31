"""Advisory R4.1 assistant pre-review ledger."""
from __future__ import annotations

from pathlib import Path

from scripts.r4_1_pre_review import (
    RecommendationClass,
    preflight_designation_source,
)

ROOT = Path(__file__).parents[1]


def test_preflight_quarantines_source_order_span_mismatch() -> None:
    row = {
        "source_case_ref": "case:source-order",
        "surface": "The server is offline. You said goodbye.",
        "candidate_output": "The server is offline. You said goodbye.",
        "resulting_scenario_row": {
            "surface_examples": ["goodbye. the server is offline."]
        },
        "candidate_bindings": [
            {
                "binding_ref": "binding:farewell",
                "surface": "goodbye",
                "start": 0,
                "end": 7,
                "unit_refs": ["unit:goodbye"],
                "designation_fact_ref": "fact:farewell",
                "candidate_target_ref": "event:farewell",
            },
            {
                "binding_ref": "binding:server",
                "surface": "server",
                "start": 13,
                "end": 19,
                "unit_refs": ["unit:server"],
                "designation_fact_ref": "fact:server",
                "candidate_target_ref": "entity:server",
            },
        ],
    }

    result = preflight_designation_source(row)

    assert (
        result.recommendation_class
        == RecommendationClass.BLOCKED_EVIDENCE_MISMATCH
    )
    assert result.action is None
    assert any(
        issue.issue_kind == "span_text_mismatch"
        for issue in result.issues
    )
    assert any(
        issue.issue_kind == "surface_example_order_mismatch"
        for issue in result.issues
    )


def test_preflight_accepts_matching_designation_geometry() -> None:
    row = {
        "source_case_ref": "case:matching",
        "surface": "goodbye. the server is offline.",
        "candidate_output": "goodbye. the server is offline.",
        "resulting_scenario_row": {
            "surface_examples": ["goodbye. the server is offline."]
        },
        "candidate_bindings": [
            {
                "binding_ref": "binding:farewell",
                "surface": "goodbye",
                "start": 0,
                "end": 7,
                "unit_refs": ["unit:goodbye"],
                "designation_fact_ref": "fact:farewell",
                "candidate_target_ref": "event:farewell",
            },
            {
                "binding_ref": "binding:server",
                "surface": "server",
                "start": 13,
                "end": 19,
                "unit_refs": ["unit:server"],
                "designation_fact_ref": "fact:server",
                "candidate_target_ref": "entity:server",
            },
            {
                "binding_ref": "binding:offline",
                "surface": "offline",
                "start": 23,
                "end": 30,
                "unit_refs": ["unit:offline"],
                "designation_fact_ref": "fact:offline",
                "candidate_target_ref": "value:offline",
            },
        ],
    }

    result = preflight_designation_source(row)

    assert result.recommendation_class is None
    assert result.action is None
    assert result.issues == ()
