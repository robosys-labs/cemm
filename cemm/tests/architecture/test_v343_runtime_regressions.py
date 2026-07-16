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

def test_v346_temporal_adjunct_preserves_core_state_query(runtime: Runtime):
    base = runtime.run_text("how are you?", context_id="v346:time")
    qualified = runtime.run_text("how are you today?", context_id="v346:time")

    assert _errors(base) == ()
    assert _errors(qualified) == ()
    assert qualified.surface_payload.surface_text == "I am available."
    assert qualified.selected_interpretations
    selected = qualified.selected_interpretations[0]
    assert selected.predicate_semantic_key == "has_state"
    assert selected.coverage_ratio >= 0.70
    assert selected.score_breakdown

    proposition = next(
        candidate.proposition
        for graph in qualified.meaning_candidates
        for candidate in graph.candidate_propositions
        if candidate.proposition.id == selected.proposition_ref
    )
    assert proposition.valid_time is not None
    assert proposition.valid_time.start is not None
    assert proposition.valid_time.end is not None


def test_v346_unresolved_residue_penalizes_but_does_not_erase_meaning(runtime: Runtime):
    cycle = runtime.run_text(
        "how are you today mysteriously",
        context_id="v346:partial",
    )
    assert _errors(cycle) == ()
    assert cycle.selected_interpretations
    assert cycle.selected_interpretations[0].predicate_semantic_key == "has_state"
    assert cycle.meaning_candidates[0].unresolved_fragments
    assert cycle.selected_interpretations[0].unresolved_fragment_refs
    assert cycle.surface_payload.surface_text == "I am available."


def test_v346_full_name_is_one_ordered_grounded_value_and_supersedes_short_form(
    runtime: Runtime,
):
    from cemm.kernel.memory.semantic import FactQuery

    short = runtime.run_text("my name is Chibueze", context_id="v346:name")
    assert _errors(short) == ()
    corrected = runtime.run_text(
        "My full name is actually Chibueze Opata",
        context_id="v346:name",
    )
    assert _errors(corrected) == ()
    assert corrected.selected_interpretations
    selected = next(
        item for item in corrected.selected_interpretations
        if item.predicate_semantic_key == "named"
    )
    assert selected.coverage_ratio == pytest.approx(1.0)

    active = runtime.semantic_memory.query(FactQuery(
        predicate_key="named",
        role_constraints={"holder": "user"},
        context_refs=("actual",),
    ))
    assert len(active) == 1
    fact = active[0]
    assert fact.role("name").surface == "Chibueze Opata"
    assert fact.role("name_form").semantic_key == "name_form:full"

    answer = runtime.run_text("what's my name?", context_id="v346:name")
    assert _errors(answer) == ()
    assert answer.surface_payload.surface_text == "Your name is Chibueze Opata."

    qualified_answer = runtime.run_text(
        "what is my full name?",
        context_id="v346:name",
    )
    assert _errors(qualified_answer) == ()
    assert qualified_answer.surface_payload.surface_text == (
        "Your name is Chibueze Opata."
    )


def test_v346_dialogue_ledger_resolves_recent_system_anaphora(runtime: Runtime):
    first = runtime.run_text("how are you?", context_id="v346:anaphora")
    assert first.surface_payload.surface_text == "I am available."

    cycle = runtime.run_text(
        "do you always say that?",
        context_id="v346:anaphora",
    )
    assert _errors(cycle) == ()
    interpretation = next(
        item for item in cycle.selected_interpretations
        if item.predicate_semantic_key == "communicates"
    )
    content = next(
        binding.filler_ref
        for binding in interpretation.role_bindings
        if binding.role_schema_ref == "role:content"
    )
    assert content.startswith("clause:")
    assert any(
        name == "anaphora_resolution" and value > 0
        for name, value in interpretation.score_breakdown
    )
    assert cycle.context_snapshot.recent_system_clause is not None
    assert cycle.response_candidates
    assert cycle.surface_payload.surface_text != "Please clarify what you mean."


