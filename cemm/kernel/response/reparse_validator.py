"""ReparseValidator — generated content reparses into compatible candidates.

Import boundary: model submodules only. No engine imports.

Architectural guardrails (AGENTS.md §19):
- Generated content should round-trip into compatible semantic candidates
  under the same language pack.
- Generated content reparses compatibly.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ..model.message import SemanticMessagePlan, MessageContentItem


@dataclass(frozen=True, slots=True)
class ReparseResult:
    """Result of reparse validation.

    Generated content should round-trip into compatible semantic
    candidates under the same language pack.
    """
    is_compatible: bool
    original_item_count: int = 0
    reparsed_item_count: int = 0
    mismatched_refs: tuple[str, ...] = ()
    detail: str = ""


class ReparseValidator:
    """Validates that generated content reparses compatibly.

    Generated content should round-trip into compatible semantic
    candidates under the same language pack.

    In a full implementation, this would:
    1. Take the realized surface text
    2. Feed it back through the language adapter
    3. Compare the resulting semantic candidates with the original plan

    Here we provide the structure and interface for this validation.
    """

    def validate_reparse(
        self,
        original_plan: SemanticMessagePlan,
        reparsed_plan: SemanticMessagePlan,
    ) -> ReparseResult:
        """Validate that a reparsed plan is compatible with the original.

        Compares semantic refs and discourse functions between the
        original and reparsed plans.
        """
        original_refs = {item.semantic_ref for item in original_plan.content_items}
        reparsed_refs = {item.semantic_ref for item in reparsed_plan.content_items}

        # Check that all original refs are present in reparsed
        missing = original_refs - reparsed_refs
        if missing:
            return ReparseResult(
                is_compatible=False,
                original_item_count=len(original_plan.content_items),
                reparsed_item_count=len(reparsed_plan.content_items),
                mismatched_refs=tuple(missing),
                detail=f"reparsed plan is missing {len(missing)} semantic refs from original",
            )

        # Check discourse function compatibility
        original_fns = {
            item.semantic_ref: item.discourse_function
            for item in original_plan.content_items
        }
        reparsed_fns = {
            item.semantic_ref: item.discourse_function
            for item in reparsed_plan.content_items
        }

        mismatched: list[str] = []
        for ref, fn in original_fns.items():
            reparsed_fn = reparsed_fns.get(ref)
            if reparsed_fn is not None and reparsed_fn != fn:
                mismatched.append(ref)

        if mismatched:
            return ReparseResult(
                is_compatible=False,
                original_item_count=len(original_plan.content_items),
                reparsed_item_count=len(reparsed_plan.content_items),
                mismatched_refs=tuple(mismatched),
                detail="discourse functions do not match",
            )

        return ReparseResult(
            is_compatible=True,
            original_item_count=len(original_plan.content_items),
            reparsed_item_count=len(reparsed_plan.content_items),
        )

    def check_round_trip(
        self,
        original_plan: SemanticMessagePlan,
        surface_text: str,
        reparse_fn: Any,
    ) -> ReparseResult:
        """Check that surface text reparses into a compatible plan.

        The reparse_fn is a callable that takes surface text and returns
        a SemanticMessagePlan. This is provided by the language adapter.
        """
        try:
            reparsed = reparse_fn(surface_text)
        except Exception as e:
            return ReparseResult(
                is_compatible=False,
                detail=f"reparse failed: {e}",
            )

        return self.validate_reparse(original_plan, reparsed)
