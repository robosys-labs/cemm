#!/usr/bin/env python3
"""Neutral presentation projections for accountable R4.1 review."""
from __future__ import annotations

import copy
from dataclasses import dataclass
from types import MappingProxyType
from typing import Mapping

from cemm_authoritative_hybrid.canonical import stable_ref

from scripts.r4_1_review_session import ReviewAction, ReviewSession

PHASE_ORDER = (
    "identity",
    "structural",
    "purpose",
    "recipe",
    "designation",
    "export",
)
_PURPOSES = ("train", "selection", "calibration", "frozen_test")
MAX_GUIDED_EVIDENCE_BLOCKS = 12
MAX_GUIDED_TARGET_REFS = 512
MAX_GUIDED_EXAMPLES = 5


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


@dataclass(frozen=True, slots=True)
class _GuidedTarget:
    item_ref: str
    phase: str
    row_kind: str
    source_ref: str
    purpose: str | None = None
    cohort_ref: str | None = None


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


def _item_ref(
    *,
    phase: str,
    row_kind: str,
    source_ref: str,
    purpose: str | None = None,
) -> str:
    return stable_ref(
        "guided_review_item",
        {
            "phase": phase,
            "row_kind": row_kind,
            "source_ref": source_ref,
            "purpose": purpose,
        },
    )


def _target(
    *,
    phase: str,
    row_kind: str,
    source_ref: str,
    purpose: str | None = None,
    cohort_ref: str | None = None,
) -> _GuidedTarget:
    return _GuidedTarget(
        item_ref=_item_ref(
            phase=phase,
            row_kind=row_kind,
            source_ref=source_ref,
            purpose=purpose,
        ),
        phase=phase,
        row_kind=row_kind,
        source_ref=source_ref,
        purpose=purpose,
        cohort_ref=cohort_ref,
    )


def _wire(value: object) -> object:
    if isinstance(value, Mapping):
        return {key: _wire(item) for key, item in value.items()}
    if type(value) in {list, tuple}:
        return [_wire(item) for item in value]
    if type(value) is frozenset:
        return sorted(_wire(item) for item in value)
    return copy.deepcopy(value)


def _source_summary(row: Mapping[str, object]) -> str:
    surface = row.get("surface")
    if type(surface) is str and surface.strip():
        return surface
    scenario = row.get("resulting_scenario_row")
    if isinstance(scenario, Mapping):
        examples = scenario.get("surface_examples")
        if (
            type(examples) is list
            and examples
            and type(examples[0]) is str
            and examples[0].strip()
        ):
            return examples[0]
    candidate = row.get("candidate_output")
    if type(candidate) is str and candidate.strip():
        return candidate
    return (
        "This decision has no reviewed surface summary; "
        "inspect technical evidence."
    )


