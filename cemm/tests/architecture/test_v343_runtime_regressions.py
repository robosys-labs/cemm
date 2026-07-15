"""Regression acceptance for the post-v3.4.3 canonical runtime migration."""
from __future__ import annotations

import pytest

from cemm.app.runtime import Runtime


@pytest.fixture(scope="module")
def runtime() -> Runtime:
    return Runtime()


def _errors(cycle) -> tuple[str, ...]:
    return tuple(getattr(cycle.trace, "errors", ()) or ())


def test_expressive_greeting_reaches_authorized_surface(runtime: Runtime):
    cycle = runtime.run_text("hiii")
    assert _errors(cycle) == ()
    assert cycle.surface_payload.surface_text == "Hello."
    assert cycle.realization_authorization.authorized
    assert len(cycle.selected_interpretations) == 1
    assert cycle.selected_interpretations[0].predicate_semantic_key == "greet"
    assert len(cycle.response_intents) == 1
    roles = {
        role.role_key: role.value_ref
        for role in cycle.response_intents[0].roles
    }
    assert roles == {"source": "self", "addressee": "user"}
    assert cycle.learning_transactions == ()


def test_broad_self_state_query_is_not_a_missing_dimension_lesson(runtime: Runtime):
    cycle = runtime.run_text("how are you?")
    assert _errors(cycle) == ()
    assert cycle.surface_payload.surface_text == "I am available."
    assert cycle.realization_authorization.authorized
    assert cycle.gaps == ()
    assert cycle.learning_transactions == ()

    interpretation = cycle.selected_interpretations[0]
    assert interpretation.predicate_semantic_key == "has_state"
    assert interpretation.communicative_force == "ask"
    assert {
        binding.role_schema_ref: binding.filler_ref
        for binding in interpretation.role_bindings
    } == {"role:holder": "self"}

    grounding = cycle.grounded_candidates[0].for_predication(
        interpretation.predication_ref
    )
    assert grounding.unresolved_role_refs == ()
    assert set(grounding.query_role_refs) >= {
        "role:dimension",
        "role:value",
    }
    assert any(
        "observation:self:operational_status" in result.relation_refs
        for result in cycle.retrieval_results
    )
    assert cycle.response_intents[0].predicate_key == "has_state"
    assert "observation:self:operational_status" in (
        cycle.response_intents[0].provenance_refs
    )


def test_unresolved_dialogue_repairs_without_opening_learning(runtime: Runtime):
    text = "what's going on, seems you don't understand nothing"
    cycle = runtime.run_text(text)
    assert _errors(cycle) == ()
    assert cycle.surface_payload.surface_text == "Please clarify what you mean."
    assert cycle.realization_authorization.authorized
    assert cycle.learning_transactions == ()
    assert all(not gap.learnable for gap in cycle.gaps)
    assert text not in cycle.surface_payload.surface_text


def test_name_query_uses_retrieval_not_input_echo(runtime: Runtime):
    cycle = runtime.run_text("what is your name?")
    assert _errors(cycle) == ()
    assert cycle.surface_payload.surface_text == "My name is CEMM."
    assert cycle.realization_authorization.authorized
    assert cycle.learning_transactions == ()
    assert any(
        "observation:self:name" in result.relation_refs
        for result in cycle.retrieval_results
    )


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("salut", "Bonjour."),
        ("comment allez vous ?", "Je suis disponible."),
    ],
)
def test_same_semantic_closure_in_french(
    runtime: Runtime,
    text: str,
    expected: str,
):
    cycle = runtime.run_text(text, language_hint="fr")
    assert _errors(cycle) == ()
    assert cycle.surface_payload.surface_text == expected
    assert cycle.realization_authorization.authorized
    assert cycle.learning_transactions == ()


def test_decide_is_an_explicit_cycle_artifact(runtime: Runtime):
    cycle = runtime.run_text("hi")
    assert "decide" in cycle.trace.stages
    assert cycle.response_intents
    assert cycle.message_plan.clauses
    assert cycle.message_plan.clauses[0].provenance_refs
