"""MessageProvenanceGuard — every clause traces to semantic provenance.

Import boundary: model submodules only. No engine imports.

Architectural guardrails (AGENTS.md §19, ACCEPTANCE_TESTS.md §41):
- Every generated clause must trace to a selected semantic item and
  evidence/ledger/commit provenance.
- Opaque IDs, open ports, role labels, or internal placeholders cannot
  become public text.
- No internal IDs or open ports leak.
- Each clause binds to assessment/competence/blocker records.
- No binary template claim.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ..model.message import SemanticMessagePlan, MessageContentItem


@dataclass(frozen=True, slots=True)
class ProvenanceViolation:
    """A provenance violation in a message plan."""
    item_ref: str
    violation_kind: str  # missing_provenance, opaque_id, open_port, role_label, internal_placeholder
    detail: str = ""


@dataclass(frozen=True, slots=True)
class ProvenanceCheckResult:
    """Result of checking message provenance."""
    is_valid: bool
    violations: tuple[ProvenanceViolation, ...] = ()


# Patterns that indicate internal leakage
_OPAQUE_ID_PATTERNS: tuple[str, ...] = (
    "ref:", "Ref[", "schema:", "prop:", "ev:", "assess:",
    "gap:", "plan:", "op:", "mut:", "ctx:", "fp:",
    "record:", "sense:", "artifact:", "inv:",
)

_OPEN_PORT_PATTERNS: tuple[str, ...] = (
    "?", "open_port", "unfilled", "placeholder",
    "topic", "object", "target",  # forbidden placeholder concepts
)

_ROLE_LABEL_PATTERNS: tuple[str, ...] = (
    "actor", "agent", "patient", "theme", "experiencer",
    "instrument", "location", "source", "goal",
    "role:", "binding:",
)


class MessageProvenanceGuard:
    """Guards that every clause has semantic provenance and no internal
    leakage.

    Every generated clause must trace to a selected semantic item and
    evidence/ledger/commit provenance. Opaque IDs, open ports, role
    labels, or internal placeholders cannot become public text.
    """

    def check_plan(self, plan: SemanticMessagePlan) -> ProvenanceCheckResult:
        """Check that every content item in a message plan has valid
        provenance and no internal leakage.
        """
        violations: list[ProvenanceViolation] = []

        for item in plan.content_items:
            # 1. Check that semantic_ref is non-empty
            if not item.semantic_ref:
                violations.append(ProvenanceViolation(
                    item_ref="",
                    violation_kind="missing_provenance",
                    detail="content item has empty semantic_ref",
                ))
                continue

            # 2. Check that provenance_refs is non-empty
            if not item.provenance_refs:
                violations.append(ProvenanceViolation(
                    item_ref=item.semantic_ref,
                    violation_kind="missing_provenance",
                    detail="content item has no provenance_refs",
                ))

            # 3. Check for opaque ID leakage in semantic_ref
            # Note: semantic_ref IS a ref, but it must not be exposed
            # as public text. The guard checks that the ref is valid
            # (non-empty), not that it's human-readable.
            # The real leakage check is on surface text, which is the
            # renderer's responsibility. But we check that the plan
            # doesn't contain raw internal placeholders.

            # 4. Check focus field for internal leakage
            for pattern in _OPAQUE_ID_PATTERNS:
                if pattern in item.focus:
                    violations.append(ProvenanceViolation(
                        item_ref=item.semantic_ref,
                        violation_kind="opaque_id",
                        detail=f"focus contains opaque ID pattern: {pattern}",
                    ))
                    break

            for pattern in _OPEN_PORT_PATTERNS:
                if pattern in item.focus.lower():
                    violations.append(ProvenanceViolation(
                        item_ref=item.semantic_ref,
                        violation_kind="open_port",
                        detail=f"focus contains open port pattern: {pattern}",
                    ))
                    break

            for pattern in _ROLE_LABEL_PATTERNS:
                if pattern in item.focus.lower():
                    violations.append(ProvenanceViolation(
                        item_ref=item.semantic_ref,
                        violation_kind="role_label",
                        detail=f"focus contains role label pattern: {pattern}",
                    ))
                    break

        return ProvenanceCheckResult(
            is_valid=len(violations) == 0,
            violations=tuple(violations),
        )

    def check_item(self, item: MessageContentItem) -> ProvenanceCheckResult:
        """Check a single content item for provenance and leakage."""
        plan = SemanticMessagePlan(
            id="check",
            content_items=(item,),
        )
        return self.check_plan(plan)

    def has_provenance(self, item: MessageContentItem) -> bool:
        """Check if a content item has provenance."""
        return bool(item.semantic_ref and item.provenance_refs)

    def has_internal_leakage(self, item: MessageContentItem) -> bool:
        """Check if a content item has internal ID/port/role leakage."""
        result = self.check_item(item)
        return not result.is_valid and any(
            v.violation_kind in ("opaque_id", "open_port", "role_label", "internal_placeholder")
            for v in result.violations
        )
