"""Reviewed source -> exact lowered learning-authority bridge for Phase 14.

This module does not activate authority and never interprets user wording. It converts a
reviewed language-package structural learning contract into exact ConstructionRecord metadata
only while building/reviewing a new authority revision. Runtime learning consumes only the
resulting exact, content-addressed ConstructionRecord metadata.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any, Mapping

from .model import ConstructionRecord
from ..schema.model import UseDecision, UseOperation


class Phase14LearningAuthorityError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class DefinitionLearningContractSeedV351:
    """Language-source contract; categories are reviewed construction data, not semantics."""

    form_category: str
    parent_category: str
    definition_relation: str = "subtype"
    requested_uses: tuple[UseOperation, ...] = (
        UseOperation.GROUND,
        UseOperation.COMPOSE,
        UseOperation.QUERY,
    )

    def __post_init__(self) -> None:
        if not self.form_category.strip() or not self.parent_category.strip():
            raise Phase14LearningAuthorityError("definition learning categories must be non-empty")
        if self.form_category == self.parent_category:
            raise Phase14LearningAuthorityError("definition form and parent categories must be distinct")
        if self.definition_relation != "subtype":
            raise Phase14LearningAuthorityError(
                "direct Phase-14 definition learning only reviews the structural subtype relation"
            )
        if not self.requested_uses or len(set(self.requested_uses)) != len(self.requested_uses):
            raise Phase14LearningAuthorityError("definition learning requested uses must be unique/non-empty")


def _unique_slot_for_category(construction: ConstructionRecord, category: str) -> str:
    matches = tuple(
        slot.slot_ref for slot in construction.slots if category in tuple(slot.accepted_categories)
    )
    if len(matches) != 1:
        raise Phase14LearningAuthorityError(
            f"reviewed learning category must lower to exactly one construction slot:{category}:{matches}"
        )
    return matches[0]


def compile_definition_learning_metadata_v351(
    construction: ConstructionRecord,
    contract: DefinitionLearningContractSeedV351,
    *,
    review_refs: tuple[str, ...] = (),
    authorization_refs: tuple[str, ...] = (),
    risk_refs: tuple[str, ...] = (),
    promotion_policy_ref: str = "policy:v351:reviewed-learning-promotion",
) -> Mapping[str, Any]:
    """Return exact metadata for a new reviewed construction revision.

    The release builder must persist/review/hash the returned record as a new authority
    revision. This function never mutates a live ConstructionRecord or store.
    """
    if not construction.competence_case_refs:
        raise Phase14LearningAuthorityError("definition learning construction requires competence cases")
    form_slot_ref = _unique_slot_for_category(construction, contract.form_category)
    parent_slot_ref = _unique_slot_for_category(construction, contract.parent_category)
    if form_slot_ref == parent_slot_ref:
        raise Phase14LearningAuthorityError("definition learning slots unexpectedly collapse")
    if not promotion_policy_ref.strip():
        raise Phase14LearningAuthorityError("definition learning promotion policy ref is required")

    metadata = dict(construction.metadata)
    open_slots = tuple(sorted(set((*tuple(metadata.get("open_observation_slots", ()) or ()), form_slot_ref))))
    requested = tuple(
        {
            "operation": operation.value,
            "decision": UseDecision.ALLOW.value,
            "reason": "reviewed definition-teaching construction learning axis",
        }
        for operation in contract.requested_uses
    )
    metadata.update({
        "open_observation_slots": open_slots,
        "semantic_definition_projection_v351": {
            "form_slot_ref": form_slot_ref,
            "parent_slot_ref": parent_slot_ref,
            "definition_relation": contract.definition_relation,
            "competence_case_refs": tuple(construction.competence_case_refs),
            "requested_uses": requested,
            "review_refs": tuple(sorted(set(review_refs))),
            "authorization_refs": tuple(sorted(set(authorization_refs))),
            "risk_refs": tuple(sorted(set(risk_refs))),
            "promotion_policy_ref": promotion_policy_ref,
        },
        "phase14_learning_authority_source": "reviewed-structural-contract-v1",
    })
    return metadata


def with_compiled_definition_learning_metadata_v351(
    construction: ConstructionRecord,
    contract: DefinitionLearningContractSeedV351,
    **kwargs,
) -> ConstructionRecord:
    """Build-time helper; caller must assign a new reviewed revision before publication."""
    return replace(
        construction,
        metadata=compile_definition_learning_metadata_v351(construction, contract, **kwargs),
    )


def validate_definition_learning_authority_v351(construction: ConstructionRecord) -> None:
    """Fail closed unless an exact lowered construction is usable by Phase-14 extraction."""
    metadata = dict(construction.metadata)
    raw = metadata.get("semantic_definition_projection_v351")
    if not isinstance(raw, Mapping):
        raise Phase14LearningAuthorityError("construction lacks semantic_definition_projection_v351")
    form_slot_ref = str(raw.get("form_slot_ref", ""))
    parent_slot_ref = str(raw.get("parent_slot_ref", ""))
    known = {slot.slot_ref for slot in construction.slots}
    if not form_slot_ref or not parent_slot_ref or form_slot_ref == parent_slot_ref:
        raise Phase14LearningAuthorityError("definition learning metadata has invalid slot refs")
    if form_slot_ref not in known or parent_slot_ref not in known:
        raise Phase14LearningAuthorityError("definition learning metadata references unknown exact slot")
    if form_slot_ref not in set(metadata.get("open_observation_slots", ()) or ()):
        raise Phase14LearningAuthorityError("definition form slot is not exact open-observation authority")
    if str(raw.get("definition_relation", "")) != "subtype":
        raise Phase14LearningAuthorityError("definition learning relation is not reviewed subtype")
    if not tuple(raw.get("competence_case_refs", ()) or ()):
        raise Phase14LearningAuthorityError("definition learning authority lacks competence cases")
    requested = tuple(raw.get("requested_uses", ()) or ())
    if not requested:
        raise Phase14LearningAuthorityError("definition learning authority lacks requested use axes")
    operations = []
    for item in requested:
        if not isinstance(item, Mapping):
            raise Phase14LearningAuthorityError("definition requested use must be a mapping")
        operation = UseOperation(str(item.get("operation", "")))
        decision = UseDecision(str(item.get("decision", "")))
        if decision is not UseDecision.ALLOW:
            raise Phase14LearningAuthorityError("reviewed definition source must explicitly request ALLOW axes")
        operations.append(operation)
    if len(operations) != len(set(operations)):
        raise Phase14LearningAuthorityError("definition requested use axes are duplicated")


__all__ = [
    "DefinitionLearningContractSeedV351",
    "Phase14LearningAuthorityError",
    "compile_definition_learning_metadata_v351",
    "validate_definition_learning_authority_v351",
    "with_compiled_definition_learning_metadata_v351",
]
