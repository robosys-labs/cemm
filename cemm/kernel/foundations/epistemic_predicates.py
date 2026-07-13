"""Epistemic and learning foundation predicates.

Import boundary: model + schema submodules only. No engine imports.

Epistemic/learning predicates (SEMANTIC_FOUNDATIONS.md §4):
    remembers(self, record)
    has_access_to(self, record)
    has_evidence_for(self, proposition, evidence)
    understands(self, schema_revision, competence_set, context)
    uncertain_about(self, target, blocker_set)
    means(lexical_form, schema_sense)
    defines(source, schema_revision, proposition)
    learns(self, artifact, evidence)

`learns` is derived from committed artifact change and validated use.
It is not triggered by a teaching utterance alone.

These are ordinary predicates over ordinary records — self is a stable
Referent, not a special atom kind (AGENTS.md §11).
"""
from __future__ import annotations

from ..schema.role import RoleSchema
from ..schema.predicate import (
    PredicateSchema,
    AspectProfile,
    ContextBehavior,
    PolarityBehavior,
    ModalityBehavior,
    IdentityPolicy,
    CardinalityPolicy,
    EvidencePolicy,
    PersistencePolicy,
)


def _role(key: str, required: bool = True, cardinality: str = "one",
           accepted_families: frozenset[str] | None = None) -> RoleSchema:
    return RoleSchema(
        role_key=key,
        required=required,
        cardinality=cardinality,
        accepted_object_families=accepted_families or frozenset({"referent", "value", "proposition", "predication"}),
    )


def remembers_predicate() -> PredicateSchema:
    """remembers(self, record) — self successfully retrieved a stored trace."""
    return PredicateSchema(
        semantic_key="remembers",
        predication_kind="relation",
        role_refs=("role:self", "role:record"),
        polarity_behavior=PolarityBehavior(
            supports_negation=True,
            negation_kind="contradictory",
        ),
        modality_behavior=ModalityBehavior(supports_modality=True),
        identity_policy=IdentityPolicy(
            includes_valid_time=True,
            includes_modal_qualifiers=True,
        ),
        cardinality_policy=CardinalityPolicy(
            cardinality="many",
            reinforcement_policy="reinforce",
        ),
        evidence_policy=EvidencePolicy(minimum_evidence_count=1),
        persistence_policy=PersistencePolicy(retention="session"),
    )


def has_access_to_predicate() -> PredicateSchema:
    """has_access_to(self, record) — self can access a record."""
    return PredicateSchema(
        semantic_key="has_access_to",
        predication_kind="state",
        role_refs=("role:self", "role:record"),
        polarity_behavior=PolarityBehavior(
            supports_negation=True,
            negation_kind="contradictory",
        ),
        modality_behavior=ModalityBehavior(supports_modality=True),
        identity_policy=IdentityPolicy(
            includes_valid_time=True,
            includes_modal_qualifiers=True,
        ),
        cardinality_policy=CardinalityPolicy(
            cardinality="many",
            reinforcement_policy="reinforce",
        ),
        evidence_policy=EvidencePolicy(minimum_evidence_count=1),
        persistence_policy=PersistencePolicy(retention="session"),
    )


def has_evidence_for_predicate() -> PredicateSchema:
    """has_evidence_for(self, proposition, evidence) — self has evidence for a proposition."""
    return PredicateSchema(
        semantic_key="has_evidence_for",
        predication_kind="relation",
        role_refs=("role:self", "role:proposition", "role:evidence"),
        polarity_behavior=PolarityBehavior(
            supports_negation=True,
            negation_kind="contradictory",
        ),
        modality_behavior=ModalityBehavior(supports_modality=True),
        identity_policy=IdentityPolicy(
            includes_valid_time=True,
            includes_modal_qualifiers=True,
        ),
        cardinality_policy=CardinalityPolicy(
            cardinality="many",
            reinforcement_policy="reinforce",
        ),
        evidence_policy=EvidencePolicy(minimum_evidence_count=1),
        persistence_policy=PersistencePolicy(retention="long_term"),
    )


def understands_predicate() -> PredicateSchema:
    """understands(self, schema_revision, competence_set, context) — self can operate over a schema."""
    return PredicateSchema(
        semantic_key="understands",
        predication_kind="state",
        role_refs=("role:self", "role:schema_revision", "role:competence_set", "role:context"),
        polarity_behavior=PolarityBehavior(
            supports_negation=True,
            negation_kind="contradictory",
        ),
        modality_behavior=ModalityBehavior(supports_modality=True),
        identity_policy=IdentityPolicy(
            includes_valid_time=True,
            includes_modal_qualifiers=True,
        ),
        cardinality_policy=CardinalityPolicy(
            cardinality="many",
            reinforcement_policy="reinforce",
        ),
        evidence_policy=EvidencePolicy(minimum_evidence_count=1),
        persistence_policy=PersistencePolicy(retention="session"),
    )


