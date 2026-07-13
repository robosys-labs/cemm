"""Executable foundational predicates — type signatures, truth/query, inference.

Import boundary: model + schema submodules only. No engine imports.

Foundational predicates (SEMANTIC_FOUNDATIONS.md §3):
    same_identity / different_identity
    instance_of
    occupies_role
    participates_in
    has_state
    occurs / transitions
    located_at
    before / after
    depends_on
    causes / enables / prevents
    refers_to / represents

These labels are not assumed to explain themselves. Their kernel
semantics and property tests make them foundational.

Each predicate defines:
- type signature (role schemas)
- truth/query behavior
- inference contracts
- contradiction semantics
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol

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


# ── Role schemas for foundational predicates ───────────────────────


def _role(key: str, required: bool = True, cardinality: str = "one",
           accepted_families: frozenset[str] | None = None) -> RoleSchema:
    return RoleSchema(
        role_key=key,
        required=required,
        cardinality=cardinality,
        accepted_object_families=accepted_families or frozenset({"referent", "value"}),
    )


# ── Foundational predicate definitions ─────────────────────────────


def same_identity_predicate() -> PredicateSchema:
    """same_identity(a, b) — a and b refer to the same entity."""
    return PredicateSchema(
        semantic_key="same_identity",
        predication_kind="relation",
        role_refs=("role:a", "role:b"),
        context_behavior=ContextBehavior(
            supports_reported=True,
            supports_hypothetical=True,
            supports_quoted=True,
        ),
        polarity_behavior=PolarityBehavior(
            supports_negation=True,
            negation_kind="contradictory",
        ),
        modality_behavior=ModalityBehavior(supports_modality=False),
        identity_policy=IdentityPolicy(
            includes_valid_time=True,
            includes_modal_qualifiers=False,
            includes_attribution=False,
        ),
        cardinality_policy=CardinalityPolicy(
            cardinality="many",
            reinforcement_policy="reinforce",
        ),
        evidence_policy=EvidencePolicy(
            minimum_evidence_count=1,
            requires_independent_sources=False,
            allows_self_attribution=True,
        ),
        persistence_policy=PersistencePolicy(retention="long_term"),
    )


def different_identity_predicate() -> PredicateSchema:
    """different_identity(a, b) — a and b refer to distinct entities."""
    return PredicateSchema(
        semantic_key="different_identity",
        predication_kind="relation",
        role_refs=("role:a", "role:b"),
        polarity_behavior=PolarityBehavior(
            supports_negation=True,
            negation_kind="contradictory",
        ),
        modality_behavior=ModalityBehavior(supports_modality=False),
        identity_policy=IdentityPolicy(
            includes_valid_time=True,
            includes_modal_qualifiers=False,
        ),
        cardinality_policy=CardinalityPolicy(
            cardinality="many",
            reinforcement_policy="reinforce",
        ),
        evidence_policy=EvidencePolicy(minimum_evidence_count=1),
        persistence_policy=PersistencePolicy(retention="long_term"),
    )


def instance_of_predicate() -> PredicateSchema:
    """instance_of(entity, kind) — entity is an instance of kind."""
    return PredicateSchema(
        semantic_key="instance_of",
        predication_kind="relation",
        role_refs=("role:entity", "role:kind"),
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


def occupies_role_predicate() -> PredicateSchema:
    """occupies_role(entity, role, event/process) — entity fills a role in an event."""
    return PredicateSchema(
        semantic_key="occupies_role",
        predication_kind="relation",
        role_refs=("role:entity", "role:role", "role:process"),
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


def participates_in_predicate() -> PredicateSchema:
    """participates_in(entity, event/process) — entity participates in an event."""
    return PredicateSchema(
        semantic_key="participates_in",
        predication_kind="relation",
        role_refs=("role:entity", "role:event"),
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


def has_state_predicate() -> PredicateSchema:
    """has_state(entity, state_dimension, value) — entity has a state value."""
    return PredicateSchema(
        semantic_key="has_state",
        predication_kind="state",
        role_refs=("role:entity", "role:dimension", "role:value"),
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
            cardinality="exclusive",
            reinforcement_policy="supersede",
        ),
        evidence_policy=EvidencePolicy(minimum_evidence_count=1),
        persistence_policy=PersistencePolicy(retention="long_term"),
    )


def occurs_predicate() -> PredicateSchema:
    """occurs(event) — an event occurs."""
    return PredicateSchema(
        semantic_key="occurs",
        predication_kind="event",
        agentive=False,
        role_refs=("role:event",),
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


def transitions_predicate() -> PredicateSchema:
    """transitions(entity, from_state, to_state) — entity transitions between states."""
    return PredicateSchema(
        semantic_key="transitions",
        predication_kind="event",
        agentive=False,
        role_refs=("role:entity", "role:from_state", "role:to_state"),
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
        evidence_policy=EvidencePolicy(minimum_evidence_count=1),
        persistence_policy=PersistencePolicy(retention="long_term"),
    )


def located_at_predicate() -> PredicateSchema:
    """located_at(entity, location) — entity is at a location."""
    return PredicateSchema(
        semantic_key="located_at",
        predication_kind="state",
        role_refs=("role:entity", "role:location"),
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
            cardinality="exclusive",
            reinforcement_policy="supersede",
        ),
        evidence_policy=EvidencePolicy(minimum_evidence_count=1),
        persistence_policy=PersistencePolicy(retention="long_term"),
    )


def before_predicate() -> PredicateSchema:
    """before(a, b) — event/time a is before event/time b."""
    return PredicateSchema(
        semantic_key="before",
        predication_kind="relation",
        role_refs=("role:a", "role:b"),
        polarity_behavior=PolarityBehavior(
            supports_negation=True,
            negation_kind="contradictory",
        ),
        modality_behavior=ModalityBehavior(supports_modality=False),
        identity_policy=IdentityPolicy(
            includes_valid_time=True,
            includes_modal_qualifiers=False,
        ),
        cardinality_policy=CardinalityPolicy(
            cardinality="many",
            reinforcement_policy="reinforce",
        ),
        evidence_policy=EvidencePolicy(minimum_evidence_count=1),
        persistence_policy=PersistencePolicy(retention="long_term"),
    )


def after_predicate() -> PredicateSchema:
    """after(a, b) — event/time a is after event/time b."""
    return PredicateSchema(
        semantic_key="after",
        predication_kind="relation",
        role_refs=("role:a", "role:b"),
        polarity_behavior=PolarityBehavior(
            supports_negation=True,
            negation_kind="contradictory",
        ),
        modality_behavior=ModalityBehavior(supports_modality=False),
        identity_policy=IdentityPolicy(
            includes_valid_time=True,
            includes_modal_qualifiers=False,
        ),
        cardinality_policy=CardinalityPolicy(
            cardinality="many",
            reinforcement_policy="reinforce",
        ),
        evidence_policy=EvidencePolicy(minimum_evidence_count=1),
        persistence_policy=PersistencePolicy(retention="long_term"),
    )


def depends_on_predicate() -> PredicateSchema:
    """depends_on(a, b) — a depends on b."""
    return PredicateSchema(
        semantic_key="depends_on",
        predication_kind="relation",
        role_refs=("role:dependent", "role:dependency"),
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


def causes_predicate() -> PredicateSchema:
    """causes(cause, effect) — cause causes effect."""
    return PredicateSchema(
        semantic_key="causes",
        predication_kind="relation",
        agentive=False,
        role_refs=("role:cause", "role:effect"),
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
            minimum_evidence_count=1,
            requires_independent_sources=False,
        ),
        persistence_policy=PersistencePolicy(retention="long_term"),
    )


def enables_predicate() -> PredicateSchema:
    """enables(enabler, enabled) — enabler enables enabled."""
    return PredicateSchema(
        semantic_key="enables",
        predication_kind="relation",
        role_refs=("role:enabler", "role:enabled"),
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


def prevents_predicate() -> PredicateSchema:
    """prevents(preventer, prevented) — preventer prevents prevented."""
    return PredicateSchema(
        semantic_key="prevents",
        predication_kind="relation",
        role_refs=("role:preventer", "role:prevented"),
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


def refers_to_predicate() -> PredicateSchema:
    """refers_to(expression, referent) — expression refers to referent."""
    return PredicateSchema(
        semantic_key="refers_to",
        predication_kind="relation",
        role_refs=("role:expression", "role:referent"),
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


def represents_predicate() -> PredicateSchema:
    """represents(representation, target) — representation represents target."""
    return PredicateSchema(
        semantic_key="represents",
        predication_kind="relation",
        role_refs=("role:representation", "role:target"),
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


# ── Registry ───────────────────────────────────────────────────────


def foundational_predicates() -> dict[str, PredicateSchema]:
    """Get all foundational predicate schemas."""
    return {
        "same_identity": same_identity_predicate(),
        "different_identity": different_identity_predicate(),
        "instance_of": instance_of_predicate(),
        "occupies_role": occupies_role_predicate(),
        "participates_in": participates_in_predicate(),
        "has_state": has_state_predicate(),
        "occurs": occurs_predicate(),
        "transitions": transitions_predicate(),
        "located_at": located_at_predicate(),
        "before": before_predicate(),
        "after": after_predicate(),
        "depends_on": depends_on_predicate(),
        "causes": causes_predicate(),
        "enables": enables_predicate(),
        "prevents": prevents_predicate(),
        "refers_to": refers_to_predicate(),
        "represents": represents_predicate(),
    }


def foundational_roles() -> dict[str, RoleSchema]:
    """Get all foundational role schemas."""
    roles: dict[str, RoleSchema] = {}
    for key in [
        "a", "b", "entity", "kind", "role", "process", "event",
        "dimension", "value", "from_state", "to_state", "location",
        "dependent", "dependency", "cause", "effect",
        "enabler", "enabled", "preventer", "prevented",
        "expression", "referent", "representation", "target",
    ]:
        roles[f"role:{key}"] = _role(key)
    return roles
