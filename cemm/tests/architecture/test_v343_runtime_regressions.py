"""Executable acceptance for compositional v3.4.4 runtime closure."""
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
    assert cycle.learning_transactions == ()


@pytest.mark.parametrize(
    "text",
    [
        "how are you?",
        "how're you?",
        "oh well, how are you?",
        "I mean how are you?",
        "well, how are you?",
        "please, how are you?",
    ],
)
def test_state_query_survives_contractions_and_discourse_prefaces(
    runtime: Runtime,
    text: str,
):
    cycle = runtime.run_text(text)
    assert _errors(cycle) == ()
    assert cycle.surface_payload.surface_text == "I am available."
    assert cycle.realization_authorization.authorized
    assert cycle.gaps == ()
    assert cycle.learning_transactions == ()
    assert any(
        item.predicate_semantic_key == "has_state"
        and item.communicative_force == "ask"
        for item in cycle.selected_interpretations
    )


@pytest.mark.parametrize(
    "text",
    [
        "what is your name?",
        "what's your name?",
        "what’s your name?",
        "well, what's your name?",
    ],
)
def test_name_query_uses_retrieval_after_token_expansion(
    runtime: Runtime,
    text: str,
):
    cycle = runtime.run_text(text)
    assert _errors(cycle) == ()
    assert cycle.surface_payload.surface_text == "My name is CEMM."
    assert cycle.realization_authorization.authorized
    assert cycle.learning_transactions == ()
    assert any(
        "observation:self:name" in result.relation_refs
        for result in cycle.retrieval_results
    )


@pytest.mark.parametrize(
    ("surface", "components"),
    [
        ("what's", ("what", "is")),
        ("how's", ("how", "is")),
        ("how're", ("how", "are")),
        ("you're", ("you", "are")),
        ("I'm", ("i", "am")),
        ("can't", ("can", "not")),
        ("couldn't", ("could", "not")),
        ("don't", ("do", "not")),
        ("doesn't", ("does", "not")),
    ],
)
def test_english_token_expansions_preserve_raw_source(
    runtime: Runtime,
    surface: str,
    components: tuple[str, ...],
):
    cycle = runtime.run_text(surface)
    assert _errors(cycle) == ()
    token = cycle.surface_evidence[0].token_stream.tokens[0]
    assert token.raw_form == surface
    assert token.contraction is not None
    assert tuple(value.casefold() for value in token.contraction.components) == components
    if "not" in components:
        assert token.is_negation


_EN_CAPABILITIES = [
    ("perceive", "I can perceive input.", "op:perceive", True),
    ("interpret", "I can interpret meaning.", "op:interpret", True),
    ("ground", "I can ground meaning.", "op:ground", True),
    ("retrieve", "I can retrieve stored information.", "op:retrieve", True),
    ("infer", "I can infer.", "op:infer", True),
    ("learn", "I can learn from evidence.", "op:learn", True),
    ("store", "I can store grounded facts.", "op:store_fact", True),
    ("answer", "I can answer questions.", "op:answer", True),
    ("realize", "I can realize responses.", "op:realize", True),
    ("dispatch", "I cannot dispatch responses.", "op:dispatch", False),
]


@pytest.mark.parametrize(
    ("surface", "expected", "operation", "capable"),
    _EN_CAPABILITIES,
)
def test_specific_capability_query_uses_live_assessment(
    runtime: Runtime,
    surface: str,
    expected: str,
    operation: str,
    capable: bool,
):
    cycle = runtime.run_text(f"can you {surface}?")
    assert _errors(cycle) == ()
    assert cycle.surface_payload.surface_text == expected
    assert cycle.realization_authorization.authorized
    assert cycle.learning_transactions == ()
    assert len(cycle.capability_assessments) == 1
    assessment = cycle.capability_assessments[0]
    assert assessment.operation_schema_ref == operation
    assert assessment.is_capable is capable
    assert assessment.assessment_id
    assert cycle.response_intents[0].predicate_key == "capable_of"
    assert cycle.response_intents[0].polarity == (
        "positive" if capable else "negative"
    )
    assert cycle.response_intents[0].provenance_refs
    proof = cycle.realization_authorization.clause_proofs[0]
    assert proof.self_claim_proof is not None
    assert proof.self_claim_proof.authorized


def test_open_capability_query_reports_only_live_operations(runtime: Runtime):
    cycle = runtime.run_text("what can you do?")
    assert _errors(cycle) == ()
    assert cycle.realization_authorization.authorized
    assert "Please clarify" not in cycle.surface_payload.surface_text
    assert "I can learn from evidence." in cycle.surface_payload.surface_text
    assert "I can answer questions." in cycle.surface_payload.surface_text
    assessments = {
        item.operation_schema_ref: item
        for item in cycle.capability_assessments
    }
    assert len(assessments) == 10
    assert not assessments["op:dispatch"].is_capable
    assert all(
        item.is_capable
        for key, item in assessments.items()
        if key != "op:dispatch"
    )
    assert len(cycle.response_intents) == 9
    assert all(
        intent.predicate_key == "capable_of"
        for intent in cycle.response_intents
    )
    assert ". I can " in cycle.surface_payload.surface_text


