"""Regression acceptance for the post-v3.4.3 canonical runtime migration."""
from __future__ import annotations

import pytest

from cemm.app.runtime import Runtime


@pytest.fixture
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


def test_user_assertion_becomes_grounded_retrievable_knowledge(runtime: Runtime):
    from cemm.kernel.memory.semantic import FactQuery

    assertion = runtime.run_text("OK, my name is Chibueze")
    assert _errors(assertion) == ()
    assert assertion.surface_payload.surface_text == "Okay."
    assert any(
        item.predicate_semantic_key == "named"
        and item.communicative_force == "assert"
        for item in assertion.selected_interpretations
    )
    facts = runtime.semantic_memory.query(FactQuery(
        predicate_key="named",
        role_constraints={"holder": "user"},
        context_refs=("actual",),
    ))
    assert facts
    assert facts[-1].role("name").surface == "Chibueze"
    assert not facts[-1].role("name").value_ref.startswith("opaque:")

    query = runtime.run_text("what is my name?")
    assert _errors(query) == ()
    assert query.surface_payload.surface_text == "Your name is Chibueze."
    assert any(
        "fact:" in ref
        for ref in query.response_intents[0].provenance_refs
    )


def test_foundation_rules_are_connected_to_bounded_inference(runtime: Runtime):
    from cemm.kernel.inference.catalog import SemanticRuleCatalog
    from cemm.kernel.inference.engine import BoundedInferenceEngine
    from cemm.kernel.inference.rule_model import (
        InferenceBudget,
        SemanticFact as InferenceFact,
    )

    catalog = SemanticRuleCatalog(runtime.schema_store)
    rules = catalog.active_rules()
    assert any(rule.rule_id == "algebra:resides_with:symmetric" for rule in rules)
    outcome = BoundedInferenceEngine().infer(
        seed_facts=(InferenceFact(
            fact_id="seed:residence",
            predicate_key="resides_with",
            roles={"resident": "person:a", "co_resident": "person:b"},
            context_ref="actual",
        ),),
        rules=rules,
        budget=InferenceBudget(
            max_steps=32,
            max_depth=4,
            max_new_facts=16,
            max_rule_firings=32,
            wall_clock_ms=50,
        ),
        dependency_fingerprint="acceptance:v35",
    )
    assert any(
        fact.predicate_key == "resides_with"
        and fact.roles == {"resident": "person:b", "co_resident": "person:a"}
        for fact in outcome.derived_facts
    )
    assert outcome.elapsed_ms <= 250


def test_conditional_teaching_produces_nonempty_provisional_rule(runtime: Runtime):
    cycle = runtime.run_text("if I am a person then I am an agent")
    assert _errors(cycle) == ()
    assert cycle.rule_learning_results
    result = cycle.rule_learning_results[0]
    assert result.rule_schema_ref
    envelope = runtime.schema_store.get(result.rule_schema_ref)
    assert envelope is not None
    assert envelope.status == "provisional"
    assert envelope.payload.premises
    assert envelope.payload.conclusions
    assert envelope.payload.enabled_by_default is False
    assert "independent_competence_required" in result.blocker_refs


def test_french_assertion_uses_same_grounded_identity_path(runtime: Runtime):
    assertion = runtime.run_text(
        "ok, mon nom est Chibueze",
        language_hint="fr",
    )
    assert _errors(assertion) == ()
    assert assertion.surface_payload.surface_text == "D’accord."
    query = runtime.run_text(
        "quel est mon nom ?",
        language_hint="fr",
    )
    assert _errors(query) == ()
    assert query.surface_payload.surface_text == "Votre nom est Chibueze."