def test_v346_grounded_difficulty_evaluation_is_not_unresolved(runtime: Runtime):
    cycle = runtime.run_text(
        "it's so hard to talk to you",
        context_id="v346:difficulty",
    )
    assert _errors(cycle) == ()
    assert any(
        item.predicate_semantic_key == "evaluates_difficulty"
        for item in cycle.selected_interpretations
    )
    assert cycle.surface_payload.surface_text != "Please clarify what you mean."


def test_v346_grounded_definition_creates_anchored_provisional_kind(runtime: Runtime):
    learned = runtime.run_text(
        "president is a person",
        context_id="v346:definition",
    )
    assert _errors(learned) == ()
    assert learned.definition_learning_results
    result = learned.definition_learning_results[0]
    assert result.status == "provisional"
    assert result.schema_record_ref
    assert result.anchor_refs
    assert "independent_competence_required" in result.blocker_refs

    envelope = runtime.schema_store.get(result.schema_record_ref)
    assert envelope is not None
    assert envelope.status == "provisional"
    assert envelope.payload.parent_kind_refs == ("person",)
    assert envelope.payload.grounding_anchor_refs
    assert runtime.schema_store.lookup_lexical_form(
        "president", "en"
    ) == (result.semantic_key,)

    reused = runtime.run_text(
        "I am a president",
        context_id="v346:definition",
    )
    assert _errors(reused) == ()
    assert any(
        item.predicate_semantic_key == "instance_of"
        and any(
            binding.role_schema_ref == "role:kind"
            and binding.filler_ref == result.semantic_key
            for binding in item.role_bindings
        )
        for item in reused.selected_interpretations
    )


def test_v346_agenda_inference_is_delta_triggered_and_bounded():
    from cemm.kernel.inference.agenda_engine import AgendaInferenceEngine
    from cemm.kernel.inference.rule_model import (
        CycleClass,
        InferenceBudget,
        RuleAtom,
        RuleStrength,
        SemanticFact as InferenceFact,
        SemanticRule,
    )

    irrelevant = tuple(
        InferenceFact(
            fact_id=f"irrelevant:{index}",
            predicate_key="noise",
            roles={"left": str(index)},
            context_ref="actual",
        )
        for index in range(200)
    )
    delta = InferenceFact(
        fact_id="delta:subkind",
        predicate_key="subkind_of",
        roles={"child_kind": "president", "parent_kind": "person"},
        context_ref="actual",
    )
    instance = InferenceFact(
        fact_id="seed:instance",
        predicate_key="instance_of",
        roles={"entity": "person:1", "kind": "president"},
        context_ref="actual",
    )
    rule = SemanticRule(
        rule_id="test:instance_subkind",
        premises=(
            RuleAtom("instance_of", {"entity": "$x", "kind": "$a"}),
            RuleAtom("subkind_of", {"child_kind": "$a", "parent_kind": "$b"}),
        ),
        conclusions=(
            RuleAtom("instance_of", {"entity": "$x", "kind": "$b"}),
        ),
        strength=RuleStrength.STRICT,
        cycle_class=CycleClass.POSITIVE_MONOTONE,
    )
    outcome = AgendaInferenceEngine().infer(
        seed_facts=(*irrelevant, instance, delta),
        delta_facts=(delta,),
        rules=(rule,),
        budget=InferenceBudget(
            max_steps=8,
            max_depth=4,
            max_new_facts=4,
            max_rule_firings=8,
            wall_clock_ms=50,
        ),
        dependency_fingerprint="test:v346:agenda",
    )
    assert outcome.status == "fixed_point"
    assert outcome.steps <= 2
    assert any(
        fact.predicate_key == "instance_of"
        and fact.roles == {"entity": "person:1", "kind": "person"}
        for fact in outcome.derived_facts
    )


