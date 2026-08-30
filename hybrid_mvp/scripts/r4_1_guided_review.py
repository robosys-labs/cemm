#!/usr/bin/env python3
"""Neutral presentation projections for accountable R4.1 review."""
from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import TYPE_CHECKING, Mapping

if TYPE_CHECKING:
    from scripts.r4_1_review_session import ReviewSession

PHASE_ORDER = (
    "identity",
    "structural",
    "purpose",
    "recipe",
    "designation",
    "export",
)


@dataclass(frozen=True, slots=True)
class ChoiceGuidance:
    label: str
    explanation: str
    consequence: str
    blocks_authoring: bool


@dataclass(frozen=True, slots=True)
class RowGuidance:
    instruction: str
    question: str
    choices: Mapping[str, ChoiceGuidance]


def _choice(
    label: str,
    explanation: str,
    consequence: str,
    *,
    blocks: bool = False,
) -> ChoiceGuidance:
    return ChoiceGuidance(label, explanation, consequence, blocks)


def _row(
    instruction: str,
    question: str,
    **choices: ChoiceGuidance,
) -> RowGuidance:
    return RowGuidance(instruction, question, MappingProxyType(choices))


def _purpose_choice(label: str, owner: str) -> ChoiceGuidance:
    return _choice(
        label,
        f"Give the exact displayed case or group to {owner}.",
        f"The displayed members become isolated members of {owner}.",
    )