def test_unlicensed_extra_content_does_not_hijack_known_query(runtime: Runtime):
    cycle = runtime.run_text("banana how are you?")
    assert _errors(cycle) == ()
    assert cycle.surface_payload.surface_text == "Please clarify what you mean."
    assert cycle.learning_transactions == ()


def test_unresolved_dialogue_repairs_without_opening_learning(runtime: Runtime):
    text = "what's going on, seems you don't understand nothing"
    cycle = runtime.run_text(text)
    assert _errors(cycle) == ()
    assert cycle.surface_payload.surface_text == "Please clarify what you mean."
    assert cycle.realization_authorization.authorized
    assert cycle.learning_transactions == ()
    assert all(not gap.learnable for gap in cycle.gaps)
    assert text not in cycle.surface_payload.surface_text


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("salut", "Bonjour."),
        ("comment allez vous ?", "Je suis disponible."),
        ("je veux dire comment allez vous ?", "Je suis disponible."),
        ("eh bien comment allez vous ?", "Je suis disponible."),
        ("quel est votre nom ?", "Je m’appelle CEMM."),
        ("blorpt", "Veuillez préciser ce que vous voulez dire."),
    ],
)
def test_french_dialogue_and_retrieval_are_compositional(
    runtime: Runtime,
    text: str,
    expected: str,
):
    cycle = runtime.run_text(text, language_hint="fr")
    assert _errors(cycle) == ()
    assert cycle.surface_payload.surface_text == expected
    assert cycle.realization_authorization.authorized
    assert cycle.learning_transactions == ()


@pytest.mark.parametrize(
    ("surface", "components"),
    [
        ("pouvez-vous", ("pouvez", "vous")),
        ("êtes-vous", ("êtes", "vous")),
    ],
)
def test_french_token_expansions_preserve_raw_source(
    runtime: Runtime,
    surface: str,
    components: tuple[str, ...],
):
    cycle = runtime.run_text(surface, language_hint="fr")
    assert _errors(cycle) == ()
    token = cycle.surface_evidence[0].token_stream.tokens[0]
    assert token.raw_form == surface
    assert token.contraction is not None
    assert tuple(value.casefold() for value in token.contraction.components) == components


_FR_CAPABILITIES = [
    ("percevoir", "Je peux percevoir les entrées.", "op:perceive", True),
    ("interpréter", "Je peux interpréter le sens.", "op:interpret", True),
    ("ancrer", "Je peux ancrer le sens.", "op:ground", True),
    (
        "retrouver",
        "Je peux retrouver les informations stockées.",
        "op:retrieve",
        True,
    ),
    ("inférer", "Je peux inférer.", "op:infer", True),
    (
        "apprendre",
        "Je peux apprendre à partir de preuves.",
        "op:learn",
        True,
    ),
    (
        "stocker",
        "Je peux stocker des faits fondés.",
        "op:store_fact",
        True,
    ),
    (
        "répondre",
        "Je peux répondre aux questions.",
        "op:answer",
        True,
    ),
    (
        "réaliser",
        "Je peux réaliser des réponses.",
        "op:realize",
        True,
    ),
    (
        "transmettre",
        "Je ne peux pas transmettre des réponses.",
        "op:dispatch",
        False,
    ),
]


@pytest.mark.parametrize(
    ("surface", "expected", "operation", "capable"),
    _FR_CAPABILITIES,
)
def test_french_capability_queries_use_same_live_assessments(
    runtime: Runtime,
    surface: str,
    expected: str,
    operation: str,
    capable: bool,
):
    cycle = runtime.run_text(
        f"pouvez-vous {surface} ?",
        language_hint="fr",
    )
    assert _errors(cycle) == ()
    assert cycle.surface_payload.surface_text == expected
    assert cycle.realization_authorization.authorized
    assessment = cycle.capability_assessments[0]
    assert assessment.operation_schema_ref == operation
    assert assessment.is_capable is capable


def test_french_open_capability_query_exercises_multiclause_realization(
    runtime: Runtime,
):
    cycle = runtime.run_text(
        "que pouvez vous faire ?",
        language_hint="fr",
    )
    assert _errors(cycle) == ()
    assert cycle.realization_authorization.authorized
    assert "Je peux apprendre à partir de preuves." in (
        cycle.surface_payload.surface_text
    )
    assert "Je peux répondre aux questions." in cycle.surface_payload.surface_text
    assert len(cycle.response_intents) == 9
    assert ". Je peux " in cycle.surface_payload.surface_text


def test_decide_and_capability_are_explicit_cycle_artifacts(runtime: Runtime):
    cycle = runtime.run_text("can you learn?")
    assert "decide" in cycle.trace.stages
    assert cycle.response_intents
    assert cycle.capability_assessments
    assert cycle.message_plan.clauses
    assert cycle.message_plan.clauses[0].provenance_refs