def test_v346_french_temporal_and_full_name_share_semantic_path(runtime: Runtime):
    state = runtime.run_text(
        "comment allez vous aujourd’hui ?",
        language_hint="fr",
        context_id="v346:fr",
    )
    assert _errors(state) == ()
    assert state.surface_payload.surface_text == "Je suis disponible."
    selected = state.selected_interpretations[0]
    assert selected.predicate_semantic_key == "has_state"
    proposition = next(
        candidate.proposition
        for graph in state.meaning_candidates
        for candidate in graph.candidate_propositions
        if candidate.proposition.id == selected.proposition_ref
    )
    assert proposition.valid_time is not None

    assertion = runtime.run_text(
        "mon nom complet est Chibueze Opata",
        language_hint="fr",
        context_id="v346:fr",
    )
    assert _errors(assertion) == ()
    query = runtime.run_text(
        "quel est mon nom complet ?",
        language_hint="fr",
        context_id="v346:fr",
    )
    assert _errors(query) == ()
    assert query.surface_payload.surface_text == "Votre nom est Chibueze Opata."


def test_v346_embedded_name_knowledge_query_uses_context_not_clarification(
    runtime: Runtime,
):
    runtime.run_text(
        "my full name is Chibueze Opata",
        context_id="v346:knowledge",
    )
    cycle = runtime.run_text(
        "you don't even know my name?",
        context_id="v346:knowledge",
    )
    assert _errors(cycle) == ()
    interpretation = next(
        item for item in cycle.selected_interpretations
        if item.predicate_semantic_key == "knows"
    )
    assert interpretation.communicative_force == "ask"
    assert cycle.surface_payload.surface_text == "Your name is Chibueze Opata."
    assert cycle.surface_payload.surface_text != "Please clarify what you mean."


def test_v346_response_ranking_preserves_but_rejects_unnecessary_clarification(
    runtime: Runtime,
):
    cycle = runtime.run_text(
        "how are you today mysteriously",
        context_id="v346:response-ranking",
    )
    assert _errors(cycle) == ()
    assert len(cycle.response_candidates) >= 2
    assert cycle.response_intents[0].predicate_key == "has_state"
    clarification = next(
        candidate for candidate in cycle.response_candidates
        if candidate.intent.predicate_key == "requests"
    )
    answer = next(
        candidate for candidate in cycle.response_candidates
        if candidate.intent.predicate_key == "has_state"
    )
    assert answer.score > clarification.score
    assert any(
        name == "unnecessary_clarification" and value < 0
        for name, value in clarification.score_breakdown
    )


def test_v346_semantic_qualifier_identity_is_cross_context_and_cross_language(
    runtime: Runtime,
):
    from cemm.kernel.memory.semantic import FactQuery

    runtime.run_text(
        "my full name is Chibueze Opata",
        context_id="v346:qualifier-source",
    )
    english = runtime.run_text(
        "what is my full name?",
        context_id="v346:qualifier-query",
    )
    assert _errors(english) == ()
    assert english.surface_payload.surface_text == "Your name is Chibueze Opata."

    facts = runtime.semantic_memory.query(FactQuery(
        predicate_key="named",
        role_constraints={"holder": "user"},
        context_refs=("actual",),
    ))
    assert facts[-1].role("name_form").value_ref == "name_form:full"

    french = runtime.run_text(
        "quel est mon nom complet ?",
        language_hint="fr",
        context_id="v346:qualifier-query-fr",
    )
    assert _errors(french) == ()
    selected = next(
        item for item in french.selected_interpretations
        if item.predicate_semantic_key == "named"
    )
    assert any(
        binding.role_schema_ref == "role:name_form"
        and binding.filler_ref == "name_form:full"
        for binding in selected.role_bindings
    )
    assert french.surface_payload.surface_text == "Votre nom est Chibueze Opata."


