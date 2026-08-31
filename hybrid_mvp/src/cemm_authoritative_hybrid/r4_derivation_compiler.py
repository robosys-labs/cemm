"""Pure reviewed-blueprint compilation for R4.1 supervision."""
from __future__ import annotations

from dataclasses import dataclass

from .expressions import SemanticExpression
from .programs import ProgramAction, SemanticSwitchProgram, SourceAssignment
from .proposal_context import ProposalContext
from .r4_expansion import ExpandedCase
from .r4_supervision import (
    DerivationBlueprint,
    GroundedSelectorBinding,
    StructuralSelectorBinding,
)
from .verifier_reconstruction import reconstruct_expected_expression


@dataclass(frozen=True)
class CompiledReviewedDerivation:
    program: SemanticSwitchProgram
    expression: SemanticExpression
    assigned_source_unit_refs: tuple[str, ...]
    residual_source_unit_refs: tuple[str, ...]
    operation_count: int


class DerivationCompilationError(ValueError):
    """A reviewed blueprint cannot reconstruct its source-owned expression."""


class ReviewedDerivationCompiler:
    """Compile one reviewed blueprint without invoking a runtime compiler."""

    def compile(
        self,
        *,
        case: ExpandedCase,
        context: ProposalContext,
        blueprint: DerivationBlueprint,
    ) -> CompiledReviewedDerivation:
        if type(case) is not ExpandedCase or type(context) is not ProposalContext:
            raise TypeError("reviewed derivation requires exact case and context")
        if type(blueprint) is not DerivationBlueprint:
            raise TypeError("blueprint must be exact DerivationBlueprint")
        try:
            return self._compile_checked(case=case, context=context, blueprint=blueprint)
        except DerivationCompilationError:
            raise
        except (IndexError, KeyError, TypeError, ValueError) as exc:
            raise DerivationCompilationError(
                "reviewed derivation violates exact Program reconstruction"
            ) from exc

    def _compile_checked(
        self,
        *,
        case: ExpandedCase,
        context: ProposalContext,
        blueprint: DerivationBlueprint,
    ) -> CompiledReviewedDerivation:
        if context.revision_pin != case.contract.revision_pin:
            raise DerivationCompilationError("case and context revisions differ")
        assignment_blueprint = blueprint.source_assignment_blueprint
        if assignment_blueprint.observed_source_unit_refs != context.source_unit_refs:
            raise DerivationCompilationError(
                "source assignments do not equal the immutable context units"
            )
        assignments_by_unit = {
            row.source_unit_ref: row for row in assignment_blueprint.assignments
        }
        if len(assignments_by_unit) != len(context.source_unit_refs):
            raise DerivationCompilationError(
                "every observed source unit must be assigned exactly once"
            )

        selectors = {
            row.selector_handle: row for row in blueprint.selector_bindings
        }
        if len(selectors) != len(blueprint.selector_bindings):
            raise DerivationCompilationError("blueprint selector handles are not unique")
        operation_count = len(selectors)
        for selector in blueprint.selector_bindings:
            if type(selector) is GroundedSelectorBinding:
                self._validate_grounded_selector(
                    selector=selector,
                    case=case,
                    context=context,
                    assignments_by_unit=assignments_by_unit,
                )
            elif type(selector) is StructuralSelectorBinding:
                if (
                    selector.selector_kind == "context_slot"
                    and selector.value_ref != context.context_ref
                ):
                    raise DerivationCompilationError(
                        "blueprint selects a different proposal context"
                    )
                if selector.selector_kind == "mode_slot" and context.mode_slot(
                    selector.value_ref
                ) is None:
                    raise DerivationCompilationError(
                        "blueprint selects an unknown mode slot"
                    )
            else:
                raise DerivationCompilationError("unknown selector binding type")

        action_sources: dict[int, list[str]] = {
            index: [] for index in range(len(blueprint.actions))
        }
        for row in assignment_blueprint.assignments:
            if row.target_action_index is not None:
                action_sources[row.target_action_index].append(row.source_unit_ref)
        actions = tuple(
            ProgramAction.create(
                action_index=row.action_index,
                action_type=row.action_type,
                arguments=tuple(
                    selectors[handle].value_ref for handle in row.selector_handles
                ),
                source_unit_refs=tuple(action_sources[row.action_index]),
            )
            for row in blueprint.actions
        )
        operation_count += len(actions)
        assignment_rows = tuple(
            SourceAssignment.create(
                source_unit_ref=row.source_unit_ref,
                contribution_slot_ref=row.contribution_slot_ref,
                assignment_kind=row.assignment_kind,
                target_action_ref=(
                    None
                    if row.target_action_index is None
                    else actions[row.target_action_index].action_ref
                ),
                target_role_ref=row.target_role_ref,
                residual_kind=row.residual_kind,
                critical=row.critical,
            )
            for row in assignment_blueprint.assignments
        )
        operation_count += len(assignment_rows)
        mode_actions = tuple(
            row for row in actions if row.action_type == "select_mode"
        )
        if len(mode_actions) != 1:
            raise DerivationCompilationError(
                "reviewed derivation requires one exact mode action"
            )
        program = SemanticSwitchProgram.create(
            orientation_ref=context.orientation_ref,
            proposal_context_ref=context.context_ref,
            actions=actions,
            root_refs=blueprint.root_local_refs,
            mode_slot_ref=mode_actions[0].arguments[0],
            goal_refs=(),
            source_unit_refs=assignment_blueprint.observed_source_unit_refs,
            source_assignments=assignment_rows,
            revision_pin=context.revision_pin,
        )
        expression = reconstruct_expected_expression(program, context)
        if (
            expression is None
            or expression.expression_ref != blueprint.expected_expression_ref
        ):
            raise DerivationCompilationError(
                "blueprint does not reconstruct expected expression"
            )
        expected = {
            row.expression_ref: row for row in case.contract.expected_expressions
        }
        if expected.get(expression.expression_ref) != expression:
            raise DerivationCompilationError(
                "compiled expression differs from source truth"
            )
        residuals = tuple(
            row.source_unit_ref
            for row in assignment_rows
            if row.assignment_kind == "residual"
        )
        return CompiledReviewedDerivation(
            program=program,
            expression=expression,
            assigned_source_unit_refs=tuple(
                row.source_unit_ref for row in assignment_rows
            ),
            residual_source_unit_refs=residuals,
            operation_count=operation_count,
        )

    @staticmethod
    def _validate_grounded_selector(
        *,
        selector: GroundedSelectorBinding,
        case: ExpandedCase,
        context: ProposalContext,
        assignments_by_unit: dict[str, object],
    ) -> None:
        if (
            selector.source_case_ref != case.case_ref
            or selector.surface_ref != case.surface_ref
        ):
            raise DerivationCompilationError(
                "grounded selector crosses its exact case or surface"
            )
        lookup_name = {
            "designation_slot": "designation",
            "frame_slot": "frame",
            "contribution_slot": "contribution",
            "reference_slot": "reference",
            "scope_slot": "scope",
            "expression_link_slot": "expression_link",
            "variable_slot": "variable",
            "transition_slot": "transition",
        }[selector.selector_kind]
        component = getattr(context, lookup_name)(selector.graph_component_ref)
        if component is None:
            raise DerivationCompilationError(
                "grounded selector graph component is absent from context"
            )

        if selector.source_selector_kind == "source_unit":
            assignment = assignments_by_unit.get(selector.source_selector_ref)
            if assignment is None:
                raise DerivationCompilationError(
                    "grounded source unit is not owned by an assignment"
                )
            source_unit_refs = (selector.source_selector_ref,)
        else:
            matches = tuple(
                row
                for row in assignments_by_unit.values()
                if row.contribution_slot_ref == selector.source_selector_ref
            )
            if len(matches) != 1:
                raise DerivationCompilationError(
                    "grounded contribution is not owned by one assignment"
                )
            contribution = context.contribution(selector.source_selector_ref)
            if contribution is None:
                raise DerivationCompilationError(
                    "grounded contribution is absent from context"
                )
            source_unit_refs = contribution.source_unit_refs

        spans_by_unit = {
            unit_ref: (start, end)
            for unit_ref, start, end in context.source_unit_spans
        }
        expected_spans = tuple(spans_by_unit[unit_ref] for unit_ref in source_unit_refs)
        actual_spans = tuple((row.start, row.end) for row in selector.spans)
        if actual_spans != expected_spans or any(
            start < 0 or end <= start or end > len(case.surface)
            for start, end in actual_spans
        ):
            raise DerivationCompilationError(
                "grounded selector span differs from immutable context geometry"
            )
        kind = getattr(component, "target_kind", None) or getattr(
            component, "predicate_kind", None
        )
        if kind is not None and selector.semantic_kind_ref != f"semantic_kind:{kind}":
            raise DerivationCompilationError(
                "grounded selector semantic kind differs from context"
            )


__all__ = [
    "CompiledReviewedDerivation",
    "DerivationCompilationError",
    "ReviewedDerivationCompiler",
]
