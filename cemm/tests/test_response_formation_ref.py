from __future__ import annotations

from types import SimpleNamespace

from cemm.response import ResponseFormationEngine
from cemm.response.primitive_goal_composer import PrimitiveGoalComposer
from cemm.response.types import ResponseSituation, WriteOutcome


class _Program:
    def __init__(self, *, atom_ids=None, instruction_kind="social", surface="") -> None:
        self._entry = SimpleNamespace(
            atom_ids=list(atom_ids or []),
            instruction_kind=instruction_kind,
            surface=surface,
        )

    @property
    def entry_instruction(self):
        return self._entry


def _intent_atom(key: str):
    return SimpleNamespace(kind="intent", key=key, features={})


def test_goal_composer_uses_intent_atoms_not_english_surface() -> None:
    situation = ResponseSituation(
        obligation_frame=SimpleNamespace(obligation_kind="social_reply", context={}, evidence_policy="none"),
        semantic_program=_Program(atom_ids=["a1"], surface="unrelated surface"),
        uol_graph=SimpleNamespace(atoms={"a1": _intent_atom("greeting")}),
    )

    goals = PrimitiveGoalComposer().compose(situation)

    assert [goal.goal_type for goal in goals] == ["greet"]


def test_response_engine_answers_user_profile_from_binding() -> None:
    fill = SimpleNamespace(
        surface="Chibu",
        concept_id="",
        entity_id="",
        relation_key="has_name",
        confidence=0.9,
        source_frame_ids=["rel1"],
        evidence_refs=[],
        features={"property_dimension": "name"},
    )
    binding = SimpleNamespace(
        has_answer=True,
        slot_fills=[fill],
        confidence=0.9,
        abstention_reason="",
        explanation_paths=[],
    )
    situation = ResponseSituation(
        obligation_frame=SimpleNamespace(
            obligation_kind="answer_user_profile",
            context={},
            evidence_policy="required",
        ),
        answer_binding=binding,
    )

    result = ResponseFormationEngine().form(situation)

    assert result.text == "Your name is Chibu."
    assert "rel1" in result.evidence_refs


def test_response_engine_does_not_claim_memory_before_commit() -> None:
    situation = ResponseSituation(
        obligation_frame=SimpleNamespace(
            obligation_kind="store_patch",
            context={},
            evidence_policy="speaker_asserted",
        ),
        semantic_program=_Program(surface="my name is Chibu"),
        write_outcome=WriteOutcome(commit_status="proposed", patch_count=1),
    )

    result = ResponseFormationEngine().form(situation)

    assert result.text == "Got it."
    assert "learned" not in result.text.lower()
    assert "stored" not in result.text.lower()


def test_response_engine_safety_refusal_is_required() -> None:
    situation = ResponseSituation(
        obligation_frame=SimpleNamespace(obligation_kind="abstain_policy", context={}, evidence_policy="none"),
        safety_frame=SimpleNamespace(category="interpersonal_violence", severity="high"),
    )

    result = ResponseFormationEngine().form(situation)

    assert result.text.startswith("No.")
    assert "safety" in result.diagnostics["moves"][0]["tags"]