def uncertain_about_predicate() -> PredicateSchema:
    """uncertain_about(self, target, blocker_set) — self has uncertainty about a target."""
    return PredicateSchema(
        semantic_key="uncertain_about",
        predication_kind="state",
        role_refs=("role:self", "role:target", "role:blocker_set"),
        polarity_behavior=PolarityBehavior(
            supports_negation=True,
            negation_kind="contradictory",
        ),
        modality_behavior=ModalityBehavior(supports_modality=True),
        identity_policy=IdentityPolicy(
            includes_valid_time=True,
            includes_modal_qualifiers=True,
        ),
        cardinality_policy=CardinalityPolicy(
            cardinality="many",
            reinforcement_policy="reinforce",
        ),
        evidence_policy=EvidencePolicy(minimum_evidence_count=1),
        persistence_policy=PersistencePolicy(retention="session"),
    )


def means_predicate() -> PredicateSchema:
    """means(lexical_form, schema_sense) — a lexical form means a schema sense."""
    return PredicateSchema(
        semantic_key="means",
        predication_kind="relation",
        role_refs=("role:lexical_form", "role:schema_sense"),
        polarity_behavior=PolarityBehavior(
            supports_negation=True,
            negation_kind="contradictory",
        ),
        modality_behavior=ModalityBehavior(supports_modality=True),
        identity_policy=IdentityPolicy(
            includes_valid_time=True,
            includes_modal_qualifiers=True,
        ),
        cardinality_policy=CardinalityPolicy(
            cardinality="many",
            reinforcement_policy="reinforce",
        ),
        evidence_policy=EvidencePolicy(minimum_evidence_count=1),
        persistence_policy=PersistencePolicy(retention="long_term"),
    )


def defines_predicate() -> PredicateSchema:
    """defines(source, schema_revision, proposition) — a source defines a proposition via a schema."""
    return PredicateSchema(
        semantic_key="defines",
        predication_kind="relation",
        role_refs=("role:source", "role:schema_revision", "role:proposition"),
        polarity_behavior=PolarityBehavior(
            supports_negation=True,
            negation_kind="contradictory",
        ),
        modality_behavior=ModalityBehavior(supports_modality=True),
        identity_policy=IdentityPolicy(
            includes_valid_time=True,
            includes_modal_qualifiers=True,
        ),
        cardinality_policy=CardinalityPolicy(
            cardinality="many",
            reinforcement_policy="reinforce",
        ),
        evidence_policy=EvidencePolicy(minimum_evidence_count=1),
        persistence_policy=PersistencePolicy(retention="long_term"),
    )


def learns_predicate() -> PredicateSchema:
    """learns(self, artifact, evidence) — self learned an artifact from evidence.

    `learns` is derived from committed artifact change and validated use.
    It is not triggered by a teaching utterance alone.
    """
    return PredicateSchema(
        semantic_key="learns",
        predication_kind="event",
        agentive=False,
        role_refs=("role:self", "role:artifact", "role:evidence"),
        aspect_profile=AspectProfile(tense="unspecified", aspect="perfective", is_stative=False),
        polarity_behavior=PolarityBehavior(
            supports_negation=True,
            negation_kind="contradictory",
        ),
        modality_behavior=ModalityBehavior(supports_modality=True),
        identity_policy=IdentityPolicy(
            includes_valid_time=True,
            includes_modal_qualifiers=True,
        ),
        cardinality_policy=CardinalityPolicy(
            cardinality="many",
            reinforcement_policy="reinforce",
        ),
        evidence_policy=EvidencePolicy(
            minimum_evidence_count=2,
            requires_independent_sources=True,
            allows_self_attribution=False,
        ),
        persistence_policy=PersistencePolicy(retention="long_term"),
    )


# ── Registry ───────────────────────────────────────────────────────


def epistemic_predicates() -> dict[str, PredicateSchema]:
    """Get all epistemic/learning foundation predicate schemas."""
    return {
        "remembers": remembers_predicate(),
        "has_access_to": has_access_to_predicate(),
        "has_evidence_for": has_evidence_for_predicate(),
        "understands": understands_predicate(),
        "uncertain_about": uncertain_about_predicate(),
        "means": means_predicate(),
        "defines": defines_predicate(),
        "learns": learns_predicate(),
    }


def epistemic_roles() -> dict[str, RoleSchema]:
    """Get all epistemic/learning role schemas."""
    roles: dict[str, RoleSchema] = {}
    for key in [
        "self", "record", "proposition", "evidence",
        "schema_revision", "competence_set", "context",
        "target", "blocker_set",
        "lexical_form", "schema_sense",
        "source", "artifact",
    ]:
        roles[f"role:{key}"] = _role(key)
    return roles
