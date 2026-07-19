"""Stable structural compatibility between durable record families and use axes.

This is kernel mechanics, not domain ontology: it never inspects semantic keys,
concept names, words, values, or fixtures.
"""
from __future__ import annotations

from typing import Any

from ..schema.model import UseOperation
from ..storage.model import RecordKind


_COMPATIBLE: dict[RecordKind, frozenset[UseOperation]] = {
    RecordKind.SCHEMA: frozenset(UseOperation),
    RecordKind.FACET_ENTITLEMENT: frozenset({UseOperation.COMPOSE, UseOperation.QUERY, UseOperation.INFER}),
    # Contextual referents/type assertions/facets are factual graph state, not
    # learned semantic-definition authority. They use their existing commit/
    # epistemic admission paths rather than Phase-13 promotion.
    RecordKind.DEFAULT_RULE: frozenset({UseOperation.INFER}),
    # Language packs/forms/links are substrate records. Their activation is
    # needed by lexical/construction competence, but the actual semantic use
    # axis is carried by the sense/construction record that consumes them.
    RecordKind.LANGUAGE_PACK: frozenset({UseOperation.GROUND, UseOperation.COMPOSE, UseOperation.REALIZE}),
    RecordKind.LANGUAGE_FORM: frozenset({UseOperation.GROUND, UseOperation.REALIZE}),
    RecordKind.LEXICAL_SENSE: frozenset({UseOperation.GROUND, UseOperation.COMPOSE, UseOperation.REALIZE}),
    RecordKind.FORM_SENSE_LINK: frozenset({UseOperation.GROUND}),
    RecordKind.CONSTRUCTION: frozenset({UseOperation.GROUND, UseOperation.COMPOSE, UseOperation.REALIZE}),
    RecordKind.TRANSITION_CONTRACT: frozenset({UseOperation.TRANSITION}),
    RecordKind.CAPABILITY_DEPENDENCY: frozenset({UseOperation.TRANSITION}),
    RecordKind.IMPACT_RULE: frozenset({UseOperation.IMPACT}),
    RecordKind.IMPORTANCE_POLICY: frozenset({UseOperation.IMPACT}),
    RecordKind.RESPONSE_POLICY_RULE: frozenset({UseOperation.RESPONSE_POLICY}),
}


def record_kind_supports_use(record_kind: RecordKind, operation: UseOperation) -> bool:
    return operation in _COMPATIBLE.get(record_kind, frozenset())


def record_supports_use(record_kind: RecordKind, record: Any, operation: UseOperation) -> bool:
    """Refine family compatibility using only typed structural fields.

    Some canonical records already carry an explicit use axis (for example a
    lexical sense). A promotion grant must never silently reinterpret that
    structural declaration merely because the broader record family can serve
    several use axes.
    """
    if not record_kind_supports_use(record_kind, operation):
        return False
    declared = getattr(record, "use_operation", None)
    if declared is not None:
        return declared == operation
    return True
