"""Audited v3.4.1 semantic and realization communication closure.

The tokenizer does not own a known-word ontology.  This module registers a
small ordinary-schema closure that lets CEMM discuss its own uncertainty and
conduct teaching dialogue.  Every open-class realization points to an active
semantic schema; closed-class realizations point to grammar competence tests.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ..model.identity import Permission, Provenance, Scope, ScopeLevel
from ..model.refs import FrozenMap
from ..model.surface import LexicalFormRef
from ..schema.envelope import SchemaEnvelope
from ..schema.entity_kind import EntityKindSchema
from ..schema.construction import ConstructionSchema
from ..schema.lexeme import LexemeSenseSchema
from ..schema.operation import OperationSchema
from ..schema.predicate import (
    CardinalityPolicy,
    ContextBehavior,
    EvidencePolicy,
    IdentityPolicy,
    ModalityBehavior,
    PersistencePolicy,
    PolarityBehavior,
    PredicateSchema,
    QueryProjection,
)
from ..schema.realization import RealizationSchema
from ..schema.role import RoleSchema
from ..schema.store import SemanticSchemaStore

_BOOT_VERSION = "v3.4.1"


@dataclass(frozen=True, slots=True)
class RealizationSpec:
    surface: str
    part_of_speech: str
    modes: frozenset[str]
    closed_class: bool = False
    form_key: str = "base"


def _active_envelope(
    *,
    record_id: str,
    semantic_key: str,
    schema_kind: str,
    payload: Any,
    test_refs: tuple[str, ...],
    confidence: float = 1.0,
) -> SchemaEnvelope:
    """Create an audited boot record with explicit assessment lineage."""
    return SchemaEnvelope(
        record_id=record_id,
        semantic_key=semantic_key,
        schema_kind=schema_kind,
        status="active",
        scope=Scope(level=ScopeLevel.GLOBAL),
        version=1,
        payload=payload,
        support_refs=test_refs,
        confidence=confidence,
        permission=Permission.public(),
        provenance=Provenance(
            source_id=f"boot:{_BOOT_VERSION}",
            source_kind="boot",
            language_tag="und",
        ),
        grounding_assessment_ref=f"boot_assessment:grounding:{record_id}",
        competence_assessment_ref=f"boot_assessment:competence:{record_id}",
        epistemic_admissibility_ref=f"boot_assessment:admissibility:{record_id}",
        activation_environment_fingerprint=f"foundation:{_BOOT_VERSION}",
    )


def _role(
    key: str,
    *,
    embedded_proposition: bool = False,
    embedded_predication: bool = False,
) -> RoleSchema:
    return RoleSchema(
        role_key=key,
        required=True,
        accepted_object_families=frozenset(
            {"referent", "value", "proposition", "predication", "context"}
        ),
        allows_open_port=True,
        allows_embedded_proposition=embedded_proposition,
        allows_embedded_predication=embedded_predication,
    )


def _predicate(
    key: str,
    roles: tuple[str, ...],
    *,
    kind: str = "relation",
    stative: bool = False,
    query_roles: tuple[str, ...] = (),
) -> PredicateSchema:
    from ..model.predication import AspectProfile

    normalized_query_roles = tuple(
        role if role.startswith("role:") else f"role:{role}"
        for role in query_roles
    )
    projections = (
        QueryProjection(projection_kind="open_role", role_refs=normalized_query_roles),
    ) if query_roles else ()
    return PredicateSchema(
        semantic_key=key,
        predication_kind=kind,
        agentive=False,
        aspect_profile=AspectProfile(is_stative=stative),
        role_refs=tuple(f"role:{role}" for role in roles),
        context_behavior=ContextBehavior(
            supports_reported=True,
            supports_hypothetical=True,
            supports_counterfactual=True,
            supports_quoted=True,
        ),
        polarity_behavior=PolarityBehavior(
            supports_negation=True,
            negation_kind="contradictory",
        ),
        modality_behavior=ModalityBehavior(supports_modality=True),
        query_projections=projections,
        identity_policy=IdentityPolicy(
            includes_valid_time=True,
            includes_modal_qualifiers=True,
            includes_attribution=True,
        ),
        cardinality_policy=CardinalityPolicy(
            cardinality="many",
            reinforcement_policy="reinforce",
        ),
        evidence_policy=EvidencePolicy(minimum_evidence_count=1),
        persistence_policy=PersistencePolicy(retention="long_term"),
    )


_ROLE_KEYS = frozenset({
    "entity", "kind", "child_kind", "parent_kind", "knower", "content",
    "lexical_form", "schema_sense", "believer", "proposition", "subject",
    "complement", "requested_content", "truth_status", "question",
    "addressee", "source", "target", "semantic_family", "differentiator",
    "role_holder", "office_role", "evidence", "record", "artifact",
    "recognizer", "holder", "agent", "requirement", "left", "right",
    "operation", "recipient", "information", "speaker", "condition",
    "context", "message",
})


# These predicates are deliberately operationally distinct.  In particular,
# recognizes_form does not entail understands/knows, and stores does not entail
# remembers or knows.
_PREDICATES: dict[str, PredicateSchema] = {
    "instance_of": _predicate("instance_of", ("entity", "kind"), query_roles=("kind",)),
    "subkind_of": _predicate("subkind_of", ("child_kind", "parent_kind"), query_roles=("parent_kind",)),
    "knows": _predicate("knows", ("knower", "content"), stative=True, query_roles=("content",)),
    "means": _predicate("means", ("lexical_form", "schema_sense"), stative=True, query_roles=("schema_sense",)),
    "believes": _predicate("believes", ("believer", "proposition"), stative=True, query_roles=("proposition",)),
    "copular": _predicate("copular", ("subject", "complement"), stative=True, query_roles=("complement",)),
    "query_content": _predicate("query_content", ("requested_content",), kind="event", query_roles=("requested_content",)),
    "query_truth": _predicate("query_truth", ("proposition", "truth_status"), kind="event", query_roles=("truth_status",)),
    "greet": _predicate("greet", ("source", "addressee"), kind="event"),
    "desires": _predicate("desires", ("holder", "content"), stative=True, query_roles=("content",)),
    "has_condition": _predicate("has_condition", ("holder", "condition"), stative=True, query_roles=("condition",)),
    "capable_of": _predicate("capable_of", ("agent", "operation"), stative=True, query_roles=("operation",)),
    "recognizes_form": _predicate("recognizes_form", ("recognizer", "lexical_form"), stative=True),
    "has_usable_definition": _predicate("has_usable_definition", ("holder", "schema_sense"), stative=True),
    "has_sufficient_information": _predicate("has_sufficient_information", ("agent", "content"), stative=True),
    "requires_information": _predicate("requires_information", ("agent", "requirement"), stative=True),
    "associates": _predicate("associates", ("source", "left", "right"), kind="relation"),
    "stores": _predicate("stores", ("agent", "artifact"), kind="event"),
    "completes": _predicate("completes", ("agent", "operation"), kind="event"),
    "corrects": _predicate("corrects", ("agent", "proposition"), kind="event"),
    "has_access_to": _predicate("has_access_to", ("holder", "information"), stative=True),
    "receives": _predicate("receives", ("recipient", "information"), kind="event"),
    "requests": _predicate("requests", ("speaker", "addressee", "content"), kind="event"),
    "is_incomplete": _predicate("is_incomplete", ("artifact",), stative=True),
}


_ENTITY_KINDS: dict[str, EntityKindSchema] = {
    "lexical_form": EntityKindSchema(
        semantic_key="lexical_form",
        parent_kind_refs=("information_object",),
        identity_criteria=("language_tag", "normalized_surface", "sense_cluster"),
    ),
    "semantic_definition": EntityKindSchema(
        semantic_key="semantic_definition",
        parent_kind_refs=("information_object",),
        identity_criteria=("target_schema_ref", "constitutive_structure"),
    ),
    "role": EntityKindSchema(
        semantic_key="role",
        parent_kind_refs=("information_object",),
        identity_criteria=("role_schema_ref", "applicability_context"),
    ),
    "semantic_distinction": EntityKindSchema(
        semantic_key="semantic_distinction",
        parent_kind_refs=("information_object",),
        identity_criteria=("contrasted_schema_refs",),
    ),
    "explanation": EntityKindSchema(
        semantic_key="explanation",
        parent_kind_refs=("information_object",),
        identity_criteria=("claim_ref", "evidence_path"),
    ),
    "answer_record": EntityKindSchema(
        semantic_key="answer_record",
        parent_kind_refs=("information_object",),
        identity_criteria=("question_ref", "answer_content_ref"),
    ),
    "condition": EntityKindSchema(
        semantic_key="condition",
        parent_kind_refs=("information_object",),
        identity_criteria=("holder_ref", "dimension_ref", "valid_time"),
    ),
    "example": EntityKindSchema(
        semantic_key="example",
        parent_kind_refs=("information_object",),
        identity_criteria=("target_schema_ref", "case_ref"),
    ),
    "non_example": EntityKindSchema(
        semantic_key="non_example",
        parent_kind_refs=("information_object",),
        identity_criteria=("target_schema_ref", "contrast_case_ref"),
    ),
    "information_object": EntityKindSchema(
        semantic_key="information_object",
        identity_criteria=("content_identity", "provenance"),
    ),
    "physical_entity": EntityKindSchema(
        semantic_key="physical_entity",
        identity_criteria=("spatiotemporal_identity",),
    ),
    "software_system": EntityKindSchema(
        semantic_key="software_system",
        parent_kind_refs=("information_object",),
        identity_criteria=("implementation_identity", "runtime_boundary"),
    ),
    "machine": EntityKindSchema(
        semantic_key="machine",
        parent_kind_refs=("physical_entity", "software_system"),
        identity_criteria=("designed_mechanism", "operational_function"),
    ),
    "mechanical": EntityKindSchema(
        semantic_key="mechanical",
        parent_kind_refs=("physical_entity",),
        identity_criteria=("mechanism_ref", "physical_operation"),
    ),
    "digital": EntityKindSchema(
        semantic_key="digital",
        parent_kind_refs=("information_object",),
        identity_criteria=("discrete_representation",),
    ),
    "name": EntityKindSchema(
        semantic_key="name",
        parent_kind_refs=("information_object",),
        identity_criteria=("bearer_ref", "surface_form", "naming_context"),
    ),
    "person": EntityKindSchema(
        semantic_key="person",
        identity_criteria=("stable_referent_identity",),
    ),
}


_OPERATIONS: dict[str, OperationSchema] = {
    "op:answer": OperationSchema(
        semantic_key="op:answer",
        operation_class="communicative",
        input_roles=("role:question", "role:content", "role:context"),
        output_roles=("role:message",),
        idempotency_policy="at_most_once",
    ),
}


# Surface -> canonical semantic identity.  Closed class keys are grammar keys,
# not domain concepts.
_LEXEMES: tuple[tuple[str, str, str], ...] = (
    ("know", "knows", "verb"), ("knows", "knows", "verb"),
    ("knew", "knows", "verb"), ("known", "knows", "verb"),
    ("mean", "means", "verb"), ("means", "means", "verb"),
    ("meant", "means", "verb"),
    ("believe", "believes", "verb"), ("believes", "believes", "verb"),
    ("hi", "greet", "interjection"), ("hello", "greet", "interjection"),
    ("hey", "greet", "interjection"),
    ("want", "desires", "verb"), ("wants", "desires", "verb"),
    ("desire", "desires", "verb"), ("desires", "desires", "verb"),
    ("machine", "machine", "noun"),
    ("mechanical", "mechanical", "adjective"),
    ("digital", "digital", "adjective"),
    ("name", "name", "noun"),
    ("can", "capable_of", "verb"),
    ("condition", "condition", "noun"),
    ("recognize", "recognizes_form", "verb"),
    ("word", "lexical_form", "noun"),
    ("definition", "semantic_definition", "noun"),
    ("person", "person", "noun"), ("role", "role", "noun"),
    ("need", "requires_information", "verb"),
    ("distinction", "semantic_distinction", "noun"),
    ("explanation", "explanation", "noun"),
    ("link", "associates", "verb"), ("links", "associates", "verb"),
    ("information", "information_object", "noun"),
    ("answer", "answer_record", "noun"),
    ("store", "stores", "verb"), ("stored", "stores", "verb"),
    ("complete", "completes", "verb"), ("completed", "completes", "verb"),
    ("correct", "corrects", "verb"),
    ("have", "has_usable_definition", "verb"),
    ("receive", "receives", "verb"), ("received", "receives", "verb"),
    ("incomplete", "is_incomplete", "adjective"),
    ("give", "requests", "verb"),
    ("example", "example", "noun"),
    ("non-example", "non_example", "noun"),
    ("both", "grammar:quantifier_both", "determiner"),
    ("enough", "grammar:quantifier_sufficiency", "determiner"),
)


_REALIZATIONS: dict[str, RealizationSpec] = {
    "greet": RealizationSpec("hello", "interjection", frozenset({"assert", "probe", "qualified"})),
    "desires": RealizationSpec("want", "verb", frozenset({"assert", "qualified", "probe"})),
    "machine": RealizationSpec("machine", "noun", frozenset({"assert", "qualified", "probe"})),
    "mechanical": RealizationSpec("mechanical", "adjective", frozenset({"assert", "qualified", "probe"})),
    "digital": RealizationSpec("digital", "adjective", frozenset({"assert", "qualified", "probe"})),
    "name": RealizationSpec("name", "noun", frozenset({"assert", "qualified", "probe"})),
    "capable_of": RealizationSpec("can", "verb", frozenset({"assert", "qualified"})),
    "condition": RealizationSpec("condition", "noun", frozenset({"assert", "qualified", "probe"})),
    "recognizes_form": RealizationSpec("recognize", "verb", frozenset({"assert", "qualified", "probe"})),
    "lexical_form": RealizationSpec("word", "noun", frozenset({"assert", "qualified", "probe"})),
    "semantic_definition": RealizationSpec("definition", "noun", frozenset({"assert", "qualified", "probe"})),
    "means": RealizationSpec("mean", "verb", frozenset({"assert", "qualified", "probe"})),
    "person": RealizationSpec("person", "noun", frozenset({"assert", "qualified", "probe"})),
    "role": RealizationSpec("role", "noun", frozenset({"assert", "qualified", "probe"})),
    "grammar:quantifier_both": RealizationSpec("both", "determiner", frozenset({"assert", "qualified", "probe"}), closed_class=True),
    "requires_information": RealizationSpec("need", "verb", frozenset({"assert", "qualified", "probe"})),
    "semantic_distinction": RealizationSpec("distinction", "noun", frozenset({"assert", "qualified", "probe"})),
    "explanation": RealizationSpec("explanation", "noun", frozenset({"assert", "qualified", "probe"})),
    "associates": RealizationSpec("links", "verb", frozenset({"qualified", "probe"})),
    "information_object": RealizationSpec("information", "noun", frozenset({"assert", "qualified", "probe"})),
    "grammar:quantifier_sufficiency": RealizationSpec("enough", "determiner", frozenset({"assert", "qualified", "probe"}), closed_class=True),
    "answer_record": RealizationSpec("answer", "noun", frozenset({"assert", "qualified", "probe"})),
    "stores": RealizationSpec("stored", "verb", frozenset({"assert"})),
    "completes": RealizationSpec("complete", "verb", frozenset({"assert"})),
    "corrects": RealizationSpec("correct", "verb", frozenset({"assert"})),
    "has_usable_definition": RealizationSpec("have", "verb", frozenset({"assert", "qualified", "probe"})),
    "receives": RealizationSpec("received", "verb", frozenset({"assert"})),
    "is_incomplete": RealizationSpec("incomplete", "adjective", frozenset({"assert", "qualified"})),
    "requests": RealizationSpec("give", "verb", frozenset({"probe", "qualified"})),
    "example": RealizationSpec("example", "noun", frozenset({"probe", "qualified"})),
    "non_example": RealizationSpec("non-example", "noun", frozenset({"probe", "qualified"})),
}


_CONSTRUCTIONS: tuple[ConstructionSchema, ...] = (
    ConstructionSchema(
        semantic_key="construction:en:copular_instance",
        language_tag="en",
        pattern="[subject] [copula] [category]",
        predicate_schema_ref="instance_of",
        role_mappings={"entity": "subject", "kind": "complement"},
        constraints=("subject_is_deictic_or_referential",),
    ),
    ConstructionSchema(
        semantic_key="construction:en:copular_definition",
        language_tag="en",
        pattern="[subject] [copula] [category]",
        predicate_schema_ref="subkind_of",
        role_mappings={"child_kind": "subject", "parent_kind": "complement"},
        constraints=("subject_is_not_wh_operator", "subject_is_not_deictic_pronoun"),
    ),
    ConstructionSchema(
        semantic_key="construction:en:condition_question",
        language_tag="en",
        pattern="[wh:how] [copula] [holder]",
        predicate_schema_ref="has_condition",
        role_mappings={"holder": "holder"},
        open_role_refs=("role:condition",),
        communicative_force="ask",
    ),
    ConstructionSchema(
        semantic_key="construction:en:definition_question",
        language_tag="en",
        pattern="[wh:what] [copula] [kind]",
        predicate_schema_ref="subkind_of",
        role_mappings={"child_kind": "kind"},
        open_role_refs=("role:parent_kind",),
        communicative_force="ask",
    ),
    ConstructionSchema(
        semantic_key="construction:en:meaning_question",
        language_tag="en",
        pattern="[wh:what] [aux:do] [lexical_form] [lemma:mean]",
        predicate_schema_ref="means",
        role_mappings={"lexical_form": "lexical_form"},
        open_role_refs=("role:schema_sense",),
        communicative_force="ask",
    ),
    ConstructionSchema(
        semantic_key="construction:en:wh_question",
        language_tag="en",
        pattern="[wh] [clause]",
        predicate_schema_ref="query_content",
        role_mappings={"requested_content": "wh"},
        open_role_refs=("role:requested_content",),
        communicative_force="ask",
    ),
    ConstructionSchema(
        semantic_key="construction:en:yes_no_question",
        language_tag="en",
        pattern="[aux] [subject] [predicate]",
        predicate_schema_ref="query_truth",
        role_mappings={"auxiliary": "auxiliary", "subject": "subject", "predicate": "predicate"},
        open_role_refs=("role:truth_status",),
        communicative_force="ask",
    ),
    ConstructionSchema(
        semantic_key="construction:en:desire_knowledge_question",
        language_tag="en",
        pattern="[aux:do] [holder] [lemma:want] [lemma:know] [content]",
        predicate_schema_ref="desires",
        role_mappings={"holder": "holder", "content": "content"},
        constraints=("content_lexicalized_as_information",),
        communicative_force="ask",
    ),
    ConstructionSchema(
        semantic_key="construction:en:complement_clause:know",
        language_tag="en",
        pattern="[predicate] [embedded_clause]",
        predicate_schema_ref="knows",
        role_mappings={"knower": "subject", "content": "content"},
        constraints=("predicate_lemma:know",),
    ),
    ConstructionSchema(
        semantic_key="construction:en:complement_clause:mean",
        language_tag="en",
        pattern="[predicate] [embedded_clause]",
        predicate_schema_ref="means",
        role_mappings={"content": "content"},
        constraints=("predicate_lemma:mean",),
    ),
    ConstructionSchema(
        semantic_key="construction:en:complement_clause:believe",
        language_tag="en",
        pattern="[predicate] [embedded_clause]",
        predicate_schema_ref="believes",
        role_mappings={"believer": "subject", "proposition": "content"},
        constraints=("predicate_lemma:believe", "predicate_lemma:think"),
    ),
)


def semantic_specs() -> tuple[dict[str, PredicateSchema], dict[str, EntityKindSchema]]:
    """Expose immutable copies for the independent structural validator."""
    return dict(_PREDICATES), dict(_ENTITY_KINDS)


def operation_specs() -> dict[str, OperationSchema]:
    return dict(_OPERATIONS)


def lexical_specs() -> tuple[tuple[str, str, str], ...]:
    return _LEXEMES


def realization_specs() -> dict[str, RealizationSpec]:
    return dict(_REALIZATIONS)


def construction_specs() -> tuple[ConstructionSchema, ...]:
    return _CONSTRUCTIONS


def _semantic_record_ref(store: SemanticSchemaStore, semantic_key: str) -> str:
    active = store.find_active(semantic_key)
    return active.record_id if active is not None else ""


def register_v341_foundations(store: SemanticSchemaStore) -> tuple[str, ...]:
    """Register and index the v3.4.1 communication closure idempotently."""
    registered: list[str] = []

    for role_key in sorted(_ROLE_KEYS):
        record_id = f"boot:v341:role:{role_key}"
        if store.get(record_id) is None:
            test_refs = (f"test:v341:role:{role_key}:typed",)
            store.register(_active_envelope(
                record_id=record_id,
                semantic_key=f"role:{role_key}",
                schema_kind="role",
                payload=_role(
                    role_key,
                    embedded_proposition=(role_key in {"content", "proposition", "question"}),
                    embedded_predication=(role_key in {"content", "proposition"}),
                ),
                test_refs=test_refs,
            ))
            registered.append(record_id)

    for key, schema in _ENTITY_KINDS.items():
        if store.find_active(key) is not None:
            continue
        record_id = f"boot:v341:entity_kind:{key}"
        test_refs = (f"test:v341:entity_kind:{key}:identity",)
        store.register(_active_envelope(
            record_id=record_id,
            semantic_key=key,
            schema_kind="entity_kind",
            payload=schema,
            test_refs=test_refs,
        ))
        registered.append(record_id)

    for key, schema in _PREDICATES.items():
        if store.find_active(key) is not None:
            continue
        record_id = f"boot:v341:predicate:{key}"
        test_refs = (
            f"test:v341:predicate:{key}:role_structure",
            f"test:v341:predicate:{key}:polarity",
            f"test:v341:predicate:{key}:query_behavior",
        )
        store.register(_active_envelope(
            record_id=record_id,
            semantic_key=key,
            schema_kind="predicate",
            payload=schema,
            test_refs=test_refs,
        ))
        registered.append(record_id)

    for key, schema in _OPERATIONS.items():
        if store.find_active(key) is not None:
            continue
        record_id = f"boot:v341:operation:{key.removeprefix('op:')}"
        test_refs = (f"test:v341:operation:{key}:live_capability_target",)
        store.register(_active_envelope(
            record_id=record_id,
            semantic_key=key,
            schema_kind="operation",
            payload=schema,
            test_refs=test_refs,
        ))
        registered.append(record_id)

    for index, (surface, semantic_key, pos) in enumerate(_LEXEMES):
        record_id = f"boot:v341:lexeme:en:{index}"
        if store.get(record_id) is None:
            semantic_ref = "" if semantic_key.startswith("grammar:") else _semantic_record_ref(store, semantic_key)
            store.register(_active_envelope(
                record_id=record_id,
                semantic_key=f"lexeme:en:{semantic_key}:{index}",
                schema_kind="lexeme_sense",
                payload=LexemeSenseSchema(
                    semantic_key=semantic_key,
                    lexical_form_refs=(LexicalFormRef(
                        surface=surface,
                        language_tag="en",
                        normalised=surface.casefold(),
                    ),),
                    semantic_schema_ref=semantic_ref,
                    predicate_schema_ref=(
                        semantic_ref
                        if semantic_ref and getattr(store.get(semantic_ref), "schema_kind", "") == "predicate"
                        else ""
                    ),
                    part_of_speech=pos,
                ),
                test_refs=(f"test:v341:lexeme:en:{index}:lookup",),
            ))
            store.index_lexical_form(surface.casefold(), "en", semantic_key)
            registered.append(record_id)

    for semantic_key, spec in _REALIZATIONS.items():
        record_id = f"boot:v341:realization:en:{semantic_key}"
        realization_key = f"realize:en:{semantic_key}"
        if store.get(record_id) is None:
            semantic_ref = "" if spec.closed_class else _semantic_record_ref(store, semantic_key)
            test_refs = (
                f"test:v341:realization:en:{semantic_key}:lexical_lookup",
                f"test:v341:realization:en:{semantic_key}:round_trip",
            )
            store.register(_active_envelope(
                record_id=record_id,
                semantic_key=realization_key,
                schema_kind="realization",
                payload=RealizationSchema(
                    semantic_key=semantic_key,
                    language_tag="en",
                    lemma=spec.surface,
                    part_of_speech=spec.part_of_speech,
                    forms=FrozenMap({spec.form_key: spec.surface}),
                    semantic_schema_ref=semantic_ref,
                    allowed_use_modes=spec.modes,
                    closed_class=spec.closed_class,
                    competence_test_refs=test_refs,
                ),
                test_refs=test_refs,
            ))
            registered.append(record_id)

    for index, schema in enumerate(_CONSTRUCTIONS):
        record_id = f"boot:v341:construction:en:{index}"
        if store.get(record_id) is None:
            predicate_ref = _semantic_record_ref(store, schema.predicate_schema_ref)
            payload = ConstructionSchema(
                semantic_key=schema.semantic_key,
                language_tag=schema.language_tag,
                pattern=schema.pattern,
                predicate_schema_ref=predicate_ref or schema.predicate_schema_ref,
                role_mappings=schema.role_mappings,
                open_role_refs=schema.open_role_refs,
                communicative_force=schema.communicative_force,
                constraints=schema.constraints,
            )
            store.register(_active_envelope(
                record_id=record_id,
                semantic_key=schema.semantic_key,
                schema_kind="construction",
                payload=payload,
                test_refs=(f"test:v341:construction:en:{index}:match",),
            ))
            registered.append(record_id)

    return tuple(registered)
