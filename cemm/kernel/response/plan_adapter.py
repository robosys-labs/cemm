"""Adapter from the current v3.4 message model to canonical v3.4.3 plans.

This is a one-way migration boundary.  It exists only during cutover and must be
deleted once the canonical planner emits model.emission.SemanticMessagePlan
directly.
"""
from __future__ import annotations

from ..model.emission import (
    PlannedClause,
    SemanticMessagePlan,
    SemanticRoleValue,
    UseMode,
)


_USE_MODES = {
    "assert": UseMode.ASSERT,
    "qualified": UseMode.QUALIFIED,
    "probe": UseMode.PROBE,
    "mention": UseMode.MENTION,
    "quote": UseMode.QUOTE,
}


def adapt_message_plan(plan) -> SemanticMessagePlan:
    clauses: list[PlannedClause] = []
    content_items = tuple(getattr(plan, "content_items", ()) or ())
    for item in content_items:
        item_provenance = tuple(getattr(item, "provenance_refs", ()) or ())
        for source_clause in tuple(getattr(item, "clauses", ()) or ()):
            role_values = tuple(
                SemanticRoleValue(
                    role_key=getattr(role, "role_key", ""),
                    value_ref=(
                        getattr(role, "semantic_ref", "")
                        or getattr(role, "value_ref", "")
                    ),
                    value_kind=getattr(role, "value_kind", "referent"),
                    semantic_key=getattr(role, "semantic_key", ""),
                    surface_hint=getattr(role, "surface_hint", ""),
                    use_mode=_USE_MODES.get(
                        getattr(role, "use_mode", "assert"),
                        UseMode.ASSERT,
                    ),
                    provenance_refs=tuple(
                        getattr(role, "provenance_refs", ()) or ()
                    ),
                )
                for role in tuple(getattr(source_clause, "role_values", ()) or ())
                if getattr(role, "role_key", "")
            )
            clauses.append(
                PlannedClause(
                    clause_id=(
                        getattr(source_clause, "clause_ref", "")
                        or getattr(source_clause, "id", "")
                    ),
                    predicate_key=getattr(source_clause, "predicate_key", ""),
                    roles=role_values,
                    communicative_force=getattr(
                        source_clause, "communicative_force", "assert"
                    ),
                    polarity=getattr(source_clause, "polarity", "positive"),
                    modality=getattr(source_clause, "modality", "actual"),
                    context_ref=getattr(source_clause, "context_ref", ""),
                    valid_time_ref=getattr(source_clause, "valid_time_ref", ""),
                    qualification_key=getattr(
                        source_clause, "qualification_key", ""
                    ),
                    required=bool(getattr(source_clause, "required", True)),
                    provenance_refs=tuple(
                        dict.fromkeys(
                            (
                                *item_provenance,
                                *tuple(
                                    getattr(
                                        source_clause,
                                        "provenance_refs",
                                        (),
                                    )
                                    or ()
                                ),
                            )
                        )
                    ),
                )
            )

    return SemanticMessagePlan(
        plan_id=getattr(plan, "id", "") or getattr(plan, "plan_id", ""),
        clauses=tuple(clauses),
        language_tag=getattr(plan, "language", "und"),
        channel=getattr(plan, "channel", "text"),
        addressee_refs=tuple(getattr(plan, "addressee_refs", ()) or ()),
        goal_refs=tuple(
            getattr(plan, "communicative_goal_refs", ())
            or getattr(plan, "goal_refs", ())
            or ()
        ),
        provenance_refs=tuple(
            dict.fromkeys(
                ref
                for item in content_items
                for ref in tuple(getattr(item, "provenance_refs", ()) or ())
            )
        ),
    )