GUIDANCE: Mapping[str, RowGuidance] = MappingProxyType(
    {
        "composed_expression_proposal": _row(
            "Compare the source sentence with the complete proposed semantic graph.",
            "Does this exact graph preserve every proposition, role, scope and link in the source?",
            approve_exact_proposal=_choice(
                "Use this exact proposal",
                "Record that the displayed graph exactly represents the source.",
                "This proposal remains eligible for supervised authoring.",
            ),
            reject_exact_proposal=_choice(
                "Reject and repair this proposal",
                "Record that the graph is not an exact representation of the source.",
                "Dependent authoring stays blocked until the earliest owner is repaired.",
                blocks=True,
            ),
        ),
        "conflict_preservation": _row(
            "Inspect the two source-supported alternatives without settling either one.",
            "Should both displayed alternatives remain available for later exact settling?",
            preserve_as_alternatives=_choice(
                "Preserve both alternatives",
                "Keep both conflicting source-supported alternatives without settling either one.",
                "Later exact constraints must settle the alternatives.",
            ),
        ),
        "legacy_conditional": _row(
            "Choose how the bounded legacy conditional family is represented.",
            "Should its unresolved cases remain typed gaps or be retired with reserved indices?",
            retain_typed_proposal_gaps=_choice(
                "Retain typed gaps",
                "Preserve unresolved proposals as typed gaps with their reserved identities.",
                "The gap cases remain diagnostic and cannot become semantic supervision.",
            ),
            retire_with_reserved_indices=_choice(
                "Retire and reserve indices",
                "Remove the legacy cases while preserving their reserved indices.",
                "The retired cases cannot participate in R4.1 supervision.",
            ),
        ),
        "generator_patch": _row(
            "Bind generation to the same reviewed legacy-conditional branch.",
            "Which exact generator variant must reproduce the structural decision?",
            retain_typed_proposal_gaps=_choice(
                "Retain typed gaps",
                "Generate the reviewed branch that preserves unresolved proposals as typed gaps.",
                "Generation must reproduce the matching typed-gap branch exactly.",
            ),
            retire_with_reserved_indices=_choice(
                "Retire and reserve indices",
                "Generate the reviewed branch that retires the cases and reserves their indices.",
                "Generation must reproduce the matching retirement branch exactly.",
            ),
        ),
        "restart_diagnostic": _row(
            "Inspect the restart case as diagnostic evidence rather than semantic gold.",
            "Should this exact case remain diagnostic, or be rejected pending replacement?",
            approve_diagnostic_only=_choice(
                "Keep as diagnostic only",
                "Exclude the case from semantic supervision and retain it only for diagnostics.",
                "The case may expose regressions but cannot train or score meaning.",
            ),
            reject_pending_replacement=_choice(
                "Reject pending replacement",
                "Block use of the case until its source owner supplies a replacement.",
                "Dependent authoring stays blocked pending source repair.",
                blocks=True,
            ),
        ),
        "membership": _row(
            "Assign this exact source case to one reviewed purpose or disposition.",
            "Which purpose or disposition owns this case without causing leakage?",
            direct_train=_purpose_choice("Assign to training", "training"),
            direct_selection=_purpose_choice(
                "Assign to model selection", "model selection"
            ),
            direct_calibration=_purpose_choice(
                "Assign to calibration", "calibration"
            ),
            direct_frozen_test=_purpose_choice(
                "Assign to frozen test", "the isolated frozen final test"
            ),
            assign_to_reviewed_group=_choice(
                "Use the reviewed group decision",
                "Inherit the purpose chosen for the displayed duplicate-risk group.",
                "The case cannot diverge from its reviewed group purpose.",
            ),
            approve_diagnostic_only=_choice(
                "Keep as diagnostic only",
                "Exclude the case from semantic supervision and retain it only for diagnostics.",
                "The case may expose regressions but cannot train or score meaning.",
            ),
            reject_pending_replacement=_choice(
                "Reject pending replacement",
                "Block use of the case until its source owner supplies a replacement.",
                "Dependent authoring stays blocked pending source repair.",
                blocks=True,
            ),
        ),
        "duplicate_group": _row(
            "Keep duplicate-risk members together in one purpose partition.",
            "Which one purpose owns every displayed group member, or must the group be repaired?",
            approve_train=_purpose_choice("Assign group to training", "training"),
            approve_selection=_purpose_choice(
                "Assign group to model selection", "model selection"
            ),
            approve_calibration=_purpose_choice(
                "Assign group to calibration", "calibration"
            ),
            approve_frozen_test=_purpose_choice(
                "Assign group to frozen test", "the isolated frozen final test"
            ),
            reject_group=_choice(
                "Reject this group",
                "Block every displayed member pending repair of group ownership.",
                "Dependent purpose assignment and authoring stay blocked.",
                blocks=True,
            ),
        ),
        "challenge_holdout": _row(
            "Decide whether this topology is reserved as a cross-purpose challenge holdout.",
            "Should the displayed topology be reserved for one purpose or remain ordinarily assignable?",
            not_a_holdout=_choice(
                "Do not reserve as a holdout",
                "Leave this topology eligible for ordinary purpose assignment.",
                "Member cases still require their normal purpose decisions.",
            ),
            holdout_train=_purpose_choice("Reserve for training", "training"),
            holdout_selection=_purpose_choice(
                "Reserve for model selection", "model selection"
            ),
            holdout_calibration=_purpose_choice(
                "Reserve for calibration", "calibration"
            ),
            holdout_frozen_test=_purpose_choice(
                "Reserve for frozen test", "the isolated frozen final test"
            ),
        ),
        "denominator": _row(
            "Verify the minimum representation required for this family.",
            "Should every purpose contain at least one reviewed member of this family?",
            minimum_one_each=_choice(
                "Require at least one per purpose",
                "Enforce the displayed denominator minimum for all four purposes.",
                "Purpose validation fails if any partition lacks the required member.",
            ),
        ),
        "proposal_recipe_family": _row(
            "Inspect this normalized proposal family separately for the displayed purpose.",
            "Does this exact purpose-local recipe preserve the reviewed family parameters?",
            approve=_choice(
                "Approve this purpose-local recipe",
                "Accept the exact displayed family parameters for this purpose only.",
                "The family becomes eligible for purpose-local proposal expansion.",
            ),
            reject=_choice(
                "Reject and repair this recipe",
                "Record that this family recipe is not acceptable for the displayed purpose.",
                "This family and purpose remain blocked until repaired.",
                blocks=True,
            ),
        ),
        "designation_nonempty": _row(
            "Compare every displayed surface span with its exact authority-backed target.",
            "Does this exact candidate set contain every and only the valid designation bindings?",
            approve_candidate_bindings=_choice(
                "Accept this exact candidate set",
                "Record every and only the displayed designation binding.",
                "The exact set becomes eligible for designation supervision.",
            ),
            reject=_choice(
                "Reject and repair these bindings",
                "Record that the candidate set or source geometry requires repair.",
                "The case remains blocked until the earliest owner is repaired.",
                blocks=True,
            ),
        ),
        "designation_empty": _row(
            "Verify that this reviewed nonsemantic source has no designation binding.",
            "Is the exact empty designation set correct for this source?",
            approve_exact_empty=_choice(
                "Record this exact empty set",
                "Record that the reviewed nonsemantic case has no designation binding.",
                "The exact empty set becomes eligible as reviewed supervision evidence.",
            ),
            reject=_choice(
                "Reject and repair this empty set",
                "Record that authority or source geometry requires repair.",
                "The case remains blocked until the earliest owner is repaired.",
                blocks=True,
            ),
        ),
    }
)


def active_choice_labels(session: ReviewSession) -> dict[str, set[str]]:
    """Return the exact selectable vocabulary in one authenticated session."""
    result: dict[str, set[str]] = {}
    for rows in (
        session.indexes.structural_rows_by_ref.values(),
        session.indexes.purpose_rows_by_ref.values(),
    ):
        for row in rows:
            labels = result.setdefault(row["row_kind"], set())
            labels.update(
                option["label"]
                for option in row["options"]
                if option["selectable"] is True
            )
    result["proposal_recipe_family"] = {"approve", "reject"}
    result["designation_nonempty"] = {
        "approve_candidate_bindings",
        "reject",
    }
    result["designation_empty"] = {"approve_exact_empty", "reject"}
    return result