def test_v346_definition_learning_does_not_bypass_schema_lifecycle(runtime: Runtime):
    from cemm.kernel.memory.semantic import FactQuery

    cycle = runtime.run_text(
        "president is a person",
        context_id="v346:no-definition-fact-bypass",
    )
    assert _errors(cycle) == ()
    result = cycle.definition_learning_results[0]
    assert result.status == "provisional"
    selected = next(
        item for item in cycle.selected_interpretations
        if item.predicate_semantic_key == "subkind_of"
    )
    child_ref = next(
        binding.filler_ref for binding in selected.role_bindings
        if binding.role_schema_ref == "role:child_kind"
    )
    assert runtime.semantic_memory.query(FactQuery(
        predicate_key="subkind_of",
        role_constraints={"child_kind": child_ref},
        context_refs=("actual",),
    )) == ()


def test_v346_conclusion_only_variables_become_bounded_existentials():
    from cemm.kernel.learning.grounded_rule_learner import GroundedRuleLearner
    from cemm.kernel.schema.rule import RuleAtom

    premise = (
        RuleAtom("related_to", {"left": "$v1", "right": "user"}),
    )
    conclusion = (
        RuleAtom("instance_of", {"entity": "$v2", "kind": "person"}),
        RuleAtom("related_to", {"left": "$v1", "right": "$v2"}),
    )
    premise, conclusion, declarations = GroundedRuleLearner._existentialize(
        premise, conclusion
    )
    assert premise[0].roles["left"] == "$v1"
    assert conclusion[0].roles["entity"] == "?e1"
    assert conclusion[1].roles["right"] == "?e1"
    assert len(declarations) == 1
    assert declarations[0].variable == "?e1"
    assert declarations[0].entity_kind_ref == "person"
    assert declarations[0].maximum_instances == 1


def test_v346_recursive_schema_compiler_blocks_unanchored_semantic_structure(
    runtime: Runtime,
):
    from cemm.kernel.learning.anchored_schema_compiler import (
        AnchoredLearnedSchemaCompiler,
    )
    from cemm.kernel.learning.assimilator import StagedContribution
    from cemm.kernel.schema.provenance import ProvenanceKind
    from cemm.kernel.model.identity import Scope, ScopeLevel

    compiler = AnchoredLearnedSchemaCompiler(runtime.schema_store)
    artifact = compiler.compile(
        target_semantic_key="learned_kind:unanchored",
        target_surface="unanchored",
        language_tag="en",
        scope=Scope(level=ScopeLevel.SESSION, session_id="v346:anchor"),
        contributions=(
            StagedContribution(
                field_name="semantic_family",
                field_value="entity_kind",
                provenance_kind=ProvenanceKind.ASSERTED,
                evidence_ref="evidence:v346",
            ),
            StagedContribution(
                field_name="parent_kind_ref",
                field_value="nonexistent_kind",
                provenance_kind=ProvenanceKind.ASSERTED,
                evidence_ref="evidence:v346",
            ),
        ),
        source_ref="source:v346",
        version=1,
    )
    assert "grounding_anchor:entity_kind:nonexistent_kind" in (
        artifact.unresolved_fields
    )
    assert "grounded_entity_place_event_self_anchor" in (
        artifact.unresolved_fields
    )
    assert artifact.primary_envelope.payload.grounding_anchor_refs == ()


def test_v346_correction_can_reactivate_a_previously_superseded_identity(
    runtime: Runtime,
):
    from cemm.kernel.memory.semantic import FactQuery

    runtime.run_text("my name is Chibueze", context_id="v346:reactivate")
    runtime.run_text(
        "my full name is Chibueze Opata",
        context_id="v346:reactivate",
    )
    correction = runtime.run_text(
        "my name is actually Chibueze",
        context_id="v346:reactivate",
    )
    assert _errors(correction) == ()
    facts = runtime.semantic_memory.query(FactQuery(
        predicate_key="named",
        role_constraints={"holder": "user"},
        context_refs=("actual",),
    ))
    assert len(facts) == 1
    assert facts[0].role("name").surface == "Chibueze"
    answer = runtime.run_text(
        "what is my name?",
        context_id="v346:reactivate",
    )
    assert answer.surface_payload.surface_text == "Your name is Chibueze."
