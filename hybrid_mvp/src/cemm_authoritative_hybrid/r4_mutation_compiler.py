"""Pure compilation of reviewed R4.1 mutation contracts."""
from __future__ import annotations

import copy

from .r3_codec import freeze_json, thaw_json
from .r4_contracts import SourceDisposition
from .r4_expansion import ExpandedCase
from .r4_mutations import SemanticMutation
from .r4_supervision import MutationContract


class MutationCompilationError(ValueError):
    """A reviewed mutation cannot be applied to its exact source case."""


def resolve_exact_json_path(
    payload: object, path: tuple[str | int, ...]
) -> object:
    """Resolve one already-bounded path without coercion or key creation."""

    current = payload
    for component in path:
        if type(component) is str:
            if type(current) is not dict or component not in current:
                raise MutationCompilationError(
                    "reviewed mutation path does not resolve exactly"
                )
            current = current[component]
        else:
            if (
                type(component) is not int
                or type(current) is not list
                or component < 0
                or component >= len(current)
            ):
                raise MutationCompilationError(
                    "reviewed mutation path does not resolve exactly"
                )
            current = current[component]
    return current


def replace_exact_json_path(
    payload: object,
    path: tuple[str | int, ...],
    replacement: object,
) -> None:
    """Replace one existing leaf while preserving all other source bytes."""

    if not path:
        raise MutationCompilationError("reviewed mutation path is empty")
    parent = resolve_exact_json_path(payload, path[:-1]) if len(path) > 1 else payload
    leaf = path[-1]
    if type(leaf) is str:
        if type(parent) is not dict or leaf not in parent:
            raise MutationCompilationError(
                "reviewed mutation replacement target does not exist"
            )
        parent[leaf] = replacement
        return
    if (
        type(leaf) is not int
        or type(parent) is not list
        or leaf < 0
        or leaf >= len(parent)
    ):
        raise MutationCompilationError(
            "reviewed mutation replacement target does not exist"
        )
    parent[leaf] = replacement


def render_json_path(path: tuple[str | int, ...]) -> str:
    """Render the canonical tuple path used by Semantic Mutation ABI 2."""

    rendered = ""
    for component in path:
        if type(component) is int:
            rendered += f"[{component}]"
        else:
            rendered += ("." if rendered else "") + component
    return rendered


def _is_applicable(case: ExpandedCase, contract: MutationContract) -> bool:
    if case.source_disposition is SourceDisposition.RESTART_DIAGNOSTIC_CANDIDATE:
        return False
    kind = contract.applicability_ref.removeprefix("mutation_applicability:")
    constraints = case.contract.situation_constraints
    if kind == "semantic_expression":
        return bool(case.contract.expected_expressions)
    if kind == "permission_required":
        return "permission:set_state" in constraints.get("permission_refs", ())
    if kind == "adapter_required":
        return "adapter:state" in constraints.get("adapter_refs", ())
    if kind == "all_supervised":
        return True
    raise MutationCompilationError("unknown reviewed mutation applicability")


class ReviewedMutationCompiler:
    """Compile source-owned mutation truth without an implementation oracle."""

    def compile(
        self, *, case: ExpandedCase, contract: MutationContract
    ) -> SemanticMutation:
        if type(case) is not ExpandedCase or type(contract) is not MutationContract:
            raise TypeError("reviewed mutation requires exact case and contract")
        if contract.source_case_ref != case.case_ref:
            raise MutationCompilationError(
                "mutation contract belongs to another case"
            )
        if contract.selector_kind != "json_path" or contract.operation != "replace":
            raise MutationCompilationError(
                "mutation contract uses an unsupported selector or operation"
            )
        if not _is_applicable(case, contract):
            raise MutationCompilationError(
                "mutation contract is inapplicable to its source case"
            )
        dimension_prefix = "mutation_dimension:"
        if not contract.changed_dimension_ref.startswith(dimension_prefix):
            raise MutationCompilationError(
                "mutation dimension is not a canonical reviewed ref"
            )
        dimension = contract.changed_dimension_ref.removeprefix(dimension_prefix)
        if contract.mutation_family_ref != f"mutation_family:{dimension}":
            raise MutationCompilationError(
                "mutation family and changed dimension disagree"
            )
        path_owner = contract.changed_path[:1]
        if (
            (contract.scope == "contract" and path_owner != ("contract",))
            or (
                contract.scope == "environment"
                and path_owner != ("environment",)
            )
            or (
                contract.scope == "persistence"
                and contract.changed_path[:2] != ("contract", "revision_pin")
            )
        ):
            raise MutationCompilationError(
                "mutation scope does not own its changed path"
            )

        payload = copy.deepcopy(case.as_dict())
        if type(payload) is not dict:
            raise MutationCompilationError("expanded case did not emit an exact object")
        before = resolve_exact_json_path(payload, contract.changed_path)
        if freeze_json(before) != contract.expected_before:
            raise MutationCompilationError("reviewed mutation before-value drift")
        replacement = thaw_json(contract.replacement_after)
        replace_exact_json_path(payload, contract.changed_path, replacement)
        after = resolve_exact_json_path(payload, contract.changed_path)
        if freeze_json(after) != contract.replacement_after:
            raise MutationCompilationError("reviewed mutation after-value drift")

        return SemanticMutation.create(
            parent_case_ref=case.case_ref,
            parent_contract_ref=case.contract.contract_ref,
            scope=contract.scope,
            dimension=dimension,
            changed_path=render_json_path(contract.changed_path),
            before=before,
            after=after,
            mutated_case=payload,
            expected_earliest_owner=contract.expected_earliest_owner,
            expected_status=contract.expected_status,
            expected_error_code=contract.expected_error_code,
            lineage_refs=(
                case.case_ref,
                case.contract.contract_ref,
                contract.mutation_family_ref,
            ),
            review_refs=contract.review_refs,
        )


__all__ = [
    "MutationCompilationError",
    "ReviewedMutationCompiler",
    "render_json_path",
    "replace_exact_json_path",
    "resolve_exact_json_path",
]