class GuidedReviewService:
    """Project one neutral guided decision over an authenticated session."""

    def __init__(self, session: ReviewSession) -> None:
        self.session = session
        targets: list[_GuidedTarget] = []
        for row_ref, row in sorted(
            session.indexes.structural_rows_by_ref.items(),
            key=lambda item: (item[1]["row_kind"], item[0]),
        ):
            targets.append(
                _target(
                    phase="structural",
                    row_kind=row["row_kind"],
                    source_ref=row_ref,
                )
            )
        for row_ref, row in sorted(
            session.indexes.purpose_rows_by_ref.items(),
            key=lambda item: (item[1]["row_kind"], item[0]),
        ):
            targets.append(
                _target(
                    phase="purpose",
                    row_kind=row["row_kind"],
                    source_ref=row_ref,
                )
            )
        for family_ref in sorted(session.indexes.proposal_families_by_ref):
            for purpose in _PURPOSES:
                targets.append(
                    _target(
                        phase="recipe",
                        row_kind="proposal_recipe_family",
                        source_ref=family_ref,
                        purpose=purpose,
                    )
                )
        exception_refs = session.indexes.designation_exception_case_refs
        for case_ref in sorted(exception_refs):
            targets.append(
                _target(
                    phase="designation",
                    row_kind="designation_case",
                    source_ref=case_ref,
                )
            )
        for cohort_ref in sorted(
            session.indexes.routine_designation_cohorts
        ):
            targets.append(
                _target(
                    phase="designation",
                    row_kind="designation_cohort",
                    source_ref=cohort_ref,
                    cohort_ref=cohort_ref,
                )
            )
        self._targets = tuple(targets)
        self._target_by_ref = MappingProxyType(
            {target.item_ref: target for target in targets}
        )
        self._export_ref = _item_ref(
            phase="export",
            row_kind="export",
            source_ref="reviewed-selection",
        )
        self._ordered_refs = tuple(target.item_ref for target in targets) + (
            self._export_ref,
        )
        self._projection_revision = -1
        self._state_by_ref: Mapping[str, object] = MappingProxyType({})
        self._projection_builds = 0
        self._choice_actions: dict[
            str, tuple[str, ReviewAction, ChoiceGuidance]
        ] = {}

    @property
    def projection_builds(self) -> int:
        return self._projection_builds

    @property
    def ordered_item_refs(self) -> tuple[str, ...]:
        return self._ordered_refs

    def _refresh_state_projection(self) -> None:
        if self._projection_revision == self.session.state_revision:
            return
        state = self.session.state
        structural = {
            row["row_ref"]: row["selected_option_ref"]
            for row in state["structural_selections"]
        }
        purpose = {
            row["row_ref"]: row["selected_option_ref"]
            for row in state["purpose_selections"]
        }
        recipes = {
            row["family_ref"]: {
                recipe["purpose"]: recipe
                for recipe in row["purpose_recipes"]
            }
            for row in state["proposal_recipe_selections"]
        }
        designations = {
            row["source_case_ref"]: row["decision"]
            for row in state["designation_selections"]
        }
        evaluation = self.session.evaluation()
        self._state_by_ref = MappingProxyType(
            {
                "reviewer_refs": tuple(state["reviewer_refs"]),
                "structural": structural,
                "purpose": purpose,
                "recipes": recipes,
                "designations": designations,
                "case_purposes": dict(evaluation.case_purposes),
                "active_supervised_case_refs": frozenset(
                    evaluation.active_supervised_case_refs
                ),
            }
        )
        self._choice_actions.clear()
        self._projection_revision = self.session.state_revision
        self._projection_builds += 1

    def _is_unresolved(self, target: _GuidedTarget) -> bool:
        if target.phase == "structural":
            return self._state_by_ref["structural"][target.source_ref] is None
        if target.phase == "purpose":
            return self._state_by_ref["purpose"][target.source_ref] is None
        if target.phase == "recipe":
            family = self.session.indexes.proposal_families_by_ref[
                target.source_ref
            ]
            case_purposes = self._state_by_ref["case_purposes"]
            applicable = any(
                case_purposes.get(case_ref) == target.purpose
                for case_ref in family["member_case_refs"]
            )
            return (
                applicable
                and target.purpose
                not in self._state_by_ref["recipes"][target.source_ref]
            )
        if target.phase == "designation":
            if target.row_kind == "designation_case":
                return (
                    target.source_ref
                    in self._state_by_ref["active_supervised_case_refs"]
                    and self._state_by_ref["designations"][target.source_ref]
                    is None
                )
            refs = self.session.indexes.routine_designation_cohorts[
                target.source_ref
            ]
            active = self._state_by_ref["active_supervised_case_refs"]
            decisions = [
                self._state_by_ref["designations"][case_ref]
                for case_ref in refs
            ]
            return set(refs) <= active and all(
                decision is None for decision in decisions
            )
        return False

    def _project_identity(self) -> Mapping[str, object]:
        return MappingProxyType(
            {
                "item_ref": _item_ref(
                    phase="identity",
                    row_kind="identity",
                    source_ref="accountable-reviewers",
                ),
                "phase": "identity",
                "primary_action": "save_reviewer_identity",
                "instruction": (
                    "Enter the canonical reviewer identity that will own "
                    "every confirmed decision."
                ),
                "reviewer_question": "Which canonical reviewer refs own this review?",
                "selected_choice_ref": None,
                "technical_evidence": {},
                "wrapped": False,
            }
        )

    def _project_target(
        self,
        target: _GuidedTarget,
        *,
        wrapped: bool,
    ) -> Mapping[str, object]:
        if target.phase == "structural":
            source = self.session.indexes.structural_rows_by_ref[
                target.source_ref
            ]
        elif target.phase == "purpose":
            source = self.session.indexes.purpose_rows_by_ref[
                target.source_ref
            ]
        elif target.phase == "recipe":
            source = self.session.indexes.proposal_families_by_ref[
                target.source_ref
            ]
        elif target.phase == "designation":
            if target.row_kind == "designation_case":
                source = self.session.indexes.designation_rows_by_case[
                    target.source_ref
                ]
            else:
                refs = self.session.indexes.routine_designation_cohorts[
                    target.source_ref
                ]
                source = self.session.indexes.designation_rows_by_case[
                    refs[0]
                ]
        else:
            raise ValueError("guided target phase is unavailable")
        guidance_key = target.row_kind
        if target.phase == "designation":
            guidance_key = (
                "designation_nonempty"
                if source["candidate_bindings"]
                else "designation_empty"
            )
        guidance = GUIDANCE[guidance_key]
        choices = self._project_choices(
            target=target,
            source=source,
            guidance=guidance,
        )
        return MappingProxyType(
            {
                "item_ref": target.item_ref,
                "phase": target.phase,
                "row_kind": target.row_kind,
                "instruction": guidance.instruction,
                "source_summary": _source_summary(source),
                "proposal_summary": (
                    (
                        f"{source['target_kind']} family for "
                        f"{target.purpose}; {len(source['member_case_refs'])} "
                        "total family members."
                        if target.phase == "recipe"
                        else (
                            f"{len(source['candidate_bindings'])} exact "
                            "designation binding candidates."
                            if target.phase == "designation"
                            else source.get("candidate_output")
                        )
                    )
                    or "Inspect the exact projected evidence below."
                ),
                "reviewer_question": guidance.question,
                "choices": choices,
                "cohort": self._cohort_projection(target),
                "selected_choice_ref": None,
                "technical_evidence": {
                    "source": _wire(source),
                    "purpose": target.purpose,
                },
                "wrapped": wrapped,
            }
        )

    def _cohort_projection(
        self,
        target: _GuidedTarget,
    ) -> Mapping[str, object] | None:
        if target.row_kind != "designation_cohort":
            return None
        refs = self.session.indexes.routine_designation_cohorts[
            target.source_ref
        ]
        return MappingProxyType(
            {
                "cohort_ref": target.source_ref,
                "member_count": len(refs),
                "target_refs": list(refs),
                "representative_examples": [
                    self.session.indexes.designation_rows_by_case[case_ref][
                        "surface"
                    ]
                    for case_ref in refs[:MAX_GUIDED_EXAMPLES]
                ],
            }
        )

    @staticmethod
    def _opaque_choice_ref(
        *,
        item_ref: str,
        option_key: str,
        target_refs: tuple[str, ...],
    ) -> str:
        return stable_ref(
            "guided_review_choice",
            {
                "item_ref": item_ref,
                "option_key": option_key,
                "target_refs": list(target_refs),
            },
        )

    def _project_choices(
        self,
        *,
        target: _GuidedTarget,
        source: Mapping[str, object],
        guidance: RowGuidance,
    ) -> list[dict[str, object]]:
        result: list[dict[str, object]] = []
        if target.phase in {"structural", "purpose"}:
            options = [
                (option["label"], option)
                for option in source["options"]
                if option["selectable"] is True
            ]
        elif target.phase == "recipe":
            options = [(key, None) for key in guidance.choices]
        elif target.phase == "designation":
            options = [(key, None) for key in guidance.choices]
        else:
            raise ValueError("guided choice phase is unavailable")
        for option_key, option in options:
            choice_guidance = guidance.choices[option_key]
            if target.phase == "structural":
                assert option is not None
                action = ReviewAction.structural(
                    row_ref=target.source_ref,
                    selected_option_ref=option["option_ref"],
                )
            elif target.phase == "purpose":
                action = ReviewAction.purpose(
                    row_refs=(target.source_ref,),
                    option_label=option_key,
                )
            elif target.phase == "recipe":
                assert target.purpose is not None
                action = ReviewAction.recipe(
                    family_ref=target.source_ref,
                    purpose=target.purpose,
                    decision=option_key,
                    reviewed_parameters={
                        "review_basis": "accountable_ui_exact_family"
                    },
                )
            elif target.phase == "designation":
                if target.row_kind == "designation_case":
                    action = ReviewAction.designation_cases(
                        case_refs=(target.source_ref,),
                        decision=option_key,
                        individual=True,
                    )
                else:
                    action = ReviewAction.designation_cohort(
                        cohort_ref=target.source_ref,
                        decision=option_key,
                    )
            else:
                raise ValueError("guided choice phase is unavailable")
            choice_ref = self._opaque_choice_ref(
                item_ref=target.item_ref,
                option_key=option_key,
                target_refs=action.target_refs,
            )
            self._choice_actions[choice_ref] = (
                target.item_ref,
                action,
                choice_guidance,
            )
            result.append(
                {
                    "choice_ref": choice_ref,
                    "label": choice_guidance.label,
                    "explanation": choice_guidance.explanation,
                    "consequence": choice_guidance.consequence,
                    "blocks_authoring": choice_guidance.blocks_authoring,
                }
            )
        return result

    def resolve_choice(
        self,
        *,
        item_ref: str,
        choice_ref: str,
    ) -> ReviewAction:
        self._refresh_state_projection()
        if type(item_ref) is not str or item_ref not in self._target_by_ref:
            raise ValueError("guided item ref is invalid")
        if type(choice_ref) is not str:
            raise TypeError("guided choice ref must be an exact string")
        target = self._target_by_ref[item_ref]
        if not self._is_unresolved(target):
            raise ValueError("guided item is no longer unresolved")
        if choice_ref not in self._choice_actions:
            self._project_target(target, wrapped=False)
        try:
            owner_ref, action, _ = self._choice_actions[choice_ref]
        except KeyError as exc:
            raise ValueError("guided choice ref is invalid") from exc
        if owner_ref != item_ref:
            raise ValueError("guided choice belongs to a different item")
        return action

    def preview_choice(
        self,
        *,
        item_ref: str,
        choice_ref: str,
    ) -> Mapping[str, object]:
        action = self.resolve_choice(
            item_ref=item_ref,
            choice_ref=choice_ref,
        )
        _, _, guidance = self._choice_actions[choice_ref]
        preview = self.session.preview(action)
        return MappingProxyType(
            {
                "preview_hash": preview.preview_hash,
                "state_revision": preview.state_revision,
                "decision_summary": (
                    f"{guidance.label}. {guidance.explanation}"
                ),
                "affected_count": len(preview.affected_refs),
                "cleared_count": len(preview.cleared_refs),
                "affected_refs": list(preview.affected_refs),
                "cleared_refs": list(preview.cleared_refs),
                "requires_clear_confirmation": (
                    preview.requires_clear_confirmation
                ),
                "resulting_counts": dict(preview.resulting_counts),
                "blocks_authoring": guidance.blocks_authoring,
            }
        )

    def iter_current_items(self) -> tuple[Mapping[str, object], ...]:
        self._refresh_state_projection()
        unresolved = [
            target for target in self._targets if self._is_unresolved(target)
        ]
        if not unresolved:
            return ()
        phase = unresolved[0].phase
        return tuple(
            self._project_target(target, wrapped=False)
            for target in unresolved
            if target.phase == phase
        )

    def designation_cohort_items(self) -> tuple[Mapping[str, object], ...]:
        result: list[Mapping[str, object]] = []
        exceptions = self.session.indexes.designation_exception_case_refs
        for cohort_ref, refs in sorted(
            self.session.indexes.routine_designation_cohorts.items()
        ):
            if len(refs) > MAX_GUIDED_TARGET_REFS:
                raise ValueError("guided designation cohort exceeds its bound")
            if exceptions.intersection(refs):
                raise ValueError("guided designation cohort contains an exception")
            examples = [
                self.session.indexes.designation_rows_by_case[case_ref][
                    "surface"
                ]
                for case_ref in refs[:MAX_GUIDED_EXAMPLES]
            ]
            result.append(
                MappingProxyType(
                    {
                        "phase": "designation",
                        "item_ref": _item_ref(
                            phase="designation",
                            row_kind="designation_cohort",
                            source_ref=cohort_ref,
                        ),
                        "cohort": {
                            "cohort_ref": cohort_ref,
                            "member_count": len(refs),
                            "target_refs": list(refs),
                            "representative_examples": examples,
                        },
                    }
                )
            )
        return tuple(result)

    def _project_export(self, *, wrapped: bool) -> Mapping[str, object]:
        bootstrap = self.session.bootstrap()
        return MappingProxyType(
            {
                "item_ref": self._export_ref,
                "phase": "export",
                "primary_action": "validate_and_export",
                "review_complete": bootstrap["review_complete"],
                "authoring_ready": bootstrap["authoring_ready"],
                "blocking_rejection_refs": bootstrap[
                    "blocking_rejection_refs"
                ],
                "wrapped": wrapped,
            }
        )

    def next_item(
        self,
        *,
        after_item_ref: str | None,
    ) -> Mapping[str, object]:
        self._refresh_state_projection()
        if not self._state_by_ref["reviewer_refs"]:
            return self._project_identity()
        if after_item_ref is None:
            start = 0
        else:
            if after_item_ref not in self._ordered_refs:
                raise ValueError("guided after-item ref is invalid")
            start = self._ordered_refs.index(after_item_ref) + 1
        total = len(self._ordered_refs)
        for offset in range(total):
            index = (start + offset) % total
            ref = self._ordered_refs[index]
            wrapped = start > 0 and index < start
            if ref == self._export_ref:
                continue
            target = self._target_by_ref[ref]
            if self._is_unresolved(target):
                return self._project_target(target, wrapped=wrapped)
        return self._project_export(wrapped=start >= total)
